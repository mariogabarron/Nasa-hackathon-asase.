from typing import List, Optional
from contextlib import asynccontextmanager
import ee
import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

GEE_PROJECT_ID = "gen-lang-client-0182377274"


# ==============================================================================
# INICIALIZACIÓN DE EARTH ENGINE AL ARRANCAR LA API
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Conectando con Google Earth Engine al iniciar el servidor...")
    try:
        ee.Initialize(project=GEE_PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT_ID)
    yield


app = FastAPI(
    title="NASA & Earth Engine Crop Data API",
    description="API para extraer datos agroclimáticos (NASA POWER, SMAP y SoilGrids)",
    version="1.0.0",
    lifespan=lifespan,
)


# ==============================================================================
# FUNCIÓN AUXILIAR: CLASIFICACIÓN TEXTURAL USDA
# ==============================================================================
def clasificar_textura_usda(arcilla, limo, arena):
    if any(v is None or np.isnan(v) for v in [arcilla, limo, arena]):
        return "Desconocida"
    total = arcilla + limo + arena
    if total <= 0:
        return "Desconocida"

    c = (arcilla / total) * 100.0
    si = (limo / total) * 100.0
    sa = (arena / total) * 100.0

    if si + 1.5 * c < 15:
        return "Arenosa (Sand)"
    elif si + 1.5 * c >= 15 and si + 2.0 * c < 30:
        return "Areno-francosa (Loamy Sand)"
    elif (c >= 7 and c < 20 and sa > 52 and (si + 2.0 * c) >= 30) or (c < 7 and si < 50 and (si + 2.0 * c) >= 30):
        return "Franco-arenosa (Sandy Loam)"
    elif c >= 7 and c < 27 and si >= 28 and si < 50 and sa <= 52:
        return "Franca (Loam)"
    elif (si >= 50 and c >= 12 and c < 27) or (si >= 50 and si < 80 and c < 12):
        return "Franco-limosa (Silt Loam)"
    elif si >= 80 and c < 12:
        return "Limosa (Silt)"
    elif c >= 20 and c < 35 and si < 28 and sa > 45:
        return "Franco-arcillo-arenosa (Sandy Clay Loam)"
    elif c >= 27 and c < 40 and sa > 20 and sa <= 45:
        return "Franco-arcillosa (Clay Loam)"
    elif c >= 27 and c < 40 and sa <= 20:
        return "Franco-arcillo-limosa (Silty Clay Loam)"
    elif c >= 35 and sa > 45:
        return "Arcillo-arenosa (Sandy Clay)"
    elif c >= 40 and si >= 40:
        return "Arcillo-limosa (Silty Clay)"
    elif c >= 40 and sa <= 45 and si < 40:
        return "Arcillosa (Clay)"
    return "Franca (Loam)"


