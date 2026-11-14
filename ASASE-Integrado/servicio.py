"""Puente getter -> agregación diaria -> motor IAC/rotación."""
from idiomas import tr
import hashlib
import json
from dataclasses import replace, asdict
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from errores import DatosInsuficientes
from getter import get_tabla
from iac import (PARAMETROS, Territorio, cargar_cultivos, calcular_iac,
                 recomendar_rotacion, validar_historial_ids, entero)
from validacion import validar_consulta, resolver_periodo

CATALOGO = cargar_cultivos(Path(__file__).with_name("cultivos.json"))


def agregar_tabla(tabla, start_date, end_date, point=None, bbox=None):
    """Fechas inclusivas. Devuelve Territorio y nº real de días representados."""
    inicio, fin, lat, lon, dias = validar_consulta(start_date, end_date, point, bbox)
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        raise DatosInsuficientes("El getter no ha devuelto una tabla diaria con datos")
    df = tabla.copy(deep=True)
    if df.columns.duplicated().any():
        raise DatosInsuficientes("Hay columnas duplicadas en la tabla")
    fechas = df.pop("fecha") if "fecha" in df.columns else df.index
    # No interpretar índices enteros como nanosegundos desde 1970.
    if pd.api.types.is_numeric_dtype(fechas):
        raise DatosInsuficientes("La tabla necesita un índice de fechas o columna fecha")
    try:
        indice = pd.DatetimeIndex(pd.to_datetime(fechas, errors="raise", utc=True))
    except (ValueError, TypeError) as exc:
        raise DatosInsuficientes("Fechas inválidas en la tabla") from exc
    if indice.isna().any() or not indice.equals(indice.normalize()):
        raise DatosInsuficientes("Se requiere una fila por día, a las 00:00 UTC")
    if indice.duplicated().any():
        raise DatosInsuficientes("Hay días duplicados; no se permite duplicar lluvia")
    df.index = indice.tz_localize(None)
    esperado = pd.date_range(inicio, fin, freq="D", name="fecha")
    faltan = esperado.difference(df.index)
    sobran = df.index.difference(esperado)
    if len(faltan) or len(sobran):
        raise DatosInsuficientes(f"Cobertura diaria incorrecta: faltan {len(faltan)} días y sobran {len(sobran)}")
    df = df.reindex(esperado)
    requeridas = list(PARAMETROS) + ["suelo_textura_clase"]
    ausentes = set(requeridas) - set(df.columns)
    for k in ausentes:
        df[k] = np.nan
    for k in PARAMETROS:
        if df[k].map(lambda v: isinstance(v, (bool, np.bool_))).any():
            raise DatosInsuficientes(f"{k} contiene booleanos")
        try:
            df[k] = pd.to_numeric(df[k], errors="raise")
        except (ValueError, TypeError) as exc:
            raise DatosInsuficientes(f"{k} contiene valores no numéricos") from exc
        df[k] = df[k].replace([-999, -9999, np.inf, -np.inf], np.nan)
    texturas = df["suelo_textura_clase"].fillna("Desconocida")
    conocidas = texturas[texturas != "Desconocida"]
    if not conocidas.empty:
        texturas = texturas.replace("Desconocida", conocidas.iloc[0])
    if not texturas.map(lambda v: isinstance(v, str) and bool(v.strip())).all() or texturas.nunique() != 1:
        raise DatosInsuficientes("La textura debe ser la misma cadena de texto durante todo el período")
    ubicacion = {"point": list(point) if point is not None else None,
                 "bbox": list(bbox) if bbox is not None else None}
    identificador = "parcela-" + hashlib.sha256(json.dumps(ubicacion, sort_keys=True).encode()).hexdigest()[:16]
    metadata = dict(id=identificador, nombre="Parcela consultada", latitud=lat, longitud=lon,
                    fecha=end_date, suelo_textura_clase=texturas.iloc[0], permitir_ausentes=True)
    # Validar cada día evita ocultar una humedad negativa o extremos incoherentes
    # mediante una media aparentemente válida.
    for fecha, fila in df.iterrows():
        try:
            Territorio(**{**metadata, "fecha": fecha.date().isoformat()},
                       **{k: float(fila[k]) if pd.notna(fila[k]) else None for k in PARAMETROS})
        except ValueError as exc:
            raise DatosInsuficientes(f"Dato inválido el {fecha.date()}: {exc}") from exc
    avisos = [tr(f"{k}: {int(df[k].count())}/{dias} días disponibles.", f"{k}: {int(df[k].count())}/{dias} days available.") for k in PARAMETROS if df[k].count() < dias]
    valores = {k: float(df[k].mean()) for k in PARAMETROS}
    valores["temp_min_C"] = float(df["temp_min_C"].min())
    valores["temp_max_C"] = float(df["temp_max_C"].max())
    valores["precipitacion_mm"] = float(df["precipitacion_mm"].sum(min_count=dias))
    valores = {k: (v if np.isfinite(v) else None) for k,v in valores.items()}
    if not any(v is not None for v in valores.values()):
        raise DatosInsuficientes("No hay ninguna variable numérica disponible")
    if df["precipitacion_mm"].count() < dias:
        avisos.append(tr("Precipitación excluida: el acumulado completo no se conoce; no se sustituye por cero.", "Precipitation excluded: the full accumulated total is unknown; it is not replaced with zero."))
    metadata["avisos_datos"] = tuple(avisos)
    return Territorio(**metadata, **valores), dias


