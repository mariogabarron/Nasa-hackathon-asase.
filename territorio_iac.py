from dataclasses import dataclass


@dataclass
class Territorio_en_intervalo_fechas:
    # Identificación y localización
    id: str
    nombre: str
    latitud: float
    longitud: float
    fecha_inicio: str  # Formato: "YYYY-MM-DD"; selecciona la estación del año
    fecha_fin: str # Formato: "YYYY-MM-DD"; selecciona la estación del año

    # 1. Temperatura media del territorio entre los dias de inicio y fin
    temp_media_C: float

    # 2. Temperatura mínima registrada de entre todos lso días
    temp_min_C: float

    # 3. Temperatura máxima registrada de entre todos los dias
    temp_max_C: float

    # 4. Precipitación acumulada (mm en el período estudiado)(la suma de tods los dias)
    precipitacion_mm: float

    # 5. Radiación solar media diaria (MJ/m²/día)
    radiacion_solar_MJ_m2: float

    # 6. Humedad superficial del suelo, 0–5 cm (m³/m³), es la media diaria
    humedad_suelo_smap_m3m3: float

    # 7. Humedad en la zona radicular, 0–100 cm (m³/m³), es al media diaria
    humedad_raiz_smap_m3m3: float

    # 8. Temperatura del suelo (°C), es la media diaria
    temp_suelo_smap_C: float

    # 9. pH del suelo, 0–30 cm, media diaria
    suelo_ph_0_30cm: float

    # 10. Carbono orgánico del suelo (g/kg)
    suelo_carbono_organico_g_kg: float

    # 11. Clase textural del suelo
    suelo_textura_clase: str

    # Variables auxiliares para determinar la textura; no llevan peso propio
    suelo_arcilla_pct: float
    suelo_arena_pct: float
    suelo_limo_pct: float
