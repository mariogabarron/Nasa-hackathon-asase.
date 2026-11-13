# Tipo de proyecto
Una aplicación web de tipo mapa que tenga dos funciones: Obtener ubicación actual y obtener conclusiones sobre qué cultivos son mejores para cultivar para el periodo de cultivo objetivo y el historial de cultivo dado (dos últimos periodos de cultivo).

# Estructuras de datos

## Cultivo
Representa una clase de cultivo con sus condiciones óptimas.

## Periodo de cultivo
Año y enumerado de otoño-invierno y primavera-verano

## Respuesta de las APIs
Juntar en una misma estructura de datos todos los datos relevantes para el procesamiento, de una o de varias APIs.

## Información de cultivo
Juntamos la respuesta de las APIs con datos sobre el historial de cultivo

# APIs e información a recoger
NASA POWER (50x60km) : Temperatura, radiación solar, precipitación y viento
SMAP (earthaccess en python): Humedad del suelo
ECOSTRESS: Temperatura de las plantas y evotranspiración (para cada planta??)

# Resumen de tecnologías:

## React

