import uuid
from sqlalchemy import Column, String


def generate_uuid() -> str:
    return str(uuid.uuid4())


class UUIDMixin:
    """
    Mixin que agrega una columna id de tipo CHAR(36) usada como UUID.
    MySQL no tiene un tipo UUID nativo simple en versiones comunes,
    por eso se almacena como string de 36 caracteres.
    """
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
