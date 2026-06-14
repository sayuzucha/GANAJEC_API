from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.controllers.dueno_controller import DuenoController
from app.schemas.general_schema import RanchoUpdate, GanaderoCreate, GanaderoUpdate

router = APIRouter()
dueno_only = require_role("dueno")


# 1. Perfil del dueno
@router.get("/{dueno_id}")
async def perfil(dueno_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.perfil(db, dueno_id)


# 2. Dashboard general del rancho
@router.get("/ranchos/{rancho_id}")
async def obtener_rancho(rancho_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.obtener_rancho(db, rancho_id)


# 3. Actualizar datos del rancho
@router.put("/ranchos/{rancho_id}")
async def actualizar_rancho(rancho_id: str, data: RanchoUpdate, db: Session = Depends(get_db),
                             usuario=Depends(dueno_only)):
    return DuenoController.actualizar_rancho(db, rancho_id, data)


# 4. Listar ganaderos del rancho
@router.get("/ranchos/{rancho_id}/ganaderos")
async def listar_ganaderos(rancho_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.listar_ganaderos(db, rancho_id)


# 5. Registrar nuevo ganadero
@router.post("/ganaderos", status_code=201)
async def registrar_ganadero(data: GanaderoCreate, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.registrar_ganadero(db, data)


# 6. Actualizar/desactivar ganadero
@router.put("/ganaderos/{ganadero_id}")
async def actualizar_ganadero(ganadero_id: str, data: GanaderoUpdate, db: Session = Depends(get_db),
                               usuario=Depends(dueno_only)):
    return DuenoController.actualizar_ganadero(db, ganadero_id, data)


# 7. Listar todos los bovinos del rancho
@router.get("/ranchos/{rancho_id}/bovinos")
async def listar_bovinos_rancho(rancho_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.listar_bovinos_rancho(db, rancho_id)


# 8. Ver suscripcion/plan actual
@router.get("/{dueno_id}/suscripcion")
async def obtener_suscripcion(dueno_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.obtener_suscripcion(db, dueno_id)
