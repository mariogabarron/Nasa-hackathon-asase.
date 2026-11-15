# asase.

**Inteligencia agrícola para convertir datos en decisiones.**

Plataforma de apoyo a la decisión agrícola que combina datos ambientales, información del suelo y un modelo matemático explicable para evaluar la aptitud de distintos cultivos, comparar alternativas y orientar estrategias de rotación. Su primer caso de uso se centra en el **norte de Ghana**.

> **Una cosecha sostiene mucho más que un campo.** Nuestro objetivo es que la información técnica llegue a las comunidades que más pueden beneficiarse de ella, sin exigir que cada agricultor disponga de un smartphone o utilice una aplicación.

**Proyecto desarrollado en el contexto de NASA Space Apps Challenge 2026.**  
**Estado:** prototipo funcional, con interfaz y motor de cálculo desarrollados por separado; integración y validación agronómica pendientes.

---

## 01. El problema

La variabilidad de las precipitaciones, las limitaciones de acceso al agua y la degradación del suelo complican la planificación agrícola. Una decisión de siembra inadecuada puede traducirse en menor disponibilidad de alimentos, pérdida de ingresos y menos recursos para la siguiente campaña.

Muchas soluciones digitales parten de una premisa difícil de cumplir: que cada agricultor pueda acceder de forma constante a una aplicación, interpretar sus resultados y actuar individualmente. Además, los problemas agrícolas no siempre se limitan a una parcela; a menudo requieren **comparar zonas y coordinar prioridades a escala territorial**.

## 02. Nuestra propuesta

**asase.** está concebida principalmente para **técnicos agrícolas, ingenieros agrónomos y cooperativas**, que pueden analizar varias zonas, estudiar alternativas y trasladar recomendaciones comprensibles a los agricultores locales.

El agricultor es el beneficiario final; el especialista actúa como puente entre la información técnica y la decisión sobre el terreno.

La plataforma busca responder a cuatro preguntas:

1. **¿Dónde actuar primero?** Identificar zonas que requieren mayor atención según el cultivo y las condiciones analizadas.
2. **¿Qué cultivar?** Comparar la aptitud de los cultivos considerados para una zona o parcela.
3. **¿Cuándo plantar?** Evaluar escenarios de siembra según las condiciones disponibles y referencias estacionales.
4. **¿Cómo aprovechar mejor el terreno?** Proponer secuencias de rotación que reduzcan los periodos sin cultivo, respetando las restricciones modeladas.

## 03. Funcionalidades

### Interfaz para técnicos y cooperativas

- **Resumen territorial:** mapa interactivo del norte de Ghana y visualización de zonas prioritarias.
- **Análisis de zonas y regiones:** selección de áreas, cultivos y periodos para consultar indicadores de aptitud.
- **Alternativas de cultivos:** comparación de opciones del catálogo agrícola.
- **Registro de parcelas:** asociación de cultivos a parcelas e historial de los registros introducidos.
- **Panel de Índice de Aptitud de Cultivo (IAC):** presentación contextual del indicador al seleccionar una zona.
- **Fuentes:** sección destinada a documentar el origen de los datos utilizados.
- **Interfaz bilingüe:** español e inglés, con preferencia de idioma conservada en el navegador.

El prototipo frontend es una aplicación **HTML, CSS y JavaScript** que puede abrirse localmente. La interacción, la navegación y el historial en navegador están implementados; **los valores agrícolas mostrados por esta interfaz son de demostración y todavía no proceden del motor Python**. El acceso de técnico es ilustrativo, no un sistema de autenticación productivo.

### Motor de cálculo en Python

El motor implementa dos tipos de operación:

| Operación | Objetivo |
| --- | --- |
| `iac` | Evaluar la aptitud de un cultivo concreto o comparar los 12 cultivos del catálogo. |
| `rotaciones` | Generar alternativas de sucesión de cultivos para un periodo de planificación. |

