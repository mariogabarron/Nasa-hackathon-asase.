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
Configura tu propio proyecto; ya no se utiliza el proyecto fijo del getter original. No se incluyen credenciales ni se solicitan en el frontend. Puedes comprobar las fuentes con `python comprobar_fuentes.py` después de configurar el servidor.

### Credenciales de Google Earth Engine en Vercel

1. Usa el **JSON completo de una clave de cuenta de servicio** descargado de Google Cloud (IAM y administración → Cuentas de servicio → tu cuenta → Claves → Añadir clave → JSON). Debe incluir `type`, `project_id`, `private_key_id`, `private_key`, **`client_email` y `token_uri`**; conserva también los demás campos del archivo original. Los cuatro primeros campos por sí solos no bastan.
2. En tu proyecto de Vercel, abre **Settings → Environment Variables**. Crea **`GEE_SERVICE_ACCOUNT_JSON`** y pega como valor todo el contenido del archivo, desde `{` hasta `}`. No pegues su nombre/ruta, no lo conviertas a Base64 ni añadas comillas alrededor del objeto. Conserva los `\n` de `private_key` tal como aparecen en el JSON: el backend los interpreta al leerlo.
3. Aplica la variable a **Production** y también a **Preview** si vas a consultar datos desde despliegues de prueba. Guárdala como secreto si está disponible esa opción. El backend toma el proyecto de `project_id`; solo añade **`GEE_PROJECT_ID`** si quieres usar otro proyecto con permisos para esa cuenta.
4. Despliega este código actualizado y ejecuta **Redeploy** después de guardar/cambiar variables. No hace falta ejecutar `earthengine authenticate` en Vercel ni guardar un archivo de credenciales allí.
5. Haz una consulta histórica de IAC desde el mapa para verificar el acceso real. `/health` solo comprueba que la aplicación responde; no verifica Earth Engine.

El proyecto debe estar registrado para Earth Engine, tener habilitada la Earth Engine API y permitir el acceso de la cuenta de servicio. Para las consultas, revisa el rol **Earth Engine Resource Viewer** y, cuando corresponda, **Service Usage Consumer**. Una clave válida no sustituye esos permisos.

El secreto se lee únicamente en Python, permanece en memoria y no se devuelve al navegador ni se escribe en archivos temporales. No lo pongas en `frontend/`, en `vercel.json` ni en variables con prefijos públicos (`NEXT_PUBLIC_`, `VITE_`). No subas la clave al repositorio. Los errores de configuración no muestran el contenido del JSON o la clave privada.

Para usar el mismo JSON **en local**, guárdalo fuera de `frontend/`, por ejemplo en `secrets/earthengine-key.json` (carpeta ignorada por Git):

