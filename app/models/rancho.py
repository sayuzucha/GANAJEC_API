import random
import string

from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


def _generar_codigo() -> str:
    """Genera un código de invitación de 8 caracteres: letras mayúsculas + dígitos.
    Ejemplo: 'GAN4X2BQ'. El controller verifica unicidad en BD."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=8))


class RanchoGanadero(Base):
    """
    Tabla intermedia N:M entre Rancho y Usuario(ganadero).
    Un ganadero puede estar asignado a varios ranchos y
    un rancho puede tener varios ganaderos.
    """
    __tablename__ = "rancho_ganaderos"

    rancho_id   = Column(String(36), ForeignKey("ranchos.id"),   primary_key=True)
    ganadero_id = Column(String(36), ForeignKey("usuarios.id"),  primary_key=True)
    asignado_en = Column(DateTime, server_default=func.now())

    # Relaciones de navegación (opcionales, útiles en consultas ORM)
    rancho   = relationship("Rancho",   back_populates="asignaciones")
    ganadero = relationship("Usuario",  back_populates="asignaciones_rancho")

    def to_dict(self):
        return {
            "rancho_id":   self.rancho_id,
            "ganadero_id": self.ganadero_id,
            "asignado_en": self.asignado_en.isoformat() if self.asignado_en else None,
        }


class Rancho(Base, UUIDMixin):
    __tablename__ = "ranchos"

    nombre              = Column(String(150), nullable=False)
    municipio           = Column(String(100), nullable=False)
    estado              = Column(String(100), nullable=False)
    dueno_id            = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    creado_en           = Column(DateTime, server_default=func.now())
    # Código de invitación que el dueño comparte con sus ganaderos.
    # El ganadero lo pega en la app para unirse al rancho (POST /ganadero/unirse-rancho).
    codigo_invitacion   = Column(String(8), nullable=False, unique=True, index=True,
                                 default=_generar_codigo)

    # Relaciones
    dueno        = relationship("Usuario", back_populates="ranchos", foreign_keys=[dueno_id])
    bovinos      = relationship("Bovino",  back_populates="rancho")
    asignaciones = relationship("RanchoGanadero", back_populates="rancho",
                                cascade="all, delete-orphan")

    def to_dict(self, include_codigo=False):
        data = {
            "id":              self.id,
            "nombre":          self.nombre,
            "municipio":       self.municipio,
            "estado":          self.estado,
            "dueno_id":        self.dueno_id,
            "total_bovinos":   len(self.bovinos)       if self.bovinos       else 0,
            "total_ganaderos": len(self.asignaciones)  if self.asignaciones  else 0,
            "creado_en":       self.creado_en.isoformat() if self.creado_en  else None,
        }
        # El código solo se devuelve cuando el dueño lo solicita explícitamente
        # (al crear el rancho o al consultar su perfil). No se expone en endpoints públicos.
        if include_codigo:
            data["codigo_invitacion"] = self.codigo_invitacion
        return data
