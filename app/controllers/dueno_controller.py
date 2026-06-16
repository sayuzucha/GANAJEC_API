from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Usuario, Rancho, RanchoGanadero, Bovino, Suscripcion
from app.schemas.general_schema import (
    RanchoCreate, RanchoUpdate,
    GanaderoCreate, GanaderoUpdate,
    AsignarGanaderoRancho,
)
from app.core.security import hash_password
from app.models.rancho import _generar_codigo


class DuenoController:
    """
    Controlador del rol Dueño del rancho.

    Lógica de rancho-ganadero:
    - Un dueño puede tener N ranchos.
    - Un rancho puede tener N ganaderos (tabla intermedia rancho_ganaderos).
    - Un ganadero puede estar asignado a M ranchos (del mismo dueño u otros).
    - Al registrar un ganadero nuevo, se crea el Usuario y se asigna al rancho indicado.
    - Se puede asignar un ganadero existente a un rancho adicional con
      POST /api/dueno/ranchos/{rancho_id}/ganaderos.
    """

    # 1. GET /api/dueno/{dueno_id}
    @staticmethod
    def perfil(db: Session, dueno_id: str):
        dueno = db.query(Usuario).filter(
            Usuario.id == dueno_id, Usuario.rol == "dueno"
        ).first()
        if not dueno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el dueno con id '{dueno_id}' no existe",
            )

        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()

        # Total de ganaderos únicos en TODOS los ranchos del dueño
        rancho_ids = [r.id for r in ranchos]
        ganadero_ids_unicos = set()
        if rancho_ids:
            asignaciones = (
                db.query(RanchoGanadero.ganadero_id)
                .filter(RanchoGanadero.rancho_id.in_(rancho_ids))
                .all()
            )
            ganadero_ids_unicos = {a.ganadero_id for a in asignaciones}

        return {
            **dueno.to_dict(),
            "total_ranchos": len(ranchos),
            "total_ganaderos": len(ganadero_ids_unicos),
            # include_codigo=True para que el dueño pueda ver/compartir los códigos
            "ranchos": [r.to_dict(include_codigo=True) for r in ranchos],
        }

    # 1b. POST /api/dueno/ranchos
    @staticmethod
    def crear_rancho(db: Session, dueno_id: str, data: RanchoCreate):
        # Generar código único: reintenta si hay colisión (improbable con 8 chars)
        for _ in range(5):
            codigo = _generar_codigo()
            if not db.query(Rancho).filter(Rancho.codigo_invitacion == codigo).first():
                break

        nuevo = Rancho(
            nombre=data.nombre,
            municipio=data.municipio,
            estado=data.estado,
            dueno_id=dueno_id,
            codigo_invitacion=codigo,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        # include_codigo=True: el dueño necesita ver el código para compartirlo
        return nuevo.to_dict(include_codigo=True)

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

        # Ganaderos asignados a este rancho via tabla intermedia
        asignaciones = (
            db.query(RanchoGanadero)
            .filter(RanchoGanadero.rancho_id == rancho_id)
            .all()
        )
        ganadero_ids = [a.ganadero_id for a in asignaciones]
        ganaderos = (
            db.query(Usuario)
            .filter(Usuario.id.in_(ganadero_ids))
            .all()
            if ganadero_ids else []
        )

        return {
            "rancho": rancho.to_dict(),
            "resumen": {
                "total_bovinos": len(bovinos),
                "por_categoria": por_categoria,
                "total_ganaderos": len(ganaderos),
            },
            "ganaderos": [g.to_dict() for g in ganaderos],
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

        asignaciones = (
            db.query(RanchoGanadero)
            .filter(RanchoGanadero.rancho_id == rancho_id)
            .all()
        )
        ganadero_ids = [a.ganadero_id for a in asignaciones]
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

    # 5. POST /api/dueno/ganaderos — crea ganadero nuevo y lo asigna al rancho
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
        db.flush()  # obtener nuevo.id sin hacer commit aún

        # Asignar al rancho en la tabla intermedia
        asignacion = RanchoGanadero(
            rancho_id=data.rancho_id,
            ganadero_id=nuevo.id,
        )
        db.add(asignacion)
        db.commit()
        db.refresh(nuevo)

        return {
            **nuevo.to_dict(),
            "rancho_asignado": rancho.nombre,
        }

    # 5b. POST /api/dueno/ranchos/{rancho_id}/ganaderos — asigna ganadero EXISTENTE
    @staticmethod
    def asignar_ganadero(db: Session, rancho_id: str, data: AsignarGanaderoRancho):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el rancho con id '{rancho_id}' no existe",
            )

        ganadero = db.query(Usuario).filter(
            Usuario.id == data.ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el ganadero con id '{data.ganadero_id}' no existe",
            )

        ya_asignado = db.query(RanchoGanadero).filter(
            RanchoGanadero.rancho_id == rancho_id,
            RanchoGanadero.ganadero_id == data.ganadero_id,
        ).first()
        if ya_asignado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto: el ganadero '{ganadero.nombre}' ya esta asignado a este rancho",
            )

        asignacion = RanchoGanadero(rancho_id=rancho_id, ganadero_id=data.ganadero_id)
        db.add(asignacion)
        db.commit()

        return {
            "mensaje": f"Ganadero '{ganadero.nombre}' asignado al rancho '{rancho.nombre}'",
            "ganadero": ganadero.to_dict(),
        }

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
        return {
            "rancho": rancho.nombre,
            "total": len(bovinos),
            "bovinos": [b.to_dict() for b in bovinos],
        }

    # 8. GET /api/dueno/{dueno_id}/suscripcion
    @staticmethod
    def obtener_suscripcion(db: Session, dueno_id: str):
        dueno = db.query(Usuario).filter(
            Usuario.id == dueno_id, Usuario.rol == "dueno"
        ).first()
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
