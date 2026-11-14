Actualización de rotaciones: 63 tests superados. Referencia mensual 2025, períodos de plantación multianuales, final opcional y prioridad de ocupación. No se ha realizado nueva descarga real de Earth Engine.

Actualización: 59 pruebas superadas; caso de pH totalmente nulo probado con tabla controlada y endpoint HTTP. No se ha repetido la descarga real de Earth Engine de la localización indicada.

# Verificación de entrega · 14 de noviembre de 2026

## Comprobado

- 56 tests automáticos: 27 del motor anterior, 27 de integración/API/agregación
  y 2 de construcción y serialización de consultas con el SDK real de Earth Engine.
- Casos de punto y BBOX, consulta de un día con fechas inclusivas, extremos,
  sumas, medias, textura, historial de IDs, respuesta de un cultivo o los 12,
  rotación de un año y errores 422/502/503.
- Validación de duplicados, días ausentes, NaN, infinitos, centinelas y valores
  diarios inválidos que podrían quedar ocultos por una media.
- Descarga real de NASA POWER para [9.4, -0.84], 2025-04-01 a 2025-04-03:
  3 días y las 5 variables pedidas. Precipitación diaria: 0.04, 0.22 y 0.65 mm.
  Mínimas: 25.48, 26.48 y 26.78 °C. Máximas: 38.99, 40.12 y 39.21 °C.

## Pendiente de credenciales del servidor

La inicialización real de Earth Engine devolvió la indicación de ejecutar
`earthengine authenticate`. Este entorno no dispone de credenciales de la
cuenta/proyecto. Por tanto, **no se ha verificado una descarga real completa
de SMAP y SoilGrids ni el recorrido completo con todas las fuentes reales**.

Las dos pruebas del SDK validan expresiones serializables y el contrato de
respuesta con respuestas simuladas. No comprueban permisos de acceso a assets,
cobertura actual de datos ni ejecución en los servidores de Google.

Para cerrar esta comprobación en el servidor autorizado:

```bash
earthengine authenticate
export GEE_PROJECT_ID="gen-lang-client-0182377274"
python3 comprobar_fuentes.py
```

Los tests verifican comportamiento del software. Los coeficientes heurísticos
de historial y las propuestas de rotación no constituyen validación agronómica.
