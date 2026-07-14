from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, limiter
from app.controllers.auth_controller import AuthController
from app.schemas.auth_schema import (
    RegisterRequest,
    LoginRequest,
    FcmTokenUpdate,
    VerificarEmailRequest,
    ReenviarCodigoRequest,
    SolicitarRecuperacionRequest,
    RestablecerPasswordRequest,
    PreRegistroRequest,
)

router = APIRouter()


# Registro: max 3 cuentas por minuto desde la misma IP
@router.post("/register", status_code=201)
@limiter.limit("3/minute")
async def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    return AuthController.register(db, data)


@router.post("/pre-register")
@limiter.limit("3/minute")
async def pre_register(request: Request, data: PreRegistroRequest, db: Session = Depends(get_db)):
    return AuthController.pre_register(db, data)


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


@router.post("/verificar-email")
async def verificar_email(request: Request, data: VerificarEmailRequest, db: Session = Depends(get_db)):
    return AuthController.verificar_email(db, data)


@router.post("/reenviar-codigo")
@limiter.limit("3/minute")
async def reenviar_codigo(request: Request, data: ReenviarCodigoRequest, db: Session = Depends(get_db)):
    return AuthController.reenviar_codigo(db, data)


@router.post("/solicitar-recuperacion")
@limiter.limit("3/minute")
async def solicitar_recuperacion(request: Request, data: SolicitarRecuperacionRequest, db: Session = Depends(get_db)):
    return AuthController.solicitar_recuperacion(db, data)


@router.post("/restablecer-password")
async def restablecer_password(request: Request, data: RestablecerPasswordRequest, db: Session = Depends(get_db)):
    return AuthController.restablecer_password(db, data)
