"""Valida expresiones con el SDK REAL y metadatos oficiales del SDK.

No equivale a descargar datos de Google: se sustituye solo computeValue.
"""
import json
from unittest.mock import patch

import ee
from ee.apitestcase import ApiTestCase

from getter import descargar_smap, descargar_suelo, construir_geometria


class EarthEngineGraphTests(ApiTestCase):
    def test_smap_fecha_final_inclusiva_y_grafo_serializable(self):
        grafos=[]

        def simular_respuesta(obj):
            grafos.append(json.loads(obj.serialize()))
            return {'features':[{'properties':{'fecha':'2025-04-01','escenas':8,
                                    'sm_surface':.2,'sm_rootzone':.3,'soil_temp_layer1':300.15}}]}

        geom=construir_geometria(ee,[9.4,-.84],None)
        with patch.object(ee.data,'computeValue',side_effect=simular_respuesta):
            df=descargar_smap(ee,'2025-04-01','2025-04-01',geom)
        self.assertEqual(len(df),1)
        serializado=json.dumps(grafos)
        self.assertIn('2025-04-02',serializado)
        self.assertIn('Image.reduceRegion',serializado)
        self.assertIn('NASA/SMAP/SPL4SMGP/008',serializado)

    def test_suelo_bbox_grafo_serializable(self):
        grafos=[]

        def simular_respuesta(obj):
            grafos.append(json.loads(obj.serialize()))
            return {'ph':60,'soc':150,'clay':200,'silt':400,'sand':400}

        geom=construir_geometria(ee,None,[9,-1,10,0])
        with patch.object(ee.data,'computeValue',side_effect=simular_respuesta):
            r=descargar_suelo(ee,geom)
        self.assertEqual(r['suelo_ph_0_30cm'],6)
        self.assertIn('projects/soilgrids-isric/phh2o_mean',json.dumps(grafos))
