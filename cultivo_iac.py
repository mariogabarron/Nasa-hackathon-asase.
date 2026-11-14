from dataclasses import dataclass

@dataclass
class Cultivo:
    # Identificación
    id: int
    nombre: str
    nombre_cientifico: str
    familia: str
    duracion_ciclo_dias: int

    # 1. Temperatura media (°C), la temp que sería ideal
    temp_media_C: tuple[float, float]

    #2 temperaturas tope
    temp_tope: tuple[float, float]

    # 4. Precipitación, intervalo de precipitaciones ideal
    precipitacion_mm: tuple[float, float]

    # 5. Radiación solar (MJ/m²/día), intervalo quer sería ideal
    radiacion_solar_MJ_m2: tuple[float, float]

    # 6. Humedad superficial (m³/m³)
    humedad_suelo_smap_m3m3: tuple[float, float]

    # 7. Humedad radicular (m³/m³)
    humedad_raiz_smap_m3m3: tuple[float, float]

    # 8. Temperatura del suelo (°C)
    temp_suelo_smap_C: tuple[float, float]

    # 9. pH del suelo
    suelo_ph_0_30cm: tuple[float, float]

    # 10. Carbono orgánico (g/kg)
    suelo_carbono_organico_g_kg: float

    # 11. Textura de suelo apta (opcional, si no se pasa texturas_aptas)
    suelo_textura_clase: str | None = None
