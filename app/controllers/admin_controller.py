from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Usuario, Rancho, Bovino, AuditoriaLog, ConfiguracionSistema
from app.schemas.general_schema import UsuarioUpdate, ConfiguracionUpdate


class AdminController:
    """
    Controlador del rol Administrador. Endpoints:
    1. Perfil del admin
    2. Listar usuarios (filtro opcional por rol)
    3. Actualizar usuario
    4. Eliminar usuario
    5. Listar ranchos
    6. Estado del sistema (estadisticas + logs de auditoria)
    7. Actualizar configuracion del sistema
    """

    # 1. GET /api/admin/{admin_id}
    @staticmethod
    def perfil(db: Session, admin_id: str):
        admin = db.query(Usuario).filter(Usuario.id == admin_id, Usuario.rol == "admin").first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el administrador con id '{admin_id}' no existe",
            )
        return admin.to_dict()

    # 2. GET /api/admin/usuarios
    @staticmethod
    def listar_usuarios(db: Session, rol: str = None):
        if rol is not None and rol not in ("ganadero", "dueno", "admin"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Solicitud invalida: el rol '{rol}' no es valido. "
                       f"Usa 'ganadero', 'dueno' o 'admin'",
            )

        query = db.query(Usuario)
        if rol is not None:
            query = query.filter(Usuario.rol == rol)

        usuarios = query.order_by(Usuario.creado_en.desc()).all()
        return {"total": len(usuarios), "usuarios": [u.to_dict() for u in usuarios]}

    # 3. PUT /api/admin/usuarios/{usuario_id}
    @staticmethod
    def actualizar_usuario(db: Session, usuario_id: str, data: UsuarioUpdate, admin_actual: Usuario):
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el usuario con id '{usuario_id}' no existe",
            )

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitud invalida: no se enviaron campos para actualizar",
            )

        if usuario.rol == "admin" and updates.get("activo") is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: no se puede desactivar a un administrador",
            )

        for campo, valor in updates.items():
            setattr(usuario, campo, valor)

        log = AuditoriaLog(
            usuario_id=admin_actual.id,
            accion="actualizo_usuario",
            entidad_afectada=f"usuarios:{usuario.id}",
            detalle=updates,
        )
        db.add(log)

        db.commit()
        db.refresh(usuario)
        return usuario.to_dict()

    # 4. DELETE /api/admin/usuarios/{usuario_id}
    @staticmethod
    def eliminar_usuario(db: Session, usuario_id: str, admin_actual: Usuario):
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el usuario con id '{usuario_id}' no existe",
            )

        if usuario.rol == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: no se puede eliminar a un administrador",
            )

        if usuario.id == admin_actual.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: no puedes eliminar tu propia cuenta",
            )

        nombre = usuario.nombre
        log = AuditoriaLog(
            usuario_id=admin_actual.id,
            accion="elimino_usuario",
            entidad_afectada=f"usuarios:{usuario.id}",
            detalle={"nombre": nombre, "email": usuario.email, "rol": usuario.rol},
        )
        db.add(log)
        db.delete(usuario)
        db.commit()
        return {"mensaje": f"Usuario '{nombre}' eliminado correctamente"}

    # 5. GET /api/admin/ranchos
    @staticmethod
    def listar_ranchos(db: Session):
        ranchos = db.query(Rancho).all()
        return {"total": len(ranchos), "ranchos": [r.to_dict() for r in ranchos]}

    # 6. GET /api/admin/sistema/estado
    @staticmethod
    def estado_sistema(db: Session):
        total_usuarios = db.query(Usuario).count()
        total_ranchos = db.query(Rancho).count()
        total_bovinos = db.query(Bovino).count()

        logs = (
            db.query(AuditoriaLog)
            .order_by(AuditoriaLog.creado_en.desc())
            .limit(50)
            .all()
        )

        return {
            "estado_general": "operativo",
            "estadisticas": {
                "total_usuarios": total_usuarios,
                "total_ranchos": total_ranchos,
                "total_bovinos": total_bovinos,
            },
            "logs_auditoria": {
                "total": len(logs),
                "detalle": [l.to_dict() for l in logs],
            },
            "modelos_ml": {
                "RandomForest": "activo",
                "IsolationForest": "activo",
                "CatBoost": "activo",
                "spaCy_NLP": "activo",
                "DistilBETO": "activo",
            },
        }

    # 7. PUT /api/admin/configuracion/{clave}
    @staticmethod
    def actualizar_configuracion(db: Session, clave: str, data: ConfiguracionUpdate, admin_actual: Usuario):
        config = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: no existe configuracion con clave '{clave}'",
            )

        config.valor = data.valor
        config.actualizado_por = admin_actual.id

        log = AuditoriaLog(
            usuario_id=admin_actual.id,
            accion="actualizo_configuracion",
            entidad_afectada=f"configuracion_sistema:{clave}",
            detalle={"nuevo_valor": data.valor},
        )
        db.add(log)

        db.commit()
        db.refresh(config)
        return config.to_dict()
