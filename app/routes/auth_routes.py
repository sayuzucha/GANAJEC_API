from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.controllers.auth_controller import AuthController
from app.schemas.auth_schema import RegisterRequest, LoginRequest, FcmTokenUpdate

router = APIRouter()


# Registro de un nuevo usuario (ganadero, dueno o admin)
@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return AuthController.register(db, data)


# Login: retorna token JWT + datos del usuario
@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    return AuthController.login(db, data)


# Registrar / actualizar el FCM token del dispositivo.
# La app móvil debe llamar este endpoint justo después del login.
# Enviar fcm_token=null desuscribe las notificaciones push del dispositivo.
@router.put("/fcm-token")
async def update_fcm_token(
    data: FcmTokenUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    return AuthController.update_fcm_token(db, usuario.id, data)
