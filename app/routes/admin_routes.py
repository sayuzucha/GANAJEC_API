from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.controllers.admin_controller import AdminController
from app.schemas.general_schema import UsuarioUpdate, ConfiguracionUpdate

router = APIRouter()
admin_only = require_role("admin")


# ──────────────────────────────────────────────────────────────
# IMPORTANTE: las rutas literales (/usuarios, /ranchos, /sistema/...)
# deben registrarse ANTES de /{admin_id}. FastAPI/Starlette compara
# las rutas en el orden en que se registran, y "/{admin_id}" (un solo
# segmento) coincidiria con "/usuarios" o "/ranchos" si se registrara
# primero, interceptando esas peticiones.
# ──────────────────────────────────────────────────────────────

# 2. Listar usuarios (filtro opcional ?rol=ganadero|dueno|admin)
@router.get("/usuarios")
async def listar_usuarios(rol: str = None, db: Session = Depends(get_db), usuario=Depends(admin_only)):
    return AdminController.listar_usuarios(db, rol)


# 3. Actualizar estado/rol de un usuario
@router.put("/usuarios/{usuario_id}")
async def actualizar_usuario(usuario_id: str, data: UsuarioUpdate, db: Session = Depends(get_db),
                              usuario=Depends(admin_only)):
    return AdminController.actualizar_usuario(db, usuario_id, data, usuario)


# 4. Eliminar usuario
@router.delete("/usuarios/{usuario_id}")
async def eliminar_usuario(usuario_id: str, db: Session = Depends(get_db), usuario=Depends(admin_only)):
    return AdminController.eliminar_usuario(db, usuario_id, usuario)


# 5. Listar todos los ranchos del sistema
@router.get("/ranchos")
async def listar_ranchos(db: Session = Depends(get_db), usuario=Depends(admin_only)):
    return AdminController.listar_ranchos(db)


# 6. Estado del sistema: estadisticas, logs de auditoria, modelos ML
@router.get("/sistema/estado")
async def estado_sistema(db: Session = Depends(get_db), usuario=Depends(admin_only)):
    return AdminController.estado_sistema(db)


# 7. Actualizar un valor de configuracion del sistema
@router.put("/configuracion/{clave}")
async def actualizar_configuracion(clave: str, data: ConfiguracionUpdate, db: Session = Depends(get_db),
                                    usuario=Depends(admin_only)):
    return AdminController.actualizar_configuracion(db, clave, data, usuario)


# 1. Perfil del admin — DEBE QUEDAR AL FINAL (catch-all de 1 segmento)
@router.get("/{admin_id}")
async def perfil(admin_id: str, db: Session = Depends(get_db), usuario=Depends(admin_only)):
    return AdminController.perfil(db, admin_id)
