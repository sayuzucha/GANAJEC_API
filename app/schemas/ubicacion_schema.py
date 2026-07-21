from pydantic import BaseModel
from typing import List


class EstadoResponse(BaseModel):
    cve_ent: str
    clave: str
    nombre: str


class MunicipiosResponse(BaseModel):
    estado: str
    municipios: List[str]


class EstadosMunicipiosResponse(BaseModel):
    estados: List[EstadoResponse]
