from sqlalchemy import Column, String, Float, Integer, JSON, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class Plan(Base, UUIDMixin):
    __tablename__ = "planes"

    nombre = Column(String(100), nullable=False)
    precio_mensual = Column(Float, nullable=False)
    precio_anual = Column(Float, nullable=True)
    limite_bovinos = Column(Integer, nullable=False)
    permisos = Column(JSON, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    suscripciones = relationship("Suscripcion", back_populates="plan")

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio_mensual": self.precio_mensual,
            "precio_anual": self.precio_anual,
            "limite_bovinos": self.limite_bovinos,
            "permisos": self.permisos,
            "activo": self.activo,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }


class Suscripcion(Base, UUIDMixin):
    __tablename__ = "suscripciones"

    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    plan_id = Column(String(36), ForeignKey("planes.id"), nullable=False)
    tipo_suscripcion = Column(String(20), nullable=False, default="mensual")  # mensual | anual

    inicio = Column(Date, nullable=False)
    fin = Column(Date, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)

    # Relaciones
    usuario = relationship("Usuario", back_populates="suscripciones")
    plan = relationship("Plan", back_populates="suscripciones")

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "plan_id": self.plan_id,
            "tipo_suscripcion": self.tipo_suscripcion,
            "plan": self.plan.to_dict() if self.plan else None,
            "inicio": self.inicio.isoformat() if self.inicio else None,
            "fin": self.fin.isoformat() if self.fin else None,
            "activa": self.activa,
        }
