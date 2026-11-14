import json
import unittest
from datetime import date
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import getter
from errores import DatosInsuficientes, ErrorFuente, ErrorConfiguracion
from iac import calcular_iac, recomendar_rotacion
from main import app, proveedor_getter
from servicio import agregar_tabla, predecir, CATALOGO


def tabla_ejemplo():
    return pd.DataFrame({
        'temp_media_C':[24.,27.,30.], 'temp_min_C':[18.,20.,22.],
        'temp_max_C':[30.,32.,35.], 'precipitacion_mm':[2.,5.,8.],
        'radiacion_solar_MJ_m2':[18.,21.,24.],
        'humedad_suelo_smap_m3m3':[.20,.25,.30],
        'humedad_raiz_smap_m3m3':[.25,.30,.35],
        'temp_suelo_smap_C':[22.,25.,28.],
        'suelo_ph_0_30cm':[6.,6.2,6.4],
        'suelo_carbono_organico_g_kg':[15.,18.,21.],
        'suelo_textura_clase':['Franca (Loam)']*3,
    },index=pd.date_range('2025-04-01','2025-04-03',name='fecha'))


def tabla_2025():
    df=tabla_ejemplo().iloc[[1]].copy()
    df=pd.concat([df]*365,ignore_index=True)
    df.index=pd.date_range('2025-01-01','2025-12-31',name='fecha')
    df['temp_min_C']=24.;df['temp_max_C']=30.
    return df


def peticion(**cambios):
    return dict(start_date='2025-04-01',end_date='2025-04-03',point=[9.4,-.84],bbox=None,
                historial=[],accion='iac',**cambios)


class AgregacionTests(unittest.TestCase):
    def agregar(self,df=None,**kwargs):
        return agregar_tabla(tabla_ejemplo() if df is None else df,
                             '2025-04-01','2025-04-03',**({'point':[9.4,-.84]}|kwargs))

    def test_agregados_exactos(self):
        t,n=self.agregar()
        self.assertEqual(n,3)
        self.assertEqual(t.temp_min_C,18)
        self.assertEqual(t.temp_max_C,35)
        self.assertEqual(t.precipitacion_mm,15)
        for k,v in {'temp_media_C':27,'radiacion_solar_MJ_m2':21,
                    'humedad_suelo_smap_m3m3':.25,'humedad_raiz_smap_m3m3':.30,
                    'temp_suelo_smap_C':25,'suelo_ph_0_30cm':6.2,
                    'suelo_carbono_organico_g_kg':18}.items():
            self.assertAlmostEqual(getattr(t,k),v)
        self.assertEqual(t.suelo_textura_clase,'Franca (Loam)')
        self.assertEqual(t.fecha,'2025-04-03')

    def test_bbox_y_orden_inverso(self):
        t,_=self.agregar(tabla_ejemplo().iloc[::-1],point=None,bbox=[9,-1,10,0])
        self.assertEqual((t.latitud,t.longitud),(9.5,-.5))
        self.assertEqual(t.precipitacion_mm,15)

    def test_columna_fecha_y_no_mutacion(self):
        df=tabla_ejemplo().reset_index()
        original=df.copy(deep=True)
        t,_=self.agregar(df)
        self.assertEqual(t.precipitacion_mm,15)
        pd.testing.assert_frame_equal(df,original)

    def test_un_dia_inclusivo(self):
        t,n=agregar_tabla(tabla_ejemplo().iloc[:1],'2025-04-01','2025-04-01',point=[9,-1])
        self.assertEqual(n,1)
        self.assertEqual(t.precipitacion_mm,2)

    def test_dias_faltantes_duplicados_o_extra(self):
        df=tabla_ejemplo()
        for malo in [df.iloc[:2],pd.concat([df,df.iloc[:1]]),df.set_axis(pd.date_range('2025-04-02',periods=3))]:
            with self.assertRaises(DatosInsuficientes): self.agregar(malo)

    def test_nan_inf_sentinel_no_se_suman_como_cero(self):
        for v in [np.nan,np.inf,-999.,-9999.,None,True]:
            df=tabla_ejemplo().astype(object)
            df.iloc[1,df.columns.get_loc('precipitacion_mm')]=v
            if v is True:
                with self.assertRaises(DatosInsuficientes): self.agregar(df)
            else:
                t,_=self.agregar(df)
                self.assertIsNone(t.precipitacion_mm)

    def test_datos_diarios_invalidos_no_ocultos_por_media(self):
        df=tabla_ejemplo()
        df.loc[df.index[0],'humedad_suelo_smap_m3m3']=-.1
        with self.assertRaises(DatosInsuficientes): self.agregar(df)

    def test_textura_variable_y_columna_ausente(self):
        df=tabla_ejemplo()
        df.loc[df.index[1],'suelo_textura_clase']='Arcillosa'
        with self.assertRaises(DatosInsuficientes): self.agregar(df)
        t,_=self.agregar(tabla_ejemplo().drop(columns='temp_min_C'))
        self.assertIsNone(t.temp_min_C)

    def test_no_filas_subdiarias(self):
        df=tabla_ejemplo()
        df.index=df.index+pd.Timedelta(hours=1)
        with self.assertRaises(DatosInsuficientes): self.agregar(df)


