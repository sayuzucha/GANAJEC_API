from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from sqlalchemy import func
from app.models import Usuario, Rancho, Bovino, Suscripcion, Veterinario
from app.models.registro_sintoma import RegistroSintoma, Prediccion
from app.models.alerta import Alerta
import datetime
from app.schemas.general_schema import (
    RanchoCreate, RanchoUpdate,
    GanaderoCreate, GanaderoUpdate,
    AsignarGanaderoRancho,
    VeterinarioCreate, VeterinarioUpdate,
)
from app.core.security import hash_password
from app.models.rancho import _generar_codigo


class DuenoController:
    """
    Controlador del rol Dueño del rancho.

    Lógica de rancho-ganadero:
    - Un dueño puede tener N ranchos.
    - Un ganadero pertenece a exactamente 1 rancho (rancho_id en usuarios).
    - El dueño puede registrar ganaderos nuevos asignándolos directamente a un rancho.
    - El dueño puede reasignar un ganadero existente a otro rancho.
    """

    # 1. GET /api/dueno/{dueno_id}
    @staticmethod
    def actualizar_perfil(db: Session, dueno_id: str, data):
        """El dueño actualiza su propio nombre, email y/o contraseña."""
        dueno = db.query(Usuario).filter(
            Usuario.id == dueno_id, Usuario.rol == "dueno"
        ).first()
        if not dueno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el dueño con id '{dueno_id}' no existe",
            )

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitud invalida: no se enviaron campos para actualizar",
            )

        if "email" in updates:
            existe = db.query(Usuario).filter(
                Usuario.email == updates["email"],
                Usuario.id != dueno_id,
            ).first()
            if existe:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflicto: ya existe un usuario con el correo '{updates['email']}'",
                )
            dueno.email = updates["email"]

        if "nombre" in updates:
            dueno.nombre = updates["nombre"]

        if "password" in updates:
            from app.core.security import hash_password
            dueno.password_hash = hash_password(updates["password"])

        db.commit()
        db.refresh(dueno)
        return dueno.to_dict()

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
        rancho_ids = [r.id for r in ranchos]

        total_ganaderos = 0
        if rancho_ids:
            total_ganaderos = db.query(Usuario).filter(
                Usuario.rancho_id.in_(rancho_ids),
                Usuario.rol == "ganadero",
            ).count()

        return {
            **dueno.to_dict(),
            "total_ranchos": len(ranchos),
            "total_ganaderos": total_ganaderos,
            "ranchos": [r.to_dict(include_codigo=True) for r in ranchos],
        }

    # 1b. POST /api/dueno/ranchos
    @staticmethod
    def crear_rancho(db: Session, dueno_id: str, data: RanchoCreate):
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

        ganaderos = db.query(Usuario).filter(
            Usuario.rancho_id == rancho_id,
            Usuario.rol == "ganadero",
        ).all()

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

        ganaderos = db.query(Usuario).filter(
            Usuario.rancho_id == rancho_id,
            Usuario.rol == "ganadero",
        ).all()

        # Contar bovinos por ganadero en una sola query
        bovino_counts = {}
        if ganaderos:
            ganadero_ids = [g.id for g in ganaderos]
            counts = (
                db.query(Bovino.ganadero_id, func.count(Bovino.id))
                .filter(Bovino.ganadero_id.in_(ganadero_ids))
                .group_by(Bovino.ganadero_id)
                .all()
            )
            bovino_counts = {gid: cnt for gid, cnt in counts}

        return {
            "rancho": rancho.nombre,
            "total": len(ganaderos),
            "ganaderos": [
                {**g.to_dict(), "total_bovinos": bovino_counts.get(g.id, 0)}
                for g in ganaderos
            ],
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
            rancho_id=data.rancho_id,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)

        return {
            **nuevo.to_dict(),
            "rancho_asignado": rancho.nombre,
        }

    # 5b. POST /api/dueno/ranchos/{rancho_id}/ganaderos — reasigna ganadero EXISTENTE
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

        if ganadero.rancho_id == rancho_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto: el ganadero '{ganadero.nombre}' ya está asignado a este rancho",
            )

        ganadero.rancho_id = rancho_id
        db.commit()
        db.refresh(ganadero)

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

    # ── GANADERO: eliminar del rancho ─────────────────────────────────────

    # DELETE /api/dueno/ranchos/{rancho_id}/ganaderos/{ganadero_id}
    @staticmethod
    def eliminar_ganadero_rancho(db: Session, rancho_id: str, ganadero_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id,
            Usuario.rol == "ganadero",
            Usuario.rancho_id == rancho_id,
        ).first()
        if not ganadero:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="El ganadero no pertenece a este rancho")

        ganadero.rancho_id = None
        db.commit()
        return {"mensaje": f"Ganadero '{ganadero.nombre}' removido del rancho '{rancho.nombre}'"}

    @staticmethod
    def mover_ganadero(db: Session, rancho_id: str, ganadero_id: str, nuevo_rancho_id: str, dueno_id: str):
        """Mueve un ganadero de rancho_id a nuevo_rancho_id, ambos deben pertenecer al dueño."""
        # Verificar que el rancho origen pertenece al dueño
        rancho_origen = db.query(Rancho).filter(
            Rancho.id == rancho_id, Rancho.dueno_id == dueno_id
        ).first()
        if not rancho_origen:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No encontrado: rancho origen no existe o no tienes acceso")

        # Verificar que el rancho destino también pertenece al dueño
        rancho_destino = db.query(Rancho).filter(
            Rancho.id == nuevo_rancho_id, Rancho.dueno_id == dueno_id
        ).first()
        if not rancho_destino:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No encontrado: rancho destino no existe o no tienes acceso")

        if rancho_id == nuevo_rancho_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Conflicto: el ganadero ya está en ese rancho")

        # Verificar que el ganadero pertenece al rancho origen
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id,
            Usuario.rol == "ganadero",
            Usuario.rancho_id == rancho_id,
        ).first()
        if not ganadero:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="El ganadero no pertenece a este rancho")

        ganadero.rancho_id = nuevo_rancho_id
        db.commit()
        db.refresh(ganadero)
        return {
            "mensaje": f"Ganadero '{ganadero.nombre}' movido a rancho '{rancho_destino.nombre}'",
            "ganadero": ganadero.to_dict(),
        }

    # ── GANADERO: ver bovinos ─────────────────────────────────────────────

    # GET /api/dueno/ganaderos/{ganadero_id}/bovinos
    @staticmethod
    def bovinos_de_ganadero(db: Session, ganadero_id: str):
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: ganadero '{ganadero_id}' no existe")

        bovinos = db.query(Bovino).filter(Bovino.ganadero_id == ganadero_id).all()
        return {
            "ganadero": ganadero.to_dict(),
            "total_bovinos": len(bovinos),
            "bovinos": [b.to_dict() for b in bovinos],
        }

    # ── BOVINO: detalle completo ──────────────────────────────────────────

    # GET /api/dueno/bovinos/{bovino_id}
    @staticmethod
    def detalle_bovino(db: Session, bovino_id: str, dueno_id: str):
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: bovino '{bovino_id}' no existe")
        # BOLA: verificar que el bovino pertenece a un rancho del dueno
        rancho = db.query(Rancho).filter(
            Rancho.id == bovino.rancho_id, Rancho.dueno_id == dueno_id
        ).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Acceso denegado: este bovino no pertenece a tus ranchos")

        registros = (
            db.query(RegistroSintoma)
            .filter(RegistroSintoma.bovino_id == bovino_id)
            .order_by(RegistroSintoma.registrado_en.desc())
            .all()
        )
        registros_con_prediccion = []
        for r in registros:
            item = r.to_dict()
            if r.prediccion:
                item["prediccion"] = r.prediccion.to_dict()
            registros_con_prediccion.append(item)

        alertas = (
            db.query(Alerta)
            .filter(Alerta.bovino_id == bovino_id)
            .order_by(Alerta.creado_en.desc())
            .all()
        )

        return {
            "bovino": bovino.to_dict(),
            "total_registros": len(registros),
            "total_alertas": len(alertas),
            "registros_sintomas": registros_con_prediccion,
            "alertas": [a.to_dict() for a in alertas],
        }

    # ── ESTADÍSTICAS para gráficas ────────────────────────────────────────

    # GET /api/dueno/ranchos/{rancho_id}/estadisticas
    @staticmethod
    def estadisticas_rancho(db: Session, rancho_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        bovinos = db.query(Bovino).filter(Bovino.rancho_id == rancho_id).all()
        bovino_ids = [b.id for b in bovinos]

        # ── Gráfica 1: Bovinos por categoría ──
        por_categoria = {}
        for b in bovinos:
            por_categoria[b.categoria] = por_categoria.get(b.categoria, 0) + 1

        # ── Gráfica 2: Alertas por severidad ──
        alertas_data = {"baja": 0, "media": 0, "alta": 0}
        if bovino_ids:
            alertas = db.query(Alerta).filter(Alerta.bovino_id.in_(bovino_ids)).all()
            for a in alertas:
                alertas_data[a.severidad] = alertas_data.get(a.severidad, 0) + 1

        # ── Gráfica 3: Predicciones del mes (últimos 30 días) ──
        hace_30 = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        predicciones_mes = []
        if bovino_ids:
            registros = (
                db.query(RegistroSintoma)
                .filter(
                    RegistroSintoma.bovino_id.in_(bovino_ids),
                    RegistroSintoma.registrado_en >= hace_30,
                )
                .order_by(RegistroSintoma.registrado_en.asc())
                .all()
            )
            for r in registros:
                if r.prediccion:
                    predicciones_mes.append({
                        "fecha": r.registrado_en.strftime("%Y-%m-%d"),
                        "enfermedad": r.prediccion.enfermedad,
                        "severidad": r.prediccion.severidad,
                        "bovino": r.bovino.nombre if r.bovino else None,
                    })

        return {
            "rancho": rancho.nombre,
            "grafica_bovinos_por_categoria": por_categoria,
            "grafica_alertas_por_severidad": alertas_data,
            "grafica_predicciones_mes": predicciones_mes,
        }

    # ── VETERINARIOS ──────────────────────────────────────────────────────

    # GET /api/dueno/veterinarios  →  todos los vets del dueño
    @staticmethod
    def listar_todos_veterinarios(db: Session, dueno_id: str):
        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()
        vistos = set()
        vets = []
        for rancho in ranchos:
            for vet in rancho.veterinarios:
                if vet.id not in vistos:
                    vistos.add(vet.id)
                    d = vet.to_dict()
                    d["ranchos"] = [{"id": r.id, "nombre": r.nombre} for r in vet.ranchos]
                    vets.append(d)
        return {"total": len(vets), "veterinarios": vets}

    # POST /api/dueno/veterinarios  →  crear veterinario (sin rancho aún)
    @staticmethod
    def crear_veterinario(db: Session, data: VeterinarioCreate):
        vet = Veterinario(
            nombre=data.nombre,
            telefono=data.telefono,
            ubicacion=data.ubicacion,
            lugar=data.lugar,
            notas=data.notas,
        )
        db.add(vet)
        db.commit()
        db.refresh(vet)
        return vet.to_dict(include_ranchos=True)

    # POST /api/dueno/ranchos/{rancho_id}/veterinarios/{vet_id}  →  asociar
    @staticmethod
    def asociar_veterinario(db: Session, rancho_id: str, vet_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        vet = db.query(Veterinario).filter(Veterinario.id == vet_id).first()
        if not vet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: veterinario '{vet_id}' no existe")

        if vet in rancho.veterinarios:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="El veterinario ya está asociado a este rancho")

        rancho.veterinarios.append(vet)
        db.commit()
        return {"mensaje": f"Veterinario '{vet.nombre}' asociado a rancho '{rancho.nombre}'",
                "veterinario": vet.to_dict(include_ranchos=True)}

    # GET /api/dueno/ranchos/{rancho_id}/veterinarios
    @staticmethod
    def listar_veterinarios(db: Session, rancho_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        vets = rancho.veterinarios
        return {"rancho": rancho.nombre, "total": len(vets), "veterinarios": [v.to_dict() for v in vets]}

    # DELETE /api/dueno/ranchos/{rancho_id}/veterinarios/{vet_id}  →  quitar asociación
    @staticmethod
    def quitar_veterinario(db: Session, rancho_id: str, vet_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        vet = db.query(Veterinario).filter(Veterinario.id == vet_id).first()
        if not vet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: veterinario '{vet_id}' no existe")

        if vet not in rancho.veterinarios:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="El veterinario no está asociado a este rancho")

        rancho.veterinarios.remove(vet)
        db.commit()
        return {"mensaje": f"Veterinario '{vet.nombre}' desvinculado de rancho '{rancho.nombre}'"}

    # PUT /api/dueno/veterinarios/{vet_id}
    @staticmethod
    def actualizar_veterinario(db: Session, vet_id: str, dueno_id: str, data: VeterinarioUpdate):
        vet = db.query(Veterinario).filter(Veterinario.id == vet_id).first()
        if not vet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: veterinario '{vet_id}' no existe")
        # BOLA: solo el dueno que tenga este vet en alguno de sus ranchos puede editarlo
        ranchos_dueno = {r.id for r in db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()}
        vet_ranchos = {r.id for r in vet.ranchos}
        if not ranchos_dueno.intersection(vet_ranchos):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Acceso denegado: este veterinario no esta asociado a tus ranchos")

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No se enviaron campos para actualizar")

        for campo, valor in updates.items():
            setattr(vet, campo, valor)

        db.commit()
        db.refresh(vet)
        return vet.to_dict(include_ranchos=True)

    # DELETE /api/dueno/veterinarios/{vet_id}  →  eliminar veterinario completamente
    @staticmethod
    def eliminar_veterinario(db: Session, vet_id: str, dueno_id: str):
        vet = db.query(Veterinario).filter(Veterinario.id == vet_id).first()
        if not vet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: veterinario '{vet_id}' no existe")
        # BOLA: solo el dueno que tenga este vet en alguno de sus ranchos puede eliminarlo
        ranchos_dueno = {r.id for r in db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()}
        vet_ranchos = {r.id for r in vet.ranchos}
        if not ranchos_dueno.intersection(vet_ranchos):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Acceso denegado: este veterinario no esta asociado a tus ranchos")

        nombre = vet.nombre
        db.delete(vet)
        db.commit()
        return {"mensaje": f"Veterinario '{nombre}' eliminado correctamente"}

    # ── VISTAS GLOBALES (todos los ranchos del dueño) ────────────────────

    # GET /api/dueno/bovinos
    @staticmethod
    def todos_bovinos(db: Session, dueno_id: str, limit: int = 50, offset: int = 0):
        """Todos los bovinos de todos los ranchos del dueño, con rancho y ganadero."""
        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()
        if not ranchos:
            return {"total_ranchos": 0, "total_bovinos": 0, "bovinos": []}

        rancho_map = {r.id: r.nombre for r in ranchos}
        rancho_ids = list(rancho_map.keys())

        base_query = db.query(Bovino).filter(Bovino.rancho_id.in_(rancho_ids))
        total_bovinos = base_query.count()
        bovinos = base_query.offset(offset).limit(limit).all()

        ganadero_ids = list({b.ganadero_id for b in bovinos})
        ganadero_map = {}
        if ganadero_ids:
            ganaderos = db.query(Usuario).filter(Usuario.id.in_(ganadero_ids)).all()
            ganadero_map = {g.id: g.nombre for g in ganaderos}

        resultado = []
        for b in bovinos:
            item = b.to_dict()
            item["rancho_nombre"] = rancho_map.get(b.rancho_id)
            item["ganadero_nombre"] = ganadero_map.get(b.ganadero_id)
            resultado.append(item)

        return {
            "total_ranchos": len(ranchos),
            "total_bovinos": total_bovinos,
            "limit": limit,
            "offset": offset,
            "bovinos": resultado,
        }

    # GET /api/dueno/predicciones
    @staticmethod
    def todas_predicciones(db: Session, dueno_id: str):
        """Todas las predicciones ML de los bovinos de sus ranchos."""
        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()
        if not ranchos:
            return {"total": 0, "predicciones": []}

        rancho_map = {r.id: r.nombre for r in ranchos}
        rancho_ids = list(rancho_map.keys())

        bovinos = db.query(Bovino).filter(Bovino.rancho_id.in_(rancho_ids)).all()
        if not bovinos:
            return {"total": 0, "predicciones": []}

        bovino_map = {b.id: b for b in bovinos}
        bovino_ids = list(bovino_map.keys())

        ganadero_ids = list({b.ganadero_id for b in bovinos})
        ganadero_map = {}
        if ganadero_ids:
            ganaderos = db.query(Usuario).filter(Usuario.id.in_(ganadero_ids)).all()
            ganadero_map = {g.id: g.nombre for g in ganaderos}

        registros = (
            db.query(RegistroSintoma)
            .filter(RegistroSintoma.bovino_id.in_(bovino_ids))
            .order_by(RegistroSintoma.registrado_en.desc())
            .all()
        )

        resultado = []
        for r in registros:
            if not r.prediccion:
                continue
            bovino = bovino_map.get(r.bovino_id)
            item = r.prediccion.to_dict()
            item["registrado_en"] = r.registrado_en.isoformat() if r.registrado_en else None
            item["texto_libre"] = r.texto_libre
            item["bovino_id"] = r.bovino_id
            item["bovino_nombre"] = bovino.nombre if bovino else None
            item["ganadero_nombre"] = ganadero_map.get(bovino.ganadero_id) if bovino else None
            item["rancho_nombre"] = rancho_map.get(bovino.rancho_id) if bovino else None
            resultado.append(item)

        return {"total": len(resultado), "predicciones": resultado}

    # GET /api/dueno/historial
    @staticmethod
    def historial_bovinos(db: Session, dueno_id: str):
        """
        Historial de registros de síntomas de cada bovino,
        agrupados por rancho → ganadero → bovino.
        """
        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()
        if not ranchos:
            return {"ranchos": []}

        rancho_ids = [r.id for r in ranchos]
        bovinos = db.query(Bovino).filter(Bovino.rancho_id.in_(rancho_ids)).all()

        ganadero_ids = list({b.ganadero_id for b in bovinos})
        ganadero_map = {}
        if ganadero_ids:
            ganaderos = db.query(Usuario).filter(Usuario.id.in_(ganadero_ids)).all()
            ganadero_map = {g.id: g for g in ganaderos}

        bovino_ids = [b.id for b in bovinos]
        registros = (
            db.query(RegistroSintoma)
            .filter(RegistroSintoma.bovino_id.in_(bovino_ids))
            .order_by(RegistroSintoma.registrado_en.desc())
            .all()
        )

        # registros indexados por bovino_id
        registros_por_bovino: dict = {}
        for r in registros:
            registros_por_bovino.setdefault(r.bovino_id, []).append(r)

        # bovinos indexados por rancho_id
        bovinos_por_rancho: dict = {}
        for b in bovinos:
            bovinos_por_rancho.setdefault(b.rancho_id, []).append(b)

        resultado = []
        for rancho in ranchos:
            bovinos_rancho = bovinos_por_rancho.get(rancho.id, [])
            # agrupar por ganadero
            por_ganadero: dict = {}
            for b in bovinos_rancho:
                por_ganadero.setdefault(b.ganadero_id, []).append(b)

            ganaderos_lista = []
            for gid, bov_list in por_ganadero.items():
                ganadero = ganadero_map.get(gid)
                bovinos_detalle = []
                for b in bov_list:
                    regs = registros_por_bovino.get(b.id, [])
                    bovinos_detalle.append({
                        **b.to_dict(),
                        "total_registros": len(regs),
                        "registros": [
                            {**r.to_dict(include_prediccion=True)}
                            for r in regs
                        ],
                    })
                ganaderos_lista.append({
                    "ganadero_id": gid,
                    "ganadero_nombre": ganadero.nombre if ganadero else None,
                    "total_bovinos": len(bov_list),
                    "bovinos": bovinos_detalle,
                })

            resultado.append({
                "rancho_id": rancho.id,
                "rancho_nombre": rancho.nombre,
                "total_ganaderos": len(ganaderos_lista),
                "ganaderos": ganaderos_lista,
            })

        return {"total_ranchos": len(resultado), "ranchos": resultado}

    # GET /api/dueno/reportes
    @staticmethod
    def reportes(db: Session, dueno_id: str):
        """
        Gráficas generales (todos los ranchos del dueño) + detalle por bovino.
        """
        ranchos = db.query(Rancho).filter(Rancho.dueno_id == dueno_id).all()
        if not ranchos:
            return {
                "general": {
                    "bovinos_por_categoria": {},
                    "alertas_por_severidad": {"baja": 0, "media": 0, "alta": 0},
                    "predicciones_por_mes": [],
                },
                "por_bovino": [],
            }

        rancho_map = {r.id: r.nombre for r in ranchos}
        rancho_ids = list(rancho_map.keys())
        bovinos = db.query(Bovino).filter(Bovino.rancho_id.in_(rancho_ids)).all()
        bovino_ids = [b.id for b in bovinos]
        bovino_map = {b.id: b for b in bovinos}

        ganadero_ids = list({b.ganadero_id for b in bovinos})
        ganadero_map = {}
        if ganadero_ids:
            ganaderos = db.query(Usuario).filter(Usuario.id.in_(ganadero_ids)).all()
            ganadero_map = {g.id: g.nombre for g in ganaderos}

        # ── General: bovinos por categoría ──
        por_categoria: dict = {}
        for b in bovinos:
            por_categoria[b.categoria] = por_categoria.get(b.categoria, 0) + 1

        # ── General: alertas por severidad ──
        alertas_data = {"baja": 0, "media": 0, "alta": 0}
        if bovino_ids:
            alertas = db.query(Alerta).filter(Alerta.bovino_id.in_(bovino_ids)).all()
            for a in alertas:
                alertas_data[a.severidad] = alertas_data.get(a.severidad, 0) + 1

        # ── General: predicciones del último mes ──
        hace_30 = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        predicciones_mes = []
        registros_all = []
        if bovino_ids:
            registros_all = (
                db.query(RegistroSintoma)
                .filter(RegistroSintoma.bovino_id.in_(bovino_ids))
                .order_by(RegistroSintoma.registrado_en.asc())
                .all()
            )
            for r in registros_all:
                if r.prediccion and r.registrado_en and r.registrado_en >= hace_30:
                    bovino = bovino_map.get(r.bovino_id)
                    predicciones_mes.append({
                        "fecha": r.registrado_en.strftime("%Y-%m-%d"),
                        "enfermedad": r.prediccion.enfermedad,
                        "severidad": r.prediccion.severidad,
                        "bovino_nombre": bovino.nombre if bovino else None,
                        "ganadero_nombre": ganadero_map.get(bovino.ganadero_id) if bovino else None,
                        "rancho_nombre": rancho_map.get(bovino.rancho_id) if bovino else None,
                    })

        # ── Por bovino: historial de predicciones + severidad ──
        registros_por_bovino: dict = {}
        for r in registros_all:
            registros_por_bovino.setdefault(r.bovino_id, []).append(r)

        por_bovino = []
        for b in bovinos:
            regs = registros_por_bovino.get(b.id, [])
            preds = [r.prediccion for r in regs if r.prediccion]
            sev_count = {"leve": 0, "moderada": 0, "alta": 0}
            for p in preds:
                sev_count[p.severidad] = sev_count.get(p.severidad, 0) + 1
            por_bovino.append({
                "bovino_id": b.id,
                "bovino_nombre": b.nombre,
                "categoria": b.categoria,
                "ganadero_nombre": ganadero_map.get(b.ganadero_id),
                "rancho_nombre": rancho_map.get(b.rancho_id),
                "total_registros": len(regs),
                "total_predicciones": len(preds),
                "severidad_distribucion": sev_count,
                "predicciones": [
                    {
                        "fecha": r.registrado_en.strftime("%Y-%m-%d") if r.registrado_en else None,
                        "enfermedad": r.prediccion.enfermedad,
                        "confianza": r.prediccion.confianza,
                        "severidad": r.prediccion.severidad,
                    }
                    for r in regs if r.prediccion
                ],
            })

        return {
            "general": {
                "bovinos_por_categoria": por_categoria,
                "alertas_por_severidad": alertas_data,
                "predicciones_por_mes": predicciones_mes,
            },
            "por_bovino": por_bovino,
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
