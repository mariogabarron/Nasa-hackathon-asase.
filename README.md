# space-apps-agriculture

## Descripción

Una plataforma de agricultura predictiva y preventiva para países en desarrollo que utiliza datos satelitales de la NASA y modelos matemáticos para identificar zonas agrícolas vulnerables, anticipar riesgos para la productividad del suelo y recomendar estrategias de rotación de cultivos que ayuden a conservar su fertilidad.

## Organización del equipo

- **Clara y Mario — UI:** diseñar la interfaz y transformar los resultados del algoritmo en mapas, indicadores y explicaciones comprensibles.
- **Albero y Edu — Datasets:** obtener, limpiar y unificar los datos seleccionados.
- **Navarro y David — Algoritmo Python:** desarrollar el cálculo del Índice de Aptitud de Cultivo (IAC) mediante un sistema de pesos y reglas.

## Estado actual

- Seleccionados los parámetros iniciales y sus fuentes:
  - **NASA POWER:** temperatura y precipitación.
  - **SoilGrids:** pH, textura y carbono orgánico.
  - **NASA SMAP:** humedad radicular, pendiente de decidir su incorporación.
- Definido el enfoque del algoritmo: comparar las condiciones del terreno con los requisitos del cultivo y calcular el IAC.
- El IAC representará la **aptitud del terreno para un cultivo**, no una estimación directa de producción en toneladas.

## Siguientes pasos

1. **Acotar el piloto:** elegir una región y los primeros cultivos para limitar el desarrollo ***HECHO***
2. **Preparar los datasets:** comprobar cobertura, unidades, profundidades y datos faltantes. ***HECHO***
3. **Acordar el formato de intercambio:** definir qué datos recibe el algoritmo y qué resultados entrega a la UI. ***HECHO***
4. **Definir pesos y reglas:** establecer requisitos por cultivo y cómo afectan las condiciones limitantes al IAC. ***POR HACER***
5. **Implementar y validar el algoritmo:** probar casos conocidos y revisar que las puntuaciones sean coherentes.
6. **Integrar la UI:** mostrar el IAC, sus factores limitantes y la información disponible de cada zona.
7. **Ampliar la funcionalidad:** incorporar pronósticos y comparación de rotaciones sobre una primera versión validada. ***FASE 3?***
