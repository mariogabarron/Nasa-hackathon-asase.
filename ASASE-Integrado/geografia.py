"""Country coverage from the bundled, attributed geoBoundaries ADM0 polygon."""
import json
from pathlib import Path

from shapely.geometry import Point, box, shape

_DATA = Path(__file__).parent / "frontend/data/ghana.geojson"
GHANA = shape(json.loads(_DATA.read_text())["features"][0]["geometry"])


def validar_ghana(point=None, bbox=None):
    geometry = Point(point[1], point[0]) if point is not None else box(bbox[1], bbox[0], bbox[3], bbox[2])
    if not GHANA.covers(geometry):
        raise ValueError("Selecciona un punto o un área completamente dentro de Ghana.")
