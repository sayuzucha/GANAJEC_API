from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, limiter
from app.controllers.auth_controller import AuthController
from app.schemas.auth_schema import RegisterRequest, LoginRequest, FcmTokenUpdate

router = APIRouter()


# Registro: max 3 cuentas por minuto desde la misma IP
@router.post("/register", status_code=201)
@limiter.limit("3/minute")
async def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    return AuthController.register(db, data)


# Login: max 5 intentos por minuto desde la misma IP (anti brute-force)
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    return AuthController.login(db, data)


# Registrar / actualizar el FCM token del dispositivo.
@router.put("/fcm-token")
async def update_fcm_token(
    data: FcmTokenUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    return AuthController.update_fcm_token(db, usuario.id, data)
