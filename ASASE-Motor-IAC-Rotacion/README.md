# ASASE · Motor de IAC y rotación anual

Python 3.10 o posterior. Sin paquetes externos. Incluye las dos dataclasses,
los 12 cultivos del JSON proporcionado, cálculo explicable, ajuste por historial,
planificación anual y un adaptador JSON para el backend.

**Es un modelo heurístico de aptitud, no un predictor validado de rendimiento.**
Un IAC de 80 no significa un 80 % de productividad ni una probabilidad del 80 %.
Los pesos proceden del PDF aportado; las reglas adicionales se detallan abajo.

## 1. Ejecutar

Desde esta carpeta:

```bash
python3 iac.py ejemplo_iac.json
python3 iac.py ejemplo_historial.json
python3 iac.py ejemplo_rotacion.json
python3 iac.py ejemplo_rotacion_mensual.json
python3 -m unittest -v
```

Los ejemplos utilizan **datos sintéticos**, no mediciones de una parcela real.
El primero devuelve:

```json
{"iac": 100.0, "razon": null}
```

El ejemplo con historial devuelve:

```json
{
  "iac": 85.49,
  "razon": "Historial: repetición de Maíz. El ajuste acumulado por repetición reduce 14.51 puntos; regla provisional, no deterioro medido del suelo."
}
```

## 2. Uso desde Python

```python
import json
from pathlib import Path
from iac import Territorio, cargar_cultivos, calcular_iac, cargar_historial

catalogo = cargar_cultivos('cultivos.json')
datos = json.loads(Path('ejemplo_iac.json').read_text(encoding='utf-8'))
territorio = Territorio(**datos['territorio'])

resultado = calcular_iac(
    territorio,
    catalogo[1],
    dias_precipitacion=30,
)

# Recalcular usando registros del frontend:
historial = cargar_historial([
    {
        'territorio_id': territorio.id,
        'cultivo_id': 1,
        'fecha_inicio': '2025-11-20',
        'fecha_fin': '2026-03-20',
    }
])
recalculado = calcular_iac(
    territorio, catalogo[1],
    dias_precipitacion=30,
    historial=historial,
    catalogo=catalogo,
)
```

La salida pública contiene **solo `iac` y `razon`**. `razon` es `null` si no
hay ninguna pérdida. En otro caso identifica la mayor pérdida ponderada,
incluso si el IAC no es bajo. Bajo 40 añade «IAC bajo»; el umbral es configurable.
Para depurar el modelo, `evaluar_iac()` devuelve además pesos, puntuaciones,
pérdidas, estación e IAC antes del historial. No hace falta enviar ese detalle
al frontend.

`Cultivo.id` es `int` y su carbono es `float`, corrigiendo `Int` y `floa` del
esquema original. Los intervalos JSON se convierten a tuplas. La textura se
acepta en el JSON pero se excluye de todos los cálculos.

## 3. Pesos y fórmula

Fuente: «Matriz de Pesos y Justificacion Agronomica - Norte de Ghana 2(1).pdf»,
página 2. Se conservan las celdas originales. Las columnas completas suman 1.

| Parámetro | Abr–Jun | Jul–Sep | Oct–Nov | Dic–Mar |
|---|---:|---:|---:|---:|
| Temperatura media | 0.05 | 0.08 | 0.10 | 0.08 |
| Temperatura mínima | 0.03 | 0.03 | 0.04 | 0.07 |
| Temperatura máxima | 0.08 | 0.04 | 0.08 | 0.14 |
| Precipitación | 0.22 | 0.24 | 0.12 | 0.04 |
| Radiación solar | 0.06 | 0.12 | 0.14 | 0.08 |
| Humedad superficial | 0.24 | 0.07 | 0.06 | 0.15 |
| Humedad radicular | 0.08 | 0.18 | 0.22 | 0.24 |
| Temperatura del suelo | 0.08 | 0.03 | 0.04 | 0.05 |
| pH | 0.05 | 0.07 | 0.06 | 0.05 |
| Carbono orgánico | 0.06 | 0.07 | 0.07 | 0.05 |
| **Suma sin textura** | **0.95** | **0.93** | **0.93** | **0.95** |

Se divide cada peso por la suma de su columna, por lo que la suma efectiva
vuelve a ser 1. La fecha selecciona la estación del **norte de Ghana**; no se
deduce un régimen climático distinto a partir de latitud y longitud.

```text
w_normalizado[i] = peso_pdf[i] / suma_pesos_sin_textura
IAC_base = 100 × suma(w_normalizado[i] × idoneidad[i])
perdida[i] = 100 × w_normalizado[i] × (1 - idoneidad[i])
```

La razón es el factor con mayor pérdida de puntos, no necesariamente el de
peor puntuación individual. Por ejemplo, una humedad superficial moderadamente
inadecuada puede pesar más que un carbono muy bajo en abril.

## 4. Conversión de valores a idoneidad

