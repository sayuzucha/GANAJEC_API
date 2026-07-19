import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routes.auth_routes import router as auth_router
from app.routes.ganadero_routes import router as ganadero_router
from app.routes.dueno_routes import router as dueno_router
from app.routes.admin_routes import router as admin_router
from app.core.database import engine, Base
from app.core.deps import limiter
import app.models  # registra todos los modelos antes de create_all
from app.routes.payment_routes import router as payment_router

logger = logging.getLogger("ganajec")

# Tamano maximo de payload: 1 MB (proteccion contra DoS por payloads enormes)
MAX_PAYLOAD_BYTES = 1 * 1024 * 1024


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)  # crea las tablas si no existen
    app = FastAPI(
        title="GANAJEC AI API",
        description="API REST (MVC + ORM/MySQL) para la plataforma de prediccion "
                     "de enfermedades bovinas GANAJEC AI",
        version="2.0.0",
    )

    # Rate limiter (anti brute-force)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Limite de payload (anti DoS)
    @app.middleware("http")
    async def limit_payload_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"status": 413, "error": "Payload muy grande",
                         "message": "El cuerpo de la solicitud supera el limite de 1 MB",
                         "path": str(request.url.path)},
            )
        return await call_next(request)

    # CORS: credentials=False porque la API usa Bearer token, no cookies.
    # allow_origins=["*"] es seguro sin cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    REASONS = {
        400: "Solicitud invalida",
        401: "No autorizado",
        403: "Acceso denegado",
        404: "No encontrado",
        405: "Metodo no permitido",
        409: "Conflicto",
        422: "Datos invalidos",
        500: "Error interno del servidor",
    }

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if exc.status_code == 404 and detail in (None, "Not Found"):
            detail = f"La ruta '{request.url.path}' no existe en esta API"
        reason = REASONS.get(exc.status_code, "Error")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": exc.status_code,
                "error": reason,
                "message": reason,
                "detail": detail,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": 422,
                "error": "Unprocessable Entity",
                "message": "Datos invalidos",
                "detail": exc.errors(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": 409,
                "error": "Conflicto",
                "message": "Conflicto",
                "detail": "La operacion viola una restriccion de la base de datos "
                           "(dato duplicado o relacion invalida)",
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error("SQLAlchemyError en %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "error": "Error interno del servidor",
                "message": "Error interno del servidor",
                "detail": "Ocurrio un error al comunicarse con la base de datos",
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # El error real se loguea server-side, nunca se expone al cliente
        logger.exception("Error no controlado en %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "error": "Error interno del servidor",
                "message": "Error interno del servidor",
                "detail": "Ocurrio un error inesperado. Intenta de nuevo mas tarde.",
                "path": str(request.url.path),
            },
        )

    app.include_router(auth_router, prefix="/api/auth", tags=["Autenticacion"])
    app.include_router(ganadero_router, prefix="/api/ganadero", tags=["Ganadero"])
    app.include_router(dueno_router, prefix="/api/dueno", tags=["Dueno del rancho"])
    app.include_router(admin_router, prefix="/api/admin", tags=["Administrador"])
    app.include_router(payment_router)
    @app.get("/api", tags=["Root"])
    async def root():
        return {
            "api": "GANAJEC AI",
            "version": "2.0.0",
            "status": "ok",
            "endpoints": {
                "auth": "/api/auth",
                "ganadero": "/api/ganadero",
                "dueno": "/api/dueno",
                "admin": "/api/admin",
                "payments": "/api/payments",
            },
        }

    return app


app = create_app()