```bash
export GEE_SERVICE_ACCOUNT_FILE="$PWD/secrets/earthengine-key.json"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

En PowerShell: `$env:GEE_SERVICE_ACCOUNT_FILE="$PWD/secrets/earthengine-key.json"`.
Prioridad: `GEE_SERVICE_ACCOUNT_JSON` → `GEE_SERVICE_ACCOUNT_FILE` → autenticación local/ADC existente. Si se define un secreto vacío o inválido, se informa del error y no se cambia silenciosamente a otra cuenta. Las credenciales se inicializan una vez por proceso; reinicia el servidor local o vuelve a desplegar al cambiarlas. La aplicación no carga archivos `.env` automáticamente.

Referencias oficiales: [cuentas de servicio de Earth Engine](https://developers.google.com/earth-engine/guides/service_account) y [variables de entorno de Vercel](https://vercel.com/docs/environment-variables/managing-environment-variables).

## Pantallas

- **Inicio de sesión:** se conserva la pantalla original y su acceso de demostración, con EN como idioma inicial y selector ES/EN. Se respeta una elección anterior guardada. No autentica usuarios: no envía ni guarda contraseñas. No protege los endpoints ni los registros locales.
- **Mapa:** histórico con fechas pasadas (hasta ayer), selector de nombres cargados desde `cultivos.json` a través de `/cultivos`, ordenado alfabéticamente en ES/EN, sin IDs visibles y con buscador (ignora acentos), mapa Leaflet con zoom, autolocalización y selección al pulsar. El panel derecho permite obtener el IAC del cultivo seleccionado. También se pueden introducir coordenadas manualmente y añadir un historial de cultivos previo. Se puede navegar por el mapamundi; solo se aceptan selecciones dentro del polígono de Ghana.
- **Recomendaciones:** selección de punto, fechas de plantación desde mañana y entre una y cinco propuestas. Las propuestas devueltas se muestran por IAC medio descendente, con días cultivados como desempate y nulos al final. Muestra las secuencias devueltas por la API, IAC de cada ciclo, fechas, ocupación y supuestos. Permite añadir historial previo y consultar el beneficio económico estimado de cada propuesta con presupuesto suficiente. No inventa recomendaciones cuando la API falla.
- **Parcelas:** crear, seleccionar, editar y eliminar parcelas; dibujar un rectángulo pulsando dos esquinas opuestas, completamente dentro de Ghana. No hay selector ni formulario de puntos en esta página. Cada parcela guarda su nombre, ubicación e historial ordenado; no existe un cultivo actual/plantado. El cultivo elegido en el selector superior sirve solo para calcular un IAC. El botón de recomendaciones está en una sección separada y tiene sus propias fechas debajo, independientes de las del IAC.
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

El historial previo se introduce manualmente, del más antiguo al más reciente. No se añade automáticamente el cultivo que se está evaluando. Mapa y Recomendaciones comparten un historial editable durante la sesión y lo envían a la API; las parcelas conservan su historial independiente. Revisa el historial si cambias de punto. El selector superior cambia únicamente el cultivo del análisis, sin guardar un cultivo plantado en la parcela.

Las recomendaciones utilizan exclusivamente el patrón mensual de 2025 que repite el motor original. No son un pronóstico meteorológico. El IAC usa las fechas observadas indicadas por el usuario. En las rotaciones, `fecha_fin` de cada tramo es exclusiva; el fin del rango solicitado es inclusivo.

Las áreas son cajas rectangulares, no polígonos catastrales: NASA POWER toma el centro; SMAP/SoilGrids promedian la caja. No se admiten cajas que crucen el antimeridiano.

### Fechas de recomendaciones y colores

Las recomendaciones, tanto por punto como por parcela, requieren ambas fechas posteriores a hoy (desde mañana, según la fecha local del navegador). Hay un mínimo en el calendario, un aviso pequeño junto a los campos y una comprobación antes de enviar. Fechas vacías, pasadas, de hoy o un rango invertido bloquean la consulta. El IAC mantiene su rango histórico independiente y el frontend solo permite fechas pasadas, hasta ayer, con mensaje de error y comprobación antes de enviar. La API conserva la posibilidad de consultar escenarios históricos para compatibilidad; esta restricción de fechas futuras pertenece al frontend.

Los IAC individuales, medios de propuesta y de cada ciclo se colorean en rojo para valores `<40`, ámbar para `40 ≤ IAC <70` y verde para `IAC ≥70`. Una leyenda acompaña los resultados; los nulos aparecen como `—` en tono neutro. Son bandas de interfaz, no una nueva calibración agronómica.

## Formato y estimación económica

Los valores visibles se truncan hacia cero: dos decimales como máximo para IAC, porcentajes, importes y superficies, y cinco para coordenadas. No se añaden ceros a enteros. Se conserva la precisión interna para consultas, cálculos y ordenación.

Cada propuesta incluye beneficio estimado, entendido como **margen antes de costes fijos**, en GHS/ha para puntos y en GHS totales para parcelas. Se suman ingresos menos costes variables de cada ciclo completo, sin ajustar el rendimiento por IAC. El presupuesto puede modificarse sin repetir la consulta climática. Los ajustes se guardan en `localStorage` (`asase.budgets.v1`) y se recuperan al recargar, sin sincronización entre dispositivos. Si el navegador impide guardar, se avisa y se mantienen solo en memoria.

Los **12 cultivos tienen ingresos y costes iniciales guardados**, con fuente, año, unidad, tratamiento elegido y conversiones en `frontend/data/economic-references.json`. El script equivalente `.js` carga exactamente esos datos sin peticiones adicionales. La página **Fuentes** presenta la tabla de los 12 cultivos y las referencias individuales.

Los importes son referencias históricas heterogéneas; **no son precios actuales ni previsiones comparables entre cultivos**. Para guisante se utiliza explícitamente un presupuesto de Horsham (Australia), convertido de AUD a GHS con tipos históricos de 2022; no está validado económicamente para Ghana. Las cifras de yuca se convierten de USD/acre a GHS/ha con el tipo de 2020, año de publicación. No se aplica una actualización general por inflación. Consulta `ECONOMIA.md` para los valores y su trazabilidad. Si el usuario borra un campo, el cálculo se bloquea en lugar de sustituirlo por cero.

Se supone que toda el área rectangular se cultiva en cada ciclo; su superficie se aproxima sobre una esfera de radio medio terrestre. El barbecho se supone sin ingresos ni costes variables. No incluye costes fijos, inversión, impuestos, descuento temporal ni ganancia incremental frente a un escenario anterior. Los márgenes negativos se muestran como pérdidas; los ciclos incompletos no se valoran. Las propuestas continúan ordenadas por IAC, no por dinero.

## Delimitación de Ghana

La geometría local proviene de [geoBoundaries gbOpen GHA ADM0](https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM0/), identificador `GHA-ADM0-71095829`, commit `9469f09`, dominio público (Stanford Digital Repository). La selección se valida en el frontend y en `/predecir`; para rectángulos se comprueba toda el área, no solo las esquinas. El mapa no tiene límites de desplazamiento ni zoom restringido al país. Fuentes documenta las fechas y procedencia de la geometría.

`frontend/data/ghana.js` es una copia generada de `ghana.geojson` para cargar la geometría sin otra petición de red. Deben actualizarse juntas; una prueba comprueba que coinciden. El backend lee el GeoJSON mediante Shapely.

## Persistencia, idiomas y errores

- Las parcelas se guardan en `localStorage`, clave `asase.parcels.v3`, sin base de datos compartida ni sincronización por cuenta. Distintos usuarios del mismo navegador/origen comparten esos registros. Borrar los datos del navegador los elimina.
- Las parcelas existentes en `asase.parcels.v3` se migran automáticamente: se elimina `cropId` conservando nombre, ubicación e historial. No se transforma ese antiguo atributo en un registro histórico inventado. Las parcelas antiguas basadas en un punto se conservan, pero requieren editar y delimitar un área antes de volver a analizarlas; no se inventa su superficie.
- Los registros regionales del frontend antiguo en `asase.records.v2` no se borran ni se migran automáticamente: no contienen coordenadas reales. Si los necesitas, crea las nuevas parcelas con su ubicación verificada.
- Si el navegador rechaza el almacenamiento, se avisa y los cambios quedan solo en memoria. Una consulta no modifica el historial ni guarda su resultado como observación histórica.
- Los resultados muestran la ubicación, las fechas, el cultivo y el historial usados. Cambiar esos parámetros invalida el resultado y descarta respuestas tardías. El botón de cancelar detiene la espera del cliente; un cálculo ya iniciado en el servidor puede terminar igualmente.
- El cliente espera hasta cuatro minutos. Expone errores de validación (422), fuentes/datos (502), configuración (503), red y respuestas inválidas, sin puntuaciones de sustitución.
- **EN es el idioma inicial** si no existe una preferencia válida, incluso si no se puede leer el almacenamiento. Una elección explícita ES/EN anterior se conserva. ES/EN se mantiene para la interfaz y todos los nombres del catálogo. Las peticiones `/predecir` incluyen `language: "es" | "en"` (la API mantiene español cuando un cliente externo omite el campo; el frontend siempre envía el idioma seleccionado). La API genera razones, justificaciones, supuestos, avisos y mensajes públicos de error en el idioma solicitado. Las claves JSON/IDs permanecen estables. Al cambiar de idioma se invalidan los resultados anteriores; la siguiente consulta responde en el nuevo idioma. No se usa traducción externa ni se mezcla el idioma entre peticiones concurrentes.

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
- `frontend/analysis-ui.js`, `economics.js`: historial, fechas, presupuesto persistente, fuentes y truncado visual.
- `frontend/data/economic-references.json`, `.js`: presupuestos documentados para los 12 cultivos.
- `scripts/build_economic_data.py`: regenera el JS desde el JSON sin alterar las cifras.
- `frontend/geo.js`, `frontend/data/ghana.*`, `geografia.py`: delimitación compartida de Ghana.
- `cultivos.json`: catálogo único del backend; no se duplica en el frontend.
- `getter.py`, `validacion.py`: fuentes y validación originales.
- `servicio.py`: agregación y orden descendente de las propuestas devueltas; la generación sigue usando la búsqueda aproximada original.
- `iac.py`, `idiomas.py`: motor con explicaciones bilingües; fórmulas y filtros conservados.
- `tests/`: pruebas originales y pruebas nuevas de integración.

Referencia de Leaflet: https://leafletjs.com/reference-1.9.4.html. Su licencia BSD se conserva en `frontend/vendor/leaflet/LICENSE`.
