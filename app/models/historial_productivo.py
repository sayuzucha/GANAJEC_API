from sqlalchemy import Column, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import UUIDMixin


class HistorialProductivo(Base, UUIDMixin):
    __tablename__ = "historial_productivo"

    bovino_id = Column(String(36), ForeignKey("bovinos.id"), nullable=False)

    fecha = Column(Date, nullable=False)
    litros_leche = Column(Float, nullable=True)
    kg_alimento = Column(Float, nullable=True)
    ganancia_peso_kg = Column(Float, nullable=True)
    temperatura = Column(Float, nullable=True)
    anomalia_detectada = Column(Boolean, default=False, nullable=False)

    # Relaciones
    bovino = relationship("Bovino", back_populates="historial_productivo")

    def to_dict(self):
        return {
            "id": self.id,
            "bovino_id": self.bovino_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "litros_leche": self.litros_leche,
            "kg_alimento": self.kg_alimento,
            "ganancia_peso_kg": self.ganancia_peso_kg,
            "temperatura": self.temperatura,
            "anomalia_detectada": self.anomalia_detectada,
        }
