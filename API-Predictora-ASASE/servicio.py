"""Puente getter -> agregación diaria -> motor IAC/rotación."""
import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from errores import DatosInsuficientes
from getter import get_tabla
from iac import (PARAMETROS, Territorio, cargar_cultivos, calcular_iac,
                 recomendar_rotacion, validar_historial_ids, entero)
from validacion import validar_consulta

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
    avisos = [f"{k}: {int(df[k].count())}/{dias} días disponibles." for k in PARAMETROS if df[k].count() < dias]
    valores = {k: float(df[k].mean()) for k in PARAMETROS}
    valores["temp_min_C"] = float(df["temp_min_C"].min())
    valores["temp_max_C"] = float(df["temp_max_C"].max())
    valores["precipitacion_mm"] = float(df["precipitacion_mm"].sum(min_count=dias))
    valores = {k: (v if np.isfinite(v) else None) for k,v in valores.items()}
    if not any(v is not None for v in valores.values()):
        raise DatosInsuficientes("No hay ninguna variable numérica disponible")
    if df["precipitacion_mm"].count() < dias:
        avisos.append("Precipitación excluida: el acumulado completo no se conoce; no se sustituye por cero.")
    metadata["avisos_datos"] = tuple(avisos)
    return Territorio(**metadata, **valores), dias


def predecir(start_date, end_date, point=None, bbox=None, historial=None,
             accion="iac", cultivo_id=None, *, getter=None, catalogo=None):
    """Mismos argumentos del getter + IDs históricos + acción.

    Sin cultivo_id, iac devuelve un mapa por ID de cultivo. Con cultivo_id,
    devuelve únicamente iac y razon. El historial no incluye el cultivo objetivo.
    getter puede inyectarse para integrar otra implementación o probar sin red.
    """
    validar_consulta(start_date, end_date, point, bbox)
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
    tabla = (getter or get_tabla)(start_date, end_date, point, bbox)
    territorio, dias = agregar_tabla(tabla, start_date, end_date, point, bbox)
    if accion == "iac":
        def evaluar(c):
            return calcular_iac(territorio, c, dias_precipitacion=dias, catalogo=cat, historial_ids=ids)
        if cultivo_id is not None:
            return evaluar(cat[cultivo_id])
        return {str(cid): evaluar(cat[cid]) for cid in sorted(cat)}
    # La rotación empieza DESPUÉS del período observado; no se inventa un
    # pronóstico mensual a partir de los promedios de ese período.
    comienzo = (pd.Timestamp(end_date).date() + timedelta(days=1)).isoformat()
    plan = recomendar_rotacion(replace(territorio, fecha=comienzo), cat,
                              dias_precipitacion=dias, historial_ids=ids)
    plan["periodo_observado"] = {"start_date": start_date, "end_date": end_date, "dias": dias}
    return plan
