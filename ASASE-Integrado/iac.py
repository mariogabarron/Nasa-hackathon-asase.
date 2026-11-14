"""Motor IAC de ASASE. Python 3.10+, sin dependencias externas.

Pesos: PDF aportado, tabla de la página 2. Las funciones de idoneidad,
el ajuste por historial y los filtros de rotación son reglas de prototipo,
no coeficientes calibrados ni predicciones de rendimiento.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def numero(x: Any, nombre: str, minimo=None, maximo=None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f"{nombre}: se necesita un número finito")
    if minimo is not None and x < minimo or maximo is not None and x > maximo:
        raise ValueError(f"{nombre}: fuera de [{minimo}, {maximo}]")
    return float(x)


def entero(x: Any, nombre: str, minimo=1) -> int:
    if type(x) is not int or x < minimo:
        raise ValueError(f"{nombre}: se necesita un entero >= {minimo}")
    return x


def fecha_iso(x: str) -> date:
    if not isinstance(x, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
        raise ValueError("Fecha obligatoria en formato YYYY-MM-DD")
    return date.fromisoformat(x)


def texto(x: str, nombre: str) -> None:
    if not isinstance(x, str) or not x.strip():
        raise ValueError(f"{nombre}: texto no vacío requerido")


@dataclass(frozen=True)
class Territorio:
    id: str
    nombre: str
    latitud: float
    longitud: float
    fecha: str
    temp_media_C: float
    temp_min_C: float
    temp_max_C: float
    precipitacion_mm: float
    radiacion_solar_MJ_m2: float
    humedad_suelo_smap_m3m3: float
    humedad_raiz_smap_m3m3: float
    temp_suelo_smap_C: float
    suelo_ph_0_30cm: float
    suelo_carbono_organico_g_kg: float
    # Compatibilidad con el frontend: se acepta, pero NUNCA se utiliza.
    suelo_textura_clase: str | None = None
    permitir_ausentes: bool = False
    avisos_datos: tuple[str, ...] = ()

    def __post_init__(self):
        texto(self.id, "id")
        texto(self.nombre, "nombre")
        fecha_iso(self.fecha)
        numero(self.latitud, "latitud", -90, 90)
        numero(self.longitud, "longitud", -180, 180)
        for k in PARAMETROS:
            numero(getattr(self, k), k) if getattr(self, k) is not None or not self.permitir_ausentes else None
        for k in ("precipitacion_mm", "radiacion_solar_MJ_m2", "suelo_carbono_organico_g_kg"):
            numero(getattr(self, k), k, 0) if getattr(self, k) is not None or not self.permitir_ausentes else None
        for k in ("humedad_suelo_smap_m3m3", "humedad_raiz_smap_m3m3"):
            numero(getattr(self, k), k, 0, 1) if getattr(self, k) is not None or not self.permitir_ausentes else None
        numero(self.suelo_ph_0_30cm, "suelo_ph_0_30cm", 0, 14) if self.suelo_ph_0_30cm is not None or not self.permitir_ausentes else None
        temps = [v for v in (self.temp_min_C, self.temp_media_C, self.temp_max_C) if v is not None]
        if temps != sorted(temps):
            raise ValueError("Debe cumplirse temp_min_C <= temp_media_C <= temp_max_C")


@dataclass(frozen=True)
class Cultivo:
    id: int
    nombre: str
    nombre_cientifico: str
    familia: str
    duracion_ciclo_dias: int
    temp_media_C: tuple[float, float]
    temp_tope: tuple[float, float]
    precipitacion_mm: tuple[float, float]
    radiacion_solar_MJ_m2: tuple[float, float]
    humedad_suelo_smap_m3m3: tuple[float, float]
    humedad_raiz_smap_m3m3: tuple[float, float]
    temp_suelo_smap_C: tuple[float, float]
    suelo_ph_0_30cm: tuple[float, float]
    suelo_carbono_organico_g_kg: float

    def __post_init__(self):
        entero(self.id, "cultivo.id")
        entero(self.duracion_ciclo_dias, "duracion_ciclo_dias")
        for k in ("nombre", "nombre_cientifico", "familia"):
            texto(getattr(self, k), k)
        for k in INTERVALOS:
            v = getattr(self, k)
            if not isinstance(v, (tuple, list)) or len(v) != 2:
                raise ValueError(f"{k}: se necesita un intervalo [mínimo, máximo]")
            a, b = (numero(n, k) for n in v)
            if a >= b:
                raise ValueError(f"{k}: el mínimo debe ser menor que el máximo")
            object.__setattr__(self, k, (a, b))
        if not self.temp_tope[0] < self.temp_media_C[0] < self.temp_media_C[1] < self.temp_tope[1]:
            raise ValueError("temp_tope debe contener estrictamente el intervalo térmico ideal")
        for k in ("precipitacion_mm", "radiacion_solar_MJ_m2"):
            numero(getattr(self, k)[0], k, 0)
        for k in ("humedad_suelo_smap_m3m3", "humedad_raiz_smap_m3m3"):
            for n in getattr(self, k):
                numero(n, k, 0, 1)
        for n in self.suelo_ph_0_30cm:
            numero(n, "suelo_ph_0_30cm", 0, 14)
        if numero(self.suelo_carbono_organico_g_kg, "carbono objetivo", 0) == 0:
            raise ValueError("El carbono objetivo debe ser positivo")


PARAMETROS = (
    "temp_media_C", "temp_min_C", "temp_max_C", "precipitacion_mm",
    "radiacion_solar_MJ_m2", "humedad_suelo_smap_m3m3", "humedad_raiz_smap_m3m3",
    "temp_suelo_smap_C", "suelo_ph_0_30cm", "suelo_carbono_organico_g_kg",
)
INTERVALOS = (
    "temp_media_C", "temp_tope", "precipitacion_mm", "radiacion_solar_MJ_m2",
    "humedad_suelo_smap_m3m3", "humedad_raiz_smap_m3m3", "temp_suelo_smap_C", "suelo_ph_0_30cm",
)
# Transcripción literal, sin la textura. NO se corrige arbitrariamente ninguna celda.
PESOS_PDF = {
    "inicio_lluvias": (.05, .03, .08, .22, .06, .24, .08, .08, .05, .06),
    "plena_lluvia": (.08, .03, .04, .24, .12, .07, .18, .03, .07, .07),
    "retirada_lluvias": (.10, .04, .08, .12, .14, .06, .22, .04, .06, .07),
    "seca": (.08, .07, .14, .04, .08, .15, .24, .05, .05, .05),
}
ETIQUETAS = {
    "temp_media_C": ("Temperatura media", "°C"),
    "temp_min_C": ("Temperatura mínima", "°C"),
    "temp_max_C": ("Temperatura máxima", "°C"),
    "precipitacion_mm": ("Precipitación", "mm"),
    "radiacion_solar_MJ_m2": ("Radiación solar", "MJ/m²/día"),
    "humedad_suelo_smap_m3m3": ("Humedad superficial", "m³/m³"),
    "humedad_raiz_smap_m3m3": ("Humedad radicular", "m³/m³"),
    "temp_suelo_smap_C": ("Temperatura del suelo", "°C"),
    "suelo_ph_0_30cm": ("pH del suelo", ""),
    "suelo_carbono_organico_g_kg": ("Carbono orgánico", "g/kg"),
}


def estacion(fecha: str) -> str:
    mes = fecha_iso(fecha).month
    if 4 <= mes <= 6:
        return "inicio_lluvias"
    if 7 <= mes <= 9:
        return "plena_lluvia"
    if 10 <= mes <= 11:
        return "retirada_lluvias"
    return "seca"


def pesos_normalizados(fecha: str) -> dict[str, float]:
    originales = PESOS_PDF[estacion(fecha)]
    total = math.fsum(originales)
    return {k: w / total for k, w in zip(PARAMETROS, originales)}


def limitar(x: float) -> float:
    return max(0.0, min(1.0, x))


def idoneidad_intervalo(x: float, ideal: tuple[float, float], margen: float = 1.0) -> float:
    """1 dentro del ideal; cae a 0 a una anchura de intervalo de distancia.

    Esta rampa es una convención matemática, NO un umbral agronómico publicado.
    El margen permite recalibrar la tolerancia de cada parámetro.
    """
    a, b = ideal
    distancia = max(a - x, 0.0, x - b)
    return limitar(1.0 - distancia / ((b - a) * margen))


@dataclass(frozen=True)
class Configuracion:
    # Coeficientes provisionales de riesgo por repetición, no del PDF.
    penalizacion_mismo_cultivo: float = .15
    penalizacion_misma_familia: float = .08
    penalizacion_historial_max: float = .25
    ventana_historial_dias: int = 365
    umbral_iac_bajo: float = 40.0

    def __post_init__(self):
        for k in ("penalizacion_mismo_cultivo", "penalizacion_misma_familia", "penalizacion_historial_max"):
            numero(getattr(self, k), k, 0, 1) if getattr(self, k) is not None or not self.permitir_ausentes else None
        entero(self.ventana_historial_dias, "ventana_historial_dias")
        numero(self.umbral_iac_bajo, "umbral_iac_bajo", 0, 100)


@dataclass(frozen=True)
class RegistroCultivo:
    territorio_id: str
    cultivo_id: int
    fecha_inicio: str
    fecha_fin: str  # Exclusiva: la siguiente siembra puede comenzar este día.

    def __post_init__(self):
        texto(self.territorio_id, "territorio_id")
        entero(self.cultivo_id, "cultivo_id")
        if fecha_iso(self.fecha_inicio) >= fecha_iso(self.fecha_fin):
            raise ValueError("El registro debe tener fecha_inicio < fecha_fin")


def construir(cls, datos: dict):
    """Ignora únicamente textura en Cultivo; los errores de claves no se silencian."""
    if not isinstance(datos, dict):
        raise ValueError(f"{cls.__name__}: se necesita un objeto JSON")
    datos = dict(datos)
    if cls is Cultivo:
        datos.pop("suelo_textura_clase", None)
    try:
        return cls(**datos)
    except TypeError as e:
        raise ValueError(f"{cls.__name__}: campos ausentes o desconocidos: {e}") from e


def cargar_cultivos(origen: str | Path | list[dict]) -> dict[int, Cultivo]:
    datos = json.loads(Path(origen).read_text(encoding="utf-8")) if isinstance(origen, (str, Path)) else origen
    if not isinstance(datos, list) or not datos:
        raise ValueError("El catálogo debe ser una lista no vacía")
    catalogo = {}
    for dato in datos:
        c = construir(Cultivo, dato)
        if c.id in catalogo:
            raise ValueError(f"ID de cultivo duplicado: {c.id}")
        catalogo[c.id] = c
    return catalogo


def cargar_historial(datos: str | list[dict]) -> list[RegistroCultivo]:
    if isinstance(datos, str):
        datos = json.loads(datos)
    if not isinstance(datos, list):
        raise ValueError("historial debe ser un array JSON")
    return [construir(RegistroCultivo, dato) for dato in datos]


def validar_historial(historial, territorio_id, fecha, catalogo):
    ordenado = sorted(historial, key=lambda r: r.fecha_inicio)
    anterior_fin = None
    for r in ordenado:
        if r.territorio_id != territorio_id:
            raise ValueError("El historial contiene otra parcela; filtrar por territorio_id")
        if r.cultivo_id not in catalogo:
            raise ValueError(f"Cultivo histórico desconocido: {r.cultivo_id}")
        if fecha_iso(r.fecha_fin) > fecha:
            raise ValueError("El historial solo admite cultivos terminados antes o en la consulta")
        if anterior_fin is not None and fecha_iso(r.fecha_inicio) < anterior_fin:
            raise ValueError("El historial tiene ciclos solapados o duplicados")
        anterior_fin = fecha_iso(r.fecha_fin)
    return ordenado


def validar_historial_ids(ids, catalogo):
    """IDs del más antiguo al más reciente; no se infieren fechas."""
    if not isinstance(ids, (list, tuple)):
        raise ValueError("historial debe ser una lista de IDs")
    for cid in ids:
        entero(cid, "ID histórico")
        if cid not in catalogo:
            raise ValueError(f"Cultivo histórico desconocido: {cid}")
    return tuple(ids)


def penalizacion_historial(cultivo, historial, catalogo, fecha, config, historial_ids=()):
    penalizacion = 0.0
    causas = []
    # IDs sin fechas: efecto completo, sin descuento temporal inventado.
    entradas = [(cid, 1.0) for cid in historial_ids]
    for r in historial:
        edad = (fecha - fecha_iso(r.fecha_fin)).days
        if not 0 <= edad < config.ventana_historial_dias:
            continue
        entradas.append((r.cultivo_id, 1 - edad / config.ventana_historial_dias))
    for cid, factor_tiempo in entradas:
        anterior = catalogo[cid]
        if anterior.id == cultivo.id:
            coef = config.penalizacion_mismo_cultivo
            causa = f"repetición de {cultivo.nombre}"
        elif anterior.familia.casefold() == cultivo.familia.casefold():
            coef = config.penalizacion_misma_familia
            causa = f"misma familia ({cultivo.familia}) tras {anterior.nombre}"
        else:
            continue
        aporte = coef * factor_tiempo
        penalizacion += aporte
        if aporte > 0:
            causas.append((aporte, causa))
    razon = max(causas, default=(0, ""), key=lambda x: x[0])[1]
    return min(config.penalizacion_historial_max, penalizacion), razon


def evaluar_iac(
    territorio: Territorio, cultivo: Cultivo, *,
    dias_precipitacion: int | None = None,
    historial: list[RegistroCultivo] | None = None,
    catalogo: dict[int, Cultivo] | None = None,
    config: Configuracion | None = None,
    margenes: dict[str, float] | None = None,
    historial_ids: list[int] | tuple[int, ...] = (),
) -> dict:
    """Evaluación explicable interna. La API pública usa calcular_iac.

    Si dias_precipitacion es None, el acumulado DEBE corresponder al ciclo
    completo del cultivo. Si se especifica, se compara con el intervalo del
    ciclo prorrateado a esos días (hipótesis de lluvia uniforme).
    """
    config = config or Configuracion()
    margenes = dict(margenes or {})
    permitidos = set(INTERVALOS) - {"temp_tope", "temp_media_C"}
    if set(margenes) - permitidos:
        raise ValueError("Margen para un parámetro desconocido o con límites térmicos explícitos")
    for k, v in margenes.items():
        if numero(v, k, 0) == 0:
            raise ValueError("Los márgenes deben ser positivos")
    if dias_precipitacion is not None:
        entero(dias_precipitacion, "dias_precipitacion")
    dias = cultivo.duracion_ciclo_dias if dias_precipitacion is None else dias_precipitacion
    historial = historial or []
    if (historial or historial_ids) and catalogo is None:
        raise ValueError("El historial requiere el catálogo de cultivos")
    catalogo = catalogo if catalogo is not None else {cultivo.id: cultivo}
    if cultivo.id not in catalogo or catalogo[cultivo.id] != cultivo:
        raise ValueError("El cultivo evaluado no coincide con el catálogo")
    validar_historial(historial, territorio.id, fecha_iso(territorio.fecha), catalogo)
    ids = validar_historial_ids(historial_ids, catalogo)
    if ids and historial:
        raise ValueError("Usar historial con fechas O historial_ids, no ambos")
    originales = pesos_normalizados(territorio.fecha)
    disponibles = {k:w for k,w in originales.items() if getattr(territorio,k) is not None}
    if not disponibles:
        return {"iac": None, "razon": "Sin datos suficientes para calcular el IAC.", "detalles": []}
    cobertura = sum(disponibles.values())
    pesos = {k:w/cobertura for k,w in disponibles.items()}
    ideal_min, ideal_max = cultivo.temp_media_C
    tope_min, tope_max = cultivo.temp_tope
    # El cero es solo un valor de trabajo: los parámetros ausentes NO tienen peso.
    def v(k):
        return getattr(territorio,k) if getattr(territorio,k) is not None else 0.0
    puntuaciones = {
        "temp_media_C": min(limitar((v("temp_media_C") - tope_min) / (ideal_min - tope_min)),
                            limitar((tope_max - v("temp_media_C")) / (tope_max - ideal_max))),
        "temp_min_C": limitar((v("temp_min_C") - tope_min) / (ideal_min - tope_min)),
        "temp_max_C": limitar((tope_max - v("temp_max_C")) / (tope_max - ideal_max)),
        "suelo_carbono_organico_g_kg": limitar(v("suelo_carbono_organico_g_kg") / cultivo.suelo_carbono_organico_g_kg),
    }
    rangos = {k: getattr(cultivo, k) for k in permitidos}
    rangos["precipitacion_mm"] = tuple(v * dias / cultivo.duracion_ciclo_dias for v in cultivo.precipitacion_mm)
    for k in permitidos:
        puntuaciones[k] = idoneidad_intervalo(v(k), rangos[k], margenes.get(k, 1.0))
    detalles = []
    for k, peso in pesos.items():
        valor = getattr(territorio, k)
        nombre, unidad = ETIQUETAS[k]
        if k == "temp_media_C":
            referencia = f"ideal {ideal_min:g}–{ideal_max:g} °C; topes {tope_min:g}–{tope_max:g} °C"
        elif k == "temp_min_C":
            referencia = f"idoneidad plena desde {ideal_min:g} °C; cero en o bajo {tope_min:g} °C"
        elif k == "temp_max_C":
            referencia = f"idoneidad plena hasta {ideal_max:g} °C; cero en o sobre {tope_max:g} °C"
        elif k == "suelo_carbono_organico_g_kg":
            referencia = f"objetivo mínimo {cultivo.suelo_carbono_organico_g_kg:g} g/kg"
        else:
            a, b = rangos[k]
            referencia = f"ideal {a:g}–{b:g} {unidad}"
            if k == "precipitacion_mm":
                referencia += f" en {dias} días"
        perdida = 100 * peso * (1 - puntuaciones[k])
        detalles.append({"parametro": k, "peso": peso, "idoneidad": puntuaciones[k],
                         "perdida_puntos": perdida,
                         "razon": f"{nombre}: {valor:g} {unidad}; {referencia}. Reduce {perdida:.2f} puntos del IAC."})
    base = 100 * math.fsum(pesos[k] * puntuaciones[k] for k in pesos)
    p, causa = penalizacion_historial(cultivo, historial, catalogo, fecha_iso(territorio.fecha), config, ids)
    perdida_historial = base * p
    if p > 0:
        detalles.append({"parametro": "historial", "peso": None, "idoneidad": 1 - p,
                         "perdida_puntos": perdida_historial,
                         "razon": f"Historial: {causa}. El ajuste acumulado por repetición reduce {perdida_historial:.2f} puntos; regla provisional, no deterioro medido del suelo."})
    iac = max(0.0, min(100.0, base * (1 - p)))
    peor = max(detalles, key=lambda d: d["perdida_puntos"])
    razon = peor["razon"] if peor["perdida_puntos"] > 1e-10 else None
    if razon and iac < config.umbral_iac_bajo:
        razon = "IAC bajo. Principal limitante: " + razon
    avisos = list(territorio.avisos_datos)
    if cobertura < 1 - 1e-9:
        avisos.append("IAC parcial: faltan " + ", ".join(k for k in originales if k not in disponibles) + f"; cobertura de pesos {100*cobertura:.1f}%. Pesos renormalizados; no equivale a una evaluación completa.")
    if avisos:
        razon = " ".join(([razon] if razon else []) + avisos)
    return {"iac": iac, "razon": razon, "iac_base": base,
            "estacion": estacion(territorio.fecha), "detalles": detalles}


def calcular_iac(territorio: Territorio, cultivo: Cultivo, **opciones) -> dict:
    """Salida estricta para frontend: solamente IAC (0–100) y razón/null."""
    r = evaluar_iac(territorio, cultivo, **opciones)
    return {"iac": round(r["iac"], 2) if r["iac"] is not None else None, "razon": r["razon"]}


def siguiente_mes(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def aniversario(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:  # 29 de febrero -> 28 de febrero siguiente.
        return date(d.year + 1, 2, 28)


def recomendar_rotacion(
    territorio: Territorio, catalogo: dict[int, Cultivo], *, dias_precipitacion: int,
    historial: list[RegistroCultivo] | None = None,
    escenarios: dict[str, dict] | None = None,
    config: Configuracion | None = None,
    iac_minimo: float = 60.0, idoneidad_hidrica_minima: float = .25,
    dias_entre_cultivos: int = 7, ancho_busqueda: int = 64,
    fecha_fin: str | None = None,
    n_recomendaciones: int | None = None,
    historial_ids: list[int] | tuple[int, ...] = (),
) -> dict:
    """Plan anual mediante búsqueda en haz (aproximada, no óptimo garantizado).

    escenarios: {'YYYY-MM': {'territorio': {...}, 'dias_precipitacion': 30}}.
    Si se omite, mantiene constantes los datos y lo declara como escenario
    condicional. Nunca extrapola el suelo como si fuera una medición futura.
    """
    if n_recomendaciones is not None:
        entero(n_recomendaciones, "n_recomendaciones")
    limite = n_recomendaciones or 1
    ancho_busqueda = max(ancho_busqueda, limite)
    entero(dias_precipitacion, "dias_precipitacion")
    entero(dias_entre_cultivos, "dias_entre_cultivos", 0)
    entero(ancho_busqueda, "ancho_busqueda")
    numero(iac_minimo, "iac_minimo", 0, 100)
    numero(idoneidad_hidrica_minima, "idoneidad_hidrica_minima", 0, 1)
    if not catalogo:
        raise ValueError("Catálogo vacío")
    if any(k != c.id for k, c in catalogo.items()):
        raise ValueError("Las claves del catálogo deben coincidir con sus IDs")
    config = config or Configuracion()
    inicio = fecha_iso(territorio.fecha)
    fin = fecha_iso(fecha_fin) if fecha_fin is not None else aniversario(inicio)
    if fin <= inicio:
        raise ValueError("fecha_fin exclusiva debe ser posterior al inicio")
    horizonte = (fin - inicio).days
    historial = validar_historial(historial or [], territorio.id, inicio, catalogo)
    ids = validar_historial_ids(historial_ids, catalogo)
    if ids and historial:
        raise ValueError("Usar historial con fechas O historial_ids, no ambos")
    escenarios_validados = {}
    d = inicio
    while d < fin:
        clave = d.strftime("%Y-%m")
        if escenarios is not None:
            if clave not in escenarios:
                raise ValueError(f"Falta escenario para {clave}; no se rellena silenciosamente")
            e = escenarios[clave]
            if not isinstance(e, dict) or set(e) != {"territorio", "dias_precipitacion"}:
                raise ValueError(f"Escenario {clave}: requiere territorio y dias_precipitacion")
            t = construir(Territorio, e["territorio"])
            if t.id != territorio.id or (t.latitud, t.longitud) != (territorio.latitud, territorio.longitud):
                raise ValueError("El escenario corresponde a otra parcela o ubicación")
            if t.fecha[:7] != clave:
                raise ValueError("La fecha del escenario no coincide con su mes")
            escenarios_validados[clave] = (t, entero(e["dias_precipitacion"], "dias_precipitacion"))
        d = siguiente_mes(d)

    cache = {}

    def evaluar_ciclo(d, c):
        clave = (d, c.id)
        if clave in cache:
            return cache[clave]
        termino = d + timedelta(days=c.duracion_ciclo_dias)
        cursor, media, minimo_mes = d, 0.0, 100.0
        admisible = True
        while cursor < termino:
            hasta = min(siguiente_mes(cursor), termino)
            t, periodo = escenarios_validados.get(cursor.strftime("%Y-%m"), (territorio, dias_precipitacion))
            r = evaluar_iac(replace(t, fecha=cursor.isoformat()), c, dias_precipitacion=periodo, catalogo=catalogo, config=config)
            media += r["iac"] * (hasta - cursor).days / c.duracion_ciclo_dias
            minimo_mes = min(minimo_mes, r["iac"])
            scores = {v["parametro"]: v["idoneidad"] for v in r["detalles"]}
            # Evita recomendar ciclos cuya media oculta un período crítico.
            if any(scores.get(k, 1) <= 0 for k in ("temp_media_C", "temp_min_C", "temp_max_C")):
                admisible = False
            if any(scores.get(k, 1) < idoneidad_hidrica_minima for k in ("precipitacion_mm", "humedad_suelo_smap_m3m3", "humedad_raiz_smap_m3m3")):
                admisible = False
            cursor = hasta
        cache[clave] = media, minimo_mes, admisible
        return cache[clave]

    def tramo(tipo, a, b, **extras):
        return {"tipo": tipo, "fecha_inicio": a.isoformat(), "fecha_fin": b.isoformat(),
                "dias": (b - a).days, **extras}

    # Estado: cursor, historial (real + simulado), tramos, suma IAC*días.
    disponible_inicial = inicio
    tramos_iniciales = []
    if historial:
        disponible_inicial = min(fin, max(inicio, fecha_iso(historial[-1].fecha_fin) + timedelta(days=dias_entre_cultivos)))
        if disponible_inicial > inicio:
            tramos_iniciales.append(tramo("preparacion", inicio, disponible_inicial,
                justificacion="Completa el margen de preparación tras el último cultivo registrado."))
    estados = [(disponible_inicial, tuple(historial), tramos_iniciales, 0.0)]
    mejor = (inicio, tuple(historial), [], -1.0)
    def ocupados(tramos):
        return sum(t["dias"] for t in tramos if t["tipo"] == "cultivo")

    candidatos = {}
    while estados:
        siguientes = []
        for cursor, hist, tramos, utilidad in estados:
            finalizado = (fin, hist, tramos + ([tramo("barbecho", cursor, fin,
                justificacion="Días sin cultivo en esta propuesta; no se atribuye una mejora automática del suelo.")] if cursor < fin else []), utilidad)
            firma = tuple(t["cultivo_id"] for t in tramos if t["tipo"] == "cultivo")
            previo = candidatos.get(firma)
            if previo is None or (ocupados(tramos), utilidad) > (ocupados(previo[2]), previo[3]):
                candidatos[firma] = finalizado
            if len(candidatos) > limite:
                peor = min(candidatos, key=lambda k: (ocupados(candidatos[k][2]), candidatos[k][3]))
                del candidatos[peor]
            if (ocupados(tramos), utilidad) > (ocupados(mejor[2]), mejor[3]):
                mejor = finalizado
            if cursor >= fin:
                continue
            # Puede esperar al mes siguiente para aprovechar otro escenario.
            proximo = min(siguiente_mes(cursor), fin)
            if proximo < fin:
                siguientes.append((proximo, hist, tramos + [tramo("barbecho", cursor, proximo,
                    justificacion="Espera hasta la siguiente ventana mensual evaluada.")], utilidad))
            for c in sorted(catalogo.values(), key=lambda x: x.id):
                cosecha = cursor + timedelta(days=c.duracion_ciclo_dias)
                if cosecha > fin:
                    continue
                ultimo_id = hist[-1].cultivo_id if hist else (ids[-1] if ids else None)
                if ultimo_id is not None and catalogo[ultimo_id].familia.casefold() == c.familia.casefold():
                    continue
                media, minimo_mes, admisible = evaluar_ciclo(cursor, c)
                p, _ = penalizacion_historial(c, hist, catalogo, cursor, config, ids)
                iac = media * (1 - p)
                if not admisible or minimo_mes * (1 - p) < iac_minimo:
                    continue
                eleccion = tramo("cultivo", cursor, cosecha, cultivo_id=c.id, cultivo=c.nombre,
                    familia=c.familia, iac_estimado=round(iac, 2),
                    justificacion=f"IAC medio del ciclo {iac:.1f}/100; cumple los filtros en cada mes evaluado y alterna familia respecto al cultivo anterior, si existe.")
                registro = RegistroCultivo(territorio.id, c.id, cursor.isoformat(), cosecha.isoformat())
                disponible = min(cosecha + timedelta(days=dias_entre_cultivos), fin)
                nuevos = tramos + [eleccion]
                if disponible > cosecha:
                    nuevos += [tramo("preparacion", cosecha, disponible,
                        justificacion="Margen configurable entre ciclos; no modifica el suelo simulado.")]
                siguientes.append((disponible, hist + (registro,), nuevos, utilidad + iac * c.duracion_ciclo_dias))
        # Cota optimista: cada día restante podría alcanzar 100 puntos.
        siguientes.sort(key=lambda s: (ocupados(s[2]) + (fin - s[0]).days, s[3] + 100 * (fin-s[0]).days), reverse=True)
        estados = siguientes[:ancho_busqueda]

    def presentar(estado):
        tramos = estado[2]
        # Une barbechos contiguos para una salida legible.
        unidos = []
        for t in tramos:
            if unidos and t["tipo"] == unidos[-1]["tipo"] == "barbecho":
                unidos[-1]["fecha_fin"] = t["fecha_fin"]
                unidos[-1]["dias"] += t["dias"]
                unidos[-1]["justificacion"] = "Período sin cultivo seleccionado dentro de las restricciones del modelo."
            else:
                unidos.append(dict(t))
        cultivados = sum(t["dias"] for t in unidos if t["tipo"] == "cultivo")
        supuestos = [
            "IAC heurístico, no rendimiento ni porcentaje de productividad.",
            "La lluvia del ciclo se prorratea uniformemente por días; no modela necesidades por fase.",
            "Alternancia de familias, filtros térmicos/hídricos y ajuste histórico son reglas configurables de prototipo.",
            "No se modelan riego, nitrógeno, plagas, fertilización ni evolución medida del carbono.",
        ]
        supuestos.extend(territorio.avisos_datos)
        faltantes = [k for k in PARAMETROS if getattr(territorio,k) is None]
        if faltantes:
            supuestos.append("Recomendación provisional: no se han podido verificar los filtros de las variables ausentes: " + ", ".join(faltantes))
        supuestos.append("Datos constantes: propuesta condicional, NO pronóstico climático anual." if escenarios is None
                         else "Usa los escenarios mensuales suministrados; su fiabilidad depende de la fuente.")
        if ids:
            supuestos.append("Historial solo con IDs: orden antiguo a reciente; sin fechas, el ajuste inicial no decae durante el plan.")
        return {"iac_medio_cultivado": round(estado[3]/cultivados, 4) if cultivados else None,
                "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat(), "dias": horizonte,
                "modo": "escenario_constante" if escenarios is None else "escenarios_mensuales",
                "rotacion": unidos, "dias_cultivados": cultivados,
                "justificacion": ("Propuesta que prioriza días cultivados y desempata por IAC, alternando familias, sin recortar ciclos. "
                                  "Búsqueda aproximada; los huecos se cubren con preparación o barbecho."
                                  if cultivados else "No se encontró ningún ciclo admisible con los datos, filtros y búsqueda utilizados; se devuelve el año en barbecho."),
                "supuestos": supuestos}
    ordenados = sorted(candidatos.values(), key=lambda e: (ocupados(e[2]), e[3]), reverse=True)
    # El barbecho completo se devuelve solo si no se encontró ningún cultivo.
    if any(ocupados(e[2]) for e in ordenados):
        ordenados = [e for e in ordenados if ocupados(e[2])]
    resultados = [presentar(e) for e in ordenados[:limite]]
    return resultados if n_recomendaciones is not None else resultados[0]


def procesar_peticion(payload: dict, catalogo: dict[int, Cultivo], *, config=None) -> dict:
    """Adaptador JSON -> JSON, importable desde FastAPI, Flask u otro backend.

    La acción iac devuelve EXACTAMENTE {'iac': ..., 'razon': ...}.
    ValueError indica una entrada inválida (convertir en HTTP 400/422).
    """
    if not isinstance(payload, dict):
        raise ValueError("Se necesita un objeto JSON")
    accion = payload.get("accion", "iac")
    comunes = {"accion", "territorio", "historial", "dias_precipitacion"}
    extras = {"cultivo_id"} if accion == "iac" else {"escenarios", "iac_minimo", "idoneidad_hidrica_minima", "dias_entre_cultivos", "ancho_busqueda"}
    if accion not in {"iac", "rotacion"}:
        raise ValueError("accion debe ser iac o rotacion")
    if set(payload) - comunes - extras:
        raise ValueError(f"Campos desconocidos: {sorted(set(payload) - comunes - extras)}")
    t = construir(Territorio, payload.get("territorio"))
    hist = cargar_historial(payload.get("historial", []))
    # Obligatorio por API para que la unidad temporal nunca quede implícita.
    periodo = entero(payload.get("dias_precipitacion"), "dias_precipitacion")
    if accion == "iac":
        cid = entero(payload.get("cultivo_id"), "cultivo_id")
        if cid not in catalogo:
            raise ValueError(f"Cultivo desconocido: {cid}")
        return calcular_iac(t, catalogo[cid], dias_precipitacion=periodo, historial=hist, catalogo=catalogo, config=config)
    if payload.get("escenarios") is not None and not isinstance(payload["escenarios"], dict):
        raise ValueError("escenarios debe ser un objeto por mes")
    opciones = {k: payload[k] for k in extras if k in payload}
    return recomendar_rotacion(t, catalogo, dias_precipitacion=periodo, historial=hist, config=config, **opciones)


def main():
    parser = argparse.ArgumentParser(description="ASASE: IAC e itinerario anual de cultivos")
    parser.add_argument("peticion", type=Path, help="JSON enviado por el frontend")
    parser.add_argument("--cultivos", type=Path, default=Path(__file__).with_name("cultivos.json"))
    args = parser.parse_args()
    try:
        salida = procesar_peticion(json.loads(args.peticion.read_text(encoding="utf-8")), cargar_cultivos(args.cultivos))
    except (ValueError, OSError) as e:
        parser.exit(2, f"Entrada inválida: {e}\n")
    print(json.dumps(salida, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
