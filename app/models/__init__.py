"""
Importa todos los modelos para que SQLAlchemy registre las relaciones
entre tablas antes de crear el esquema (Base.metadata.create_all).
"""
from app.models.usuario import Usuario
from app.models.rancho import Rancho
from app.models.bovino import Bovino
from app.models.registro_sintoma import RegistroSintoma, Prediccion
from app.models.historial_productivo import HistorialProductivo
from app.models.alerta import Alerta, Notificacion
from app.models.plan import Plan, Suscripcion
from app.models.configuracion_sistema import AuditoriaLog, ConfiguracionSistema
from app.models.veterinario import Veterinario

__all__ = [
    "Usuario",
    "Rancho",
    "Bovino",
    "RegistroSintoma",
    "Prediccion",
    "HistorialProductivo",
    "Alerta",
    "Notificacion",
    "Plan",
    "Suscripcion",
    "AuditoriaLog",
    "ConfiguracionSistema",
    "Veterinario",
]
