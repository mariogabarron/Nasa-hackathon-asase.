import copy
import unittest
from datetime import date
from motor_iac import (
    CONFIG, calcular_iac_observacion, estacion_para, evaluar_historial,
    puntuar_intervalo, DYNAMICAS,
)

class MotorIACTest(unittest.TestCase):
    def setUp(self):
        self.fecha=date(2026,6,15)
        self.suelo={'suelo_ph_0_30cm':6.3,'suelo_carbono_organico_g_kg':14,
                    'suelo_textura_clase':'Franco'}
        self.obs={'temp_media_C':26,'temp_min_C':19,'temp_max_C':31,
                  'precipitacion_mm':130,'radiacion_solar_MJ_m2':21,
                  'humedad_suelo_smap_m3m3':.27,'humedad_raiz_smap_m3m3':.30,
                  'temp_suelo_smap_C':27}

    def test_pesos_11_suman_uno(self):
        for name, conf in CONFIG['estaciones'].items():
            with self.subTest(estacion=name):
                self.assertEqual(len(conf['pesos']),11)
                self.assertAlmostEqual(sum(conf['pesos'].values()),1.0)

    def test_12_cultivos_tienen_11_variables(self):
        self.assertEqual(len(CONFIG['cultivos']),12)
        for name, conf in CONFIG['cultivos'].items():
            with self.subTest(cultivo=name):
                self.assertEqual(len(conf['intervalos']),9)
                self.assertEqual(set(conf['textura']),{'S1','S2','S3','N'})

    def test_mapeo_estaciones(self):
        for mon, expected in [(1,'epoca_seca_harmattan'),(3,'epoca_seca_harmattan'),
                              (4,'inicio_lluvias_siembra'),(6,'inicio_lluvias_siembra'),
                              (7,'plena_lluvia_crecimiento'),(9,'plena_lluvia_crecimiento'),
                              (10,'retirada_lluvias_cosecha'),(11,'retirada_lluvias_cosecha'),
                              (12,'epoca_seca_harmattan')]:
            self.assertEqual(estacion_para(date(2026,mon,15)),expected)

    def test_cada_cultivo_ideal_produce_100(self):
        for key,conf in CONFIG['cultivos'].items():
            with self.subTest(cultivo=key):
                vals={}
                for nombre,bd in conf['intervalos'].items():
                    vals[nombre]=(bd[2]+bd[3])/2
                vals['suelo_carbono_organico_g_kg']=conf['carbono_organico_minimos']['S1']+2
                vals['suelo_textura_clase']=conf['textura']['S1'][0]
                suelo={k:vals[k] for k in ('suelo_ph_0_30cm','suelo_carbono_organico_g_kg','suelo_textura_clase')}
                obs={k:vals[k] for k in DYNAMICAS}
                result=calcular_iac_observacion(key,self.fecha,suelo,obs)
                self.assertEqual(result['iac_100'],100)
                self.assertFalse(result['veto_activado'])

    def test_veto_precipitacion_maiz(self):
        obs=self.obs.copy();obs['precipitacion_mm']=20
        res=calcular_iac_observacion('maiz',self.fecha,self.suelo,obs)
        self.assertTrue(res['veto_activado'])
        self.assertIn('precipitacion_mm',res['variables_criticas_en_N'])
        self.assertEqual(res['iac_100'],0)
        self.assertGreater(res['iac_ponderado_antes_de_vetos_100'],0)

    def test_factor_no_critico_n_no_anula(self):
        obs=self.obs.copy();obs['temp_min_C']=8
        # Debe conservar consistencia temp_min<=temp_media<=temp_max.
        res=calcular_iac_observacion('maiz',self.fecha,self.suelo,obs)
        self.assertFalse(res['veto_activado'])
        self.assertGreater(res['iac_100'],0)
        self.assertEqual(next(x for x in res['contribuciones'] if x['parametro']=='temp_min_C')['categoria'],'N')

    def test_ajuste_suelo_arenoso_humedad(self):
        soil=dict(self.suelo, suelo_textura_clase='Franco-arenoso')
        obs=self.obs.copy(); obs['humedad_suelo_smap_m3m3']=.23
        sin=calcular_iac_observacion('maiz',self.fecha,soil,obs)
        soil.update(suelo_arena_pct=70,suelo_arcilla_pct=15,suelo_limo_pct=15)
        con=calcular_iac_observacion('maiz',self.fecha,soil,obs)
        self.assertEqual(con['ajuste_minimo_humedad_m3m3'],.03)
        def cat(res):return next(x['categoria'] for x in res['contribuciones'] if x['parametro']=='humedad_suelo_smap_m3m3')
        self.assertEqual(cat(sin),'S1')
        self.assertEqual(cat(con),'S2')
        self.assertLess(con['iac_100'],sin['iac_100'])

    def test_arroz_exceso_humedad_fuera_de_tabla(self):
        conf=CONFIG['cultivos']['arroz_bajio']['intervalos']['humedad_raiz_smap_m3m3']
        with self.assertRaisesRegex(ValueError,'no definido'):
            puntuar_intervalo(.56,conf,0,'humedad_raiz_smap_m3m3','arroz_bajio')

    def test_entrada_historica(self):
        hist=[]
        for fecha in ('2026-04-15','2026-05-15','2026-06-15'):
            hist.append(dict(fecha=fecha,**self.obs))
        d={'region':'Northern','cultivo':'maiz','fecha_consulta':'2026-06-15',
           'suelo':self.suelo,'observaciones':hist}
        res=evaluar_historial(d)
        self.assertEqual(res['numero_meses_con_datos'],3)
        self.assertEqual(res['ultima_observacion']['estacion'],'inicio_lluvias_siembra')
        self.assertIsInstance(res['variacion_entre_primera_y_ultima_observacion'],float)

    def test_no_aceptar_futuro_ni_antiguos(self):
        for fecha in ('2026-06-16','2025-06-14'):
            with self.subTest(fecha=fecha), self.assertRaisesRegex(ValueError,'fuera del intervalo'):
                evaluar_historial({'region':'Northern','cultivo':'maiz','fecha_consulta':'2026-06-15',
                                   'suelo':self.suelo,'observaciones':[dict(fecha=fecha,**self.obs)]})

    def test_faltan_datos_no_imputa(self):
        o=self.obs.copy();del o['humedad_raiz_smap_m3m3']
        with self.assertRaisesRegex(ValueError,'Falta'):
            calcular_iac_observacion('maiz',self.fecha,self.suelo,o)

if __name__=='__main__':
    unittest.main(verbosity=2)
