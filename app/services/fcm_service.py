"""
Servicio de notificaciones push via Firebase Cloud Messaging (FCM).

Usa Firebase Admin SDK (HTTP v1 API) — la única opción recomendada por
Google para servidores en producción. La API legacy (server key) fue
deprecada en junio 2024.

Configuración:
  1. En Firebase Console → Configuración del proyecto → Cuentas de servicio
     → Generar nueva clave privada → descarga el JSON.
  2. Guarda ese JSON como string en la variable de entorno
     FIREBASE_CREDENTIALS_JSON (ver .env.example).
  3. Agrega 'firebase-admin' a requirements.txt y haz pip install.

Si FIREBASE_CREDENTIALS_JSON no está configurado, el módulo queda en
modo silencioso (no lanza error) para no romper el flujo de la API en
desarrollo local.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

# ── Inicialización de Firebase (una sola vez al importar) ──────────────
_firebase_app = None


def _init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return True

    credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if not credentials_json:
        logger.warning(
            "FCM desactivado: la variable de entorno FIREBASE_CREDENTIALS_JSON "
            "no está configurada. Las notificaciones push no se enviarán."
        )
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred_dict = json.loads(credentials_json)
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK inicializado correctamente.")
        return True
    except Exception as exc:
        logger.error("Error al inicializar Firebase Admin SDK: %s", exc)
        return False


_firebase_ready = _init_firebase()


# ── Función principal ──────────────────────────────────────────────────

def send_alert_notification(
    fcm_token: str,
    titulo: str,
    cuerpo: str,
    data: dict | None = None,
) -> bool:
    """
    Envía una notificación push a un dispositivo Android/iOS via FCM.

    Args:
        fcm_token:  Token FCM del dispositivo (guardado en Usuario.fcm_token).
        titulo:     Título visible en la notificación (ej. "⚠️ Alerta productiva").
        cuerpo:     Texto del cuerpo (ej. "Lupita tiene valores fuera de lo normal").
        data:       Dict opcional de pares clave-valor extra que la app puede
                    leer en el payload de la notificación (todos deben ser strings).

    Returns:
        True si FCM aceptó el mensaje, False en caso de error o no configurado.
    """
    if not _firebase_ready:
        return False

    if not fcm_token:
        logger.debug("send_alert_notification: fcm_token vacío, omitiendo envío.")
        return False

    try:
        from firebase_admin import messaging

        notification = messaging.Notification(title=titulo, body=cuerpo)

        # Android: canal "alertas_ganajec" (debe crearse en la app Flutter/Android)
        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="alertas_ganajec",
                sound="default",
            ),
        )

        # iOS (si algún día se lanza en App Store)
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1),
            )
        )

        message = messaging.Message(
            token=fcm_token,
            notification=notification,
            android=android_config,
            apns=apns_config,
            data={str(k): str(v) for k, v in (data or {}).items()},
        )

        response = messaging.send(message)
        logger.info("Notificación FCM enviada. Message ID: %s", response)
        return True

    except Exception as exc:
        logger.error("Error al enviar notificación FCM: %s", exc)
        return False


# ── Helpers semánticos para los tipos de alerta de GANAJEC ─────────────

def notify_alerta_productiva(fcm_token: str, bovino_nombre: str, score: float) -> bool:
    """Notificación para anomalía productiva detectada por Isolation Forest."""
    return send_alert_notification(
        fcm_token=fcm_token,
        titulo="⚠️ Alerta productiva",
        cuerpo=f"{bovino_nombre} tiene valores productivos fuera de lo normal.",
        data={
            "tipo": "productiva",
            "bovino": bovino_nombre,
            "score": str(round(score, 4)),
        },
    )


def notify_alerta_clinica(fcm_token: str, bovino_nombre: str, enfermedad: str, confianza: float) -> bool:
    """Notificación para predicción clínica de alta severidad por Random Forest."""
    porcentaje = f"{confianza * 100:.0f}%"
    return send_alert_notification(
        fcm_token=fcm_token,
        titulo="🩺 Alerta clínica",
        cuerpo=f"{bovino_nombre}: posible {enfermedad} ({porcentaje} de confianza). Revísalo pronto.",
        data={
            "tipo": "clinica",
            "bovino": bovino_nombre,
            "enfermedad": enfermedad,
            "confianza": str(confianza),
        },
    )
