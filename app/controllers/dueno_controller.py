from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Usuario, Rancho, Bovino, Suscripcion
from app.schemas.general_schema import RanchoUpdate, GanaderoCreate, GanaderoUpdate
from app.core.security import hash_password


class DuenoController:
    """
    Controlador del rol Dueno del rancho. Endpoints:
    1. Perfil del dueno
    2. Dashboard del rancho
    3. Actualizar rancho
    4. Listar ganaderos del rancho
    5. Registrar nuevo ganadero
    6. Actualizar ganadero
    7. Listar todos los bovinos del rancho
    8. Ver suscripcion/plan actual
    """

    # 1. GET /api/dueno/{dueno_id}
    @staticmethod
    def perfil(db: Session, dueno_id: str):
        dueno = db.query(Usuario).filter(Usuario.id == dueno_id, Usuario.rol == "dueno").first()
        if not dueno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el dueno con id '{dueno_id}' no existe",
            )

        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()
        return {**dueno.to_dict(), "total_ranchos": len(ranchos), "ranchos": [r.to_dict() for r in ranchos]}

    # 2. GET /api/dueno/ranchos/{rancho_id}
    @staticmethod
    def obtener_rancho(db: Session, rancho_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el rancho con id '{rancho_id}' no existe",
            )

        bovinos = db.query(Bovino).filter(Bovino.rancho_id == rancho_id).all()
        por_categoria = {}
        for b in bovinos:
            por_categoria[b.categoria] = por_categoria.get(b.categoria, 0) + 1

        return {
            "rancho": rancho.to_dict(),
            "resumen": {
                "total_bovinos": len(bovinos),
                "por_categoria": por_categoria,
            },
        }

    # 3. PUT /api/dueno/ranchos/{rancho_id}
    @staticmethod
    def actualizar_rancho(db: Session, rancho_id: str, data: RanchoUpdate):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el rancho con id '{rancho_id}' no existe",
            )

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitud invalida: no se enviaron campos para actualizar",
            )

        for campo, valor in updates.items():
            setattr(rancho, campo, valor)

        db.commit()
        db.refresh(rancho)
        return rancho.to_dict()

    # 4. GET /api/dueno/ranchos/{rancho_id}/ganaderos
    @staticmethod
    def listar_ganaderos(db: Session, rancho_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el rancho con id '{rancho_id}' no existe",
            )

        # ganaderos = usuarios con rol ganadero que tienen al menos un bovino en este rancho
        ganadero_ids = {
            b.ganadero_id
            for b in db.query(Bovino).filter(Bovino.rancho_id == rancho_id).all()
        }
        ganaderos = (
            db.query(Usuario)
            .filter(Usuario.id.in_(ganadero_ids), Usuario.rol == "ganadero")
            .all()
            if ganadero_ids else []
        )

        return {
            "rancho": rancho.nombre,
            "total": len(ganaderos),
            "ganaderos": [g.to_dict() for g in ganaderos],
        }

    # 5. POST /api/dueno/ganaderos
    @staticmethod
    def registrar_ganadero(db: Session, data: GanaderoCreate):
        rancho = db.query(Rancho).filter(Rancho.id == data.rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el rancho con id '{data.rancho_id}' no existe",
            )

        existe = db.query(Usuario).filter(Usuario.email == data.email).first()
        if existe:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto: ya existe un usuario registrado con el correo '{data.email}'",
            )

        nuevo = Usuario(
            nombre=data.nombre,
            email=data.email,
            password_hash=hash_password(data.password),
            rol="ganadero",
            activo=True,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo.to_dict()

    # 6. PUT /api/dueno/ganaderos/{ganadero_id}
    @staticmethod
    def actualizar_ganadero(db: Session, ganadero_id: str, data: GanaderoUpdate):
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el ganadero con id '{ganadero_id}' no existe",
            )

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitud invalida: no se enviaron campos para actualizar",
            )

        for campo, valor in updates.items():
            setattr(ganadero, campo, valor)

        db.commit()
        db.refresh(ganadero)
        return ganadero.to_dict()

    # 7. GET /api/dueno/ranchos/{rancho_id}/bovinos
    @staticmethod
    def listar_bovinos_rancho(db: Session, rancho_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el rancho con id '{rancho_id}' no existe",
            )

        bovinos = db.query(Bovino).filter(Bovino.rancho_id == rancho_id).all()
        return {"rancho": rancho.nombre, "total": len(bovinos), "bovinos": [b.to_dict() for b in bovinos]}

    # 8. GET /api/dueno/{dueno_id}/suscripcion
    @staticmethod
    def obtener_suscripcion(db: Session, dueno_id: str):
        dueno = db.query(Usuario).filter(Usuario.id == dueno_id, Usuario.rol == "dueno").first()
        if not dueno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el dueno con id '{dueno_id}' no existe",
            )

        suscripcion = (
            db.query(Suscripcion)
            .filter(Suscripcion.usuario_id == dueno_id, Suscripcion.activa == True)  # noqa: E712
            .first()
        )
        if not suscripcion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el dueno '{dueno.nombre}' no tiene una suscripcion activa",
            )

        return suscripcion.to_dict()
