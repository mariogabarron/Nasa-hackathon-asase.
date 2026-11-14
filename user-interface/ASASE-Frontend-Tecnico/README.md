# ASASE · Frontend técnico

Abre `index.html` en un navegador moderno. No necesita instalación ni dependencias. También puede servirse con Live Server desde VS Code.

## Idiomas
- Selector **ES / EN** visible tanto en el acceso como en la barra superior. Cambia los textos de todas las vistas, mapa, formularios, mensajes y fuentes sin recargar la página.
- El idioma se recuerda en `localStorage` (`asase.language`). Español por defecto. Las fechas visibles se formatean según el idioma.
- **Importante para el backend**: los doce nombres de cultivo se traducen solo visualmente; los valores internos de los selectores y los registros guardados siguen usando los identificadores españoles originales. El cambio de idioma no migra ni borra historiales.
- Las traducciones se mantienen en `englishTranslations` dentro de `index.html`; la presentación se actualiza mediante `translateUI()`. Las futuras respuestas libres del backend requerirán sus propias traducciones o claves de mensaje.

## Funcionalidad
- Acceso del técnico y cierre de sesión. Es una simulación de frontend: no autentica, no envía ni almacena contraseñas. Usa datos ficticios o el botón de demostración.
- Resumen con mapa original del norte de Ghana, prioridades dependientes del cultivo e historial.
- Panel de IAC inicialmente cerrado; se abre al seleccionar una región y el mapa se redimensiona con transición. Compatible con teclado y preferencia de movimiento reducido.
- Registro de parcela por nombre/código, región, cultivo y fecha. Los datos se guardan en localStorage del navegador; no se sincronizan entre usuarios o dispositivos.
- Los doce cultivos solicitados están disponibles en los selectores y en alternativas.
- Calendario de consulta desde hoy hasta 90 días. Las siembras pueden registrarse con fechas pasadas o hasta el límite futuro. El calendario elige registros vigentes; no simula cambios futuros del suelo.
- Por defecto se analizan los cultivos registrados. Para cada parcela se usa el último registro efectivo en la fecha de consulta. Nombre (sin distinción de mayúsculas) y región identifican una parcela. Un nuevo registro en otra fecha representa un cambio de cultivo; no se admiten dos cambios de la misma parcela en la misma fecha.
- Mapa regional: el menor IAC de las parcelas de una región determina su color. Las regiones sin registros aparecen sin datos. Elegir un cultivo concreto compara las cinco regiones con ese mismo cultivo.
- Alternativas, análisis de regiones y fuentes tienen páginas propias. No hay rol agricultor ni plan de prevención.

## Integración pendiente
`evaluateIAC(crop, soil)` es el único adaptador de resultados simulados. Sustituir por la función del backend que devuelva `{iac, motivo}`. Si es asíncrona, añadir carga y gestión de errores antes de renderizar los resultados. Actualmente `soil` es una referencia regional ficticia; integrar muestras de suelo por parcela antes de evaluar datos reales.

El IAC mide aptitud relativa, no rendimiento en toneladas ni productividad garantizada. Las puntuaciones, motivos y umbrales son demostrativos y no están calibrados. No hay predicción temporal ni recomendaciones agronómicas reales.

La autenticación real y el almacenamiento por cuenta también quedan pendientes de backend. El acceso visual no protege los datos locales.

## Cartografía y fuentes
Polígonos originales conservados de amCharts 4 Geodata / Ghana Low, CC BY 4.0: https://github.com/amcharts/amcharts4-geodata . Las coordenadas están proyectadas y simplificadas para el SVG. El mapa no representa límites de parcelas.
NASA POWER y SoilGrids son fuentes previstas, aún sin conectar. La página Fuentes distingue cartografía, registros introducidos por el técnico e índices simulados.

## Verificación realizada
Sintaxis JavaScript; acceso de demostración; registro de parcela; historial y persistencia tras recarga; cambio de cultivo y de prioridades; apertura del panel; comparación de los doce cultivos. Comprobación visual en navegador de escritorio. Estilos adaptables incluidos; no se ha comprobado en dispositivos físicos.
