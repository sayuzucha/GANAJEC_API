from sqlalchemy import Column, String, Float, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class Bovino(Base, UUIDMixin):
    __tablename__ = "bovinos"

    rancho_id = Column(String(36), ForeignKey("ranchos.id"), nullable=False)
    ganadero_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)

    nombre = Column(String(100), nullable=False)
    raza = Column(String(100), nullable=False)
    sexo = Column(Enum("hembra", "macho", name="sexo_bovino"), nullable=False)
    categoria = Column(
        Enum("vaca", "toro", "becerro", "becerra", "novillo", "vaquilla", "torete",
             name="categoria_bovino"),
        nullable=False,
    )
    proposito = Column(
        Enum("leche", "carne", "doble", "cria", name="proposito_bovino"),
        nullable=False,
    )
    fecha_nacimiento = Column(Date, nullable=True)
    peso_kg = Column(Float, nullable=False)
    id_externo = Column(String(50), nullable=True, unique=True)
    creado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    rancho = relationship("Rancho", back_populates="bovinos")
    ganadero = relationship("Usuario", back_populates="bovinos_a_cargo", foreign_keys=[ganadero_id])
    registros_sintomas = relationship("RegistroSintoma", back_populates="bovino", cascade="all, delete-orphan")
    historial_productivo = relationship("HistorialProductivo", back_populates="bovino", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="bovino", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "rancho_id": self.rancho_id,
            "ganadero_id": self.ganadero_id,
            "nombre": self.nombre,
            "raza": self.raza,
            "sexo": self.sexo,
            "categoria": self.categoria,
            "proposito": self.proposito,
            "fecha_nacimiento": self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None,
            "peso_kg": self.peso_kg,
            "id_externo": self.id_externo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
