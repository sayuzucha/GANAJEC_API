"""
Script para crear las tablas en MySQL y crear el usuario administrador.

Uso:
    python seed.py

Requiere que la base de datos exista:
    CREATE DATABASE ganajec_db;

Y que las credenciales configuradas en .env sean correctas.
"""

from app.core.database import engine, SessionLocal, Base
from app.core.security import hash_password
from app.models import Usuario


def crear_tablas():
    """
    Crea todas las tablas definidas en los modelos de SQLAlchemy
    que todavía no existan en la base de datos.
    """
    print("Creando tablas...")

    Base.metadata.create_all(bind=engine)

    print("Tablas creadas correctamente.")


def crear_admin():
    """
    Crea el usuario administrador si todavía no existe.
    No modifica ni elimina los usuarios existentes.
    """

    db = SessionLocal()

    try:
        # Verificar si el administrador ya existe
        admin_existente = db.query(Usuario).filter(
            Usuario.email == "admin@ganajec.ai"
        ).first()

        if admin_existente:
            print("")
            print("El usuario administrador ya existe.")
            print(f"Email: {admin_existente.email}")
            print(f"Rol: {admin_existente.rol}")
            return

        # Crear usuario administrador
        admin = Usuario(
            nombre="Admin GANAJEC",
            email="admin@ganajec.ai",
            password_hash=hash_password("admin1234"),
            rol="admin",
            activo=True,
            email_verificado=True,
        )

        # Agregar el usuario a la sesión
        db.add(admin)

        # Guardar los cambios en MySQL
        db.commit()

        print("")
        print("======================================")
        print("USUARIO ADMINISTRADOR CREADO")
        print("======================================")
        print(f"Email:      {admin.email}")
        print("Password:   admin1234")
        print(f"Rol:        {admin.rol}")
        print("Activo:     Sí")
        print("Verificado: Sí")
        print("======================================")

    except Exception as e:
        # Si ocurre un error, deshacer los cambios
        db.rollback()

        print("")
        print("ERROR AL CREAR EL USUARIO ADMINISTRADOR")
        print(f"Detalle: {e}")

    finally:
        # Cerrar la conexión con la base de datos
        db.close()


if __name__ == "__main__":
    print("")
    print("======================================")
    print("INICIALIZANDO BASE DE DATOS GANAJEC")
    print("======================================")

    # 1. Crear las tablas que no existan
    crear_tablas()

    # 2. Crear únicamente el usuario administrador
    crear_admin()

    print("")
    print("Proceso terminado.")