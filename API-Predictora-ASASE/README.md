# ASASE · API predictora integrada

Integra el getter proporcionado, la agregación del período y el motor IAC.
Python **3.11 o posterior** (verificado con Python 3.12). Endpoint:
`POST /predecir`. Las acciones son exactamente **`iac`** y **`rotaciones`**.

## Arrancar

Desde esta carpeta:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
earthengine authenticate
export GEE_PROJECT_ID="gen-lang-client-0182377274"
uvicorn main:app --host 127.0.0.1 --port 8000
```

El proyecto debe estar autorizado para Earth Engine y la cuenta debe tener
acceso. En producción pueden usarse credenciales predeterminadas de Google
del servidor; `ee.Initialize` las admite. No se incluyen claves en el paquete
ni se lanza un login interactivo durante una petición HTTP.

Documentación de la API: <http://127.0.0.1:8000/docs>.
`GET /cultivos` devuelve IDs, nombres, familias y duraciones.
`GET /health` comprueba el proceso, **no** la disponibilidad de las fuentes.
Para otro origen del frontend, configurar antes de arrancar:

```bash
export CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
```

## Petición del frontend

```json
{
  "start_date": "2025-04-01",
  "end_date": "2025-04-03",
  "point": [9.4, -0.84],
  "bbox": null,
  "historial": [1, 5],
  "accion": "iac",
  "cultivo_id": 1
}
```

```bash
curl -X POST http://127.0.0.1:8000/predecir \
  -H 'Content-Type: application/json' \
  --data-binary @ejemplo_peticion_iac.json
```

| Campo | Contrato |
|---|---|
| `start_date`, `end_date` | `YYYY-MM-DD`, ambas fechas incluidas; entre 1 y 366 días |
| `point` | `[latitud, longitud]` o `null` |
| `bbox` | `[min_lat, min_lon, max_lat, max_lon]` o `null` |
| `historial` | Lista de IDs del más antiguo al más reciente; `[]` si no hay historial |
| `accion` | `iac` o `rotaciones` |
| `cultivo_id` | Opcional, solo para `iac`; selecciona el cultivo que se evalúa |

Se exige **exactamente una** localización: `point` o `bbox`. No se soportan
cajas que crucen el antimeridiano. Los IDs deben ser enteros conocidos.
Las repeticiones de un ID en el historial representan distintas siembras.
El historial contiene cultivos **anteriores**, no el cultivo objetivo.

### Respuesta de `iac`

El IAC depende del cultivo: no hay un único IAC independiente del cultivo.
Con `cultivo_id`, devuelve únicamente:

```json
{"iac": 85.0, "razon": "Descripción del factor que más puntos resta"}
```

Este JSON es ilustrativo. Si todos los factores son ideales y no hay ajuste
histórico, `razon` es `null`.

**Sin `cultivo_id`**, funciona con los argumentos solicitados originalmente
y devuelve un objeto con los **12 IDs como claves**, cada uno asociado a su
`{"iac": ..., "razon": ...}`. No se interpreta el último ID del historial
como el cultivo objetivo.

### Respuesta de `rotaciones`

Cambiar `accion` a `rotaciones` y omitir `cultivo_id`. La respuesta incluye
`rotacion`, fechas, duración e IAC estimado por ciclo, justificación y supuestos.
Empieza **el día siguiente a `end_date`** y cubre un año completo: 365 o 366 días.
No se recortan ciclos y los huecos se cubren con preparación o barbecho.

Con estos argumentos no hay previsión del clima futuro: la propuesta reutiliza
el agregado observado como **escenario constante**, variando los pesos por
estación. Se declara en la respuesta. Si el período es antiguo, la rotación
es posterior a ese período, no necesariamente posterior a hoy.

## Reglas exactas de agregación

| Entrada del motor | Agregación de la tabla diaria |
|---|---|
| `temp_min_C` | Mínimo de todas las temperaturas mínimas diarias |
| `temp_max_C` | Máximo de todas las temperaturas máximas diarias |
| `precipitacion_mm` | Suma de todos los días |
| `suelo_textura_clase` | Misma cadena original, sin transformar |
| Temperatura media, radiación, ambas humedades, temperatura del suelo, pH y carbono | Media aritmética de todos los días, con igual peso por día |

`Territorio.fecha = end_date` selecciona los pesos estacionales del IAC.
Si el período cruza estaciones, se evalúa el agregado con la estación del
último día; no se calcula la media de varios IAC diarios.

`dias_precipitacion = (end_date - start_date).days + 1`. Se pasa automáticamente
al motor para que el intervalo de lluvia del ciclo se prorratee al período
observado. Se mantienen las unidades originales: °C, mm, MJ/m²/día, m³/m³,
pH y g/kg. Se conserva la conversión Kelvin → °C de SMAP.

La textura se conserva en `Territorio` y **no entra en el IAC**, como se pidió
para el algoritmo anterior. Latitud/longitud son las del punto o el centro de
la caja. Se genera un identificador de parcela a partir de esa localización.

## Historial solo con IDs

El motor anterior aceptaba fechas. Esta integración añade `historial_ids`
sin crear fechas de siembra o cosecha ficticias:

- Mismo cultivo: ajuste provisional de 0.15 por registro.
- Misma familia y otra especie: 0.08 por registro.
- Otra familia: 0.
- Suma limitada a 0.25; `IAC = IAC_base × (1 - ajuste)`.
- Sin fechas, **no se aplica decaimiento temporal** ni se infiere qué registros
  pertenecen al último año. El cliente debe enviar el historial pertinente.
- En la rotación, el último ID indica la familia anterior; los cultivos
  propuestos sí tienen fechas y se incorporan al historial simulado.

Estos coeficientes son las reglas provisionales del prototipo, no datos del
PDF ni cambios medidos en el suelo. No se vuelve a descontar carbono/agua
de los valores ya observados. El motor conserva sus funciones anteriores con
historial fechado. Ver `MOTOR.md` para el modelo y sus limitaciones.

## Correcciones del getter

1. BBOX funciona con `point=None`: no se accede a `point[0]` antes de elegir modo.
2. Ambas fechas son inclusivas. Para Earth Engine, cuyo final es exclusivo,
   se consulta hasta `end_date + 1 día`.
3. POWER utiliza días UTC para alinearse con la agrupación de SMAP.
4. Unión externa y calendario esperado: ningún día desaparece por un `inner join`.
5. Se rechazan días ausentes/duplicados, NaN, infinitos, centinelas y valores
   diarios físicamente inválidos antes de agregar. No se convierte lluvia
   desconocida en cero ni se calculan medias con distintos días por columna.
6. Se conserva un carbono de valor cero; ya no se confunde con un valor ausente.
7. Se elimina el código de exportación CSV que estaba después de `return`.
8. SMAP se reduce a datos diarios en el servidor, por lotes de hasta 31 días,
   evitando descargar todos los píxeles de una BBOX mediante `getRegion`.
9. Se requiere presencia de las 8 escenas de SMAP por día; un dato reciente
   aún incompleto produce un error. Esto no certifica cobertura espacial completa
   de cada escena: las medias regionales se calculan sobre píxeles disponibles.
10. No se redondean los datos antes del cálculo; el IAC público se redondea al final.

Se conserva la semántica espacial del getter: **POWER consulta el centro de
la BBOX**, mientras que SMAP/SoilGrids promedian el área. No es una media
regional de POWER. También se conserva la media simple de las tres capas de
SoilGrids del código recibido; no se cambia por una ponderación por espesores.

## Integrarlo en una API existente

La carpeta no depende de un repositorio o servidor externo. Si ya tenéis una
aplicación, importad el servicio en vuestro endpoint:

```python
from servicio import predecir

