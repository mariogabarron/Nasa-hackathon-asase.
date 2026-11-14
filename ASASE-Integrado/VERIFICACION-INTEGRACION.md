# Verificación de la integración

Fecha: 14 de noviembre de 2026.

## Resultado

- **71 pruebas Python superadas:** 67 originales del motor, agregación, fuentes controladas y API; cuatro nuevas del empaquetado web, recursos estáticos, catálogo y disponibilidad de documentación.
- **6 escenarios de interfaz superados** con jsdom y Leaflet 1.9.4 real:
  1. Conservación del acceso y ES/EN, zoom, selección del punto, carga de los 12 cultivos y petición IAC con fechas y coordenadas exactas.
  2. Recomendaciones con el número solicitado, representación de planes, tramos e IAC estimado.
  3. Creación de una parcela rectangular, historial en orden, análisis IAC y rotaciones, persistencia, edición y eliminación; escapado del nombre en HTML.
  4. Autolocalización simulada, permiso denegado y errores de configuración 503, sin resultados inventados.
  5. Descartar resultados de consultas antiguas al cambiar de ubicación o cancelar.
  6. Catálogo no disponible y reintento; aviso visible cuando falla el almacenamiento local.
- Comprobación de sintaxis JavaScript.
- Hashes de los recursos locales de Leaflet coinciden con los atributos SRI del HTML.
- Código de `getter.py`, `servicio.py`, `iac.py`, `validacion.py`, `errores.py` y `cultivos.json` conservado del ZIP original.

## Alcance de las pruebas

Los tests del frontend invocan la API FastAPI real a través de TestClient, sin abrir un puerto. Solo se sustituyen las fuentes externas por una tabla diaria sintética. No hay un modo de datos sintéticos activo en producción.

El intento de iniciar Chromium fue bloqueado por las restricciones de sockets del entorno. **No se ha completado la revisión visual en un navegador real**, ni se ha probado en dispositivos físicos. Hay estilos adaptables para escritorio y móvil, pero necesitan esa comprobación visual.

No se dispone de credenciales Earth Engine autorizadas para verificar una consulta real de SMAP/SoilGrids. La descarga real debe comprobarse en el servidor configurado. No se ha verificado disponibilidad continua de las teselas OpenStreetMap ni la precisión de la geolocalización de un dispositivo.

## Comprobación manual recomendada al arrancar

1. Abrir `http://localhost:8000`, confirmar que aparece el inicio de sesión y entrar en demostración.
2. Elegir fechas observadas, cultivo y punto; obtener un IAC con las fuentes configuradas.
3. Solicitar recomendaciones en su página y revisar fechas, ciclos y supuestos.
4. Crear una parcela con punto y otra con rectángulo; añadir historial y analizar ambas.
5. Recargar, comprobar persistencia y cambiar ES/EN.
6. Revisar en una ventana estrecha el menú, controles del mapa, formularios y panel de resultados.

Los datos y límites del motor se describen en `API.md` y `MOTOR.md`; el informe previo de la API se conserva como `VERIFICACION.md`.
