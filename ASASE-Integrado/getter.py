"""Getter NASA POWER + SMAP + SoilGrids, adaptado del código proporcionado.

    start_date y end_date son INCLUSIVAS, también para una consulta de un día.
    POINT: [lat, lon]. BBOX: [min_lat, min_lon, max_lat, max_lon].
    En BBOX, POWER representa el centro; SMAP/SoilGrids promedian el área.
"""
from datetime import timedelta
import json
import logging
import math
import os
from pathlib import Path
from threading import Lock

import numpy as np
import pandas as pd
import requests

from errores import DatosInsuficientes, ErrorConfiguracion, ErrorFuente
from validacion import validar_consulta

LOG = logging.getLogger(__name__)
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_COLUMNAS = {
    "T2M": "temp_media_C", "T2M_MIN": "temp_min_C", "T2M_MAX": "temp_max_C",
    "PRECTOTCORR": "precipitacion_mm", "ALLSKY_SFC_SW_DWN": "radiacion_solar_MJ_m2",
}
SMAP_COLUMNAS = {"sm_surface": "humedad_suelo_smap_m3m3",
                 "sm_rootzone": "humedad_raiz_smap_m3m3", "soil_temp_layer1": "temp_suelo_smap_C"}
_EE = None
_LOCK = Lock()


def clasificar_textura_usda(arcilla, limo, arena):
    """Mismas reglas y etiquetas del getter del usuario."""
    valores = [arcilla, limo, arena]
    if any(v is None or not math.isfinite(v) or v < 0 for v in valores):
        return "Desconocida"
    total = sum(valores)
    if total <= 0:
        return "Desconocida"
    c, si, sa = [v / total * 100 for v in valores]
    if si + 1.5 * c < 15:
        return "Arenosa (Sand)"
    elif si + 2 * c < 30:
        return "Areno-francosa (Loamy Sand)"
    elif (7 <= c < 20 and sa > 52 and si + 2*c >= 30) or (c < 7 and si < 50 and si + 2*c >= 30):
        return "Franco-arenosa (Sandy Loam)"
    elif 7 <= c < 27 and 28 <= si < 50 and sa <= 52:
        return "Franca (Loam)"
    elif (si >= 50 and 12 <= c < 27) or (50 <= si < 80 and c < 12):
        return "Franco-limosa (Silt Loam)"
    elif si >= 80 and c < 12:
        return "Limosa (Silt)"
    elif 20 <= c < 35 and si < 28 and sa > 45:
        return "Franco-arcillo-arenosa (Sandy Clay Loam)"
    elif 27 <= c < 40 and 20 < sa <= 45:
        return "Franco-arcillosa (Clay Loam)"
    elif 27 <= c < 40 and sa <= 20:
        return "Franco-arcillo-limosa (Silty Clay Loam)"
    elif c >= 35 and sa > 45:
        return "Arcillo-arenosa (Sandy Clay)"
    elif c >= 40 and si >= 40:
        return "Arcillo-limosa (Silty Clay)"
    elif c >= 40 and sa <= 45 and si < 40:
        return "Arcillosa (Clay)"
    return "Franca (Loam)"


def cargar_cuenta_servicio():
    """Lee el secreto solo en el servidor; el JSON en memoria tiene prioridad."""
    contenido = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")
    archivo = os.environ.get("GEE_SERVICE_ACCOUNT_FILE")
    if contenido is None and archivo is None:
        return None
    if contenido is None:
        try:
            contenido = Path(archivo).read_text(encoding="utf-8-sig")
        except (OSError, ValueError):
            raise ErrorConfiguracion("No se pudo leer GEE_SERVICE_ACCOUNT_FILE.") from None
    try:
        cuenta = json.loads(contenido)
    except (ValueError, TypeError):
        raise ErrorConfiguracion("GEE_SERVICE_ACCOUNT_JSON debe contener el JSON completo de Google Cloud, sin comillas adicionales ni Base64.") from None
    if not isinstance(cuenta, dict) or cuenta.get("type") != "service_account":
        raise ErrorConfiguracion("El JSON de Google Cloud debe ser de tipo service_account.")
    requeridos = ("project_id", "private_key_id", "private_key", "client_email", "token_uri")
    faltan = [campo for campo in requeridos if not isinstance(cuenta.get(campo), str) or not cuenta[campo].strip()]
    if faltan:
        raise ErrorConfiguracion("Faltan campos en el JSON de Google Cloud: " + ", ".join(faltan))
    # No permitir un destino de intercambio de tokens distinto al de Google.
    if cuenta["token_uri"] != "https://oauth2.googleapis.com/token":
        raise ErrorConfiguracion("token_uri debe ser https://oauth2.googleapis.com/token; utiliza el JSON original de Google Cloud.")
    return cuenta