resultado = predecir(
    start_date="2025-04-01",
    end_date="2025-04-03",
    point=[9.4, -0.84],
    bbox=None,
    historial=[1, 5],
    accion="iac",
    cultivo_id=1,
)
```

`getter=otra_funcion_get_tabla` permite inyectar otro getter manteniendo los
mismos cuatro argumentos. Debe devolver la tabla completa con las columnas
esperadas y una fila por día. Solo se llama una vez por petición, aunque se
evalúen los 12 cultivos.

Errores HTTP: `422` entrada inválida; `502` datos incompletos o fallo de fuente;
`503` falta de configuración/autorización de Earth Engine. La API no almacena
el historial: el frontend/backend debe enviar la lista completa relevante.

## Verificación

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 comprobar_fuentes.py
```

La última orden **sí consulta servicios reales** y necesita Earth Engine
autorizado. Ejecuta getter → agregado → IAC y rotaciones, y sale con código
distinto de cero ante errores. No inventa un resultado si falta una fuente.

Ver `VERIFICACION.md` para lo comprobado al entregar. Los tests automáticos
usan datos controlados y respuestas remotas simuladas; no sustituyen a esta
última comprobación en el servidor autorizado.

## Documentación técnica consultada

- [Earth Engine: final de filterDate exclusivo](https://developers.google.com/earth-engine/apidocs/ee-imagecollection-filterdate)
- [Earth Engine: autenticación e inicialización](https://developers.google.com/earth-engine/guides/auth)
- [SMAP L4 versión 008](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008)
- [NASA POWER: API diaria](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [FastAPI: pruebas con TestClient](https://fastapi.tiangolo.com/tutorial/testing/)