La selección de cultivos, los periodos y los resultados se calculan de acuerdo con los parámetros y reglas definidos para el piloto. En la generación de rotaciones se busca **maximizar el tiempo con cultivo** y comparar alternativas mediante el IAC; la búsqueda es aproximada y no garantiza el óptimo global.

## 04. ¿Cómo funciona el IAC?

El **Índice de Aptitud de Cultivo (IAC)** es una puntuación multicriterio que expresa la adecuación estimada de un cultivo a determinadas condiciones ambientales y edáficas.

El cálculo utiliza valores normalizados de los parámetros relevantes y **pesos que cambian según la estación** del norte de Ghana. Su formulación básica es:

$$
IAC = 100 \sum_{i=1}^{n} w_i s_i
$$

Donde:

- `wᵢ` representa el peso del parámetro `i` para la estación considerada.
- `sᵢ` representa la puntuación de idoneidad del parámetro para el cultivo evaluado.
- Los pesos activos se normalizan para que su suma sea 1.

Se emplean cuatro niveles de idoneidad, inspirados en clasificaciones de aptitud agronómica:

| Nivel | Interpretación | Puntuación |
| --- | --- | ---: |
| S1 | Óptimo | 1,00 |
| S2 | Moderado | 0,65 |
| S3 | Marginal | 0,30 |
| N | No apto | 0,00 |

El modelo incorpora **reglas limitantes**: cuando un parámetro crítico para un cultivo se encuentra en condiciones no aptas, se activa una advertencia o clasificación de no aptitud, incluso si la suma ponderada resulta elevada. La textura del suelo se considera de forma estructurada para evitar contabilizar varias veces la misma información.

Se distinguen cuatro periodos climáticos: **inicio de lluvias (abril–junio), temporada de lluvias (julio–septiembre), retirada de lluvias (octubre–noviembre) y estación seca o Harmattan (diciembre–marzo)**.

> **Importante:** el IAC no es una predicción directa de toneladas cosechadas, rendimiento económico ni fertilidad futura. Es un indicador orientativo de **aptitud relativa**, sujeto a la calidad de los datos y a validación local.

## 05. Datos y fuentes

El diseño del sistema contempla las siguientes fuentes de observación terrestre y datos de suelo:

