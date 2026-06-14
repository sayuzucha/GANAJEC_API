from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # evita conexiones muertas
    pool_recycle=3600,
    echo=False,           # cambia a True para ver el SQL generado en consola
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency de FastAPI: abre una sesion por request y la cierra al terminar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