# ==============================================================================
# TU FUNCIÓN DE EXTRACCIÓN DE DATOS
# ==============================================================================
def get_tabla(start_date: str, end_date: str, point: Optional[List[float]], bbox: Optional[List[float]]) -> pd.DataFrame:
    MODO = "POINT" if point is not None else "BBOX"

    if MODO == "BBOX":
        min_lat, min_lon, max_lat, max_lon = bbox
        geometria = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
        query_lat = (min_lat + max_lat) / 2.0
        query_lon = (min_lon + max_lon) / 2.0
    else:
        LAT, LON = point[0], point[1]
        geometria = ee.Geometry.Point([LON, LAT])
        query_lat, query_lon = LAT, LON

    # 3. DESCARGA DE NASA POWER
    parametros_power = [
        "T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR",
        "ALLSKY_SFC_SW_DWN", "GWETTOP", "GWETROOT",
    ]
    power_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    power_params = {
        "parameters": ",".join(parametros_power),
        "community": "AG",
        "longitude": query_lon,
        "latitude": query_lat,
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "format": "JSON",
    }

    resp = requests.get(power_url, params=power_params, timeout=30)
    resp.raise_for_status()
    power_json = resp.json()["properties"]["parameter"]

    df_power = pd.DataFrame(power_json)
    df_power.replace(-999.0, np.nan, inplace=True)
    df_power.index = pd.to_datetime(df_power.index, format="%Y%m%d")
    df_power.index.name = "fecha"

    df_power.rename(columns={
        "T2M": "temp_media_C",
        "T2M_MIN": "temp_min_C",
        "T2M_MAX": "temp_max_C",
        "PRECTOTCORR": "precipitacion_mm",
        "ALLSKY_SFC_SW_DWN": "radiacion_solar_MJ_m2",
        "GWETTOP": "humedad_suelo_power_idx",
        "GWETROOT": "humedad_raiz_power_idx"
    }, inplace=True)

    # 4. DESCARGA DE NASA SMAP L4 EN GEE
    bandas_smap = ["sm_surface", "sm_rootzone", "soil_temp_layer1"]
    coleccion_smap = (
        ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")
        .filterDate(start_date, end_date)
        .select(bandas_smap)
    )

    tabla_cruda = coleccion_smap.getRegion(geometry=geometria, scale=9000).getInfo()
    cabeceras = tabla_cruda[0]
    filas = tabla_cruda[1:]
    df_smap_raw = pd.DataFrame(filas, columns=cabeceras)

    df_smap_raw["fecha"] = pd.to_datetime(df_smap_raw["time"], unit="ms").dt.floor("D")
    df_smap = df_smap_raw.groupby("fecha")[bandas_smap].mean()

    df_smap["soil_temp_layer1"] = df_smap["soil_temp_layer1"] - 273.15
    df_smap.rename(columns={
        "sm_surface": "humedad_suelo_smap_m3m3",
        "sm_rootzone": "humedad_raiz_smap_m3m3",
        "soil_temp_layer1": "temp_suelo_smap_C"
    }, inplace=True)

    # 5. PROPIEDADES DEL SUELO EN GEE (SoilGrids)
    capas_0_30cm = ["0-5cm_mean", "5-15cm_mean", "15-30cm_mean"]
    ph_img = ee.Image("projects/soilgrids-isric/phh2o_mean").select([f"phh2o_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("ph")
    soc_img = ee.Image("projects/soilgrids-isric/soc_mean").select([f"soc_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("soc")
    clay_img = ee.Image("projects/soilgrids-isric/clay_mean").select([f"clay_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("clay")
    sand_img = ee.Image("projects/soilgrids-isric/sand_mean").select([f"sand_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("sand")
    silt_img = ee.Image("projects/soilgrids-isric/silt_mean").select([f"silt_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("silt")

    suelo_combinado = ee.Image.cat([ph_img, soc_img, clay_img, sand_img, silt_img])

    geometria_suelo = geometria.buffer(500) if MODO == "POINT" else geometria
    datos_suelo = suelo_combinado.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometria_suelo,
        scale=250,
        crs="EPSG:4326",
        maxPixels=1e8
    ).getInfo()

    ph_suelo = round(datos_suelo["ph"] / 10.0, 2) if datos_suelo.get("ph") else np.nan
    carbono_org_g_kg = round(datos_suelo["soc"] / 10.0, 2) if datos_suelo.get("soc") else np.nan
    arcilla_pct = round(datos_suelo["clay"] / 10.0, 1) if datos_suelo.get("clay") else np.nan
    arena_pct = round(datos_suelo["sand"] / 10.0, 1) if datos_suelo.get("sand") else np.nan
    limo_pct = round(datos_suelo["silt"] / 10.0, 1) if datos_suelo.get("silt") else np.nan
    clase_textural = clasificar_textura_usda(arcilla_pct, limo_pct, arena_pct)

    # 6. UNIR TABLAS Y LIMPIAR COLUMNAS
    df_final = df_power.join(df_smap, how="inner").round(4)

    df_final["suelo_ph_0_30cm"] = ph_suelo
    df_final["suelo_carbono_organico_g_kg"] = carbono_org_g_kg
    df_final["suelo_arcilla_pct"] = arcilla_pct
    df_final["suelo_arena_pct"] = arena_pct
    df_final["suelo_limo_pct"] = limo_pct
    df_final["suelo_textura_clase"] = clase_textural

    df_final = df_final.drop(columns=[
        "humedad_suelo_power_idx",
        "humedad_raiz_power_idx",
        "suelo_arcilla_pct",
        "suelo_arena_pct",
        "suelo_limo_pct"
    ])

    return df_final


# ==============================================================================
# MODELO DE ENTRADA Y ENDPOINT DE LA API
# ==============================================================================
class ConsultaCultivosRequest(BaseModel):
    start_date: str = Field(..., example="2025-10-01", description="Fecha inicio YYYY-MM-DD")
    end_date: str = Field(..., example="2025-10-15", description="Fecha fin YYYY-MM-DD")
    point: Optional[List[float]] = Field(None, min_length=2, max_length=2, example=[9.4034, -0.8424], description="[lat, lon]")
    bbox: Optional[List[float]] = Field(None, min_length=4, max_length=4, example=[9.30, -0.95, 9.50, -0.75], description="[min_lat, min_lon, max_lat, max_lon]")

    @model_validator(mode="after")
    def validar_localizacion(self):
        if not self.point and not self.bbox:
            raise ValueError("Debes proporcionar 'point' o 'bbox'.")
        if self.point and self.bbox:
            raise ValueError("Proporciona únicamente 'point' o 'bbox', no ambos a la vez.")
        return self

import json
@app.post("/api/datos-cultivos")
def obtener_datos_cultivos(req: ConsultaCultivosRequest):
    try:
        df = get_tabla(
            start_date=req.start_date,
            end_date=req.end_date,
            point=req.point,
            bbox=req.bbox
        )

        # Preparar fecha como string YYYY-MM-DD
        df_reset = df.reset_index()
        df_reset["fecha"] = df_reset["fecha"].dt.strftime("%Y-%m-%d")

        # SOLUCIÓN DEFINITIVA AL ERROR DE NaN EN PANDAS + FASTAPI:
        # df.to_json() convierte todos los NaN en 'null' de forma nativa
        registros = json.loads(df_reset.to_json(orient="records"))

        return {
            "status": "ok",
            "modo": "POINT" if req.point else "BBOX",
            "total_dias": len(registros),
            "datos": registros
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al extraer datos: {str(e)}")