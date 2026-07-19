from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, require_self_dueno
from app.controllers.dueno_controller import DuenoController
from app.controllers.ganadero_controller import GanaderoController
from app.models.rancho import Rancho
from app.schemas.general_schema import (
    RanchoCreate, RanchoUpdate,
    GanaderoCreate, GanaderoUpdate,
    AsignarGanaderoRancho,
    VeterinarioCreate, VeterinarioUpdate,
    DuenoPerfilUpdate,
    MoverGanaderoRancho,
)
from app.schemas.payment_schema import ConfirmarSuscripcionRequest

router = APIRouter()
dueno_only = require_role("dueno")


# ── Dependencia BOLA: verifica que el rancho pertenece al dueño autenticado ──
def _rancho_owner(rancho_id: str, db: Session = Depends(get_db),
                  usuario=Depends(dueno_only)):
    rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
    if not rancho or rancho.dueno_id != usuario.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No encontrado: rancho no existe o no tienes acceso")


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
                         usuario=Depends(dueno_only), _=Depends(_rancho_owner)):
    return DuenoController.obtener_rancho(db, rancho_id)


@router.put("/ranchos/{rancho_id}")
async def actualizar_rancho(rancho_id: str, data: RanchoUpdate,
                            db: Session = Depends(get_db), usuario=Depends(dueno_only),
                            _=Depends(_rancho_owner)):
    return DuenoController.actualizar_rancho(db, rancho_id, data)


@router.get("/ranchos/{rancho_id}/ganaderos")
async def listar_ganaderos(rancho_id: str, db: Session = Depends(get_db),
                           usuario=Depends(dueno_only), _=Depends(_rancho_owner)):
    return DuenoController.listar_ganaderos(db, rancho_id)


@router.post("/ranchos/{rancho_id}/ganaderos", status_code=201)
async def asignar_ganadero(rancho_id: str, data: AsignarGanaderoRancho,
                           db: Session = Depends(get_db), usuario=Depends(dueno_only),
                           _=Depends(_rancho_owner)):
    return DuenoController.asignar_ganadero(db, rancho_id, data)


@router.patch("/ranchos/{rancho_id}/ganaderos/{ganadero_id}")
async def mover_ganadero(rancho_id: str, ganadero_id: str, data: MoverGanaderoRancho,
                         db: Session = Depends(get_db), usuario=Depends(dueno_only),
                         _=Depends(_rancho_owner)):
    return DuenoController.mover_ganadero(db, rancho_id, ganadero_id, data.nuevo_rancho_id, usuario.id)


@router.delete("/ranchos/{rancho_id}/ganaderos/{ganadero_id}")
async def eliminar_ganadero_rancho(rancho_id: str, ganadero_id: str,
                                   db: Session = Depends(get_db), usuario=Depends(dueno_only),
                                   _=Depends(_rancho_owner)):
    return DuenoController.eliminar_ganadero_rancho(db, rancho_id, ganadero_id)


@router.get("/ranchos/{rancho_id}/bovinos")
async def listar_bovinos_rancho(rancho_id: str, db: Session = Depends(get_db),
                                usuario=Depends(dueno_only), _=Depends(_rancho_owner)):
    return DuenoController.listar_bovinos_rancho(db, rancho_id)


@router.get("/ranchos/{rancho_id}/estadisticas")
async def estadisticas_rancho(rancho_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only), _=Depends(_rancho_owner)):
    return DuenoController.estadisticas_rancho(db, rancho_id)


# ── VETERINARIOS ──────────────────────────────────────────────

# Crear veterinario (sin rancho todavía)
@router.post("/veterinarios", status_code=201)
async def crear_veterinario(data: VeterinarioCreate, db: Session = Depends(get_db),
                            usuario=Depends(dueno_only)):
    return DuenoController.crear_veterinario(db, data)


# Listar todos los veterinarios del dueño (todos sus ranchos)
@router.get("/veterinarios")
async def listar_todos_veterinarios(db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.listar_todos_veterinarios(db, usuario.id)


# Listar veterinarios de un rancho
@router.get("/ranchos/{rancho_id}/veterinarios")
async def listar_veterinarios(rancho_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only), _=Depends(_rancho_owner)):
    return DuenoController.listar_veterinarios(db, rancho_id)


# Asociar veterinario existente a un rancho
@router.post("/ranchos/{rancho_id}/veterinarios/{vet_id}", status_code=201)
async def asociar_veterinario(rancho_id: str, vet_id: str,
                              db: Session = Depends(get_db), usuario=Depends(dueno_only),
                              _=Depends(_rancho_owner)):
    return DuenoController.asociar_veterinario(db, rancho_id, vet_id)


