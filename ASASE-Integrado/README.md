# ASASE · API y frontend integrados

Un único servidor Python sirve el frontend en `/`, los recursos en `/static` y la API original en `/cultivos`, `/predecir`, `/health` y `/docs`. No hace falta compilar el frontend ni ejecutar dos servidores.

## Arranque

Requisitos: Python 3.11 o superior, acceso a Internet para instalar dependencias, consultar las fuentes y cargar la cartografía de OpenStreetMap.

Desde esta carpeta, en macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

En Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Abre **http://localhost:8000**. No abras `frontend/index.html` directamente: sus recursos y consultas se sirven desde FastAPI.

### Activar consultas a fuentes reales

En el mismo entorno Python, autoriza una cuenta con acceso a Earth Engine y selecciona tu proyecto habilitado:

```bash
earthengine authenticate
export GEE_PROJECT_ID="TU_PROYECTO_GOOGLE_CLOUD"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

En PowerShell, establece el proyecto con `$env:GEE_PROJECT_ID="TU_PROYECTO_GOOGLE_CLOUD"`.
El getter original conserva su proyecto predeterminado; configura expresamente el tuyo si no tienes acceso a ese proyecto. No se incluyen credenciales ni se solicitan en el frontend. Puedes comprobar las fuentes con `python comprobar_fuentes.py` después de configurar el servidor.

## Pantallas

- **Inicio de sesión:** se conserva la pantalla original y su acceso de demostración, con ES/EN. No autentica usuarios: no envía ni guarda contraseñas. No protege los endpoints ni los registros locales.
- **Mapa:** rango de fechas, selector con los IDs y nombres cargados desde `cultivos.json` a través de `/cultivos`, mapa Leaflet con zoom, autolocalización y selección al pulsar. El panel derecho permite obtener el IAC del cultivo seleccionado. También se pueden introducir coordenadas manualmente.
- **Recomendaciones:** selección de punto, fechas de plantación y entre una y cinco propuestas. Muestra las secuencias devueltas por la API, IAC de cada ciclo, fechas, ocupación y supuestos. No inventa recomendaciones cuando la API falla.
- **Parcelas:** crear, seleccionar, editar y eliminar parcelas; elegir un punto representativo o dibujar un rectángulo pulsando dos esquinas opuestas. Cada parcela guarda su nombre, cultivo e historial ordenado. Permite calcular el IAC del cultivo elegido en el selector superior o solicitar recomendaciones para su ubicación e historial.
- **Fuentes:** explicación del origen de datos, alcance del motor y acceso a la documentación de la API.

La geolocalización necesita permiso del navegador y un contexto seguro: HTTPS o localhost. La selección manual sigue disponible si se deniega el permiso. Leaflet 1.9.4 está incluido en `frontend/vendor`; las teselas se descargan de OpenStreetMap y conservan su atribución.

## Fechas, coordenadas e historial

| Concepto | Contrato enviado a la API |
| --- | --- |
| Punto | `point: [latitud, longitud]` |
| Parcela rectangular | `bbox: [min_lat, min_lon, max_lat, max_lon]`; no se envía `point` |
| IAC | `accion: "iac"`, `cultivo_id` numérico y período observado inclusivo de hasta 365 días |
| Recomendaciones | `accion: "rotaciones"`, `n_recomendaciones` y rango de plantación inclusivo; sin `cultivo_id` |
| Historial | Lista de IDs numéricos, del más antiguo al más reciente; máximo 100 |

El historial previo no debe incluir el cultivo que se está evaluando. Se edita manualmente: cambiar el cultivo actual no inventa un nuevo registro histórico. Las consultas de puntos independientes envían historial vacío. El selector superior cambia el cultivo del análisis; para cambiar el cultivo guardado se usa **Editar** en la parcela.

Las recomendaciones utilizan exclusivamente el patrón mensual de 2025 que repite el motor original. No son un pronóstico meteorológico. El IAC usa las fechas observadas indicadas por el usuario. En las rotaciones, `fecha_fin` de cada tramo es exclusiva; el fin del rango solicitado es inclusivo.

Las áreas son cajas rectangulares, no polígonos catastrales: NASA POWER toma el centro; SMAP/SoilGrids promedian la caja. No se admiten cajas que crucen el antimeridiano.

## Persistencia, idiomas y errores

- Las parcelas se guardan en `localStorage`, clave `asase.parcels.v3`, sin base de datos compartida ni sincronización por cuenta. Distintos usuarios del mismo navegador/origen comparten esos registros. Borrar los datos del navegador los elimina.
- Los registros regionales del frontend antiguo en `asase.records.v2` no se borran ni se migran automáticamente: no contienen coordenadas reales. Si los necesitas, crea las nuevas parcelas con su ubicación verificada.
- Si el navegador rechaza el almacenamiento, se avisa y los cambios quedan solo en memoria. Una consulta no modifica el historial ni guarda su resultado como observación histórica.
- Los resultados muestran la ubicación, las fechas, el cultivo y el historial usados. Cambiar esos parámetros invalida el resultado y descarta respuestas tardías. El botón de cancelar detiene la espera del cliente; un cálculo ya iniciado en el servidor puede terminar igualmente.
- El cliente espera hasta cuatro minutos. Expone errores de validación (422), fuentes/datos (502), configuración (503), red y respuestas inválidas, sin puntuaciones de sustitución.
- ES/EN se conserva para la interfaz y los nombres de cultivos. Las explicaciones libres de la API permanecen en español y se muestran sin traducción automática.

## Pruebas

Pruebas del motor, API e integración HTTP:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Pruebas del frontend y su contrato con la API (Node.js 18+; Node solo se necesita para las pruebas):

```bash
npm install
npm test
```

Ejecuta las pruebas con el entorno Python anterior activado. El puente usa `python3` de forma predeterminada; en Windows o para otro intérprete define `ASASE_TEST_PYTHON` con su ruta. Por ejemplo, en PowerShell: `$env:ASASE_TEST_PYTHON=(Resolve-Path .venv\Scripts\python.exe).Path`.

Las pruebas DOM cargan Leaflet real y ejercitan los formularios, selección, zoom, geolocalización simulada, consultas y persistencia. Llaman al TestClient de la API real con datos diarios sintéticos en lugar de fuentes remotas. No equivalen a una descarga autenticada de Earth Engine ni a una revisión visual de navegador.

Consulta `VERIFICACION-INTEGRACION.md` para los resultados y las limitaciones verificadas. `API.md` y `MOTOR.md` conservan la documentación del backend original.

## Archivos principales

- `main.py`: endpoints originales y servicio estático del frontend.
- `frontend/index.html`: entrada de la aplicación.
- `frontend/base.js`, `original.css`: pantalla de acceso, traducciones, iconos y base visual conservados.
- `frontend/app.js`, `app.css`: páginas integradas, cliente API, Leaflet y parcelas.
- `cultivos.json`: catálogo único del backend; no se duplica en el frontend.
- `getter.py`, `servicio.py`, `iac.py`, `validacion.py`: motor y fuentes originales, sin cambios.
- `tests/`: pruebas originales y pruebas nuevas de integración.

Referencia de Leaflet: https://leafletjs.com/reference-1.9.4.html. Su licencia BSD se conserva en `frontend/vendor/leaflet/LICENSE`.
