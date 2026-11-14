"""Pruebas HTTP del empaquetado y contrato compartido con el frontend."""
import unittest
from fastapi.testclient import TestClient
from main import app

class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_inicio_y_assets(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('/static/app.js', page.text)
        for path in ['app.js', 'base.js', 'app.css', 'original.css',
                     'vendor/leaflet/leaflet.js', 'vendor/leaflet/leaflet.css']:
            self.assertEqual(self.client.get('/static/' + path).status_code, 200, path)

    def test_no_se_exponen_archivos_del_servidor(self):
        for path in ['/static/../main.py', '/main.py', '/static/cultivos.json']:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_catalogo_con_ids_y_nombres(self):
        catalog = self.client.get('/cultivos').json()
        self.assertEqual(len(catalog), 12)
        self.assertEqual(len({c['id'] for c in catalog}), 12)
        self.assertTrue(all(isinstance(c['id'], int) and c['nombre'] for c in catalog))

    def test_api_documentada_sigue_disponible(self):
        schema = self.client.get('/openapi.json').json()
        self.assertIn('/predecir', schema['paths'])
        self.assertEqual(self.client.get('/docs').status_code, 200)
