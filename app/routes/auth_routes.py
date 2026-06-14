from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.controllers.auth_controller import AuthController
from app.schemas.auth_schema import RegisterRequest, LoginRequest

router = APIRouter()


# Registro de un nuevo usuario (ganadero, dueno o admin)
@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return AuthController.register(db, data)


# Login: retorna token JWT + datos del usuario
@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    return AuthController.login(db, data)
