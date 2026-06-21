from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.controllers.ganadero_controller import GanaderoController
from app.schemas.ganadero_schema import (
    BovinoCreate, BovinoUpdate,
    RegistroSintomaCreate, AlertaUpdate,
    UnirseRanchoRequest, GanaderoPerfilUpdate,
)

router = APIRouter()
ganadero_only = require_role("ganadero")

# ──────────────────────────────────────────────────────────────
# ORDEN IMPORTANTE: rutas literales antes de /{ganadero_id}
# ──────────────────────────────────────────────────────────────

# 3. Detalle de un bovino
@router.get("/bovinos/{bovino_id}")
async def obtener_bovino(bovino_id: str, db: Session = Depends(get_db),
                          usuario=Depends(ganadero_only)):
    return GanaderoController.obtener_bovino(db, bovino_id)


# 4. Registrar un nuevo bovino
@router.post("/bovinos", status_code=201)
async def crear_bovino(data: BovinoCreate, db: Session = Depends(get_db),
                        usuario=Depends(ganadero_only)):
    return GanaderoController.crear_bovino(db, usuario.id, data)


# 5. Actualizar datos de un bovino
@router.put("/bovinos/{bovino_id}")
async def actualizar_bovino(bovino_id: str, data: BovinoUpdate, db: Session = Depends(get_db),
                             usuario=Depends(ganadero_only)):
    return GanaderoController.actualizar_bovino(db, bovino_id, data)


# 6. Eliminar un bovino
@router.delete("/bovinos/{bovino_id}")
async def eliminar_bovino(bovino_id: str, db: Session = Depends(get_db),
                           usuario=Depends(ganadero_only)):
    return GanaderoController.eliminar_bovino(db, bovino_id)


# 7. Predicciones de un bovino específico
@router.get("/bovinos/{bovino_id}/predicciones")
async def obtener_predicciones(bovino_id: str, db: Session = Depends(get_db),
                                usuario=Depends(ganadero_only)):
    return GanaderoController.obtener_predicciones(db, bovino_id)


# 11. Gráficas de series de tiempo de un bovino
@router.get("/bovinos/{bovino_id}/graficas")
async def graficas_bovino(bovino_id: str, db: Session = Depends(get_db),
                           usuario=Depends(ganadero_only)):
    return GanaderoController.graficas_bovino(db, bovino_id)


# 8. Registrar nota de campo / síntomas
@router.post("/registros-sintomas", status_code=201)
async def registrar_sintoma(data: RegistroSintomaCreate, db: Session = Depends(get_db),
                             usuario=Depends(ganadero_only)):
    return GanaderoController.registrar_sintoma(db, usuario.id, data)


# 10. Marcar alerta como leída
@router.patch("/alertas/{alerta_id}")
async def marcar_alerta(alerta_id: str, data: AlertaUpdate, db: Session = Depends(get_db),
                         usuario=Depends(ganadero_only)):
    return GanaderoController.marcar_alerta(db, alerta_id, data)


# 9b. Unirse a un rancho mediante código de invitación
@router.post("/unirse-rancho", status_code=201)
async def unirse_rancho(data: UnirseRanchoRequest, db: Session = Depends(get_db),
                         usuario=Depends(ganadero_only)):
    return GanaderoController.unirse_rancho(db, usuario.id, data)


# 11. Listar ganaderos colegas del mismo rancho
@router.get("/colegas")
async def listar_colegas(db: Session = Depends(get_db), usuario=Depends(ganadero_only)):
    return GanaderoController.listar_colegas(db, usuario.id)


# ── Rutas con /{ganadero_id} — AL FINAL ──────────────────────

# 2. Listar bovinos a cargo del ganadero
@router.get("/{ganadero_id}/bovinos")
async def listar_bovinos(ganadero_id: str, db: Session = Depends(get_db),
                          usuario=Depends(ganadero_only)):
    return GanaderoController.listar_bovinos(db, ganadero_id)


# 7b. Historial global de predicciones del ganadero
@router.get("/{ganadero_id}/predicciones")
async def listar_predicciones(ganadero_id: str, db: Session = Depends(get_db),
                               usuario=Depends(ganadero_only)):
    return GanaderoController.listar_predicciones(db, ganadero_id)


# 9. Listar alertas del ganadero (filtro opcional ?bovino_id=)
@router.get("/{ganadero_id}/alertas")
async def listar_alertas(ganadero_id: str, bovino_id: str = None,
                          db: Session = Depends(get_db), usuario=Depends(ganadero_only)):
    return GanaderoController.listar_alertas(db, ganadero_id, bovino_id)


# 12. Actualizar perfil propio (nombre, email, password)
@router.put("/{ganadero_id}/perfil")
async def actualizar_perfil(ganadero_id: str, data: GanaderoPerfilUpdate,
                             db: Session = Depends(get_db), usuario=Depends(ganadero_only)):
    return GanaderoController.actualizar_perfil(db, ganadero_id, data)


# 1. Perfil del ganadero — DEBE IR AL FINAL (catch-all de 1 segmento)
@router.get("/{ganadero_id}")
async def perfil(ganadero_id: str, db: Session = Depends(get_db),
                  usuario=Depends(ganadero_only)):
    return GanaderoController.perfil(db, ganadero_id)
