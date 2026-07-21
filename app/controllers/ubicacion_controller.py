import json
import os
from typing import Optional
from fastapi import HTTPException

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

_estados = None
_estados_municipios = None


def _load_estados():
    global _estados
    if _estados is None:
        path = os.path.join(DATA_DIR, "estados.json")
        with open(path, "r", encoding="utf-8") as f:
            _estados = json.load(f)
    return _estados


def _load_estados_municipios():
    global _estados_municipios
    if _estados_municipios is None:
        path = os.path.join(DATA_DIR, "estados-municipios.json")
        with open(path, "r", encoding="utf-8") as f:
            _estados_municipios = json.load(f)
    return _estados_municipios


class UbicacionController:

    @staticmethod
    def get_estados():
        return _load_estados()

    @staticmethod
    def get_municipios(estado: str):
        data = _load_estados_municipios()

        for key in data:
            if key.lower() == estado.lower():
                return {"estado": key, "municipios": data[key]}

        raise HTTPException(
            status_code=404,
            detail=f"No se encontro el estado '{estado}'"
        )
