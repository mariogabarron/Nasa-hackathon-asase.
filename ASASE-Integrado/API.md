# ASASE · API predictora

Python 3.11+. Desde esta carpeta:

```bash
python3 -m pip install -r requirements.txt
earthengine authenticate
export GEE_PROJECT_ID="gen-lang-client-0182377274"
uvicorn main:app --host 127.0.0.1 --port 8000
```

Documentación interactiva: http://127.0.0.1:8000/docs

## POST /predecir

```json
{
  "start_date": "2026-04-01",
  "end_date": "2028-03-31",
  "point": [6.6885, -1.6244],
  "bbox": null,
  "historial": [1, 5],
  "accion": "rotaciones"
}
```

## Rotaciones: fechas de plantación

- start_date es el primer día donde se quiere plantar; end_date es el último,
  incluido. Se permiten períodos superiores a 365 días.
- end_date omitido o null: un año natural desde start_date, hasta la víspera
  del aniversario. Puede abarcar 365 o 366 días. Para el 29 de febrero, el
  aniversario se define como el 28 de febrero del año siguiente.
- Se descarga UNA tabla del 1 de enero al 31 de diciembre de 2025 para la
  ubicación indicada. No se consultan datos futuros.
- Se obtienen los agregados por mes de 2025: extremos térmicos, lluvia
  acumulada y medias aritméticas de las demás variables. Ese patrón mensual
  se repite en cada año solicitado. Un febrero bisiesto usa la misma tasa
  diaria y las mismas condiciones del febrero de 2025 (28 días).
- Cada ciclo se evalúa en todos los meses que atraviesa. No se utiliza una
  única media anual como clima de todas las estaciones.
- Se prioriza la suma de días cultivados. A igual ocupación, se elige mayor
  suma de IAC por días cultivados. La búsqueda en haz es aproximada y no
  garantiza el óptimo global.
- No se impone una espera de preparación: cosecha y nueva siembra pueden
  coincidir. Se mantienen alternancia de familias, IAC mínimo y filtros
  térmicos/hídricos. Solo se incluyen ciclos completos que caben en el plazo.
- Los días no ocupados se muestran como barbecho. Un plazo más corto que
  cualquier ciclo admisible puede devolver solo barbecho.
- La respuesta incorpora dias_cultivados, porcentaje_ocupacion, referencia,
  periodo_plantacion y la justificación de cada tramo.
- Las fechas de los tramos son [fecha_inicio, fecha_fin): su final es exclusivo.
  Por eso el final global es el día posterior al end_date solicitado.

Esto es un escenario basado en 2025, no una predicción meteorológica. Que una
fecha sea favorable en 2025 no garantiza las mismas condiciones en otro año.

## IAC: fechas observadas

Para accion=iac, start_date y end_date siguen siendo el período observado.
end_date es obligatorio y el máximo es 365 días. La consulta se hace sobre
esas fechas, sin cambiarlas a 2025. cultivo_id opcional selecciona un cultivo;
si se omite devuelve los 12 resultados, identificados por ID. Cada resultado
contiene únicamente iac y razon. El IAC usa la estación de end_date.

## Localización e historial

Indicar exactamente uno: point=[latitud,longitud] o
bbox=[min_lat,min_lon,max_lat,max_lon]. Para BBOX, POWER representa su centro;
SMAP/SoilGrids promedian el área. No se admiten cajas que crucen el antimeridiano.

historial contiene IDs del más antiguo al más reciente. No se inventan fechas;
los ajustes iniciales no decaen temporalmente. Los coeficientes del historial
son heurísticos, no cambios medidos del suelo. Véase MOTOR.md para la fórmula.

## Nulos

Se omiten nulos, infinitos y centinelas en medias y extremos. Una variable
enteramente ausente se excluye del IAC y los pesos restantes se renormalizan.
Si falta precipitación de algún día, se excluye ese factor: no se reemplaza por
cero ni se confunde una suma parcial con una completa. La textura se conserva
pero no entra en el IAC. La respuesta indica la cobertura y las limitaciones.
Las variables ausentes no pueden comprobarse en los filtros de rotación.
Sin ninguna variable utilizable no puede obtenerse un IAC y se informa error.