class ServicioTests(unittest.TestCase):
    def test_inyecta_argumentos_exactos_y_unica_descarga(self):
        f=Mock(return_value=tabla_ejemplo())
        r=predecir(**peticion(cultivo_id=1),getter=f)
        f.assert_called_once_with('2025-04-01','2025-04-03',[9.4,-.84],None)
        t,n=agregar_tabla(tabla_ejemplo(),'2025-04-01','2025-04-03',point=[9.4,-.84])
        self.assertEqual(r,calcular_iac(t,CATALOGO[1],dias_precipitacion=n,catalogo=CATALOGO))
        self.assertEqual(set(r),{'iac','razon'})

    def test_sin_objetivo_devuelve_12_sin_inferirlo_del_historial(self):
        p=peticion();p['historial']=[1,5]
        f=Mock(return_value=tabla_ejemplo())
        r=predecir(**p,getter=f)
        self.assertEqual(set(r),set(map(str,range(1,13))))
        self.assertEqual(f.call_count,1)
        self.assertTrue(all(set(v)=={'iac','razon'} for v in r.values()))
        json.dumps(r,allow_nan=False)

    def test_ids_historial_penaliza_sin_fechas(self):
        p=peticion(cultivo_id=1)
        base=predecir(**p,getter=lambda *a:tabla_ejemplo())['iac']
        p['historial']=[1]
        ajustado=predecir(**p,getter=lambda *a:tabla_ejemplo())['iac']
        self.assertAlmostEqual(ajustado,base*.85,delta=.01)

    def test_entrada_invalida_no_llama_getter(self):
        for cambio in [{'historial':[99]},{'historial':['1']},{'historial':[True]},
                       {'accion':'rotacion'},{'point':None},{'bbox':[9,-1,10,0]},
                       {'point':[91,0]},{'end_date':'2025-03-30'},
                       {'end_date':'2027-01-01'},{'cultivo_id':99}]:
            f=Mock()
            with self.assertRaises(ValueError): predecir(**(peticion()|cambio),getter=f)
            f.assert_not_called()

    def test_rotacion_anual_y_ultima_familia(self):
        df=tabla_ejemplo()
        # Escenario apto para varios cultivos.
        df['temp_min_C']=24;df['temp_max_C']=30
        p=peticion();p.update(accion='rotaciones',historial=[1],start_date='2026-04-04',end_date=None)
        r=predecir(**p,getter=lambda *a:tabla_2025())
        self.assertEqual(r['fecha_inicio'],'2026-04-04')
        self.assertEqual(r['fecha_fin'],'2027-04-04')
        self.assertEqual(sum(t['dias'] for t in r['rotacion']),365)
        cultivos=[t for t in r['rotacion'] if t['tipo']=='cultivo']
        self.assertGreater(len(cultivos),0)
        self.assertNotEqual(cultivos[0]['familia'],'Poaceae')
        self.assertEqual(r['modo'],'escenarios_mensuales')


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.getter=Mock(return_value=tabla_ejemplo())
        app.dependency_overrides[proveedor_getter]=lambda:self.getter
        self.client=TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_post_iac(self):
        r=self.client.post('/predecir',json=peticion(cultivo_id=1))
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(set(r.json()),{'iac','razon'})

    def test_post_rotaciones_bbox(self):
        p=peticion();p.update(point=None,bbox=[9,-1,10,0],accion='rotaciones')
        p['end_date']=None
        self.getter.return_value=tabla_2025()
        r=self.client.post('/predecir',json=p)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['dias'],365)

    def test_post_todos(self):
        r=self.client.post('/predecir',json=peticion())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()),12)

    def test_422_campos_invalidos(self):
        for cambio in [{'historial':[True]},{'accion':'x'},{'cultivo_id':'1'},
                       {'point':[True,0]},{'campo_extra':4},{'historial':[99]}]:
            r=self.client.post('/predecir',json=peticion()|cambio)
            self.assertEqual(r.status_code,422,r.text)
        self.getter.assert_not_called()

    def test_502_no_datos(self):
        self.getter.return_value=tabla_ejemplo().iloc[:2]
        r=self.client.post('/predecir',json=peticion())
        self.assertEqual(r.status_code,502)
        self.assertEqual(r.json()['detail']['codigo'],'DATOS_INCOMPLETOS')

    def test_503_config_y_502_fuente(self):
        for error,status in [(ErrorConfiguracion('Sin credenciales'),503),(ErrorFuente('Sin conexión'),502)]:
            self.getter.side_effect=error
            r=self.client.post('/predecir',json=peticion())
            self.assertEqual(r.status_code,status)

    def test_openapi_y_catalogo(self):
        self.assertEqual(len(self.client.get('/cultivos').json()),12)
        self.assertIn('/predecir',self.client.get('/openapi.json').json()['paths'])


