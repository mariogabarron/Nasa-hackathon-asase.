"""API opcional para conectar un frontend React mediante POST /iac."""
from fastapi import FastAPI, HTTPException
from motor_iac import evaluar_historial, CONFIG

app = FastAPI(title='ASASE IAC', version='0.1.0')

@app.get('/cultivos')
def listar_cultivos():
    return [{'codigo':k,'nombre':v['nombre'],'ciclo_dias':v['ciclo_dias']}
            for k,v in CONFIG['cultivos'].items()]

@app.post('/iac')
def calcular(datos: dict):
    try:
        return evaluar_historial(datos)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
