import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


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

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"Error al enviar correo a {destinatario}: {e}") from e
