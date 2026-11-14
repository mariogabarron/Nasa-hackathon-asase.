"""Arranque: uvicorn main:app --host 127.0.0.1 --port 8000."""
import logging
import os
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from idiomas import IDIOMA, error_publico, nombre_cultivo
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictFloat, StrictStr, model_validator

from errores import DatosInsuficientes, ErrorConfiguracion, ErrorFuente
from getter import get_tabla
from servicio import predecir, CATALOGO
from validacion import validar_consulta, resolver_periodo
from geografia import validar_ghana

LOG = logging.getLogger(__name__)
Coordenada = StrictInt | StrictFloat
IdCultivo = Annotated[StrictInt, Field(ge=1)]


class Peticion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["es", "en"] = "es"
    start_date: StrictStr
    end_date: StrictStr | None = None
    point: tuple[Coordenada, Coordenada] | None = None
    bbox: tuple[Coordenada, Coordenada, Coordenada, Coordenada] | None = None
    historial: list[IdCultivo] = Field(default_factory=list, max_length=100)
    accion: Literal["iac", "rotaciones"]
    cultivo_id: IdCultivo | None = None
    n_recomendaciones: Annotated[StrictInt, Field(ge=1)] = 3

    @model_validator(mode="after")
    def comprobar(self):
        if self.accion != "rotaciones" and "n_recomendaciones" in self.model_fields_set:
            raise ValueError("n_recomendaciones solo se admite con rotaciones")
        self.end_date = resolver_periodo(self.start_date, self.end_date, self.accion)
        validar_consulta(self.start_date, self.end_date, self.point, self.bbox, permitir_largo=self.accion == "rotaciones")
        validar_ghana(self.point, self.bbox)
        if self.accion == "rotaciones" and self.cultivo_id is not None:
            raise ValueError("cultivo_id solo se utiliza con iac")
        return self


def proveedor_getter():
    # Punto de inyección para TestClient u otro getter del backend existente.
    return get_tabla


app = FastAPI(title="ASASE · API predictora", version="2.0.0",
              description="IAC y rotaciones a partir de observaciones; las rotaciones son escenarios condicionales.")
origenes = [x.strip() for x in os.environ.get("CORS_ORIGINS", "").split(",") if x.strip()]
if origenes:
    app.add_middleware(CORSMiddleware, allow_origins=origenes, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"], allow_credentials=False)


@app.get("/health")
def health():
    return {"status": "ok", "fuentes_externas_verificadas": False}


@app.get("/cultivos")
def cultivos(language: Literal["es", "en"] = "es"):
    token = IDIOMA.set(language)
    try:
        return [{"id": c.id, "nombre": nombre_cultivo(c.nombre), "familia": c.familia,
                 "duracion_ciclo_dias": c.duracion_ciclo_dias} for c in CATALOGO.values()]
    finally:
        IDIOMA.reset(token)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    if isinstance(exc.body, dict) and exc.body.get("language") == "en":
        fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
        return JSONResponse(status_code=422, content={"detail": {"codigo": "ENTRADA_INVALIDA",
            "mensaje": f"Invalid request ({fields}). Check required fields, dates, coordinates and crop IDs."}})
    return await request_validation_exception_handler(request, exc)


@app.post("/predecir")
def endpoint(peticion: Peticion, getter=Depends(proveedor_getter)):
    token = IDIOMA.set(peticion.language)
    try:
        return predecir(**peticion.model_dump(exclude={"language"}), getter=getter)
    except ErrorConfiguracion as exc:
        raise HTTPException(503, detail={"codigo": "CONFIGURACION", "mensaje": error_publico("CONFIGURACION", exc)}) from exc
    except DatosInsuficientes as exc:
        raise HTTPException(502, detail={"codigo": "DATOS_INCOMPLETOS", "mensaje": error_publico("DATOS_INCOMPLETOS", exc)}) from exc
    except ErrorFuente as exc:
        raise HTTPException(502, detail={"codigo": "FUENTE_EXTERNA", "mensaje": error_publico("FUENTE_EXTERNA", exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail={"codigo": "ENTRADA_INVALIDA", "mensaje": error_publico("ENTRADA_INVALIDA", exc)}) from exc

    finally:
        IDIOMA.reset(token)


# Frontend y API comparten origen; se conservan los endpoints originales.
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

FRONTEND = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND / "index.html")