def predecir(start_date, end_date=None, point=None, bbox=None, historial=None,
             accion="iac", cultivo_id=None, n_recomendaciones=3, *, getter=None, catalogo=None):
    """Mismos argumentos del getter + IDs históricos + acción.

    Sin cultivo_id, iac devuelve un mapa por ID de cultivo. Con cultivo_id,
    devuelve únicamente iac y razon. El historial no incluye el cultivo objetivo.
    getter puede inyectarse para integrar otra implementación o probar sin red.
    """
    entero(n_recomendaciones, "n_recomendaciones")
    end_date = resolver_periodo(start_date, end_date, accion)
    validar_consulta(start_date, end_date, point, bbox, permitir_largo=accion == "rotaciones")
    cat = CATALOGO if catalogo is None else catalogo
    if not cat:
        raise ValueError("Catálogo vacío")
    ids = validar_historial_ids([] if historial is None else historial, cat)
    if len(ids) > 100:
        raise ValueError("historial admite hasta 100 IDs")
    if accion not in {"iac", "rotaciones"}:
        raise ValueError("accion debe ser iac o rotaciones")
    if cultivo_id is not None:
        entero(cultivo_id, "cultivo_id")
        if cultivo_id not in cat:
            raise ValueError(f"Cultivo desconocido: {cultivo_id}")
        if accion != "iac":
            raise ValueError("cultivo_id solo se admite para la acción iac")
    referencia_inicio, referencia_fin = ("2025-01-01", "2025-12-31") if accion == "rotaciones" else (start_date, end_date)
    tabla = (getter or get_tabla)(referencia_inicio, referencia_fin, point, bbox)
    territorio, dias = agregar_tabla(tabla, referencia_inicio, referencia_fin, point, bbox)
    if accion == "iac":
        def evaluar(c):
            return calcular_iac(territorio, c, dias_precipitacion=dias, catalogo=cat, historial_ids=ids)
        if cultivo_id is not None:
            return evaluar(cat[cultivo_id])
        return {str(cid): evaluar(cat[cid]) for cid in sorted(cat)}
    # Repite el patrón mensual observado en 2025 para cada año de plantación.
    df = tabla.copy()
    if "fecha" in df.columns:
        df = df.set_index("fecha")
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    plantacion_inicio = pd.Timestamp(start_date)
    fin_exclusivo = pd.Timestamp(end_date) + pd.Timedelta(days=1)
    escenarios = {}
    mensuales = {}
    cursor = plantacion_inicio.replace(day=1)
    while cursor < fin_exclusivo:
        mes = cursor.month
        if mes not in mensuales:
            desde = pd.Timestamp(year=2025, month=mes, day=1)
            hasta = desde + pd.offsets.MonthEnd(0)
            mensuales[mes] = agregar_tabla(df.loc[desde:hasta], desde.date().isoformat(),
                                         hasta.date().isoformat(), point, bbox)
        t, n = mensuales[mes]
        escenarios[cursor.strftime("%Y-%m")] = {
            "territorio": asdict(replace(t, fecha=cursor.date().isoformat())),
            "dias_precipitacion": n,
        }
        cursor += pd.offsets.MonthBegin(1)
    planes = recomendar_rotacion(replace(territorio, fecha=start_date), cat,
                              dias_precipitacion=dias, historial_ids=ids,
                              escenarios=escenarios, fecha_fin=fin_exclusivo.date().isoformat(),
                              dias_entre_cultivos=0, n_recomendaciones=n_recomendaciones)
    for plan in planes:
        plan["periodo_plantacion"] = {"start_date": start_date, "end_date": end_date}
        plan["referencia"] = {"anio": 2025, "metodo": tr("Patrón mensual de 2025 repetido; no es un pronóstico.", "Repeated monthly pattern of 2025; this is not a forecast.")}
        plan["objetivo"] = tr("Maximizar días cultivados; desempatar por IAC. Búsqueda aproximada.", "Search prioritizes cropped days, breaking ties by IAC. Approximate search.")
        plan["porcentaje_ocupacion"] = round(100 * plan["dias_cultivados"] / plan["dias"], 2)
        plan["supuestos"].append(tr("Se permite cosechar y comenzar otro ciclo en la misma fecha (sin margen de preparación). Los ciclos deben caber completos y superar los filtros de aptitud.", "Harvesting and starting another cycle on the same date is allowed (no preparation interval). Complete cycles must fit and pass the suitability filters."))
        for t, _ in mensuales.values():
            plan["supuestos"].extend(a for a in t.avisos_datos if a not in plan["supuestos"])
    # Orden explícito de presentación: mayor IAC medio; desempate por días.
    # No cambia la búsqueda agronómica ni fabrica nuevos candidatos.
    planes.sort(key=lambda p: (p["iac_medio_cultivado"] if p["iac_medio_cultivado"] is not None else -1,
                               p["dias_cultivados"]), reverse=True)
    for plan in planes:
        plan["criterio_orden"] = tr("IAC medio descendente; desempate por días cultivados.",
                                    "Mean IAC descending; ties broken by cropped days.")
    # Se conservan los campos de la mejor opción para clientes anteriores.
    resultado = dict(planes[0])
    resultado["recomendaciones"] = [dict(p, posicion=i+1) for i,p in enumerate(planes)]
    resultado["n_solicitadas"] = n_recomendaciones
    resultado["n_devueltas"] = len(planes)
    resultado["criterio_diferencia"] = tr("Secuencia ordenada de IDs de cultivo distinta; cambiar solo fechas no crea otra recomendación.", "Distinct ordered sequence of crop IDs; changing dates alone does not create another recommendation.")
    if len(planes) < n_recomendaciones:
        resultado["aviso_recomendaciones"] = tr("La búsqueda no encontró suficientes secuencias distintas admisibles; no se duplican opciones.", "The search did not find enough distinct admissible sequences; options are not duplicated.")
    return resultado
