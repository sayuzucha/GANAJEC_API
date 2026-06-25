from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin
from app.models.associations import rancho_veterinario


class Veterinario(Base, UUIDMixin):
    __tablename__ = "veterinarios"

    nombre    = Column(String(150), nullable=False)
    telefono  = Column(String(20),  nullable=False)
    ubicacion = Column(String(200), nullable=True)
    lugar     = Column(String(100), nullable=True)
    notas     = Column(Text,        nullable=True)
    creado_en = Column(DateTime,    server_default=func.now())

    # Many-to-many con Rancho
    ranchos = relationship("Rancho", secondary=rancho_veterinario, back_populates="veterinarios")

    def to_dict(self, include_ranchos=False):
        data = {
            "id":        self.id,
            "nombre":    self.nombre,
            "telefono":  self.telefono,
            "ubicacion": self.ubicacion,
            "lugar":     self.lugar,
            "notas":     self.notas,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if include_ranchos:
            data["ranchos"] = [{"id": r.id, "nombre": r.nombre} for r in self.ranchos]
        return data
