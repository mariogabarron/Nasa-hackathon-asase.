"""Motor de aptitud de cultivos (IAC) para el norte de Ghana.

Sin dependencias externas. Pesos e intervalos en configuracion_iac.json,
transcritos de los dos documentos aportados por el equipo ASASE.

Formula: IAC_base = 100 * sum(peso[estacion, variable] * puntuacion[cultivo, variable]).
Puntuacion individual: S1=1, S2=0.65, S3=0.30, N=0.
Si hay veto crítico, se devuelve IAC operativo=0 y se conserva IAC_base.

El historial calcula índices mensuales *retrospectivos*, no una predicción.
"""
from __future__ import annotations

import argparse
import json
import math
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'configuracion_iac.json').read_text(encoding='utf-8'))

DYNAMICAS = (
    'temp_media_C', 'temp_min_C', 'temp_max_C', 'precipitacion_mm',
    'radiacion_solar_MJ_m2', 'humedad_suelo_smap_m3m3',
    'humedad_raiz_smap_m3m3', 'temp_suelo_smap_C',
)
ESTATICAS = ('suelo_ph_0_30cm', 'suelo_carbono_organico_g_kg', 'suelo_textura_clase')
AUXILIARES = ('suelo_arcilla_pct', 'suelo_arena_pct', 'suelo_limo_pct')
REGIONES = {'northern', 'savannah', 'north east', 'upper east', 'upper west'}
PUNTUACIONES = {'S1': 1.00, 'S2': 0.65, 'S3': 0.30, 'N': 0.00}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', texto.strip().lower())
    return ' '.join(''.join(c for c in texto if not unicodedata.combining(c))
                    .replace('_', ' ').replace('-', ' ').split())


def clave_cultivo(nombre: str) -> str:
    if nombre in CONFIG['cultivos']:
        return nombre
    equivalencias = {
        'maiz':'maiz','sorgo':'sorgo','mijo':'mijo_perla','mijo perla':'mijo_perla',
        'arroz':'arroz_bajio','arroz de bajio':'arroz_bajio',
        'mani':'cacahuete','cacahuete':'cacahuete','name':'name',
        'caupi':'caupi','frijol carilla':'caupi','soja':'soja','yuca':'yuca',
        'mandioca':'yuca','boniato':'boniato','batata':'boniato',
        'bambara':'bambara','guisante bambara':'bambara','algodon':'algodon',
    }
    key = normalizar(nombre)
    if key not in equivalencias:
        raise ValueError(f'Cultivo desconocido: {nombre!r}. Opciones: {list(CONFIG["cultivos"])}')
    return equivalencias[key]


def estacion_para(fecha: date) -> str:
    return next(
        clave for clave, dato in CONFIG['estaciones'].items()
        if fecha.month in dato['meses']
    )


def num(valor: Any, campo: str) -> float:
    if isinstance(valor, bool):
        raise ValueError(f'{campo}: se esperaba un número, no un booleano')
    try:
        n = float(valor)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{campo}: se esperaba un número: {valor!r}') from exc
    if not math.isfinite(n):
        raise ValueError(f'{campo}: debe ser finito')
    return n


def validar_entradas(suelo: dict, observacion: dict) -> tuple[dict, dict, float]:
    """Valida unidades y presencia; calcula el desplazamiento por textura.

    Nota: los PDF no proporcionan las fronteras del triangulo textural USDA.
    Por eso exigimos que la clase textural venga del equipo de datos.
    Los porcentajes se usan para validar suma=100% y ajustar humedad.
    """
    s = {}
    for key in ESTATICAS:
        if key not in suelo or suelo[key] is None:
            raise ValueError(f'Falta en suelo: {key}')
        s[key] = suelo[key] if key == 'suelo_textura_clase' else num(suelo[key],key)

    texturas_validas = {clase for c in CONFIG['cultivos'].values()
                       for grupos in c['textura'].values() for clase in grupos}
    originales = {normalizar(t): t for t in texturas_validas}
    textura_n = normalizar(str(s['suelo_textura_clase']))
    if textura_n not in originales:
        raise ValueError(f'Textura {s["suelo_textura_clase"]!r} sin intervalos definidos. Opciones: {sorted(texturas_validas)}')
    s['suelo_textura_clase'] = originales[textura_n]

    if not 0 <= s['suelo_ph_0_30cm'] <= 14:
        raise ValueError('suelo_ph_0_30cm debe estar en [0,14]')
    if s['suelo_carbono_organico_g_kg'] < 0:
        raise ValueError('suelo_carbono_organico_g_kg no puede ser negativo')

    presentes = [key in suelo and suelo[key] is not None for key in AUXILIARES]
    ajuste = 0.0
    if any(presentes):
        if not all(presentes):
            raise ValueError('Debe proporcionar los tres porcentajes de arena, arcilla y limo, o ninguno')
        for key in AUXILIARES:
            s[key] = num(suelo[key], key)
            if not 0 <= s[key] <= 100:
                raise ValueError(f'{key} fuera de [0,100]')
        if abs(sum(s[k] for k in AUXILIARES)-100.0) > 1.0:
            raise ValueError('Arena + arcilla + limo debe sumar 100% (tolerancia de ±1 punto porcentual)')
        # Regla del catalogo: arena > 65 -> +0.03; arcilla > 40 -> -0.03.
        # Son mutuamente excluyentes si las fracciones son coherentes.
        if s['suelo_arena_pct'] > 65:
            ajuste = 0.03
        elif s['suelo_arcilla_pct'] > 40:
            ajuste = -0.03

    o = {}
    for key in DYNAMICAS:
        if key not in observacion or observacion[key] is None:
            raise ValueError(f'Falta en observacion: {key}')
        o[key] = num(observacion[key], key)
    if not (o['temp_min_C'] <= o['temp_media_C'] <= o['temp_max_C']):
        raise ValueError('Debe cumplirse temp_min_C <= temp_media_C <= temp_max_C')
    if o['precipitacion_mm'] < 0 or o['radiacion_solar_MJ_m2'] < 0:
        raise ValueError('Precipitacion y radiacion deben ser >= 0')
    for key in ('humedad_suelo_smap_m3m3', 'humedad_raiz_smap_m3m3'):
        if not 0 <= o[key] <= 1:
            raise ValueError(f'{key} debe estar en [0,1] m³/m³')
    return s, o, ajuste


