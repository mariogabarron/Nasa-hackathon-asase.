class ErrorFuente(RuntimeError):
    """La fuente remota falló o devolvió un contenido incompatible."""


class DatosInsuficientes(ErrorFuente):
    """No se puede representar todo el período sin inventar o perder datos."""


class ErrorConfiguracion(RuntimeError):
    """Faltan dependencias, credenciales o permisos del servidor."""