El material recibido aporta intervalos ideales, pero no todas las curvas de
respuesta ni los umbrales de inviabilidad. Estas son las **convenciones del
prototipo**, separadas de los pesos del PDF:

- **Intervalos ordinarios:** puntuación 1 dentro de `[a,b]`; fuera, cae
  linealmente hasta 0 a una distancia de `b-a` del intervalo. Fórmula:
  `max(0, 1 - max(a-x, 0, x-b)/(b-a))`.
- **Temperatura media:** trapecio con meseta ideal y puntuación 0 en los
  topes térmicos indicados por el cultivo.
- **Temperatura mínima:** 0 en/bajo el tope inferior y 1 desde el mínimo
  ideal; interpolación lineal entre ambos.
- **Temperatura máxima:** 1 hasta el máximo ideal y 0 en/sobre el tope
  superior; interpolación lineal entre ambos.
- **Carbono:** el único valor se interpreta como objetivo mínimo, con
  `min(1, carbono_observado/carbono_objetivo)`; no se penaliza el superávit.

`margenes={'suelo_ph_0_30cm': 0.5}` permite, por ejemplo, que el pH llegue a
puntuación 0 a media anchura de intervalo. Este parámetro se admite en
`calcular_iac()` y `evaluar_iac()`. No representa una tolerancia validada.
Las puntuaciones se limitan a `[0,1]`; el IAC final, a `[0,100]`.

La suma ponderada permite que otros factores compensen uno muy adverso.
No se ha añadido un veto térmico al IAC solicitado. La función de rotación
sí utiliza filtros de admisibilidad para no escoger ciertos casos extremos.

### Período de precipitación: dato necesario

Los intervalos del JSON se interpretan como **totales por ciclo de cultivo**.
No se puede comparar directamente una lluvia de 30 días con una necesidad de
120 días. La API exige `dias_precipitacion`, que indica los días correspondientes
al acumulado observado. Se adapta el intervalo:

```text
ideal_lluvia_periodo = ideal_lluvia_ciclo × dias_precipitacion / duracion_ciclo_dias
```

Esto supone una distribución uniforme de las necesidades. No sustituye a un
balance hídrico ni modela lluvias intensas, duración de sequías o fases del cultivo.
Si el dato representa 365 días, enviar `365`; **no se infiere el período de
`fecha` ni se utiliza siempre un año por defecto**.

Solo en la función Python `calcular_iac(t, c)`, omitir el período significa
que el acumulado ya corresponde al ciclo completo de ese cultivo. Para
comparar varios cultivos sobre una misma observación, especificarlo siempre.

## 5. Historial y recálculo

Formato del array `historial` recibido desde el frontend:

```json
[
  {
    "territorio_id": "parcela-001",
    "cultivo_id": 1,
    "fecha_inicio": "2025-11-20",
    "fecha_fin": "2026-03-20"
  }
]
```

`fecha_fin` es exclusiva: un ciclo termina al comenzar ese día. El historial
debe contener solo ciclos completados en la parcela consultada. Se rechazan
IDs desconocidos, registros futuros/activos, duplicados y ciclos solapados.
No se soportan cultivos simultáneos o asociaciones dentro de la misma parcela.

**El PDF no aporta pesos de efectos históricos.** Con solo los nombres y
fechas de cultivos no es posible deducir cuántos g/kg de carbono se han perdido
ni cuánto nitrógeno queda. El código conserva las mediciones y añade un ajuste
heurístico por repetición; no vuelve a descontar carbono o humedad ya medidos.

| Regla provisional por registro | Coeficiente |
|---|---:|
| Repetición del mismo cultivo | 0.15 |
| Misma familia, otra especie | 0.08 |
| Otra familia | 0.00 |
| Tope del ajuste acumulado | 0.25 |

No se suman las dos primeras reglas para un mismo registro. Cada efecto
decrece linealmente con los días desde la cosecha y desaparece a los 365 días:

```text
P = min(0.25, suma(coeficiente × max(0, 1 - dias_desde_fin/365)))
IAC_final = IAC_base × (1 - P)
perdida_historial = IAC_base × P
```

La razón pública compara la pérdida del historial acumulado con cada pérdida
ambiental y elige la mayor. Si gana el historial, identifica su repetición
principal y aclara que el ajuste es provisional. Las pérdidas suman exactamente
`100 - IAC_final` antes del redondeo.

Se pueden recalibrar o desactivar estas reglas en el servidor:

```python
from iac import Configuracion

config = Configuracion(
    penalizacion_mismo_cultivo=0.15,
    penalizacion_misma_familia=0.08,
    penalizacion_historial_max=0.25,  # Usar 0 para desactivar el ajuste.
    ventana_historial_dias=365,
    umbral_iac_bajo=40,
)
```

No se asigna una bonificación automática a las leguminosas: faltan datos de
nutrientes, manejo y residuos que permitan cuantificarla.

## 6. Rotación de un año

```python
from iac import recomendar_rotacion

plan = recomendar_rotacion(
    territorio, catalogo,
    dias_precipitacion=30,
    historial=historial,
    iac_minimo=60,
    dias_entre_cultivos=7,
)
```

