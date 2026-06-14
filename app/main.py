from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.routes.auth_routes import router as auth_router
from app.routes.ganadero_routes import router as ganadero_router
from app.routes.dueno_routes import router as dueno_router
from app.routes.admin_routes import router as admin_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="GANAJEC AI API",
        description="API REST (MVC + ORM/MySQL) para la plataforma de prediccion "
                     "de enfermedades bovinas GANAJEC AI",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ──────────────────────────────────────────────
    # Manejadores de errores personalizados
    # Todos los errores devuelven el mismo formato JSON,
    # listo para mostrarse "bonito" en el frontend (ej. "No encontrado")
    # ──────────────────────────────────────────────

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
        """
        Captura HTTPException lanzadas desde los controllers (404, 400, 409, etc.)
        y rutas que no existen (404 automatico de FastAPI/Starlette).
        """
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
        """
        Errores de integridad de MySQL: llaves duplicadas, FK invalidas, etc.
        """
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
        """
        Cualquier otro error de base de datos (conexion perdida, query invalida, etc.)
        """
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
        """
        Red de seguridad: cualquier excepcion no controlada se convierte
        en un 500 con formato consistente, en vez de un traceback crudo.
        """
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

    # ──────────────────────────────────────────────
    # Rutas
    # ──────────────────────────────────────────────
    app.include_router(auth_router, prefix="/api/auth", tags=["Autenticacion"])
    app.include_router(ganadero_router, prefix="/api/ganadero", tags=["Ganadero"])
    app.include_router(dueno_router, prefix="/api/dueno", tags=["Dueno del rancho"])
    app.include_router(admin_router, prefix="/api/admin", tags=["Administrador"])

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
            },
        }

    return app


app = create_app()
