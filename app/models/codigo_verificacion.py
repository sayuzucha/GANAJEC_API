from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey

from app.core.database import Base
from app.models.base import UUIDMixin


class CodigoVerificacion(Base, UUIDMixin):
    __tablename__ = "codigos_verificacion"

    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    codigo = Column(String(6), nullable=False)
    tipo = Column(Enum("verificacion_email", "recuperacion_password", name="tipo_codigo"), nullable=False)
    usado = Column(Boolean, default=False, nullable=False)
    expira_en = Column(DateTime, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