def inicializar_ee():
    """Inicializa una vez; nunca abre un login interactivo dentro de la API."""
    global _EE
    with _LOCK:
        if _EE is not None:
            return _EE
        try:
            import ee
        except ImportError as exc:
            raise ErrorConfiguracion("Instalar earthengine-api con requirements.txt") from exc
        cuenta = cargar_cuenta_servicio()
        proyecto = os.environ.get("GEE_PROJECT_ID", "").strip() or (cuenta["project_id"] if cuenta else None)
        try:
            if cuenta is not None:
                credenciales = ee.ServiceAccountCredentials(key_data=json.dumps(cuenta))
                ee.Initialize(credentials=credenciales, project=proyecto)
            else:
                # Conserva la autenticación local/ADC cuando no hay JSON configurado.
                ee.Initialize(project=proyecto)
            ee.data.setDeadline(120_000)
        except Exception as exc:
            LOG.warning("No se pudo inicializar Earth Engine (%s)", type(exc).__name__)
            raise ErrorConfiguracion("Earth Engine no está autorizado. Revisa GEE_SERVICE_ACCOUNT_JSON, GEE_PROJECT_ID y el acceso del proyecto a Earth Engine.") from None
        _EE = ee
        return ee


def descargar_power(start_date, end_date, lat, lon):
    params = {"parameters": ",".join(POWER_COLUMNAS), "community": "AG",
              "longitude": lon, "latitude": lat, "start": start_date.replace("-", ""),
              "end": end_date.replace("-", ""), "format": "JSON", "time-standard": "UTC"}
    try:
        respuesta = requests.get(POWER_URL, params=params, timeout=(10, 60))
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except (requests.RequestException, ValueError) as exc:
        raise ErrorFuente("No se pudo descargar NASA POWER") from exc
    return parsear_power(contenido)


def parsear_power(contenido):
    try:
        datos = contenido["properties"]["parameter"]
        if not isinstance(datos, dict) or set(POWER_COLUMNAS) - set(datos):
            raise ValueError("Faltan parámetros POWER")
        df = pd.DataFrame({k: datos[k] for k in POWER_COLUMNAS})
        df.index = pd.to_datetime(df.index, format="%Y%m%d", errors="raise")
        df.index.name = "fecha"
        df = df.apply(pd.to_numeric, errors="raise")
        fill = contenido.get("header", {}).get("fill_value", -999)
        df = df.replace([fill, -999, -9999], np.nan)
        unidad = contenido.get("parameters", {}).get("ALLSKY_SFC_SW_DWN", {}).get("units")
        if unidad is not None and unidad.lower().replace(" ", "") not in {"mj/m^2/day", "mj/m2/day", "mj/m²/day"}:
            raise ValueError(f"Unidad de radiación inesperada: {unidad}")
        return df.rename(columns=POWER_COLUMNAS)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ErrorFuente("NASA POWER devolvió un esquema o unidades no compatibles") from exc


def construir_geometria(ee, point, bbox):
    if point is not None:
        return ee.Geometry.Point([point[1], point[0]])
    a, b, c, d = bbox
    return ee.Geometry.BBox(b, a, d, c)


