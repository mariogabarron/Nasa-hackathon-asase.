import ee
import requests
import pandas as pd
import numpy as np

def clasificar_textura_usda(arcilla, limo, arena):
    """
    Clasifica cualquier combinación de arcilla, limo y arena en una de las 12
    clases oficiales del triángulo textural USDA/FAO (sin 'Otra / Mixta').
    """
    if any(v is None or np.isnan(v) for v in [arcilla, limo, arena]):
        return "Desconocida"

    total = arcilla + limo + arena
    if total <= 0:
        return "Desconocida"

    # 1. Normalizar para que sumen exactamente 100.0%
    c = (arcilla / total) * 100.0
    si = (limo / total) * 100.0
    sa = (arena / total) * 100.0

    # 2. Reglas geométricas exactas del Triángulo Textural USDA (12 clases)
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
    else:
        # Cualquier punto milimétrico en la frontera cae en Franca
        return "Franca (Loam)"


def get_tabla(start_date, end_date, point, bbox):
    # ==============================================================================
    # 1. CONSTANTES DE CONFIGURACIÓN
    # ==============================================================================
    GEE_PROJECT_ID = "gen-lang-client-0182377274"  # Reemplaza por el ID de tu proyecto de Google Cloud

    # Rango temporal (Formato YYYY-MM-DD)
    # start_date = "2025-10-01"
    # end_date = "2026-03-31"

    # Modo de localización: elige "POINT" (un punto) o "BBOX" (área cuadrada)
    MODO = "POINT" if point != None else "BBOX"

    # Si MODO = "POINT":
    LAT = point[0]
    LON = point[1]


    # Archivo de salida
    OUTPUT_CSV = "datos_cultivos_completos.csv"


    # ==============================================================================
    # 2. AUTENTICACIÓN EN GOOGLE EARTH ENGINE
    # ==============================================================================
    print("1. Conectando con Google Earth Engine...")
    try:
        ee.Initialize(project=GEE_PROJECT_ID)
    except Exception:
        print("Iniciando autenticación interactiva de Earth Engine...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT_ID)

    if MODO == "BBOX":
        min_lat, min_lon, max_lat, max_lon = bbox
        geometria = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
        query_lat = (min_lat + max_lat) / 2.0
        query_lon = (min_lon + max_lon) / 2.0
    else:
        geometria = ee.Geometry.Point([LON, LAT])
        query_lat, query_lon = LAT, LON


    # ==============================================================================
    # 3. DESCARGA DE NASA POWER (Temperaturas, Precipitación, Radiación y Humedad)
    # ==============================================================================
    print("2. Descargando serie temporal de NASA POWER...")

    parametros_power = [
        "T2M",                # Temperatura media a 2m (°C)
        "T2M_MIN",            # Temperatura mínima a 2m (°C)
        "T2M_MAX",            # Temperatura máxima a 2m (°C)
        "PRECTOTCORR",        # Precipitación total corregida (mm/día)
        "ALLSKY_SFC_SW_DWN",  # Radiación solar incidente (MJ/m²/día en comunidad AG)
        "GWETTOP",            # Humedad superficial del suelo NASA POWER (0 a 1)
        "GWETROOT",           # Humedad en la zona radicular NASA POWER (0 a 1)
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
    # Reemplazar posibles valores nulos de la NASA (-999.0) por NaN
    df_power.replace(-999.0, np.nan, inplace=True)
    df_power.index = pd.to_datetime(df_power.index, format="%Y%m%d")
    df_power.index.name = "fecha"

    # Renombrar columnas de NASA POWER para mayor claridad
    df_power.rename(columns={
        "T2M": "temp_media_C",
        "T2M_MIN": "temp_min_C",
        "T2M_MAX": "temp_max_C",
        "PRECTOTCORR": "precipitacion_mm",
        "ALLSKY_SFC_SW_DWN": "radiacion_solar_MJ_m2",
        "GWETTOP": "humedad_suelo_power_idx",
        "GWETROOT": "humedad_raiz_power_idx"
    }, inplace=True)


    # ==============================================================================
    # 4. DESCARGA DE NASA SMAP L4 EN GEE (Humedad y Temp. Suelo a 9 km)
    # ==============================================================================
    print("3. Descargando serie temporal de SMAP L4 desde Google Earth Engine...")

    bandas_smap = [
        "sm_surface",       # Humedad superficial (0-5 cm) [m3/m3]
        "sm_rootzone",      # Humedad radicular (0-100 cm) [m3/m3]
        "soil_temp_layer1", # Temperatura del suelo capa 1 [K]
    ]

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

    # Pasar temperatura del suelo de Kelvin a Celsius y renombrar
    df_smap["soil_temp_layer1"] = df_smap["soil_temp_layer1"] - 273.15
    df_smap.rename(columns={
        "sm_surface": "humedad_suelo_smap_m3m3",
        "sm_rootzone": "humedad_raiz_smap_m3m3",
        "soil_temp_layer1": "temp_suelo_smap_C"
    }, inplace=True)


    # ==============================================================================
    # 5. PROPIEDADES DEL SUELO EN GEE (pH, Carbono Orgánico y Textura - SoilGrids)
    # ==============================================================================
    print("4. Extrayendo pH, carbono orgánico y textura del suelo (SoilGrids 250m)...")

    # Promediamos las 3 primeras capas superficiales/radiculares (0-5cm, 5-15cm, 15-30cm)
    capas_0_30cm = ["0-5cm_mean", "5-15cm_mean", "15-30cm_mean"]

    ph_img = ee.Image("projects/soilgrids-isric/phh2o_mean").select([f"phh2o_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("ph")
    soc_img = ee.Image("projects/soilgrids-isric/soc_mean").select([f"soc_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("soc")
    clay_img = ee.Image("projects/soilgrids-isric/clay_mean").select([f"clay_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("clay")
    sand_img = ee.Image("projects/soilgrids-isric/sand_mean").select([f"sand_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("sand")
    silt_img = ee.Image("projects/soilgrids-isric/silt_mean").select([f"silt_{c}" for c in capas_0_30cm]).reduce(ee.Reducer.mean()).rename("silt")

    # Combinar todas las capas del suelo en una sola imagen para hacer 1 única petición a GEE
    suelo_combinado = ee.Image.cat([ph_img, soc_img, clay_img, sand_img, silt_img])

    # Extraer el valor medio del punto o área cuadrada a 250 metros de resolución
    datos_suelo = suelo_combinado.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometria,
        scale=250,
        maxPixels=1e8
    ).getInfo()

    # Conversión de unidades nativas de ISRIC SoilGrids (vienen multiplicadas por 10)
    ph_suelo = round(datos_suelo["ph"] / 10.0, 2) if datos_suelo.get("ph") else np.nan
    carbono_org_g_kg = round(datos_suelo["soc"] / 10.0, 2) if datos_suelo.get("soc") else np.nan
    arcilla_pct = round(datos_suelo["clay"] / 10.0, 1) if datos_suelo.get("clay") else np.nan
    arena_pct = round(datos_suelo["sand"] / 10.0, 1) if datos_suelo.get("sand") else np.nan
    limo_pct = round(datos_suelo["silt"] / 10.0, 1) if datos_suelo.get("silt") else np.nan
    clase_textural = clasificar_textura_usda(arcilla_pct, limo_pct, arena_pct)


    # ==============================================================================
    # 6. UNIR TABLAS, AÑADIR VARIABLES DE SUELO Y EXPORTAR CSV
    # ==============================================================================
    print("5. Uniendo datos y guardando CSV...")

    df_final = df_power.join(df_smap, how="inner").round(4)

    # Añadir las propiedades edafológicas al DataFrame
    df_final["suelo_ph_0_30cm"] = ph_suelo
    df_final["suelo_carbono_organico_g_kg"] = carbono_org_g_kg
    df_final["suelo_arcilla_pct"] = arcilla_pct
    df_final["suelo_arena_pct"] = arena_pct
    df_final["suelo_limo_pct"] = limo_pct
    df_final["suelo_textura_clase"] = clase_textural

    df_final = df_final.drop(columns=["humedad_suelo_power_idx","humedad_raiz_power_idx", "suelo_arcilla_pct","suelo_arena_pct","suelo_limo_pct"])

    return df_final

    df_final.to_csv(OUTPUT_CSV)

    print(f"\n¡Completado! Archivo guardado en: {OUTPUT_CSV} ({len(df_final)} días)")
    print(f"Propiedades del suelo detectadas: pH={ph_suelo}, SOC={carbono_org_g_kg} g/kg, Textura={clase_textural} (Arcilla:{arcilla_pct}%, Arena:{arena_pct}%, Limo:{limo_pct}%)")
    df_final.head()