class GetterTests(unittest.TestCase):
    def test_geometria_bbox_sin_point(self):
        ee=Mock()
        getter.construir_geometria(ee,None,[9,-1,10,0])
        ee.Geometry.BBox.assert_called_once_with(-1,9,0,10)
        getter.construir_geometria(ee,[9.4,-.84],None)
        ee.Geometry.Point.assert_called_once_with([-.84,9.4])

    def test_power_parsea_sentinel_y_unidades(self):
        d={'properties':{'parameter':{k:{'20250401':1,'20250402':-999} for k in getter.POWER_COLUMNAS}},
           'parameters':{'ALLSKY_SFC_SW_DWN':{'units':'MJ/m^2/day'}}}
        r=getter.parsear_power(d)
        self.assertEqual(len(r),2)
        self.assertTrue(r.iloc[1].isna().all())
        d['parameters']['ALLSKY_SFC_SW_DWN']['units']='kWh/m^2/day'
        with self.assertRaises(ErrorFuente): getter.parsear_power(d)

    def test_power_consulta_utc_y_fechas_inclusivas(self):
        respuesta=Mock()
        respuesta.json.return_value={'properties':{'parameter':{k:{'20250401':1} for k in getter.POWER_COLUMNAS}}}
        with patch.object(getter.requests,'get',return_value=respuesta) as req:
            getter.descargar_power('2025-04-01','2025-04-01',9,-1)
            p=req.call_args.kwargs['params']
            self.assertEqual(p['start'],p['end'])
            self.assertEqual(p['time-standard'],'UTC')
            self.assertEqual(p['community'],'AG')

    def test_smap_kelvin_y_dias_incompletos(self):
        f=[{'fecha':'2025-04-01','escenas':8,'sm_surface':.2,'sm_rootzone':.3,'soil_temp_layer1':300.15}]
        r=getter.parsear_smap(f)
        self.assertAlmostEqual(r.iloc[0]['temp_suelo_smap_C'],27)
        f[0]['escenas']=7
        with self.assertRaises(DatosInsuficientes): getter.parsear_smap(f)

    def test_suelo_conserva_cero(self):
        r=getter.parsear_suelo({'ph':60,'soc':0,'clay':200,'silt':400,'sand':400})
        self.assertEqual(r['suelo_ph_0_30cm'],6)
        self.assertEqual(r['suelo_carbono_organico_g_kg'],0)
        self.assertEqual(r['suelo_textura_clase'],'Franca (Loam)')

    def test_join_no_pierde_ultimo_dia(self):
        t=tabla_ejemplo()
        power=t[list(getter.POWER_COLUMNAS.values())]
        smap=t[list(getter.SMAP_COLUMNAS.values())].iloc[:2]
        suelo=t.iloc[0][['suelo_ph_0_30cm','suelo_carbono_organico_g_kg','suelo_textura_clase']].to_dict()
        with patch.object(getter,'inicializar_ee',return_value=Mock()), \
             patch.object(getter,'descargar_power',return_value=power), \
             patch.object(getter,'descargar_smap',return_value=smap), \
             patch.object(getter,'descargar_suelo',return_value=suelo):
            r=getter.get_tabla('2025-04-01','2025-04-03',point=[9,-1])
        self.assertEqual(len(r),3)
        self.assertEqual(r['precipitacion_mm'].sum(),15)
        self.assertTrue(pd.isna(r.iloc[-1]['humedad_raiz_smap_m3m3']))


if __name__=='__main__':
    unittest.main()

