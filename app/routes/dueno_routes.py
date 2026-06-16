from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.controllers.dueno_controller import DuenoController
from app.schemas.general_schema import (
    RanchoCreate, RanchoUpdate,
    GanaderoCreate, GanaderoUpdate,
    AsignarGanaderoRancho,
)

router = APIRouter()
dueno_only = require_role("dueno")

# ──────────────────────────────────────────────────────────────
# ORDEN IMPORTANTE: rutas literales antes de /{dueno_id}
# ──────────────────────────────────────────────────────────────

# 1b. Crear un nuevo rancho para el dueño autenticado
@router.post("/ranchos", status_code=201)
async def crear_rancho(data: RanchoCreate, db: Session = Depends(get_db),
                       usuario=Depends(dueno_only)):
    return DuenoController.crear_rancho(db, usuario.id, data)


# 2. Dashboard de un rancho (bovinos + ganaderos asignados)
@router.get("/ranchos/{rancho_id}")
async def obtener_rancho(rancho_id: str, db: Session = Depends(get_db),
                          usuario=Depends(dueno_only)):
    return DuenoController.obtener_rancho(db, rancho_id)


# 3. Actualizar datos del rancho
@router.put("/ranchos/{rancho_id}")
async def actualizar_rancho(rancho_id: str, data: RanchoUpdate,
                             db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_rancho(db, rancho_id, data)


# 4. Listar ganaderos asignados a un rancho
@router.get("/ranchos/{rancho_id}/ganaderos")
async def listar_ganaderos(rancho_id: str, db: Session = Depends(get_db),
                            usuario=Depends(dueno_only)):
    return DuenoController.listar_ganaderos(db, rancho_id)


# 5b. Asignar ganadero EXISTENTE a un rancho adicional
@router.post("/ranchos/{rancho_id}/ganaderos", status_code=201)
async def asignar_ganadero(rancho_id: str, data: AsignarGanaderoRancho,
                            db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.asignar_ganadero(db, rancho_id, data)


# 7. Listar todos los bovinos de un rancho
@router.get("/ranchos/{rancho_id}/bovinos")
async def listar_bovinos_rancho(rancho_id: str, db: Session = Depends(get_db),
                                 usuario=Depends(dueno_only)):
    return DuenoController.listar_bovinos_rancho(db, rancho_id)


# 5. Registrar ganadero NUEVO y asignarlo a un rancho
@router.post("/ganaderos", status_code=201)
async def registrar_ganadero(data: GanaderoCreate, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.registrar_ganadero(db, data)


# 6. Actualizar / desactivar ganadero
@router.put("/ganaderos/{ganadero_id}")
async def actualizar_ganadero(ganadero_id: str, data: GanaderoUpdate,
                               db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_ganadero(db, ganadero_id, data)


# 8. Ver suscripcion/plan actual
@router.get("/{dueno_id}/suscripcion")
async def obtener_suscripcion(dueno_id: str, db: Session = Depends(get_db),
                               usuario=Depends(dueno_only)):
    return DuenoController.obtener_suscripcion(db, dueno_id)


# 1. Perfil del dueño — AL FINAL (catch-all de 1 segmento)
@router.get("/{dueno_id}")
async def perfil(dueno_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.perfil(db, dueno_id)