def puntuar_intervalo(valor: float, bordes: list[float | None], ajuste_minimo: float,
                      parametro: str, cultivo: str) -> str:
    """Se prioriza S1 en los bordes compartidos, luego S2 y S3.

    El ajuste de humedad afecta SOLAMENTE los tres limites inferiores
    (S3/S2/S1). Los limites superiores quedan como en el catalogo.
    Esta interpretacion del 'desplazamiento del umbral minimo' es una
    decision de implementacion explicitada en README.
    """
    l3,l2,l1,u1,u2,u3 = bordes
    l3 += ajuste_minimo
    l2 += ajuste_minimo
    l1 += ajuste_minimo
    if l1 <= valor <= u1:
        return 'S1'
    if (l2 <= valor < l1) or (u1 < valor <= u2):
        return 'S2'
    if (l3 <= valor < l2) or (u3 is not None and u2 < valor <= u3):
        return 'S3'
    if valor < l3 or (u3 is not None and valor > u3):
        return 'N'
    # En arroz, humedad > tope S2 no tiene S3/N superior en el PDF.
    raise ValueError(f'Intervalo no definido en PDF: {cultivo}, {parametro}={valor}. '
                     'No se inventa una categoria para este valor.')


def puntuar_carbono(valor: float, umbrales: dict) -> str:
    if valor >= umbrales['S1']:
        return 'S1'
    if valor >= umbrales['S2']:
        return 'S2'
    if valor >= umbrales['S3']:
        return 'S3'
    return 'N'


def puntuar_textura(textura: str, categorias: dict) -> str:
    for etiqueta in ('S1','S2','S3','N'):
        if textura in categorias[etiqueta]:
            return etiqueta
    raise ValueError(f'Textura {textura} no contemplada en la matriz')


def calcular_iac_observacion(cultivo: str, fecha: date, suelo: dict, observacion: dict) -> dict:
    clave = clave_cultivo(cultivo)
    ficha = CONFIG['cultivos'][clave]
    estacion = estacion_para(fecha)
    pesos = CONFIG['estaciones'][estacion]['pesos']
    s, o, ajuste = validar_entradas(suelo, observacion)
    valores = {**o, **s}
    detalles = []
    vetos = []

    for parametro, peso in pesos.items():
        valor = valores[parametro]
        if parametro == 'suelo_textura_clase':
            cat = puntuar_textura(valor, ficha['textura'])
        elif parametro == 'suelo_carbono_organico_g_kg':
            cat = puntuar_carbono(valor, ficha['carbono_organico_minimos'])
        else:
            ajuste_param = ajuste if parametro.startswith('humedad_') else 0.0
            cat = puntuar_intervalo(valor, ficha['intervalos'][parametro], ajuste_param, parametro, clave)
        veto = parametro in ficha['veto'] and cat == 'N'
        if veto:
            vetos.append(parametro)
        detalles.append({
            'parametro':parametro,'valor':valor,'categoria':cat,
            'puntuacion':PUNTUACIONES[cat], 'peso':peso,
            'aporte_puntos':round(100*peso*PUNTUACIONES[cat],4),
            'critico':parametro in ficha['veto'],'veto_activado':veto,
        })

    bruto = round(sum(x['aporte_puntos'] for x in detalles),2)
    # La documentacion impone categoria global N para un veto critico;
    # fijamos el indice operativo en 0 (y mantenemos el bruto, sin perder trazabilidad).
    efectivo = 0.0 if vetos else bruto
    return {
        'fecha':fecha.isoformat(), 'estacion':estacion, 'cultivo':clave,
        'cultivo_nombre':ficha['nombre'], 'iac_100':efectivo,
        'iac_ponderado_antes_de_vetos_100':bruto,
        'categoria_global':'N' if vetos else None,
        'veto_activado':bool(vetos),'variables_criticas_en_N':vetos,
        'ajuste_minimo_humedad_m3m3':ajuste,
        'contribuciones':detalles,
    }


