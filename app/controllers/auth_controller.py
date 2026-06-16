from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Usuario
from app.schemas.auth_schema import RegisterRequest, LoginRequest, FcmTokenUpdate
from app.core.security import hash_password, verify_password, create_access_token


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
