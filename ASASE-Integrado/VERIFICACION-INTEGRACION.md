# Verificación de la integración

Fecha: 14 de noviembre de 2026.

## Resultado

- **81 pruebas Python superadas:** motor, agregación, fuentes controladas, API y empaquetado, más orden descendente, localización ES/EN, datos parciales, errores e independencia del idioma entre peticiones concurrentes.
- **16 escenarios de interfaz superados** con jsdom y Leaflet 1.9.4 real:
  1. Conservación del acceso y ES/EN, zoom, selección del punto, carga de los 12 cultivos y petición IAC con fechas y coordenadas exactas.
  2. Recomendaciones con el número solicitado, representación de planes, tramos e IAC estimado.
  3. Creación de una parcela rectangular, historial en orden, análisis IAC y rotaciones, persistencia, edición y eliminación; escapado del nombre en HTML.
  4. Autolocalización simulada, permiso denegado y errores de configuración 503, sin resultados inventados.
  5. Descartar resultados de consultas antiguas al cambiar de ubicación o cancelar.
  6. Catálogo no disponible y reintento; aviso visible cuando falla el almacenamiento local.
  7. Bloqueo de pasado, hoy, fechas vacías y rangos invertidos en recomendaciones, sin enviar consultas.
  8. Migración de parcelas sin `cropId` y rangos independientes para IAC/recomendaciones.
  9. Selectores alfabéticos ES/EN, sin IDs visibles y búsqueda sin acentos.
  10. Tres colores en los límites 40/70, nulos neutros y mayor IAC primero.
  11. Cambio de idioma que limpia resultados anteriores y solicita explicaciones/planes en inglés.
  12. Truncado sin redondeo, enteros sin ceros añadidos y precisión interna conservada.
  13. Restricción a Ghana por clic, coordenadas, geolocalización y área; navegación mundial libre y rechazo de rectángulos que atraviesan la frontera aunque sus esquinas estén dentro.
  14. Fechas históricas hasta ayer e historial ordenado en Mapa y Recomendaciones.
  15. Presupuesto: pérdidas, ciclos repetidos, área, datos ausentes, ciclos incompletos y ausencia de conversión IAC-rendimiento.
  16. Beneficio o campos pendientes en cada propuesta, modificación del presupuesto y fuentes en ES/EN.
- Cuatro pruebas Python nuevas: identidad de las geometrías JS/GeoJSON, puntos y áreas dentro/fuera, frontera cóncava y rechazo por API antes de consultar las fuentes.
- Comparación adicional de 1.000 puntos y 1.000 rectángulos generados con semilla fija: el validador JS coincide con Shapely en los 2.000 casos.
- Comprobación de sintaxis JavaScript.
- Hashes de los recursos locales de Leaflet coinciden con los atributos SRI del HTML.
- Fuentes (`getter.py`), validación, errores y catálogo originales conservados. Se añaden mensajes bilingües al motor y orden descendente de presentación al servicio; las fórmulas y la búsqueda agronómica no cambian.

## Alcance de las pruebas

Los tests del frontend invocan la API FastAPI real a través de TestClient, sin abrir un puerto. Solo se sustituyen las fuentes externas por una tabla diaria sintética. No hay un modo de datos sintéticos activo en producción.

El intento de iniciar Chromium fue bloqueado por las restricciones de sockets del entorno. **No se ha completado la revisión visual en un navegador real**, ni se ha probado en dispositivos físicos. Hay estilos adaptables para escritorio y móvil, pero necesitan esa comprobación visual.

No se dispone de credenciales Earth Engine autorizadas para verificar una consulta real de SMAP/SoilGrids. La descarga real debe comprobarse en el servidor configurado. No se ha verificado disponibilidad continua de las teselas OpenStreetMap ni la precisión de la geolocalización de un dispositivo.

## Comprobación manual recomendada al arrancar

1. Abrir `http://localhost:8000`, confirmar que aparece el inicio de sesión y entrar en demostración.
2. Elegir fechas observadas, cultivo y punto; obtener un IAC con las fuentes configuradas.
3. Solicitar recomendaciones en su página y revisar fechas, ciclos y supuestos.
4. Crear una parcela rectangular dentro de Ghana; añadir historial y analizarla. Confirmar que no existe selección de punto en Parcelas.
5. Recargar, comprobar persistencia y cambiar ES/EN.
6. Comprobar que las recomendaciones rechazan hoy/pasado y que los dos rangos de la parcela no se afectan entre sí.
7. Revisar el beneficio y editar el presupuesto; comprobar pérdidas, datos pendientes y fuentes.
8. Revisar en una ventana estrecha el menú, controles del mapa, formularios y panel de resultados.

Los datos y límites del motor se describen en `API.md` y `MOTOR.md`; el informe previo de la API se conserva como `VERIFICACION.md`.
