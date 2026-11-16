import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
from geografia import GHANA, validar_ghana
from main import app, proveedor_getter
from shapely.geometry import Point


class GhanaTests(unittest.TestCase):
    def test_boundary_assets_are_identical(self):
        root = Path(__file__).parents[1] / 'frontend/data'
        data = json.loads((root/'ghana.geojson').read_text())
        script = (root/'ghana.js').read_text().split('const GHANA_BOUNDARY = ', 1)[1].strip().removesuffix(';')
        self.assertEqual(data, json.loads(script))
        self.assertTrue(GHANA.is_valid)

    def test_points_and_area(self):
        for point in [[9.4,-.84],[5.6037,-.187],[6.6885,-1.6244]]:
            validar_ghana(point=point)
        validar_ghana(bbox=[9,-1,10,0])
        for point in [[6.13,1.22],[12.37,-1.52],[0,0],[5,-3],[9,7.4]]:
            with self.assertRaises(ValueError): validar_ghana(point=point)

    def test_corners_inside_are_not_enough(self):
        b=[6.668607,-.27776,7.812855,.520324]
        self.assertTrue(all(GHANA.covers(Point(x,y)) for y,x in [(b[0],b[1]),(b[0],b[3]),(b[2],b[1]),(b[2],b[3])]))
        with self.assertRaises(ValueError): validar_ghana(bbox=b)

    def test_api_rejects_foreign_locations_before_fetching(self):
        getter = Mock(side_effect=AssertionError('must not fetch'))
        app.dependency_overrides[proveedor_getter]=lambda:getter
        try:
            client=TestClient(app)
            for geometry in [{'point':[6.13,1.22]}, {'bbox':[6.668607,-.27776,7.812855,.520324]}]:
                for language in ['es','en']:
                    r=client.post('/predecir',json={'accion':'iac','cultivo_id':1,'start_date':'2025-01-01','end_date':'2025-01-02','language':language,**geometry})
                    self.assertEqual(r.status_code,422)
                    if language=='en': self.assertIn('Invalid request',r.text)
            getter.assert_not_called()
        finally:
            app.dependency_overrides.clear()
