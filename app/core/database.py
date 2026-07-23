from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Aiven (y cualquier MySQL en la nube) requiere SSL.
# PyMySQL acepta {"ssl": {}} para habilitar TLS sin verificar certificado,
# lo que es suficiente para cifrar el canal en producción.
_connect_args = {"ssl": {}} if settings.usa_ssl else {}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # detecta conexiones muertas antes de usarlas
    pool_recycle=3600,    # recicla conexiones cada hora
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency de FastAPI: abre una sesión por request y la cierra al terminar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
