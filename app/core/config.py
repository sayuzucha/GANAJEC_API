import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Configuracion de la aplicacion. Lee de variables de entorno (.env).
    Para conectar a tu MySQL, crea un archivo .env en la raiz con:

    DB_HOST=localhost
    DB_PORT=3306
    DB_USER=root
    DB_PASSWORD=tu_password
    DB_NAME=ganajec_db
    SECRET_KEY=una_clave_secreta_larga
    """

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "ganajec_db")

    SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")

    _WEAK_KEY = "cambia-esta-clave-en-produccion"
    if SECRET_KEY == _WEAK_KEY:
        import logging as _l
        _l.getLogger("ganajec").warning(
            "SEGURIDAD: SECRET_KEY usa el valor por defecto. "
            "Define SECRET_KEY en .env antes de produccion."
        )
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

    # SMTP para envio de correos (verificacion, recuperacion)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
