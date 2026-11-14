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
