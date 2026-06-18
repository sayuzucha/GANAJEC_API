from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class BovinoCreate(BaseModel):
    nombre: str = Field(..., examples=["Lupita"])
    raza: str = Field(..., examples=["Holstein"])
    sexo: str = Field(..., pattern="^(hembra|macho)$")
    categoria: str = Field(
        ..., pattern="^(vaca|toro|becerro|becerra|novillo|vaquilla|torete)$",
        examples=["vaca"],
    )
    proposito: str = Field(..., pattern="^(leche|carne|doble|cria)$", examples=["leche"])
    fecha_nacimiento: Optional[date] = None
    peso_kg: float = Field(..., gt=0, examples=[480.5])
    id_externo: Optional[str] = Field(None, examples=["MX-0004"])


class BovinoUpdate(BaseModel):
    nombre: Optional[str] = None
    raza: Optional[str] = None
    sexo: Optional[str] = Field(None, pattern="^(hembra|macho)$")
    categoria: Optional[str] = Field(
        None, pattern="^(vaca|toro|becerro|becerra|novillo|vaquilla|torete)$"
    )
    proposito: Optional[str] = Field(None, pattern="^(leche|carne|doble|cria)$")
    fecha_nacimiento: Optional[date] = None
    peso_kg: Optional[float] = Field(None, gt=0)
    id_externo: Optional[str] = None


class RegistroSintomaCreate(BaseModel):
    bovino_id: str = Field(..., examples=["uuid-del-bovino"])
    texto_libre: str = Field(..., min_length=3, examples=["El animal presenta cojera leve en la pata trasera"])
    temperatura: Optional[float] = Field(None, examples=[39.2])
    produccion_leche: Optional[float] = Field(None, examples=[12.5])
    frecuencia_cardiaca: Optional[float] = Field(None, examples=[72.0], description="Latidos por minuto")
    frecuencia_respiratoria: Optional[float] = Field(None, examples=[28.0], description="Respiraciones por minuto")
    condicion_corporal: Optional[float] = Field(None, ge=1.0, le=5.0, examples=[3.5], description="Escala visual 1.0-5.0")
    consumo_alimento_kg: Optional[float] = Field(None, examples=[12.0], description="Kg de alimento dado")
    consumo_agua_l: Optional[float] = Field(None, examples=[65.0], description="Litros de agua aproximados")
    sintomas_seleccionados: Optional[list[str]] = Field(None, examples=[["cojera", "fiebre"]])


class AlertaUpdate(BaseModel):
    leida: bool


class UnirseRanchoRequest(BaseModel):
    codigo_invitacion: str = Field(
        ..., min_length=8, max_length=8,
        examples=["GAN4X2BQ"],
        description="Código de 8 caracteres que el dueño del rancho comparte con sus ganaderos.",
    )
