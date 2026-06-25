"""
Tablas de asociación (many-to-many) del proyecto.
Se definen aquí para evitar importaciones circulares entre modelos.
"""
from sqlalchemy import Table, Column, String, ForeignKey
from app.core.database import Base

# Un veterinario puede pertenecer a varios ranchos y viceversa.
rancho_veterinario = Table(
    "rancho_veterinarios",
    Base.metadata,
    Column("rancho_id",      String(36), ForeignKey("ranchos.id"),      primary_key=True),
    Column("veterinario_id", String(36), ForeignKey("veterinarios.id"), primary_key=True),
)