Devuelve un calendario continuo desde `territorio.fecha` hasta su aniversario:
365 o 366 días. Para un inicio el 29 de febrero, el final es el 28 de febrero
del año siguiente. Todos los intervalos son `[fecha_inicio, fecha_fin)`.

El calendario incluye cultivos con sus fechas, duración, IAC estimado y breve
justificación, y cubre los días restantes con preparación o barbecho. Los
ciclos **no se recortan** para hacerlos caber. «Rotación anual completa» significa
cobertura de todo el calendario, no cultivar obligatoriamente todos los días.

La búsqueda en haz explora siembras inmediatas y esperas hasta el mes siguiente,
retiene hasta 64 estados por iteración y maximiza la suma `IAC × días cultivados`.
Es una aproximación; no garantiza el óptimo global ni maximiza beneficio económico.
Se puede ampliar `ancho_busqueda` a cambio de más trabajo de cálculo.

Restricciones del prototipo:

1. No repetir consecutivamente familia botánica, incluyendo el último cultivo
   histórico. El barbecho no borra por sí solo esa restricción.
2. Aplicar los pesos de cada mes atravesado por el ciclo, promediando por días.
3. Recalcular el ajuste histórico en la fecha de siembra de cada ciclo y
   mantenerlo fijo durante su evaluación. Los ciclos propuestos pasan al
   historial simulado para las siguientes elecciones.
4. Exigir IAC ajustado mínimo de 60 en **cada tramo mensual**, no solo en media.
5. Exigir puntuaciones térmicas positivas y puntuación de al menos 0.25 en
   precipitación, humedad superficial y humedad radicular en cada tramo.
6. Reservar 7 días de preparación entre ciclos, configurables; si el último
   cultivo histórico terminó hace menos días, completar ese margen inicial.
7. Admitir barbecho si no se selecciona un ciclo que quepa y supere los filtros.

El filtro de precipitación supone una evaluación de **secano**: no se infiere
riego de la humedad ni se contabiliza agua de riego. Para adaptar el modelo a
regadío hacen falta entradas y reglas específicas.

### Escenarios mensuales opcionales

Con un único `Territorio` no se conocen las condiciones futuras. Si no se
aportan escenarios, la salida declara `modo: "escenario_constante"`: conserva
los valores observados durante el año y cambia los pesos según la fecha.
Por tanto, **no debe presentarse como pronóstico climático o productivo**.

Para datos futuros o climatológicos preparados por vuestro backend:

```python
plan = recomendar_rotacion(
    territorio, catalogo,
    dias_precipitacion=30,
    historial=historial,
    escenarios={
        '2026-04': {
            'territorio': datos_abril,
            'dias_precipitacion': 30,
        },
        # Un objeto equivalente por TODOS los meses cubiertos por el plan.
    },
)
```

El ejemplo completo está en `ejemplo_rotacion_mensual.json`; sus escenarios
también son sintéticos. Si falta algún mes o pertenece a otra parcela, se
rechaza la petición. No se reemplazan meses ausentes por datos actuales.
El mes de cada objeto debe coincidir con su `fecha`.

## 7. Contrato con el backend

`procesar_peticion(payload, catalogo)` recibe un diccionario ya deserializado
y devuelve otro serializable en JSON. Es independiente del framework; no
levanta un servidor, no consulta APIs y no persiste registros por sí mismo.

Para IAC, el frontend envía:

```python
payload = {
    'accion': 'iac',
    'territorio': datos_territorio,
    'cultivo_id': 1,
    'dias_precipitacion': 30,
    'historial': registros_de_la_parcela,  # [] si todavía no hay registros.
}
respuesta = procesar_peticion(payload, catalogo)
# respuesta contiene únicamente iac y razon.
```

Para rotación, enviar `accion: "rotacion"`, sin `cultivo_id`. Se aceptan
`escenarios`, `iac_minimo`, `idoneidad_hidrica_minima`, `dias_entre_cultivos` y
`ancho_busqueda`. La respuesta incluye el calendario y la justificación.

El backend debe conservar el historial y volver a enviar **el conjunto completo
de registros de la parcela**, no solo el último añadido. Filtrar por la parcela
y controlar sus permisos antes de llamar al motor. `ValueError` indica datos
inválidos y puede convertirse en HTTP 400/422. El catálogo debe cargarse una
vez al iniciar el servidor; no debe depender de parámetros modificables por
el frontend.

## 8. Qué se ha verificado

Pruebas automáticas de pesos estacionales, máximos de 100, textura ignorada,
unidades de lluvia, límites térmicos, selección de la mayor pérdida ponderada,
historial y caducidad, conservación de pérdidas, validación de datos y contrato
JSON, cobertura anual, ciclos completos, alternancia, sequía, escenarios
mensuales y año bisiesto. Estos tests verifican el software; no validan
agronómicamente los coeficientes del prototipo.
