import logging
import smtplib
import socket
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

SMTP_TIMEOUT = 15  # segundos


def enviar_codigo(destinatario: str, codigo: str, tipo: str) -> None:
    if tipo not in ("verificacion_email", "recuperacion_password"):
        raise ValueError(f"Tipo de codigo invalido: '{tipo}'")

    if tipo == "verificacion_email":
        asunto = "Verifica tu correo - GANAJEC"
    else:
        asunto = "Recupera tu contrasena - GANAJEC"

    cuerpo = (
        f"Tu codigo de verificacion es: {codigo}\n\n"
        "Este codigo expira en 15 minutos."
    )

    msg = MIMEText(cuerpo)
    msg["Subject"] = asunto
    msg["From"] = settings.SMTP_FROM
    msg["To"] = destinatario

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP no configurado (SMTP_USER/SMTP_PASSWORD vacios). Se omite envio de correo a %s", destinatario)
        return

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except socket.timeout:
        logger.error("Timeout al conectar con SMTP (%s:%s)", settings.SMTP_HOST, settings.SMTP_PORT)
        raise RuntimeError(f"Timeout al enviar correo a {destinatario}: el servidor SMTP no responde") from None
    except smtplib.SMTPAuthenticationError as e:
        logger.error("Error de autenticacion SMTP: %s", e)
        raise RuntimeError(f"Error de autenticacion SMTP al enviar correo a {destinatario}: credenciales invalidas") from None
    except Exception as e:
        logger.error("Error al enviar correo a %s: %s", destinatario, e)
        raise RuntimeError(f"Error al enviar correo a {destinatario}: {e}") from e
