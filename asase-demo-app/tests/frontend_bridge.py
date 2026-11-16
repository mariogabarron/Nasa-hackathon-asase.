"""Puente sin sockets para tests DOM: API real, fuentes diarias sintéticas.
No se importa desde producción y no sustituye comprobaciones con fuentes reales.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from fastapi.testclient import TestClient
from main import app, proveedor_getter


def tabla(inicio, fin, point=None, bbox=None):
    dates = pd.date_range(inicio, fin, name='fecha')
    return pd.DataFrame({
        'temp_media_C': 27., 'temp_min_C': 24., 'temp_max_C': 30.,
        'precipitacion_mm': 5., 'radiacion_solar_MJ_m2': 21.,
        'humedad_suelo_smap_m3m3': .25, 'humedad_raiz_smap_m3m3': .3,
        'temp_suelo_smap_C': 25., 'suelo_ph_0_30cm': 6.2,
        'suelo_carbono_organico_g_kg': 18., 'suelo_textura_clase': 'Franca (Loam)',
    }, index=dates)

app.dependency_overrides[proveedor_getter] = lambda: tabla
if __name__ == '__main__':
    args = json.load(sys.stdin)
    with TestClient(app) as client:
        r = client.request(args.get('method', 'GET'), args['url'], json=args.get('body'))
    print(json.dumps({'status': r.status_code, 'body': r.json()}, ensure_ascii=False))