def evaluar_historial(payload: dict) -> dict:
    region = payload.get('region')
    if not isinstance(region,str) or normalizar(region) not in REGIONES:
        raise ValueError('Región inválida: use Northern, Savannah, North East, Upper East o Upper West')
    cultivo = payload.get('cultivo')
    if not isinstance(cultivo,str):
        raise ValueError('Falta el nombre de cultivo')
    # Comprobamos nombre antes de calcular.
    clave = clave_cultivo(cultivo)
    try:
        consulta = date.fromisoformat(payload['fecha_consulta'])
    except (ValueError,KeyError,TypeError) as exc:
        raise ValueError('fecha_consulta debe tener formato AAAA-MM-DD') from exc
    datos = payload.get('observaciones')
    suelo = payload.get('suelo')
    if not isinstance(datos,list) or not datos:
        raise ValueError('observaciones debe ser una lista no vacía')
    if not isinstance(suelo,dict):
        raise ValueError('suelo debe ser un objeto JSON')

    # Mismo día del año anterior, con caso excepcional de 29 de febrero.
    try:
        comienzo = consulta.replace(year=consulta.year-1)
    except ValueError:
        comienzo = consulta.replace(year=consulta.year-1,day=28)
    historial = []
    fechas = set()
    meses = set()
    for n,registro in enumerate(datos):
        if not isinstance(registro,dict):
            raise ValueError(f'Observación {n}: debe ser un objeto JSON')
        try:
            fecha = date.fromisoformat(registro['fecha'])
        except (ValueError,TypeError,KeyError) as exc:
            raise ValueError(f'Observación {n}: falta fecha AAAA-MM-DD') from exc
        if not comienzo <= fecha <= consulta:
            raise ValueError(f'{fecha}: fuera del intervalo [{comienzo}, {consulta}]')
        if fecha in fechas:
            raise ValueError(f'{fecha}: fecha duplicada')
        mes=(fecha.year,fecha.month)
        if mes in meses:
            raise ValueError(f'{fecha}: hay más de una observación en el mismo mes; '
                             'agregad los datos a un único registro mensual (lluvia en mm/30 días)')
        fechas.add(fecha);meses.add(mes)
        try:
            dato = calcular_iac_observacion(clave, fecha, suelo, registro)
        except ValueError as exc:
            raise ValueError(f'Observación {fecha}: {exc}') from exc
        historial.append(dato)
    historial.sort(key=lambda x:x['fecha'])
    actual = historial[-1]
    evolucion = [
        {'fecha':r['fecha'], 'estacion':r['estacion'],'iac_100':r['iac_100'],
         'iac_ponderado_antes_de_vetos_100':r['iac_ponderado_antes_de_vetos_100'],
         'veto_activado':r['veto_activado']}
        for r in historial
    ]
    delta = round(evolucion[-1]['iac_100']-evolucion[0]['iac_100'],2) if len(evolucion)>1 else None
    return {
        'region':region, 'cultivo':clave,'cultivo_nombre':CONFIG['cultivos'][clave]['nombre'],
        'fecha_consulta':consulta.isoformat(),'periodo_historico_permitido':[comienzo.isoformat(),consulta.isoformat()],
        'numero_meses_con_datos':len(historial),
        'ultima_observacion':actual,
        'historial_12_meses':evolucion,
        'variacion_entre_primera_y_ultima_observacion':delta,
        'metodologia':'Evaluación multicriterio ponderada con veto por factor crítico',
        'advertencia':'Historial retrospectivo; NO es una predicción, ni un porcentaje de rendimiento o pérdida de productividad. Rangos y pesos requieren validación agronómica.',
    }


def main() -> None:
    parser=argparse.ArgumentParser(description='Motor IAC ASASE para el norte de Ghana')
    parser.add_argument('entrada',type=Path,help='Ruta de un JSON con suelo y observaciones')
    parser.add_argument('-o','--salida',type=Path,help='Archivo JSON de salida (opcional)')
    args=parser.parse_args()
    try:
        entrada=json.loads(args.entrada.read_text(encoding='utf-8'))
        resultado=evaluar_historial(entrada)
    except (ValueError,FileNotFoundError,json.JSONDecodeError) as exc:
        parser.exit(2,f'ERROR: {exc}\n')
    salida=json.dumps(resultado,ensure_ascii=False,indent=2)+'\n'
    if args.salida:
        args.salida.write_text(salida,encoding='utf-8')
        print(f'Informe guardado: {args.salida}')
    else:
        print(salida,end='')


if __name__=='__main__':
    main()
