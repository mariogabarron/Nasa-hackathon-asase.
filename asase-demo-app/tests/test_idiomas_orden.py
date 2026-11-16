import copy
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app, proveedor_getter
from servicio import predecir
from idiomas import IDIOMA
from test_integracion import tabla_2025, tabla_ejemplo
from errores import ErrorConfiguracion, ErrorFuente, DatosInsuficientes


class LanguageAndOrderingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[proveedor_getter] = lambda: lambda start, end, *a: (
            tabla_2025() if start == '2025-01-01' else tabla_ejemplo())

    def tearDown(self):
        app.dependency_overrides.clear()

    def request(self, language='en', **kwargs):
        payload = dict(start_date='2025-04-01', end_date='2025-04-03',
                       point=[9.4, -.84], accion='iac', cultivo_id=1, language=language)
        payload.update(kwargs)
        return self.client.post('/predecir', json=payload)

    def test_iac_english_preserves_score_and_spanish_default(self):
        en = self.request().json()
        es = self.request('es').json()
        self.assertEqual(en['iac'], es['iac'])
        self.assertIn('Maximum temperature', en['razon'])
        self.assertIn('Temperatura máxima', es['razon'])
        self.assertNotIn('días', en['razon'])
        self.assertEqual(IDIOMA.get(), 'es')

    def test_english_rotations_crop_names_reasons_and_assumptions(self):
        en = self.request(start_date='2027-01-01', end_date='2027-12-31',
                          accion='rotaciones', cultivo_id=None, historial=[1, 5]).json()
        self.assertIn('not a forecast', en['referencia']['metodo'])
        self.assertIn('descending', en['criterio_orden'])
        for p in en['recomendaciones']:
            self.assertIn('Proposal', p['justificacion'])
            self.assertTrue(all('días' not in s and 'cultivos' not in s for s in p['supuestos']))
            for seg in p['rotacion']:
                self.assertNotIn('cultivo', seg['justificacion'])
                if seg['tipo'] == 'cultivo':
                    self.assertIn(seg['cultivo'], ['Maize','Sorghum','Millet','Rice','Groundnut','Yam',
                        'Cowpea','Soybean','Cassava','Sweet potato','Pea','Cotton'])

    def test_partial_data_notices_are_english(self):
        df=tabla_ejemplo();df['suelo_ph_0_30cm']=float('nan');df.loc[df.index[0],'precipitacion_mm']=float('nan')
        app.dependency_overrides[proveedor_getter] = lambda: lambda *a: df
        r=self.request().json()
        self.assertIn('Partial IAC', r['razon'])
        self.assertIn('days available', r['razon'])
        self.assertIn('Precipitation excluded', r['razon'])
        self.assertNotIn('días', r['razon'])

    def test_errors_and_validation_in_english(self):
        for error in [ErrorConfiguracion('error español'), ErrorFuente('fuente no disponible'), DatosInsuficientes('sin datos')]:
            def fail(*a): raise error
            app.dependency_overrides[proveedor_getter] = lambda: fail
            r=self.request()
            self.assertIn(r.status_code, [502,503])
            self.assertNotIn('español', r.text)
            self.assertNotIn('fuente no disponible', r.text)
        r=self.request(start_date='fecha-invalida')
        self.assertEqual(r.status_code,422)
        self.assertIn('Invalid request',r.json()['detail']['mensaje'])
        self.assertEqual(self.request(language='fr').status_code,422)

    def test_catalogue_language_and_concurrent_request_isolation(self):
        en=self.client.get('/cultivos?language=en').json()
        self.assertEqual(next(c for c in en if c['id']==1)['nombre'],'Maize')
        with ThreadPoolExecutor(max_workers=4) as pool:
            langs=['en','es']*4
            results=list(pool.map(lambda lang: self.request(lang).json()['razon'],langs))
        for lang,reason in zip(langs,results):
            self.assertIn('Maximum temperature' if lang=='en' else 'Temperatura máxima',reason)

    def test_explicit_descending_iac_order_tie_break_and_null_last(self):
        base=dict(rotacion=[],dias=365,supuestos=[],justificacion='test')
        plans=[dict(base,iac_medio_cultivado=70,dias_cultivados=350),
               dict(base,iac_medio_cultivado=None,dias_cultivados=0),
               dict(base,iac_medio_cultivado=90,dias_cultivados=200),
               dict(base,iac_medio_cultivado=90,dias_cultivados=300)]
        with patch('servicio.recomendar_rotacion',return_value=copy.deepcopy(plans)):
            r=predecir('2027-01-01','2027-12-31',point=[9,-1],accion='rotaciones',
                       n_recomendaciones=4,getter=lambda *a:tabla_2025())
        self.assertEqual([(p['iac_medio_cultivado'],p['dias_cultivados']) for p in r['recomendaciones']],
                         [(90,300),(90,200),(70,350),(None,0)])
        self.assertEqual([p['posicion'] for p in r['recomendaciones']],[1,2,3,4])
        self.assertEqual(r['iac_medio_cultivado'],90)
        self.assertEqual(r['dias_cultivados'],300)
