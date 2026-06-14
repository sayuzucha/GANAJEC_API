from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class Alerta(Base, UUIDMixin):
    __tablename__ = "alertas"

    bovino_id = Column(String(36), ForeignKey("bovinos.id"), nullable=False)
    ganadero_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)

    tipo = Column(Enum("productiva", "clinica", name="tipo_alerta"), nullable=False)
    severidad = Column(Enum("baja", "media", "alta", name="severidad_alerta"), nullable=False)
    mensaje = Column(Text, nullable=False)
    leida = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    bovino = relationship("Bovino", back_populates="alertas")
    ganadero = relationship("Usuario", back_populates="alertas")
    notificaciones = relationship("Notificacion", back_populates="alerta", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "bovino_id": self.bovino_id,
            "ganadero_id": self.ganadero_id,
            "tipo": self.tipo,
            "severidad": self.severidad,
            "mensaje": self.mensaje,
            "leida": self.leida,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


class Notificacion(Base, UUIDMixin):
    __tablename__ = "notificaciones"

    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    alerta_id = Column(String(36), ForeignKey("alertas.id"), nullable=False)

    enviada = Column(Boolean, default=False, nullable=False)
    enviado_en = Column(DateTime, nullable=True)

    # Relaciones
    usuario = relationship("Usuario", back_populates="notificaciones")
    alerta = relationship("Alerta", back_populates="notificaciones")

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "alerta_id": self.alerta_id,
            "enviada": self.enviada,
            "enviado_en": self.enviado_en.isoformat() if self.enviado_en else None,
        }