def descargar_smap(ee, start_date, end_date, geometria):
    """Reduce cada día en servidor y descarga lotes de 31 filas.

    Evita getRegion con millones de valores para BBOX/períodos largos.
    SMAP es tridihorario: se exige presencia de sus 8 escenas por día.
    """
    inicio, fin = pd.Timestamp(start_date).date(), pd.Timestamp(end_date).date()
    fin_exclusivo = fin + timedelta(days=1)
    filas = []
    cursor = inicio
    try:
        while cursor < fin_exclusivo:
            hasta = min(cursor + timedelta(days=31), fin_exclusivo)
            col = (ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")
                   .filterDate(cursor.isoformat(), hasta.isoformat()).select(list(SMAP_COLUMNAS)))
            base = ee.Date(cursor.isoformat())

            def por_dia(offset):
                dia = base.advance(offset, "day")
                escenas = col.filterDate(dia, dia.advance(1, "day"))
                propiedades = ee.Dictionary(ee.Algorithms.If(
                    escenas.size().gt(0),
                    escenas.mean().reduceRegion(reducer=ee.Reducer.mean(), geometry=geometria,
                                                scale=9000, maxPixels=100_000_000),
                    ee.Dictionary({})))
                return ee.Feature(None, propiedades.set("fecha", dia.format("YYYY-MM-dd"))
                                  .set("escenas", escenas.size()))

            resultado = ee.FeatureCollection(ee.List.sequence(0, (hasta-cursor).days-1).map(por_dia)).getInfo()
            filas.extend(f["properties"] for f in resultado["features"])
            cursor = hasta
    except Exception as exc:
        raise ErrorFuente("No se pudo obtener SMAP de Earth Engine") from exc
    return parsear_smap(filas)


def parsear_smap(filas):
    if not filas:
        raise DatosInsuficientes("SMAP no devolvió datos")
    try:
        df = pd.DataFrame(filas)
        if "escenas" not in df or (df["escenas"].fillna(0) < 8).any():
            raise DatosInsuficientes("SMAP tiene días sin sus 8 escenas; consultar un período completo disponible")
        df["fecha"] = pd.to_datetime(df["fecha"], format="%Y-%m-%d", errors="raise")
        df = df.set_index("fecha").reindex(columns=list(SMAP_COLUMNAS))
        df = df.apply(pd.to_numeric, errors="raise").replace([-999, -9999], np.nan)
        df["soil_temp_layer1"] = df["soil_temp_layer1"] - 273.15
        return df.rename(columns=SMAP_COLUMNAS)
    except (ValueError, TypeError, KeyError) as exc:
        raise ErrorFuente("SMAP devolvió un formato no válido") from exc


def descargar_suelo(ee, geometria):
    # Se conserva la media entre las tres capas del getter recibido.
    # No cambiarla por ponderación por espesor altera su definición original.
    capas = ["0-5cm_mean", "5-15cm_mean", "15-30cm_mean"]
    imagenes = []
    try:
        for parametro, alias in [("phh2o", "ph"), ("soc", "soc"), ("clay", "clay"), ("sand", "sand"), ("silt", "silt")]:
            imagenes.append(ee.Image(f"projects/soilgrids-isric/{parametro}_mean")
                            .select([f"{parametro}_{c}" for c in capas])
                            .reduce(ee.Reducer.mean()).rename(alias))
        datos = ee.Image.cat(imagenes).reduceRegion(reducer=ee.Reducer.mean(), geometry=geometria,
                                                    scale=250, maxPixels=100_000_000).getInfo()
    except Exception as exc:
        raise ErrorFuente("No se pudo obtener SoilGrids de Earth Engine") from exc
    return parsear_suelo(datos)


def parsear_suelo(datos):
    def dividir(clave):
        valor = datos.get(clave)
        return float(valor) / 10 if valor is not None else np.nan
    try:
        return {"suelo_ph_0_30cm": dividir("ph"),
                "suelo_carbono_organico_g_kg": dividir("soc"),
                "suelo_textura_clase": clasificar_textura_usda(dividir("clay"), dividir("silt"), dividir("sand"))}
    except (ValueError, TypeError, AttributeError) as exc:
        raise ErrorFuente("SoilGrids devolvió valores no válidos") from exc


def get_tabla(start_date, end_date, point=None, bbox=None):
    inicio, fin, lat, lon, _ = validar_consulta(start_date, end_date, point, bbox)
    ee = inicializar_ee()
    geometria = construir_geometria(ee, point, bbox)
    power = descargar_power(start_date, end_date, lat, lon)
    smap = descargar_smap(ee, start_date, end_date, geometria)
    suelo = descargar_suelo(ee, geometria)
    # Join externo: un día ausente no desaparece antes de calcular sumas/medias.
    # El servicio rechazará nulos, duplicados y cualquier fecha fuera de rango.
    df = power.join(smap, how="outer")
    esperado = pd.date_range(inicio, fin, name="fecha")
    df = df.reindex(df.index.union(esperado))
    df.index.name = "fecha"
    for k, v in suelo.items():
        df[k] = v
    return df.sort_index()
