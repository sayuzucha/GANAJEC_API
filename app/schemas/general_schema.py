from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ── Dueno del rancho ──────────────────────────────────
class RanchoUpdate(BaseModel):
    nombre: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None


class GanaderoCreate(BaseModel):
    nombre: str = Field(..., min_length=3, examples=["Maria Lopez"])
    email: EmailStr = Field(..., examples=["maria@ganajec.ai"])
    password: str = Field(..., min_length=8, examples=["claveSegura123"])
    rancho_id: str = Field(..., examples=["uuid-del-rancho"])


class GanaderoUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


# ── Administrador ─────────────────────────────────────
class UsuarioUpdate(BaseModel):
    activo: Optional[bool] = None
    rol: Optional[str] = Field(None, pattern="^(ganadero|dueno|admin)$")


class ConfiguracionUpdate(BaseModel):
    valor: str = Field(..., examples=["0.85"])
