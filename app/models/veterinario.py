from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class Veterinario(Base, UUIDMixin):
    __tablename__ = "veterinarios"

    rancho_id    = Column(String(36), ForeignKey("ranchos.id"), nullable=False)
    nombre       = Column(String(150), nullable=False)
    telefono     = Column(String(20), nullable=False)
    especialidad = Column(String(100), nullable=True)
    notas        = Column(Text, nullable=True)
    creado_en    = Column(DateTime, server_default=func.now())

    # Relaciones
    rancho = relationship("Rancho", back_populates="veterinarios")

    def to_dict(self):
        return {
            "id":           self.id,
            "rancho_id":    self.rancho_id,
            "nombre":       self.nombre,
            "telefono":     self.telefono,
            "especialidad": self.especialidad,
            "notas":        self.notas,
            "creado_en":    self.creado_en.isoformat() if self.creado_en else None,
        }
