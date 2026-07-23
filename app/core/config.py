import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Configuración de la aplicación. Lee de variables de entorno (.env).

    Desarrollo local — crea un .env en la raíz:
        DB_HOST=localhost
        DB_PORT=3306
        DB_USER=root
        DB_PASSWORD=tu_password
        DB_NAME=ganajec_db
        SECRET_KEY=clave_larga_aleatoria

    Producción (Render + Aiven) — define en el dashboard de Render:
        DATABASE_URL=mysql://user:pass@host:port/db?ssl-mode=REQUIRED
        SECRET_KEY=clave_larga_aleatoria
        (el resto de vars: SMTP_*, FIREBASE_*, STRIPE_*)
    """

    # ── Base de datos ──────────────────────────────────────────────────────
    # DATABASE_URL tiene prioridad (lo da Aiven como "Service URI").
    # Si no está definido, se construye desde las partes individuales.
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = os.getenv("DB_PORT", "3306")
    DB_USER     = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "goku123")
    DB_NAME     = os.getenv("DB_NAME", "ganajec_db")

    # ── Seguridad ─────────────────────────────────────────────────────────
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

    # ── Stripe ────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

    # ── SMTP ──────────────────────────────────────────────────────────────
    SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT     = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER     = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM     = os.getenv("SMTP_FROM", "")

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Aiven devuelve "mysql://..." — SQLAlchemy necesita "mysql+pymysql://"
            if url.startswith("mysql://"):
                url = "mysql+pymysql://" + url[len("mysql://"):]
            return url
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def usa_ssl(self) -> bool:
        """True si la URL viene de Aiven (contiene 'aiven.io')."""
        url = self.DATABASE_URL or ""
        return "aiven.io" in url or os.getenv("DB_SSL", "false").lower() == "true"


settings = Settings()
