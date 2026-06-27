import logging
from datetime import datetime, timedelta
import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Usuario, CodigoVerificacion
from app.schemas.auth_schema import (
    RegisterRequest,
    LoginRequest,
    FcmTokenUpdate,
    VerificarEmailRequest,
    ReenviarCodigoRequest,
    SolicitarRecuperacionRequest,
    RestablecerPasswordRequest,
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.email_service import enviar_codigo

logger = logging.getLogger(__name__)


class AuthController:
    """Controlador de autenticacion: registro y login para los 3 roles."""

    @staticmethod
    def register(db: Session, data: RegisterRequest):
        existe = db.query(Usuario).filter(Usuario.email == data.email).first()
        if existe:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto: ya existe un usuario registrado con el correo '{data.email}'",
            )

        nuevo = Usuario(
            nombre=data.nombre,
            email=data.email,
            password_hash=hash_password(data.password),
            rol=data.rol,
            activo=True,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)

        try:
            codigo = AuthController.crear_codigo_verificacion(db, nuevo.id, "verificacion_email")
            enviar_codigo(nuevo.email, codigo.codigo, "verificacion_email")
        except Exception:
            logger.warning("Error al enviar codigo de verificacion de email", exc_info=True)

        token = create_access_token({"sub": nuevo.id, "rol": nuevo.rol})
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": nuevo.to_dict(),
        }

    @staticmethod
    def login(db: Session, data: LoginRequest):
        usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autorizado: correo o contrasena incorrectos",
            )

        if not verify_password(data.password, usuario.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autorizado: correo o contrasena incorrectos",
            )

        if not usuario.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: tu cuenta esta desactivada. Contacta al administrador",
            )

        if not usuario.email_verificado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debes verificar tu correo antes de iniciar sesion",
            )

        token = create_access_token({"sub": usuario.id, "rol": usuario.rol})
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": usuario.to_dict(),
        }

    @staticmethod
    def update_fcm_token(db: Session, usuario_id: str, data: FcmTokenUpdate):
        """
        Guarda o elimina el FCM token del dispositivo móvil del usuario.
        La app llama este endpoint inmediatamente después del login.
        """
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No encontrado: usuario no existe",
            )

        usuario.fcm_token = data.fcm_token
        db.commit()

        accion = "registrado" if data.fcm_token else "eliminado"
        return {"mensaje": f"FCM token {accion} correctamente"}

    @staticmethod
    def generar_codigo() -> str:
        return f"{secrets.randbelow(10 ** 6):06d}"

    @staticmethod
    def crear_codigo_verificacion(db: Session, usuario_id: str, tipo: str) -> CodigoVerificacion:
        codigo = AuthController.generar_codigo()
        registro = CodigoVerificacion(
            usuario_id=usuario_id,
            codigo=codigo,
            tipo=tipo,
            expira_en=datetime.utcnow() + timedelta(minutes=15),
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)
        return registro

    @staticmethod
    def verificar_email(db: Session, data: VerificarEmailRequest):
        usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: no existe un usuario con el correo '{data.email}'",
            )

        codigo_valido = (
            db.query(CodigoVerificacion)
            .filter(
                CodigoVerificacion.usuario_id == usuario.id,
                CodigoVerificacion.codigo == data.codigo,
                CodigoVerificacion.tipo == "verificacion_email",
                CodigoVerificacion.usado == False,
                CodigoVerificacion.expira_en > datetime.utcnow(),
            )
            .first()
        )
        if not codigo_valido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Codigo invalido o expirado",
            )

        usuario.email_verificado = True
        codigo_valido.usado = True
        db.commit()
        return {"mensaje": "Correo verificado correctamente"}

    @staticmethod
    def reenviar_codigo(db: Session, data: ReenviarCodigoRequest):
        usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: no existe un usuario con el correo '{data.email}'",
            )

        if data.tipo == "verificacion_email" and usuario.email_verificado:
            return {"mensaje": "El correo ya esta verificado"}

        nuevo_codigo = AuthController.crear_codigo_verificacion(db, usuario.id, data.tipo)
        enviar_codigo(usuario.email, nuevo_codigo.codigo, data.tipo)
        return {"mensaje": "Codigo enviado correctamente"}

    @staticmethod
    def solicitar_recuperacion(db: Session, data: SolicitarRecuperacionRequest):
        usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

        if usuario:
            try:
                nuevo_codigo = AuthController.crear_codigo_verificacion(db, usuario.id, "recuperacion_password")
                enviar_codigo(usuario.email, nuevo_codigo.codigo, "recuperacion_password")
            except Exception:
                logger.warning("Error al generar o enviar codigo de recuperacion", exc_info=True)

        return {"mensaje": "Si el correo esta registrado, recibiras un codigo"}

    @staticmethod
    def restablecer_password(db: Session, data: RestablecerPasswordRequest):
        usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: no existe un usuario con el correo '{data.email}'",
            )

        codigo_valido = (
            db.query(CodigoVerificacion)
            .filter(
                CodigoVerificacion.usuario_id == usuario.id,
                CodigoVerificacion.codigo == data.codigo,
                CodigoVerificacion.tipo == "recuperacion_password",
                CodigoVerificacion.usado == False,
                CodigoVerificacion.expira_en > datetime.utcnow(),
            )
            .first()
        )
        if not codigo_valido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Codigo invalido o expirado",
            )

        usuario.password_hash = hash_password(data.nueva_password)
        codigo_valido.usado = True
        db.commit()
        return {"mensaje": "Contrasena restablecida correctamente"}
