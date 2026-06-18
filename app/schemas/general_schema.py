from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ── Dueno del rancho ──────────────────────────────────
class RanchoCreate(BaseModel):
    nombre: str = Field(..., min_length=2, examples=["Rancho El Paraíso"])
    municipio: str = Field(..., min_length=2, examples=["Ocozocoautla"])
    estado: str = Field(..., min_length=2, examples=["Chiapas"])


class RanchoUpdate(BaseModel):
    nombre: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None


class AsignarGanaderoRancho(BaseModel):
    """Asigna un ganadero ya existente a un rancho adicional."""
    ganadero_id: str = Field(..., examples=["uuid-del-ganadero"])


class GanaderoCreate(BaseModel):
    nombre: str = Field(..., min_length=3, examples=["Maria Lopez"])
    email: EmailStr = Field(..., examples=["maria@ganajec.ai"])
    password: str = Field(..., min_length=8, examples=["claveSegura123"])
    rancho_id: str = Field(..., examples=["uuid-del-rancho"])


class GanaderoUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


# ── Veterinario ───────────────────────────────────────
class VeterinarioCreate(BaseModel):
    nombre:       str            = Field(..., min_length=2, examples=["Dr. Juan Pérez"])
    telefono:     str            = Field(..., min_length=7, examples=["9611234567"])
    especialidad: Optional[str]  = Field(None, examples=["Medicina bovina"])
    notas:        Optional[str]  = Field(None, examples=["Disponible lunes y miércoles"])


class VeterinarioUpdate(BaseModel):
    nombre:       Optional[str] = None
    telefono:     Optional[str] = None
    especialidad: Optional[str] = None
    notas:        Optional[str] = None


# ── Administrador ─────────────────────────────────────
class UsuarioUpdate(BaseModel):
    activo: Optional[bool] = None
    rol: Optional[str] = Field(None, pattern="^(ganadero|dueno|admin)$")


class ConfiguracionUpdate(BaseModel):
    valor: str = Field(..., examples=["0.85"])
