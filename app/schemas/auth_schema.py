from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    nombre: str = Field(..., min_length=3, examples=["Jared Torres Morga"])
    email: EmailStr = Field(..., examples=["jared@ganajec.ai"])
    password: str = Field(..., min_length=8, examples=["claveSegura123"])
    rol: str = Field(..., pattern="^(ganadero|dueno|admin)$", examples=["ganadero"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class FcmTokenUpdate(BaseModel):
    """
    Cuerpo para PUT /api/auth/fcm-token.
    La app móvil llama este endpoint justo después del login para
    registrar (o actualizar) el token FCM del dispositivo.
    Enviar fcm_token=null elimina el token (desuscribe notificaciones).
    """
    fcm_token: str | None = Field(
        ...,
        examples=["dGhpcyBpcyBhIHNhbXBsZSBmY20gdG9rZW4..."],
        description="Token FCM del dispositivo. Null para desuscribir.",
    )