| Fuente | Información de interés |
| --- | --- |
| [NASA POWER](https://power.larc.nasa.gov/) | Temperatura y radiación solar; series climáticas históricas. |
| [NASA GPM](https://gpm.nasa.gov/) | Estimaciones de precipitación. |
| [NASA SMAP](https://smap.jpl.nasa.gov/) | Indicadores de humedad del suelo. |
| [ISRIC SoilGrids](https://soilgrids.org/) | Propiedades estimadas del suelo, como pH, textura y carbono orgánico. |

El motor se ha diseñado alrededor de una matriz de **15 variables**, de las cuales **11 participan directamente en la ponderación** y 4 cumplen funciones auxiliares, como seleccionar la estación y caracterizar la textura del suelo.

**Estado de las fuentes:** la obtención de datos de NASA POWER se ha trabajado en el prototipo; el acceso a determinadas capas de SMAP y SoilGrids puede requerir configurar credenciales o servicios externos. No debe interpretarse que todas las fuentes estén integradas y operativas en cualquier instalación.

Para la planificación de rotaciones, la implementación actual utiliza **2025 como año de referencia climático**. Se trata de escenarios basados en datos históricos, **no de pronósticos meteorológicos futuros en tiempo real**.

## 06. Arquitectura y uso

```text
                   TÉCNICO / COOPERATIVA
                            │
                            ▼
                   INTERFAZ WEB (UI)
             mapa · parcelas · cultivos · IAC
                            │
                      integración
                        pendiente
                            │
                            ▼
                    API / MOTOR PYTHON
                 IAC · reglas · rotaciones
                            │
                            ▼
                  DATOS Y PARÁMETROS
              NASA · SoilGrids · catálogo
                            │
                            ▼
                  RECOMENDACIONES
                            │
                            ▼
                     AGRICULTORES
```

### Frontend

La versión estática se ejecuta abriendo `index.html` en un navegador moderno. No requiere instalar un framework ni iniciar un servidor para explorar la demostración. Los registros del prototipo se almacenan localmente en el navegador.

### Backend

El motor está desarrollado en **Python** y contempla una API mediante **FastAPI** con el endpoint `POST /predecir`. Su ejecución requiere preparar las dependencias y la configuración de datos correspondiente a la versión del backend utilizada.

Ejemplo de solicitud para comparar cultivos:

```json
{
  "accion": "iac",
  "start_date": "2025-04-01",
  "end_date": "2025-06-03",
  "point": [6.6885, -1.6244]
}
```

Si se incluye `cultivo_id`, la operación se centra en ese cultivo; si se omite, puede evaluar los 12 cultivos del catálogo.

Ejemplo de solicitud de rotaciones:

```json
{
  "accion": "rotaciones",
  "start_date": "2027-04-01",
  "end_date": "2028-03-31",
  "point": [6.6885, -1.6244],
  "n_recomendaciones": 3
}
```

En `rotaciones`, `n_recomendaciones` es un entero positivo (por defecto, `3`) y, si se omite `end_date`, se utiliza un horizonte de un año. Esta operación admite periodos superiores a 365 días. La planificación toma como referencia datos estacionales históricos de 2025.

> **Nota de integración:** los ejemplos documentan el contrato previsto del motor, pero la interfaz web distribuida como prototipo aún no realiza llamadas reales a esta API. Los nombres de archivos de arranque y la configuración de credenciales deben documentarse según el repositorio final de backend.

## 07. Estado del proyecto

| Componente | Estado |
| --- | --- |
| Definición del piloto en el norte de Ghana | Definido |
| Selección de parámetros y catálogo de 12 cultivos | Definido |
| Matriz de pesos y reglas de idoneidad | Desarrollado |
| Motor Python para IAC y propuestas de rotación | Prototipo desarrollado |
| Interfaz web interactiva y bilingüe | Prototipo desarrollado |
| Conexión entre interfaz y backend | Pendiente |
| Integración estable de todas las fuentes | En desarrollo |
| Validación con mediciones y especialistas locales | Pendiente |
| Predicciones con fuentes actualizadas en tiempo real | Visión futura |

## 08. Próximos pasos

1. **Integración:** conectar la interfaz a la API para sustituir los indicadores de demostración por cálculos reales y explicables.
2. **Calidad de datos:** verificar cobertura espacial, resolución, fechas, valores ausentes y consistencia entre fuentes.
3. **Validación agronómica:** contrastar IAC, reglas y rotaciones con especialistas y datos locales del norte de Ghana.
4. **Evaluación:** establecer métricas reproducibles para comprobar utilidad, limitaciones e incertidumbre del sistema.
5. **Despliegue en campo:** optimizar el uso desde dispositivos portátiles y en contextos de conectividad limitada.
6. **Escalabilidad:** estudiar nuevas regiones y países, adaptar parámetros a cada contexto e incorporar fuentes más recientes cuando su calidad lo permita.

## 09. Equipo

| Área | Responsables |
| --- | --- |
| Diseño e interfaz de usuario (UI) | Clara y Mario |
| Datos y fuentes (datasets) | Albero y Edu |
| Modelo matemático y algoritmo Python | Navarro y David |

## 10. Visión

Creemos que el acceso a información agrícola útil no debería depender del nivel de digitalización de una comunidad. Por eso diseñamos una herramienta para quienes pueden transformar datos complejos en decisiones coordinadas y trasladarlas directamente al campo.

**Nuestro objetivo no es solo ayudar a elegir mejores cultivos: es contribuir a que más familias encuentren en su tierra nuevas oportunidades de prosperar.**

---

*asase. es un prototipo de apoyo a decisiones agrícolas. Sus estimaciones no sustituyen el criterio de profesionales de agronomía, los análisis directos del terreno ni las recomendaciones validadas localmente.*
