from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
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
    email_verificado = Column(Boolean, default=False, nullable=False)
    ultima_actividad = Column(DateTime, nullable=True)
    creado_en = Column(DateTime, server_default=func.now())
    # Token del dispositivo móvil para notificaciones push via Firebase FCM.
    # Se actualiza desde la app tras el login con PUT /api/auth/fcm-token.
    fcm_token = Column(String(255), nullable=True)
    # Rancho al que pertenece el ganadero (solo aplica para rol=ganadero).
    # NULL significa que aún no está asignado a ningún rancho.
    rancho_id = Column(String(36), ForeignKey("ranchos.id"), nullable=True)
    # Control de notificación de asignación a rancho (solo ganaderos creados por el dueño).
    notificacion_asignacion_enviada = Column(Boolean, default=False, nullable=False)

    # Relaciones
    ranchos = relationship("Rancho", back_populates="dueno", foreign_keys="Rancho.dueno_id")
    rancho = relationship("Rancho", back_populates="ganaderos", foreign_keys=[rancho_id])
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
            "email_verificado": self.email_verificado,
            "ultima_actividad": self.ultima_actividad.isoformat() if self.ultima_actividad else None,
            "rancho_id": self.rancho_id,
            "notificacion_asignacion_enviada": self.notificacion_asignacion_enviada,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if include_email:
            data["email"] = self.email
        return data
