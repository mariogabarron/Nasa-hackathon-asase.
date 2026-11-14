# ASASE — Motor IAC · Norte de Ghana

Implementación **Python sin dependencias** para puntuar la aptitud de una región agrícola y un cultivo concreto a partir de una serie de observaciones mensuales de **hasta un año anterior** a la fecha de consulta. Los valores de ejemplo **son inventados** y sirven exclusivamente para probar la ejecución.

## Documentos de referencia

- *Matriz de Pesos y Justificacion Agronomica - Norte de Ghana 2.pdf*: cuatro estaciones, pesos de las 11 variables activas; `fecha` y fracciones de textura son auxiliares (pp. 1–4).
- *Parametros e Intervalos de Idoneidad de los 12 Cultivos - Norte de Ghana.pdf*: valores S1/S2/S3/N, vetos, duración de ciclos, unidades y desplazamiento mínimo de humedad (+/−0,03 m³/m³) (pp. 1–10).

No se han sustituido las tablas aportadas por otra fuente. Las tablas completas del código están en `configuracion_iac.json` para que el equipo pueda revisarlas y versionarlas.

## Qué calcula

1. Selecciona una de las estaciones norteñas según el mes de cada observación:
   - Abril–junio: `inicio_lluvias_siembra`
   - Julio–septiembre: `plena_lluvia_crecimiento`
   - Octubre–noviembre: `retirada_lluvias_cosecha`
   - Diciembre–marzo: `epoca_seca_harmattan`
2. Para el **cultivo seleccionado**, clasifica cada uno de los **11 parámetros activos** en S1 (1), S2 (0,65), S3 (0,30) o N (0).
3. Aplica el peso asignado a **cada parámetro en la estación correspondiente** y suma sus contribuciones:

   `IAC_ponderado = 100 * Σ(peso_estacion[parametro] × puntuacion_cultivo[parametro])`

4. Comprueba vetos de variables críticas especificadas para ese cultivo. Si una de ellas cae en N, marca `categoria_global = "N"`, presenta `iac_100 = 0` de forma **operativa** y conserva la suma original en `iac_ponderado_antes_de_vetos_100` para auditoría. El PDF exige la categoría global N; devolver cero como índice operativo es una elección explícita del motor.
5. Calcula el IAC por **observación mensual** dentro del año anterior a la consulta; devuelve su evolución y la diferencia entre la primera y última observación. No infiere valores de meses ausentes ni predice el futuro.

### Unidades de entrada

| Parámetro | Unidad / referencia |
| --- | --- |
| `temp_media_C`, `temp_min_C`, `temp_max_C` | ºC; temperatura del aire |
| `precipitacion_mm` | **mm acumulados en 30 días**, no mm/día ni suma trimestral |
| `radiacion_solar_MJ_m2` | **MJ/m²/día** |
| `humedad_suelo_smap_m3m3` | m³/m³ (0–5 cm) |
| `humedad_raiz_smap_m3m3` | m³/m³ (0–100 cm) |
| `temp_suelo_smap_C` | ºC |
| `suelo_ph_0_30cm` | pH (adimensional) |
| `suelo_carbono_organico_g_kg` | g/kg |
| `suelo_textura_clase` | nombre de textura de las categorías del PDF |
| `suelo_arcilla_pct`, `suelo_arena_pct`, `suelo_limo_pct` | %; tres valores auxiliares, opcionales en bloque |

El valor de pH, carbono orgánico y textura se proporciona una vez para la región como `suelo`. El resto llega en `observaciones`, cada una con fecha; esos parámetros son los que cambian mensualmente. Si en el futuro existe una actualización de suelo, hará falta extender el formato para admitir propiedades estáticas versionadas por fecha.

## Ejecución rápida

Desde la carpeta descomprimida:

```bash
python3 motor_iac.py ejemplo_entrada.json -o resultado.json
```

O para imprimir el resultado:

```bash
python3 motor_iac.py ejemplo_entrada.json
```

`ejemplo_entrada.json` contiene **12 observaciones sintéticas** de diciembre de 2025 a noviembre de 2026 para la región Northern y maíz. `ejemplo_resultado.json` contiene una respuesta de referencia reproducible.

## Formato de entrada