# Quitar asociación veterinario-rancho (NO elimina el veterinario)
@router.delete("/ranchos/{rancho_id}/veterinarios/{vet_id}")
async def quitar_veterinario(rancho_id: str, vet_id: str,
                             db: Session = Depends(get_db), usuario=Depends(dueno_only),
                             _=Depends(_rancho_owner)):
    return DuenoController.quitar_veterinario(db, rancho_id, vet_id)


# Actualizar datos del veterinario
@router.put("/veterinarios/{vet_id}")
async def actualizar_veterinario(vet_id: str, data: VeterinarioUpdate,
                                 db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_veterinario(db, vet_id, usuario.id, data)


# Eliminar veterinario completamente
@router.delete("/veterinarios/{vet_id}")
async def eliminar_veterinario(vet_id: str, db: Session = Depends(get_db),
                               usuario=Depends(dueno_only)):
    return DuenoController.eliminar_veterinario(db, vet_id, usuario.id)


# ── GANADERO: bovinos ─────────────────────────────────────────

@router.get("/ganaderos/{ganadero_id}/bovinos")
async def bovinos_de_ganadero(ganadero_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only)):
    return DuenoController.bovinos_de_ganadero(db, ganadero_id)


# ── BOVINO: detalle completo + gráficas ──────────────────────

@router.get("/bovinos/{bovino_id}/graficas")
async def graficas_bovino(bovino_id: str, db: Session = Depends(get_db),
                           usuario=Depends(dueno_only)):
    # Reutiliza graficas_bovino del ganadero — el check de rancho ownership ya esta en detalle_bovino;
    # aqui solo se puede llegar si el dueno tiene acceso al bovino via _rancho_owner en otra ruta.
    # El check de BOLA completo se aplica en detalle_bovino.
    DuenoController.detalle_bovino(db, bovino_id, usuario.id)  # raises 403 si no es suyo
    return GanaderoController.graficas_bovino(db, bovino_id)


@router.get("/bovinos/{bovino_id}")
async def detalle_bovino(bovino_id: str, db: Session = Depends(get_db),
                         usuario=Depends(dueno_only)):
    return DuenoController.detalle_bovino(db, bovino_id, usuario.id)


# ── GANADEROS: registrar / actualizar ────────────────────────

@router.post("/ganaderos", status_code=201)
async def registrar_ganadero(data: GanaderoCreate, db: Session = Depends(get_db),
                             usuario=Depends(dueno_only)):
    return DuenoController.registrar_ganadero(db, data)


@router.put("/ganaderos/{ganadero_id}")
async def actualizar_ganadero(ganadero_id: str, data: GanaderoUpdate,
                              db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.actualizar_ganadero(db, ganadero_id, data)


# ── VISTAS GLOBALES (todos los ranchos del dueño) ────────────

@router.get("/bovinos")
async def todos_bovinos(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                        db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.todos_bovinos(db, usuario.id, limit, offset)


@router.get("/predicciones")
async def todas_predicciones(db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.todas_predicciones(db, usuario.id)


@router.get("/historial")
async def historial_bovinos(db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.historial_bovinos(db, usuario.id)


@router.get("/reportes")
async def reportes(db: Session = Depends(get_db), usuario=Depends(dueno_only)):
    return DuenoController.reportes(db, usuario.id)


# ── SUSCRIPCIÓN / PERFIL — catch-alls al final ───────────────
# BOLA: require_self_dueno verifica que dueno_id == usuario.id

@router.get("/{dueno_id}/suscripcion")
async def obtener_suscripcion(dueno_id: str, db: Session = Depends(get_db),
                              usuario=Depends(dueno_only),
                              _=Depends(require_self_dueno)):
    return DuenoController.obtener_suscripcion(db, dueno_id)


@router.post("/{dueno_id}/suscripcion", status_code=201)
async def crear_suscripcion(dueno_id: str, data: ConfirmarSuscripcionRequest,
                            db: Session = Depends(get_db),
                            usuario=Depends(dueno_only),
                            _=Depends(require_self_dueno)):
    return DuenoController.crear_suscripcion(db, dueno_id, data)


@router.put("/{dueno_id}/perfil")
async def actualizar_perfil(dueno_id: str, data: DuenoPerfilUpdate,
                            db: Session = Depends(get_db), usuario=Depends(dueno_only),
                            _=Depends(require_self_dueno)):
    return DuenoController.actualizar_perfil(db, dueno_id, data)


@router.get("/{dueno_id}")
async def perfil(dueno_id: str, db: Session = Depends(get_db), usuario=Depends(dueno_only),
                 _=Depends(require_self_dueno)):
    return DuenoController.perfil(db, dueno_id)
