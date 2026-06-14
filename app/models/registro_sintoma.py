from sqlalchemy import Column, String, Float, Text, JSON, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import UUIDMixin


class RegistroSintoma(Base, UUIDMixin):
    __tablename__ = "registros_sintomas"

    bovino_id = Column(String(36), ForeignKey("bovinos.id"), nullable=False)
    ganadero_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)

    texto_libre = Column(Text, nullable=False)
    temperatura = Column(Float, nullable=True)
    produccion_leche = Column(Float, nullable=True)
    # ── Campos nuevos v4 — sin sensores, registrados por el ganadero ──
    frecuencia_cardiaca = Column(Float, nullable=True)       # latidos por minuto
    frecuencia_respiratoria = Column(Float, nullable=True)   # respiraciones por minuto
    condicion_corporal = Column(Float, nullable=True)        # escala visual 1.0 - 5.0
    consumo_alimento_kg = Column(Float, nullable=True)       # kg de alimento dado
    consumo_agua_l = Column(Float, nullable=True)            # litros de agua aproximados
    sintomas_seleccionados = Column(JSON, nullable=True)
    registrado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    bovino = relationship("Bovino", back_populates="registros_sintomas")
    ganadero = relationship("Usuario", back_populates="registros_sintomas")
    prediccion = relationship(
        "Prediccion", back_populates="registro", uselist=False, cascade="all, delete-orphan"
    )

    def to_dict(self, include_prediccion=False):
        data = {
            "id": self.id,
            "bovino_id": self.bovino_id,
            "ganadero_id": self.ganadero_id,
            "texto_libre": self.texto_libre,
            "temperatura": self.temperatura,
            "produccion_leche": self.produccion_leche,
            "frecuencia_cardiaca": self.frecuencia_cardiaca,
            "frecuencia_respiratoria": self.frecuencia_respiratoria,
            "condicion_corporal": self.condicion_corporal,
            "consumo_alimento_kg": self.consumo_alimento_kg,
            "consumo_agua_l": self.consumo_agua_l,
            "sintomas_seleccionados": self.sintomas_seleccionados,
            "registrado_en": self.registrado_en.isoformat() if self.registrado_en else None,
        }
        if include_prediccion and self.prediccion:
            data["prediccion"] = self.prediccion.to_dict()
        return data


class Prediccion(Base, UUIDMixin):
    __tablename__ = "predicciones"

    registro_id = Column(String(36), ForeignKey("registros_sintomas.id"), nullable=False, unique=True)

    enfermedad = Column(String(150), nullable=False)
    confianza = Column(Float, nullable=False)
    severidad = Column(Enum("leve", "moderada", "alta", name="severidad_prediccion"), nullable=False)
    features_nlp = Column(JSON, nullable=True)
    generado_en = Column(DateTime, server_default=func.now())

    # Relaciones
    registro = relationship("RegistroSintoma", back_populates="prediccion")

    def to_dict(self):
        return {
            "id": self.id,
            "registro_id": self.registro_id,
            "enfermedad": self.enfermedad,
            "confianza": self.confianza,
            "severidad": self.severidad,
            "features_nlp": self.features_nlp,
            "generado_en": self.generado_en.isoformat() if self.generado_en else None,
        }
