"""Mensajes del motor por petición; ContextVar evita mezclar idiomas entre usuarios."""
from contextvars import ContextVar

IDIOMA = ContextVar('asase_idioma', default='es')


def tr(es, en):
    return en if IDIOMA.get() == 'en' else es


CULTIVOS_EN = {
    'Maíz': 'Maize', 'Sorgo': 'Sorghum', 'Mijo': 'Millet', 'Arroz': 'Rice',
    'Cacahuete': 'Groundnut', 'Ñame': 'Yam', 'Caupi': 'Cowpea', 'Caupí': 'Cowpea', 'Guisante': 'Pea', 'Soja': 'Soybean',
    'Yuca': 'Cassava', 'Boniato': 'Sweet potato', 'Guisante bámbara': 'Bambara groundnut',
    'Algodón': 'Cotton',
}


def nombre_cultivo(nombre):
    return CULTIVOS_EN.get(nombre, nombre) if IDIOMA.get() == 'en' else nombre


def error_publico(codigo, original):
    if IDIOMA.get() == 'es':
        return str(original)
    # No se exponen mensajes técnicos de proveedores en otro idioma
    # ni posibles credenciales en la respuesta pública.
    return {
        'CONFIGURACION': 'Earth Engine is not configured or authorized. Check the server project and credentials.',
        'DATOS_INCOMPLETOS': 'The data source returned missing or invalid observations. Try another period or location.',
        'FUENTE_EXTERNA': 'An external climate or soil service failed. Please try again later.',
        'ENTRADA_INVALIDA': 'Invalid request. Check dates, coordinates, crop IDs and crop history.',
    }[codigo]
