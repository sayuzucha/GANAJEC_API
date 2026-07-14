from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime

from app.core.database import Base
from app.models.base import UUIDMixin


class PreRegistro(Base, UUIDMixin):
    __tablename__ = "pre_registros"

    nombre = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False)
    codigo = Column(String(6), nullable=False)
    expira_en = Column(DateTime, nullable=False)
    usado = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
