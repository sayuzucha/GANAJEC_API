from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class AuditoriaLog(Base, UUIDMixin):
    __tablename__ = "auditoria_logs"

    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=True)

    accion = Column(String(150), nullable=False)
    entidad_afectada = Column(String(100), nullable=False)
    detalle = Column(JSON, nullable=True)
    ip = Column(String(45), nullable=True)
    creado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    usuario = relationship("Usuario", back_populates="logs_auditoria")

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "usuario_nombre": self.usuario.nombre if self.usuario else None,
            "accion": self.accion,
            "entidad_afectada": self.entidad_afectada,
            "detalle": self.detalle,
            "ip": self.ip,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


class ConfiguracionSistema(Base, UUIDMixin):
    __tablename__ = "configuracion_sistema"

    clave = Column(String(100), nullable=False, unique=True)
    valor = Column(String(255), nullable=False)
    descripcion = Column(String(255), nullable=True)
    actualizado_por = Column(String(36), ForeignKey("usuarios.id"), nullable=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "clave": self.clave,
            "valor": self.valor,
            "descripcion": self.descripcion,
            "actualizado_por": self.actualizado_por,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