```json
{
  "region": "Northern",
  "cultivo": "maiz",
  "fecha_consulta": "2026-11-14",
  "suelo": {
    "suelo_ph_0_30cm": 6.3,
    "suelo_carbono_organico_g_kg": 12.7,
    "suelo_textura_clase": "Franco",
    "suelo_arcilla_pct": 18,
    "suelo_arena_pct": 42,
    "suelo_limo_pct": 40
  },
  "observaciones": [
    {
      "fecha": "2026-11-14",
      "temp_media_C": 29,
      "temp_min_C": 20,
      "temp_max_C": 36,
      "precipitacion_mm": 85,
      "radiacion_solar_MJ_m2": 23,
      "humedad_suelo_smap_m3m3": 0.21,
      "humedad_raiz_smap_m3m3": 0.26,
      "temp_suelo_smap_C": 32
    }
  ]
}
```

Puedes enviar hasta un año de observaciones de la misma región; se admite como máximo un registro por mes, con la fecha representativa de cada mes. Los registros se ordenan cronológicamente y se evalúan **cada uno con sus pesos estacionales**. Si envías un solo registro, obtendrás un único IAC sin tendencia.

## Formato de salida

El JSON devuelto contiene:

- `ultima_observacion`: puntuación operativa, puntuación ponderada antes de veto, estación, factores críticos, 11 contribuciones individuales (valor original, categoría, peso y aporte en puntos).
- `historial_12_meses`: fecha, estación, IAC y vetos por cada observación mensual.
- `variacion_entre_primera_y_ultima_observacion`: diferencia simple en puntos de IAC (**no equivale** a una predicción ni al porcentaje de pérdida de cosecha).
- `numero_meses_con_datos`: cantidad real de registros usados.

## API opcional para React

La función principal que debe llamar el backend es:

```python
from motor_iac import evaluar_historial
resultado = evaluar_historial(datos_json)
```

Si queréis exponerla por HTTP usando FastAPI:

```bash
python3 -m pip install -r requirements-api.txt
python3 -m uvicorn api:app --reload
```

La API expone `POST http://127.0.0.1:8000/iac` y `GET http://127.0.0.1:8000/cultivos`. La interfaz React enviará el JSON por POST y dibujará el IAC, los factores limitantes y el historial a partir de la respuesta. No se han instalado librerías ni configurado CORS para despliegue de producción.

## Tests

```bash
python3 -m unittest -v
```

Las pruebas verifican los 12 cultivos, sumas de pesos, estaciones, vetos, bordes y desplazamientos de humedad, errores por datos incompletos y ventana histórica.

## Decisiones técnicas y límites documentales

- **No se calcula rendimiento agrícola** en toneladas/hectárea ni un porcentaje de productividad. El IAC es únicamente el índice de idoneidad definido por la matriz de entrada.
- **No se pronostica el próximo año**. Las observaciones históricas permiten estudiar el IAC retrospectivo; para anticipar riesgos futuros necesitaréis series proyectadas o escenarios modelizados con validación.
- **Sin imputación artificial:** si falta una de las once variables activas no se devuelve un índice aparentemente preciso; se informa del error. Podéis diseñar después una política de ausencias y confianza.
- **Categorías globales:** los PDF no definen cortes globales de IAC para S1/S2/S3; por eso solo se fuerza `N` ante un veto y **no** se inventan categorías globales basadas en el porcentaje.
- **Textura:** como el PDF no contiene el triángulo USDA ni una regla de clasificación de fracciones, se exige la clase de textura del equipo de Datos; se comprueba que sea una clase permitida y que, si se suministran porcentajes, estos sumen 100 ± 1 punto porcentual. No se asegura coherencia geométrica entre los porcentajes y la clase. La comprobación exacta de la textura requiere agregar un clasificador textural validado.
- **Ajuste de humedad:** se interpreta el desplazamiento de ±0,03 m³/m³ de los umbrales mínimos exigidos como modificación de los tres límites **inferiores** (S3/S2/S1) de las **dos** variables SMAP; no de los límites superiores. Es una interpretación de implementación que el equipo debe aprobar.
- **Hueco en el catálogo del arroz:** para humedad del suelo o de raíz por encima de la banda superior S2, el PDF no asigna S3 ni N. El código **no inventa esa banda** y devuelve un error informativo cuando aparece un valor así.
- **Estación y fisiología:** la elección de pesos es por mes calendario, no por fase real del cultivo. El período de siembra/ciclo fenológico concreto aún no se modela.
- **El historial es temporal, no espacial:** el JSON representa una zona de muestreo o región con datos ya agregados. El módulo no agrega píxeles de satélite ni genera mapas; eso corresponde al equipo de datos/geoprocesamiento.
- **Validación agronómica:** los intervalos del material del equipo se toman como reglas del prototipo, no como valores ya validados empíricamente para cada parcela/región.