class NulosTests(unittest.TestCase):
    def test_ph_ausente_http_200(self):
        df=tabla_ejemplo();df['suelo_ph_0_30cm']=np.nan
        app.dependency_overrides[proveedor_getter]=lambda:lambda *a:df
        try:
            with TestClient(app) as client:
                r=client.post('/predecir',json=peticion(cultivo_id=1))
                self.assertEqual(r.status_code,200,r.text)
                self.assertIn('suelo_ph_0_30cm',r.json()['razon'])
                self.assertTrue(0<=r.json()['iac']<=100)
        finally: app.dependency_overrides.clear()

    def test_media_parcial_y_rotacion(self):
        df=tabla_ejemplo();df.loc[df.index[0],'temp_media_C']=np.nan
        df['suelo_ph_0_30cm']=np.nan
        t,_=agregar_tabla(df,'2025-04-01','2025-04-03',point=[9,-1])
        self.assertEqual(t.temp_media_C,28.5)
        p=peticion();p['accion']='rotaciones';p['end_date']=None
        r=predecir(**p,getter=lambda *a:tabla_2025())
        self.assertEqual(r['dias'],365)
        self.assertEqual(r['referencia']['anio'],2025)

    def test_todo_ausente_no_inventa(self):
        df=tabla_ejemplo()
        for k in df.columns:
            if k!='suelo_textura_clase': df[k]=np.nan
        with self.assertRaises(DatosInsuficientes):
            agregar_tabla(df,'2025-04-01','2025-04-03',point=[9,-1])

class PeriodoRotacionesTests(unittest.TestCase):
    def test_multianual_referencia_2025(self):
        f=Mock(return_value=tabla_2025())
        r=predecir('2026-01-01','2027-12-31',point=[9,-1],accion='rotaciones',getter=f)
        f.assert_called_once_with('2025-01-01','2025-12-31',[9,-1],None)
        self.assertEqual(r['dias'],730)
        self.assertEqual(r['fecha_fin'],'2028-01-01')
        self.assertEqual(sum(t['dias'] for t in r['rotacion']),730)
        self.assertGreater(r['dias_cultivados'],500)
        self.assertFalse(any(t['tipo']=='preparacion' for t in r['rotacion']))

    def test_default_y_bisiesto(self):
        r=predecir('2027-04-01',point=[9,-1],accion='rotaciones',getter=lambda *a:tabla_2025())
        self.assertEqual(r['dias'],366)
        self.assertEqual(r['fecha_inicio'],'2027-04-01')
        self.assertEqual(r['periodo_plantacion']['end_date'],'2028-03-31')

    def test_iac_366_dias_rechazado(self):
        with self.assertRaises(ValueError):
            predecir('2024-01-01','2024-12-31',point=[9,-1],accion='iac',getter=Mock())

    def test_periodo_corto_no_recorta_ciclo(self):
        r=predecir('2026-04-01','2026-04-10',point=[9,-1],accion='rotaciones',getter=lambda *a:tabla_2025())
        self.assertEqual(r['dias'],10)
        self.assertEqual(r['dias_cultivados'],0)

class MultiplesTests(unittest.TestCase):
    def test_tres_distintas_ordenadas_una_descarga(self):
        f=Mock(return_value=tabla_2025())
        r=predecir('2026-01-01',point=[9,-1],accion='rotaciones',getter=f)
        self.assertEqual(r['n_devueltas'],3)
        self.assertEqual(f.call_count,1)
        firmas=[tuple(t['cultivo_id'] for t in p['rotacion'] if t['tipo']=='cultivo') for p in r['recomendaciones']]
        self.assertEqual(len(set(firmas)),3)
        orden=[(p['iac_medio_cultivado'],p['dias_cultivados']) for p in r['recomendaciones']]
        self.assertEqual(orden,sorted(orden,reverse=True))
        for p in r['recomendaciones']:
            self.assertEqual(sum(t['dias'] for t in p['rotacion']),365)

    def test_cinco_y_una(self):
        for n in [1,5]:
            r=predecir('2026-01-01',point=[9,-1],accion='rotaciones',n_recomendaciones=n,getter=lambda *a:tabla_2025())
            self.assertEqual(r['n_devueltas'],n)

    def test_sin_opciones_no_duplica_barbecho(self):
        r=predecir('2026-01-01','2026-01-10',point=[9,-1],accion='rotaciones',n_recomendaciones=3,getter=lambda *a:tabla_2025())
        self.assertEqual(r['n_devueltas'],1)
        self.assertIn('aviso_recomendaciones',r)

    def test_http_validacion_y_valor_predeterminado(self):
        f=Mock(return_value=tabla_2025())
        app.dependency_overrides[proveedor_getter]=lambda:f
        try:
            with TestClient(app) as client:
                p=peticion();p.update(accion='rotaciones',end_date=None)
                for n in [0,-1,1.5,True,'3',None]:
                    self.assertEqual(client.post('/predecir',json=p|{'n_recomendaciones':n}).status_code,422)
                f.assert_not_called()
                r=client.post('/predecir',json=p)
                self.assertEqual(r.status_code,200,r.text)
                self.assertEqual(r.json()['n_solicitadas'],3)
        finally: app.dependency_overrides.clear()
