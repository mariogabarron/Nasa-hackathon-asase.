from datetime import timedelta
from iac import fecha_iso, numero


def validar_consulta(start_date, end_date, point, bbox):
    inicio, fin = fecha_iso(start_date), fecha_iso(end_date)
    if inicio > fin:
        raise ValueError("start_date debe ser <= end_date")
    dias = (fin - inicio).days + 1
    if dias > 366:
        raise ValueError("El período no puede superar 366 días")
    if (point is None) == (bbox is None):
        raise ValueError("Indicar exactamente uno de point o bbox")
    if point is not None:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("point debe ser [latitud, longitud]")
        lat = numero(point[0], "latitud", -90, 90)
        lon = numero(point[1], "longitud", -180, 180)
    else:
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise ValueError("bbox debe ser [min_lat, min_lon, max_lat, max_lon]")
        a, b, c, d = [numero(x, "bbox") for x in bbox]
        numero(a, "min_lat", -90, 90)
        numero(c, "max_lat", -90, 90)
        numero(b, "min_lon", -180, 180)
        numero(d, "max_lon", -180, 180)
        if a >= c or b >= d:
            raise ValueError("bbox requiere min_lat < max_lat y min_lon < max_lon; no cruza antimeridiano")
        lat, lon = (a+c)/2, (b+d)/2
    return inicio, fin, lat, lon, dias
