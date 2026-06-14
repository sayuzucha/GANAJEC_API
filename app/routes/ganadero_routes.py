from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.controllers.ganadero_controller import GanaderoController
from app.schemas.ganadero_schema import BovinoCreate, BovinoUpdate, RegistroSintomaCreate, AlertaUpdate

router = APIRouter()
ganadero_only = require_role("ganadero")


# 1. Perfil del ganadero
@router.get("/{ganadero_id}")
async def perfil(ganadero_id: str, db: Session = Depends(get_db),
                  usuario=Depends(ganadero_only)):
    return GanaderoController.perfil(db, ganadero_id)


# 2. Listar bovinos a cargo del ganadero
@router.get("/{ganadero_id}/bovinos")
async def listar_bovinos(ganadero_id: str, db: Session = Depends(get_db),
                          usuario=Depends(ganadero_only)):
    return GanaderoController.listar_bovinos(db, ganadero_id)


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


# 7. Predicciones de enfermedad de un bovino especifico
@router.get("/bovinos/{bovino_id}/predicciones")
async def obtener_predicciones(bovino_id: str, db: Session = Depends(get_db),
                                usuario=Depends(ganadero_only)):
    return GanaderoController.obtener_predicciones(db, bovino_id)


# 7b. Historial global: predicciones de TODOS los bovinos del ganadero
@router.get("/{ganadero_id}/predicciones")
async def listar_predicciones(ganadero_id: str, db: Session = Depends(get_db),
                               usuario=Depends(ganadero_only)):
    return GanaderoController.listar_predicciones(db, ganadero_id)


# 8. Registrar nota de campo / sintomas
@router.post("/registros-sintomas", status_code=201)
async def registrar_sintoma(data: RegistroSintomaCreate, db: Session = Depends(get_db),
                             usuario=Depends(ganadero_only)):
    return GanaderoController.registrar_sintoma(db, usuario.id, data)


# 9. Listar alertas del ganadero (filtro opcional por bovino)
@router.get("/{ganadero_id}/alertas")
async def listar_alertas(ganadero_id: str, bovino_id: str = None,
                          db: Session = Depends(get_db), usuario=Depends(ganadero_only)):
    return GanaderoController.listar_alertas(db, ganadero_id, bovino_id)


# 10. Marcar alerta como leida
@router.patch("/alertas/{alerta_id}")
async def marcar_alerta(alerta_id: str, data: AlertaUpdate, db: Session = Depends(get_db),
                         usuario=Depends(ganadero_only)):
    return GanaderoController.marcar_alerta(db, alerta_id, data)
