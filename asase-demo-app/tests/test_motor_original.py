import json
import math
import unittest
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

from iac import (Cultivo, Territorio, Configuracion, RegistroCultivo, cargar_cultivos,
                 cargar_historial, calcular_iac, evaluar_iac, pesos_normalizados,
                 estacion, recomendar_rotacion, procesar_peticion, idoneidad_intervalo,
                 aniversario, PESOS_PDF)

ROOT = Path(__file__).parent


class TestIAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = cargar_cultivos(ROOT / 'cultivos.json')
        cls.payload = json.loads((ROOT / 'ejemplo_iac.json').read_text())
        cls.t = Territorio(**cls.payload['territorio'])
        cls.c = cls.cat[1]

    def test_catalogo_12_cultivos(self):
        self.assertEqual(set(self.cat), set(range(1, 13)))
        self.assertEqual(self.cat[12].nombre, 'Caupí')
        self.assertFalse(hasattr(self.c, 'suelo_textura_clase'))

    def test_estaciones_y_sumas(self):
        esperado = ['seca'] * 3 + ['inicio_lluvias'] * 3 + ['plena_lluvia'] * 3 + ['retirada_lluvias'] * 2 + ['seca']
        for mes, est in enumerate(esperado, 1):
            fecha = f'2026-{mes:02d}-01'
            self.assertEqual(estacion(fecha), est)
            self.assertAlmostEqual(sum(pesos_normalizados(fecha).values()), 1)
        for valores, total in zip(PESOS_PDF.values(), [.95, .93, .93, .95]):
            self.assertAlmostEqual(sum(valores), total)

    def test_ideal_cien_todas_estaciones(self):
        for mes in range(1, 13):
            r = calcular_iac(replace(self.t, fecha=f'2026-{mes:02d}-01'), self.c, dias_precipitacion=30)
            self.assertEqual(r, {'iac': 100.0, 'razon': None})

    def test_textura_ignorada(self):
        a = calcular_iac(self.t, self.c, dias_precipitacion=30)
        b = calcular_iac(replace(self.t, suelo_textura_clase='Cualquier texto'), self.c, dias_precipitacion=30)
        self.assertEqual(a, b)

    def test_unidades_lluvia(self):
        a = calcular_iac(self.t, self.c, dias_precipitacion=30)
        b = calcular_iac(replace(self.t, precipitacion_mm=600), self.c, dias_precipitacion=120)
        self.assertEqual(a, b)
        self.assertEqual(b, calcular_iac(replace(self.t, precipitacion_mm=600), self.c))

    def test_lluvia_cero_y_excesiva(self):
        for lluvia in [0, 1000]:
            r = evaluar_iac(replace(self.t, precipitacion_mm=lluvia), self.c, dias_precipitacion=30)
            self.assertAlmostEqual(r['iac'], 100 * (1 - .22/.95))
            self.assertIn('Precipitación', r['razon'])

    def test_peor_factor_es_perdida_ponderada(self):
        # Carbono: puntuación 0. Superficie: 0.5, pero tiene cuatro veces su peso.
        t = replace(self.t, suelo_carbono_organico_g_kg=0, humedad_suelo_smap_m3m3=.125)
        r = evaluar_iac(t, self.c, dias_precipitacion=30)
        self.assertIn('Humedad superficial', r['razon'])

    def test_conservacion_de_perdidas(self):
        hist = [RegistroCultivo(self.t.id, 1, '2025-11-01', '2026-03-31')]
        r = evaluar_iac(replace(self.t, precipitacion_mm=0), self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat)
        self.assertAlmostEqual(100 - r['iac'], sum(d['perdida_puntos'] for d in r['detalles']))

    def test_historial_efecto_y_caducidad(self):
        hist = [RegistroCultivo(self.t.id, 1, '2025-11-01', '2026-04-01')]
        r = calcular_iac(self.t, self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat)
        self.assertEqual(r['iac'], 85)
        self.assertIn('Historial', r['razon'])
        hist = [RegistroCultivo(self.t.id, 1, '2024-11-01', '2025-04-01')]
        self.assertEqual(calcular_iac(self.t, self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat)['iac'], 100)

    def test_familia_y_familia_distinta(self):
        for cid, esperado in [(2, 92), (5, 100)]:
            hist = [RegistroCultivo(self.t.id, cid, '2025-11-01', '2026-04-01')]
            self.assertEqual(calcular_iac(self.t, self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat)['iac'], esperado)

    def test_ajuste_desactivable(self):
        hist = [RegistroCultivo(self.t.id, 1, '2025-11-01', '2026-04-01')]
        cfg = Configuracion(penalizacion_historial_max=0)
        self.assertEqual(calcular_iac(self.t, self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat, config=cfg)['iac'], 100)

    def test_limite_penalizacion(self):
        hist = [RegistroCultivo(self.t.id, 1, '2025-09-01', '2025-12-01'),
                RegistroCultivo(self.t.id, 1, '2025-12-01', '2026-04-01')]
        cfg = Configuracion(penalizacion_mismo_cultivo=.9)
        self.assertEqual(calcular_iac(self.t, self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat, config=cfg)['iac'], 75)

    def test_historial_invalido(self):
        casos = [
            [RegistroCultivo('otra', 1, '2025-01-01', '2025-03-01')],
            [RegistroCultivo(self.t.id, 99, '2025-01-01', '2025-03-01')],
            [RegistroCultivo(self.t.id, 1, '2026-03-01', '2026-05-01')],
            [RegistroCultivo(self.t.id, 1, '2025-01-01', '2025-03-01'),
             RegistroCultivo(self.t.id, 2, '2025-02-01', '2025-04-01')],
        ]
        for hist in casos:
            with self.assertRaises(ValueError):
                calcular_iac(self.t, self.c, dias_precipitacion=30, historial=hist, catalogo=self.cat)

    def test_no_nan_inf_none_bool_ni_cadenas(self):
        for valor in [float('nan'), float('inf'), None, True, '20']:
            with self.assertRaises(ValueError):
                replace(self.t, temp_media_C=valor)

    def test_datos_fisicos_invalidos(self):
        for kwargs in [{'humedad_raiz_smap_m3m3':1.1}, {'suelo_ph_0_30cm':15},
                       {'temp_min_C':35}, {'precipitacion_mm':-1}, {'fecha':'2026-02-30'},
                       {'latitud':91}, {'fecha':'20260401'}]:
            with self.assertRaises(ValueError):
                replace(self.t, **kwargs)

    def test_cultivo_invalido(self):
        for kwargs in [{'temp_media_C':(32,18)}, {'temp_tope':(20,30)},
                       {'duracion_ciclo_dias':0}, {'suelo_carbono_organico_g_kg':0}]:
            with self.assertRaises(ValueError):
                replace(self.c, **kwargs)

    def test_temperaturas_tope(self):
        r = evaluar_iac(replace(self.t, temp_min_C=10, temp_max_C=40), self.c, dias_precipitacion=30)
        scores = {d['parametro']: d['idoneidad'] for d in r['detalles']}
        self.assertEqual(scores['temp_min_C'], 0)
        self.assertEqual(scores['temp_max_C'], 0)

    def test_rampa(self):
        for x, score in [(0,0), (5,.5), (10,1), (15,1), (20,1), (25,.5), (30,0)]:
            self.assertAlmostEqual(idoneidad_intervalo(x, (10,20)), score)

    def test_carbono_no_penaliza_superavit(self):
        self.assertEqual(calcular_iac(replace(self.t, suelo_carbono_organico_g_kg=50), self.c, dias_precipitacion=30)['iac'], 100)

    def test_api_solo_dos_claves(self):
        r = procesar_peticion(self.payload, self.cat)
        self.assertEqual(set(r), {'iac','razon'})
        json.dumps(r, allow_nan=False)

    def test_api_rechaza_errores(self):
        for cambios in [{'cultivo_id':999}, {'dias_precipitacion':0}, {'dias_precipitacion':None},
                        {'cultivo_id':True}, {'otra':3}, {'accion':'otro'}]:
            with self.assertRaises(ValueError):
                procesar_peticion(dict(self.payload, **cambios), self.cat)

    def test_catalogo_duplicado(self):
        with self.assertRaises(ValueError):
            cargar_cultivos([asdict(self.c), asdict(self.c)])

    def verificar_plan(self, plan):
        self.assertEqual(sum(t['dias'] for t in plan['rotacion']), plan['dias'])
        cursor = plan['fecha_inicio']
        ultima_familia = None
        for t in plan['rotacion']:
            self.assertEqual(t['fecha_inicio'], cursor)
            self.assertEqual((date.fromisoformat(t['fecha_fin'])-date.fromisoformat(cursor)).days,t['dias'])
            if t['tipo']=='cultivo':
                c=self.cat[t['cultivo_id']]
                self.assertEqual(t['dias'], c.duracion_ciclo_dias)
                self.assertNotEqual(ultima_familia,c.familia)
                self.assertGreaterEqual(t['iac_estimado'],60)
                ultima_familia=c.familia
            cursor=t['fecha_fin']
        self.assertEqual(cursor,plan['fecha_fin'])

    def test_rotacion_anual(self):
        plan=recomendar_rotacion(self.t,self.cat,dias_precipitacion=30,ancho_busqueda=16)
        self.verificar_plan(plan)
        self.assertEqual(plan['dias'],365)
        self.assertGreater(plan['dias_cultivados'],0)
        self.assertEqual(plan['modo'],'escenario_constante')

    def test_rotacion_no_fuerza_sequia(self):
        plan=recomendar_rotacion(replace(self.t,precipitacion_mm=0),self.cat,dias_precipitacion=30)
        self.verificar_plan(plan)
        self.assertEqual(plan['dias_cultivados'],0)

    def test_rotacion_mensual(self):
        payload=json.loads((ROOT/'ejemplo_rotacion_mensual.json').read_text())
        payload['ancho_busqueda']=16
        plan=procesar_peticion(payload,self.cat)
        self.verificar_plan(plan)
        self.assertEqual(plan['modo'],'escenarios_mensuales')
        for t in plan['rotacion']:
            if t['tipo']=='cultivo':
                self.assertLessEqual(t['fecha_fin'],'2026-10-01')

    def test_no_fallback_escenario_incompleto(self):
        with self.assertRaises(ValueError):
            recomendar_rotacion(self.t,self.cat,dias_precipitacion=30,escenarios={})

    def test_bisiesto(self):
        self.assertEqual((aniversario(date(2027,4,1))-date(2027,4,1)).days,366)
        self.assertEqual(aniversario(date(2028,2,29)),date(2029,2,28))
        p=recomendar_rotacion(replace(self.t,fecha='2027-04-01',precipitacion_mm=0),self.cat,dias_precipitacion=30)
        self.verificar_plan(p)
        self.assertEqual(p['dias'],366)


if __name__ == '__main__':
    unittest.main()