## Integración y pruebas

servicio.predecir acepta los mismos argumentos que el endpoint y permite
inyectar getter=funcion para usar otro getter con la misma firma. Cada acción
consulta una sola tabla. La API no persiste historial. GET /cultivos lista
los IDs y GET /health comprueba el proceso, no las fuentes externas.
CORS_ORIGINS permite configurar orígenes del frontend separados por comas.

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 comprobar_fuentes.py
```

63 tests superados, incluidos períodos multianuales, fecha final omitida,
año bisiesto, referencia exclusiva a 2025, nulos y HTTP. Las respuestas
remotas de estas pruebas son controladas. SMAP/SoilGrids requieren credenciales
Earth Engine; no se ha completado aquí una descarga real de esas fuentes.
El script comprobar_fuentes.py permite verificarla en el servidor autorizado.

Errores: 422 entrada inválida; 502 fuente/datos insuficientes; 503 credenciales.


## Varias recomendaciones

La acción rotaciones admite n_recomendaciones, entero positivo estricto,
por defecto 3. Ejemplo: añadir `"n_recomendaciones": 5` a la petición.
No se admite este campo explícito en peticiones iac.

La respuesta añade:
- recomendaciones: lista de planes devueltos, ordenados por IAC medio ponderado por días
  descendente y, en caso de empate, días cultivados descendentes; nulos al final.
  Cada plan incluye posicion (1 = mejor IAC medio entre las propuestas devueltas).
- criterio_orden: descripción del criterio de presentación. Los campos del nivel
  superior corresponden a la primera propuesta de este orden.
- n_solicitadas y n_devueltas.
- aviso_recomendaciones cuando se encontraron menos alternativas.

Los campos de la mejor opción (rotacion, dias_cultivados, etc.) se mantienen
al nivel superior por compatibilidad. El frontend puede mostrar cada elemento
de recomendaciones. Dos planes son diferentes si sus secuencias ordenadas de
IDs de cultivo son diferentes. Para una misma secuencia se conserva el mejor
calendario encontrado; cambiar solo fechas no crea una alternativa.

Se reutiliza una única descarga de 2025 para toda la búsqueda. Los resultados
son los mejores encontrados por una búsqueda aproximada, no un top-N global
garantizado. Si no cabe ningún cultivo, se devuelve una única propuesta de
barbecho con explicación, nunca N copias del mismo plan.


## Idioma de las respuestas

`POST /predecir` admite `"language": "es"` o `"language": "en"`; por defecto `es`.
Se localizan los nombres de cultivos en las rotaciones, razones del IAC,
justificaciones, supuestos, avisos y errores públicos. Se conservan las claves
JSON, valores de enumeraciones, IDs y resultados numéricos. Un idioma no
admitido devuelve 422. `GET /cultivos?language=en` ofrece el catálogo en inglés.

Ejemplo:

```json
{
  "start_date": "2027-01-01",
  "end_date": "2027-12-31",
  "point": [9.4, -0.84],
  "accion": "rotaciones",
  "n_recomendaciones": 3,
  "language": "en"
}
```

La búsqueda original prioriza ocupación y genera propuestas distintas. Tras esa
búsqueda, el servicio ordena las propuestas encontradas por IAC medio descendente.
No es una garantía de óptimo global. La validación de fechas futuras de las
recomendaciones se aplica en la interfaz; la API sigue admitiendo escenarios
históricos para otros clientes y pruebas.


## Cobertura territorial de esta integración

`POST /predecir` acepta únicamente puntos o áreas completamente cubiertos por el polígono de Ghana incluido en el proyecto. Una selección exterior devuelve 422 antes de consultar las fuentes. El orden de coordenadas y los demás campos se mantienen. El frontend restringe las fechas IAC al pasado y las recomendaciones al futuro; la API conserva la compatibilidad temporal del motor.

La estimación económica es un cálculo de presupuesto en el frontend, independiente del contrato y las puntuaciones de `/predecir`. Se documenta en la página Fuentes y en README.md.
