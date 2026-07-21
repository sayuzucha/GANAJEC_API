from fastapi import APIRouter
from app.controllers.ubicacion_controller import UbicacionController

router = APIRouter()


@router.get("/estados")
def estados():
    return UbicacionController.get_estados()


@router.get("/municipios/{estado}")
def municipios(estado: str):
    return UbicacionController.get_municipios(estado)
