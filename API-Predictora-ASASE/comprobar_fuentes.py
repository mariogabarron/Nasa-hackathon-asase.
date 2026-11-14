"""Smoke test REAL: no mocks, no datos inventados, falla si falta una fuente."""
import argparse
import json
import sys

from getter import get_tabla
from servicio import agregar_tabla, predecir
from errores import ErrorFuente, ErrorConfiguracion


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--start',default='2025-04-01')
    p.add_argument('--end',default='2025-04-03')
    p.add_argument('--lat',type=float,default=9.4)
    p.add_argument('--lon',type=float,default=-.84)
    args=p.parse_args()
    try:
        point=[args.lat,args.lon]
        tabla=get_tabla(args.start,args.end,point,None)
        t,n=agregar_tabla(tabla,args.start,args.end,point=point)
        # Reutiliza la misma descarga para evitar repetir consultas externas.
        opciones=dict(start_date=args.start,end_date=args.end,point=point,bbox=None,
                      historial=[],getter=lambda *a:tabla)
        iac=predecir(**opciones,accion='iac',cultivo_id=1)
        rotacion=predecir(start_date=args.start,point=point,accion='rotaciones')
        print(json.dumps({'estado':'OK','dias':n,'iac_maiz':iac,
                          'rotacion_dias':rotacion['dias'],
                          'agregado':{'temp_min_C':t.temp_min_C,'temp_max_C':t.temp_max_C,
                                      'precipitacion_mm':t.precipitacion_mm}},
                         indent=2,ensure_ascii=False,allow_nan=False))
    except (ErrorFuente,ErrorConfiguracion,ValueError) as exc:
        print(f'FALLO: {exc}',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
