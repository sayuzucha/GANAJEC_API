from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class Rancho(Base, UUIDMixin):
    __tablename__ = "ranchos"

    nombre = Column(String(150), nullable=False)
    municipio = Column(String(100), nullable=False)
    estado = Column(String(100), nullable=False)
    dueno_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    dueno = relationship("Usuario", back_populates="ranchos", foreign_keys=[dueno_id])
    bovinos = relationship("Bovino", back_populates="rancho")

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "municipio": self.municipio,
            "estado": self.estado,
            "dueno_id": self.dueno_id,
            "total_bovinos": len(self.bovinos) if self.bovinos else 0,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
