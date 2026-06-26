from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date


class GanaderoPerfilUpdate(BaseModel):
    nombre:   Optional[str]      = Field(None, min_length=3, examples=["Maria Lopez"])
    email:    Optional[EmailStr] = Field(None, examples=["maria@ganajec.ai"])
    password: Optional[str]      = Field(None, min_length=8, examples=["nuevaClave123"])


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
    # ── Vitales (originales) ──────────────────────────────────────
    temperatura: Optional[float] = Field(None, ge=35.0, le=45.0, examples=[39.2], description="Celsius, rango bovino normal 38-39.5")
    produccion_leche: Optional[float] = Field(None, ge=0.0, le=100.0, examples=[12.5], description="Litros/dia")
    frecuencia_cardiaca: Optional[float] = Field(None, ge=20.0, le=250.0, examples=[72.0], description="Latidos por minuto")
    frecuencia_respiratoria: Optional[float] = Field(None, ge=5.0, le=120.0, examples=[28.0], description="Respiraciones por minuto")
    condicion_corporal: Optional[float] = Field(None, ge=1.0, le=5.0, examples=[3.5], description="Escala visual 1.0-5.0")
    consumo_alimento_kg: Optional[float] = Field(None, ge=0.0, le=150.0, examples=[12.0], description="Kg de alimento dado")
    consumo_agua_l: Optional[float] = Field(None, ge=0.0, le=500.0, examples=[65.0], description="Litros de agua aproximados")
    sintomas_seleccionados: Optional[list[str]] = Field(None, examples=[["cojera", "fiebre"]])
    # ── Productivo / reproductivo (opcionales, mejoran el modelo) ─
    parity: Optional[int] = Field(None, ge=0, le=20, examples=[2], description="Número de partos previos")
    dias_en_leche: Optional[int] = Field(None, ge=0, le=730, examples=[120], description="Días desde el último parto")
    produccion_semana_anterior: Optional[float] = Field(None, ge=0.0, le=100.0, examples=[11.5], description="Promedio de producción de leche la semana anterior (L/día)")
    # ── Entorno ──────────────────────────────────────────────────
    temperatura_ambiente: Optional[float] = Field(None, ge=-10.0, le=55.0, examples=[25.0], description="Temperatura ambiente en Celsius")
    # ── Vacunas aplicadas (0 = no, 1 = sí) ───────────────────────
    vacuna_fmdv: Optional[int] = Field(None, ge=0, le=1, examples=[1], description="Vacuna Fiebre Aftosa")
    vacuna_brucelosis: Optional[int] = Field(None, ge=0, le=1, examples=[0], description="Vacuna Brucelosis")
    vacuna_septicemia: Optional[int] = Field(None, ge=0, le=1, examples=[0], description="Vacuna Septicemia Hemorrágica")
    vacuna_carbon_sint: Optional[int] = Field(None, ge=0, le=1, examples=[0], description="Vacuna Carbón Sintomático")
    vacuna_antrax: Optional[int] = Field(None, ge=0, le=1, examples=[0], description="Vacuna Ántrax")


class AlertaUpdate(BaseModel):
    leida: bool


class UnirseRanchoRequest(BaseModel):
    codigo_invitacion: str = Field(
        ..., min_length=8, max_length=8,
        examples=["GAN4X2BQ"],
        description="Código de 8 caracteres que el dueño del rancho comparte con sus ganaderos.",
    )
