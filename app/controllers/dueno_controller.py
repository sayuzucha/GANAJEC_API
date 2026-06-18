from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
    def detalle_bovino(db: Session, bovino_id: str):
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: bovino '{bovino_id}' no existe")

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

    # POST /api/dueno/ranchos/{rancho_id}/veterinarios
    @staticmethod
    def agregar_veterinario(db: Session, rancho_id: str, data: VeterinarioCreate):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        vet = Veterinario(
            rancho_id=rancho_id,
            nombre=data.nombre,
            telefono=data.telefono,
            especialidad=data.especialidad,
            notas=data.notas,
        )
        db.add(vet)
        db.commit()
        db.refresh(vet)
        return vet.to_dict()

    # GET /api/dueno/ranchos/{rancho_id}/veterinarios
    @staticmethod
    def listar_veterinarios(db: Session, rancho_id: str):
        rancho = db.query(Rancho).filter(Rancho.id == rancho_id).first()
        if not rancho:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: rancho '{rancho_id}' no existe")

        vets = db.query(Veterinario).filter(Veterinario.rancho_id == rancho_id).all()
        return {"rancho": rancho.nombre, "total": len(vets), "veterinarios": [v.to_dict() for v in vets]}

    # PUT /api/dueno/veterinarios/{vet_id}
    @staticmethod
    def actualizar_veterinario(db: Session, vet_id: str, data: VeterinarioUpdate):
        vet = db.query(Veterinario).filter(Veterinario.id == vet_id).first()
        if not vet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: veterinario '{vet_id}' no existe")

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No se enviaron campos para actualizar")

        for campo, valor in updates.items():
            setattr(vet, campo, valor)

        db.commit()
        db.refresh(vet)
        return vet.to_dict()

    # DELETE /api/dueno/veterinarios/{vet_id}
    @staticmethod
    def eliminar_veterinario(db: Session, vet_id: str):
        vet = db.query(Veterinario).filter(Veterinario.id == vet_id).first()
        if not vet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No encontrado: veterinario '{vet_id}' no existe")

        nombre = vet.nombre
        db.delete(vet)
        db.commit()
        return {"mensaje": f"Veterinario '{nombre}' eliminado correctamente"}

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
