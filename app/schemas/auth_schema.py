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
