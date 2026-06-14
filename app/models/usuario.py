from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class Usuario(Base, UUIDMixin):
    __tablename__ = "usuarios"

    nombre = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum("ganadero", "dueno", "admin", name="rol_usuario"), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    ranchos = relationship("Rancho", back_populates="dueno", foreign_keys="Rancho.dueno_id")
    bovinos_a_cargo = relationship("Bovino", back_populates="ganadero", foreign_keys="Bovino.ganadero_id")
    registros_sintomas = relationship("RegistroSintoma", back_populates="ganadero")
    alertas = relationship("Alerta", back_populates="ganadero")
    notificaciones = relationship("Notificacion", back_populates="usuario")
    suscripciones = relationship("Suscripcion", back_populates="usuario")
    logs_auditoria = relationship("AuditoriaLog", back_populates="usuario")

    def to_dict(self, include_email=True):
        data = {
            "id": self.id,
            "nombre": self.nombre,
            "rol": self.rol,
            "activo": self.activo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if include_email:
            data["email"] = self.email
        return data
