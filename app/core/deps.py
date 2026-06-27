from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import Usuario

# Limitador de rate (instancia global, se registra en main.py)
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

# tokenUrl es solo para la documentacion de Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado: falta el token de acceso (header Authorization: Bearer ...)",
        )

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado: el token ha expirado, inicia sesion de nuevo",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado: token invalido",
        )

    usuario_id = payload.get("sub")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado: el usuario del token ya no existe",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: tu cuenta esta desactivada",
        )

    usuario.ultima_actividad = datetime.utcnow()
    db.commit()

    return usuario


def require_role(*roles: str):
    def checker(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: se requiere rol {' o '.join(roles)}",
            )
        return usuario
    return checker


# BOLA / IDOR helpers

def require_self_ganadero(ganadero_id: str, usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """El ganadero autenticado solo puede acceder a sus propios recursos."""
    if usuario.id != ganadero_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: no puedes acceder a recursos de otro usuario",
        )
    return usuario


def require_self_dueno(dueno_id: str, usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """El dueno autenticado solo puede acceder a su propio perfil/suscripcion."""
    if usuario.id != dueno_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: no puedes acceder a recursos de otro usuario",
        )
    return usuario
