from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.controllers.dueno_controller import DuenoController
from app.schemas.general_schema import (
    RanchoCreate, RanchoUpdate,
    GanaderoCreate, GanaderoUpdate,
    AsignarGanaderoRancho,
    VeterinarioCreate, VeterinarioUpdate,
)

router = APIRouter()
dueno_only = require_role("dueno")

# ──────────────────────────────────────────────────────────────
# ORDEN IMPORTANTE: rutas literales antes de /{dueno_id}
# ──────────────────────────────────────────────────────────────

# ── RANCHOS ───────────────────────────────────────────────────

@router.post("/ranchos", status_code=201)
async def crear_rancho(data: RanchoCreate, db: Session = Depends(get_db),
                       usuario=Depends(dueno_only)):
    return DuenoController.crear_rancho(db, usuario.id, data)


@router.get("/ranchos/{rancho_id}")
async def obtener_rancho(rancho_id: str, db: Session = Depends(get_db),
                         usuario=Depends(dueno_only)):
    return DuenoController.obtener_rancho(db, rancho_id)


@router.put("/ranchos/{rancho_id}")
async def actualizar_rancho(rancho_id: str, data: RanchoUpdate,
                            db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_rancho(db, rancho_id, data)


@router.get("/ranchos/{rancho_id}/ganaderos")
async def listar_ganaderos(rancho_id: str, db: Session = Depends(get_db),
                           usuario=Depends(dueno_only)):
    return DuenoController.listar_ganaderos(db, rancho_id)


@router.post("/ranchos/{rancho_id}/ganaderos", status_code=201)
async def asignar_ganadero(rancho_id: str, data: AsignarGanaderoRancho,
                           db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.asignar_ganadero(db, rancho_id, data)


@router.delete("/ranchos/{rancho_id}/ganaderos/{ganadero_id}")
async def eliminar_ganadero_rancho(rancho_id: str, ganadero_id: str,
                                   db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.eliminar_ganadero_rancho(db, rancho_id, ganadero_id)


@router.get("/ranchos/{rancho_id}/bovinos")
async def listar_bovinos_rancho(rancho_id: str, db: Session = Depends(get_db),
                                usuario=Depends(dueno_only)):
    return DuenoController.listar_bovinos_rancho(db, rancho_id)


@router.get("/ranchos/{rancho_id}/estadisticas")
async def estadisticas_rancho(rancho_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.estadisticas_rancho(db, rancho_id)


# ── VETERINARIOS ──────────────────────────────────────────────

@router.post("/ranchos/{rancho_id}/veterinarios", status_code=201)
async def agregar_veterinario(rancho_id: str, data: VeterinarioCreate,
                              db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.agregar_veterinario(db, rancho_id, data)


@router.get("/ranchos/{rancho_id}/veterinarios")
async def listar_veterinarios(rancho_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.listar_veterinarios(db, rancho_id)


@router.put("/veterinarios/{vet_id}")
async def actualizar_veterinario(vet_id: str, data: VeterinarioUpdate,
                                 db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_veterinario(db, vet_id, data)


@router.delete("/veterinarios/{vet_id}")
async def eliminar_veterinario(vet_id: str, db: Session = Depends(get_db),
                               usuario=Depends(dueno_only)):
    return DuenoController.eliminar_veterinario(db, vet_id)


# ── GANADERO: bovinos ─────────────────────────────────────────

@router.get("/ganaderos/{ganadero_id}/bovinos")
async def bovinos_de_ganadero(ganadero_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.bovinos_de_ganadero(db, ganadero_id)


# ── BOVINO: detalle completo ──────────────────────────────────

@router.get("/bovinos/{bovino_id}")
async def detalle_bovino(bovino_id: str, db: Session = Depends(get_db),
                         usuario=Depends(dueno_only)):
    return DuenoController.detalle_bovino(db, bovino_id)


# ── GANADEROS: registrar / actualizar ────────────────────────

@router.post("/ganaderos", status_code=201)
async def registrar_ganadero(data: GanaderoCreate, db: Session = Depends(get_db),
                             usuario=Depends(dueno_only)):
    return DuenoController.registrar_ganadero(db, data)


@router.put("/ganaderos/{ganadero_id}")
async def actualizar_ganadero(ganadero_id: str, data: GanaderoUpdate,
                              db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_ganadero(db, ganadero_id, data)


# ── SUSCRIPCIÓN / PERFIL — catch-alls al final ───────────────

@router.get("/{dueno_id}/suscripcion")
async def obtener_suscripcion(dueno_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.obtener_suscripcion(db, dueno_id)


@router.get("/{dueno_id}")
async def perfil(dueno_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.perfil(db, dueno_id)
