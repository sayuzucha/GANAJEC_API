from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import datetime

from app.models import Usuario, Bovino, Rancho, RegistroSintoma, Prediccion, Alerta
from app.schemas.ganadero_schema import BovinoCreate, BovinoUpdate, RegistroSintomaCreate, AlertaUpdate, UnirseRanchoRequest, GanaderoPerfilUpdate
from app.core.security import hash_password
from app.ml import predictor
from app.ml import nlp
from app.services import fcm_service


class GanaderoController:
    """
    Controlador del rol Ganadero. Endpoints:
    1. Perfil del ganadero
    2. Listar bovinos a su cargo
    3. Detalle de un bovino
    4. Registrar nuevo bovino
    5. Actualizar bovino
    6. Eliminar bovino
    7. Predicciones de un bovino (via registros_sintomas -> prediccion)
    8. Registrar nota de campo / sintoma
    9-10. Alertas: listar y marcar leida
    """

    # 1. GET /api/ganadero/{ganadero_id}
    @staticmethod
    def perfil(db: Session, ganadero_id: str):
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el ganadero con id '{ganadero_id}' no existe",
            )

        total_bovinos = db.query(Bovino).filter(Bovino.ganadero_id == ganadero_id).count()
        rancho = db.query(Rancho).filter(Rancho.id == ganadero.rancho_id).first() if ganadero.rancho_id else None
        return {
            **ganadero.to_dict(),
            "total_bovinos": total_bovinos,
            "rancho": rancho.to_dict(include_dueno_nombre=True) if rancho else None,
        }

    # 2. GET /api/ganadero/{ganadero_id}/bovinos
    @staticmethod
    def listar_bovinos(db: Session, ganadero_id: str):
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el ganadero con id '{ganadero_id}' no existe",
            )

        bovinos = db.query(Bovino).filter(Bovino.ganadero_id == ganadero_id).all()
        return {
            "ganadero": ganadero.nombre,
            "total": len(bovinos),
            "bovinos": [b.to_dict() for b in bovinos],
        }

    # 3. GET /api/ganadero/bovinos/{bovino_id}
    @staticmethod
    def obtener_bovino(db: Session, bovino_id: str):
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el bovino con id '{bovino_id}' no existe",
            )
        return bovino.to_dict()

    # 4. POST /api/ganadero/bovinos
    @staticmethod
    def crear_bovino(db: Session, ganadero_id: str, data: BovinoCreate):
        ganadero = db.query(Usuario).filter(Usuario.id == ganadero_id).first()
        if not ganadero or not ganadero.rancho_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ganadero no está asignado a ningún rancho. Únete a un rancho primero.",
            )

        rancho = db.query(Rancho).filter(Rancho.id == ganadero.rancho_id).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No encontrado: el rancho asignado al ganadero no existe",
            )

        if data.id_externo:
            duplicado = db.query(Bovino).filter(Bovino.id_externo == data.id_externo).first()
            if duplicado:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflicto: ya existe un bovino con el id externo '{data.id_externo}'",
                )

        nuevo = Bovino(
            rancho_id=ganadero.rancho_id,
            ganadero_id=ganadero_id,
            nombre=data.nombre,
            raza=data.raza,
            sexo=data.sexo,
            categoria=data.categoria,
            proposito=data.proposito,
            fecha_nacimiento=data.fecha_nacimiento,
            peso_kg=data.peso_kg,
            id_externo=data.id_externo,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo.to_dict()

    # 5. PUT /api/ganadero/bovinos/{bovino_id}
    @staticmethod
    def actualizar_bovino(db: Session, bovino_id: str, data: BovinoUpdate):
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el bovino con id '{bovino_id}' no existe",
            )

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitud invalida: no se enviaron campos para actualizar",
            )

        for campo, valor in updates.items():
            setattr(bovino, campo, valor)

        db.commit()
        db.refresh(bovino)
        return bovino.to_dict()

    # 6. DELETE /api/ganadero/bovinos/{bovino_id}
    @staticmethod
    def eliminar_bovino(db: Session, bovino_id: str):
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el bovino con id '{bovino_id}' no existe",
            )

        nombre = bovino.nombre
        db.delete(bovino)
        db.commit()
        return {"mensaje": f"Bovino '{nombre}' eliminado correctamente"}

    # 7. GET /api/ganadero/bovinos/{bovino_id}/predicciones
    @staticmethod
    def obtener_predicciones(db: Session, bovino_id: str):
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el bovino con id '{bovino_id}' no existe",
            )

        registros = (
            db.query(RegistroSintoma)
            .filter(RegistroSintoma.bovino_id == bovino_id)
            .order_by(RegistroSintoma.registrado_en.desc())
            .all()
        )

        predicciones = []
        for r in registros:
            if r.prediccion:
                item = r.prediccion.to_dict()
                item["registro"] = {
                    "texto_libre": r.texto_libre,
                    "registrado_en": r.registrado_en.isoformat() if r.registrado_en else None,
                }
                predicciones.append(item)

        return {
            "bovino_id": bovino_id,
            "nombre": bovino.nombre,
            "total_predicciones": len(predicciones),
            "predicciones": predicciones,
        }

    # 7b. GET /api/ganadero/{ganadero_id}/predicciones
    @staticmethod
    def listar_predicciones(db: Session, ganadero_id: str):
        """
        Historial global: junta las predicciones de TODOS los bovinos
        a cargo del ganadero, ordenadas de la mas reciente a la mas
        antigua, junto con un resumen rapido (severidad alta, sin
        anomalias, total del mes).
        """
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el ganadero con id '{ganadero_id}' no existe",
            )

        registros = (
            db.query(RegistroSintoma)
            .filter(RegistroSintoma.ganadero_id == ganadero_id)
            .order_by(RegistroSintoma.registrado_en.desc())
            .all()
        )

        predicciones = []
        severidad_alta = 0
        sin_anomalias = 0
        total_este_mes = 0

        hoy = datetime.date.today()

        for r in registros:
            if not r.prediccion:
                continue

            item = r.prediccion.to_dict()
            item["registro"] = {
                "texto_libre": r.texto_libre,
                "registrado_en": r.registrado_en.isoformat() if r.registrado_en else None,
            }
            item["bovino"] = {
                "id": r.bovino.id,
                "nombre": r.bovino.nombre,
                "raza": r.bovino.raza,
                "categoria": r.bovino.categoria,
            }
            predicciones.append(item)

            if item["severidad"] == "alta":
                severidad_alta += 1
            if item["enfermedad"] == predictor.TRADUCCION_ENFERMEDADES["Healthy"]:
                sin_anomalias += 1
            if r.registrado_en and r.registrado_en.year == hoy.year and r.registrado_en.month == hoy.month:
                total_este_mes += 1

        return {
            "ganadero": ganadero.nombre,
            "total": len(predicciones),
            "estadisticas": {
                "severidad_alta": severidad_alta,
                "sin_anomalias": sin_anomalias,
                "total_este_mes": total_este_mes,
            },
            "predicciones": predicciones,
        }

    # 8. POST /api/ganadero/registros-sintomas
    @staticmethod
    def registrar_sintoma(db: Session, ganadero_id: str, data: RegistroSintomaCreate):
        # Cargar el ganadero para tener su fcm_token al final
        ganadero_obj = db.query(Usuario).filter(Usuario.id == ganadero_id).first()
        bovino = db.query(Bovino).filter(Bovino.id == data.bovino_id).first()
        if not bovino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el bovino con id '{data.bovino_id}' no existe",
            )

        # ── 0. NLP: extraer sintomas del texto libre (spaCy + reglas) ──
        analisis_nlp = nlp.analizar_texto(data.texto_libre)
        sintomas_nlp = analisis_nlp["sintomas_detectados"]

        # Union entre los sintomas que el ganadero selecciono manualmente
        # y los que el NLP detecto automaticamente en el texto.
        sintomas_usuario = data.sintomas_seleccionados or []
        sintomas_fusionados = list(dict.fromkeys([*sintomas_usuario, *sintomas_nlp]))

        nuevo = RegistroSintoma(
            bovino_id=data.bovino_id,
            ganadero_id=ganadero_id,
            texto_libre=data.texto_libre,
            temperatura=data.temperatura,
            produccion_leche=data.produccion_leche,
            frecuencia_cardiaca=data.frecuencia_cardiaca,
            frecuencia_respiratoria=data.frecuencia_respiratoria,
            condicion_corporal=data.condicion_corporal,
            consumo_alimento_kg=data.consumo_alimento_kg,
            consumo_agua_l=data.consumo_agua_l,
            sintomas_seleccionados=sintomas_fusionados or None,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)

        # ── Calcular edad del bovino en meses (para el modelo ML) ──
        edad_meses = None
        if bovino.fecha_nacimiento:
            hoy = datetime.date.today()
            edad_meses = (hoy.year - bovino.fecha_nacimiento.year) * 12 + \
                         (hoy.month - bovino.fecha_nacimiento.month)

        datos_ml = {
            # ── vitales (originales) ──
            "edad_meses":           edad_meses,
            "peso_kg":              bovino.peso_kg,
            "temperatura":          nuevo.temperatura,
            "frecuencia_cardiaca":  nuevo.frecuencia_cardiaca,
            "frecuencia_respiratoria": nuevo.frecuencia_respiratoria,
            "produccion_leche":     nuevo.produccion_leche,
            "condicion_corporal":   nuevo.condicion_corporal,
            "consumo_alimento_kg":  nuevo.consumo_alimento_kg,
            "consumo_agua_l":       nuevo.consumo_agua_l,
            # ── nuevos campos opcionales (mejoran el modelo) ──
            "parity":                      data.parity,
            "dias_en_leche":               data.dias_en_leche,
            "produccion_semana_anterior":  data.produccion_semana_anterior,
            "temperatura_ambiente":        data.temperatura_ambiente,
            "vacuna_fmdv":                 data.vacuna_fmdv,
            "vacuna_brucelosis":           data.vacuna_brucelosis,
            "vacuna_septicemia":           data.vacuna_septicemia,
            "vacuna_carbon_sint":          data.vacuna_carbon_sint,
            "vacuna_antrax":               data.vacuna_antrax,
        }

        # ── 1. Random Forest: predecir enfermedad ──────────────────
        resultado_rf = predictor.predecir_enfermedad(datos_ml)

        # Calcular que tan bien los sintomas detectados por NLP
        # concuerdan con la enfermedad predicha por Random Forest
        analisis_nlp["concordancia_con_prediccion"] = nlp.calcular_concordancia(
            sintomas_nlp, resultado_rf["enfermedad_codigo"]
        )

        features_completo = {
            **resultado_rf["features_nlp"],
            "analisis_texto": analisis_nlp,
        }

        prediccion = Prediccion(
            registro_id=nuevo.id,
            enfermedad=resultado_rf["enfermedad"],
            confianza=resultado_rf["confianza"],
            severidad=resultado_rf["severidad"],
            features_nlp=features_completo,
        )
        db.add(prediccion)

        # ── 2. Isolation Forest: detectar anomalia productiva ──────
        resultado_iso = predictor.detectar_anomalia(datos_ml)
        alerta_creada = None
        if resultado_iso["es_anomalia"]:
            # Severidad de la alerta segun que tan fuera de lo normal esta
            if resultado_iso["score"] < -0.15:
                severidad_alerta = "alta"
            elif resultado_iso["score"] < -0.08:
                severidad_alerta = "media"
            else:
                severidad_alerta = "baja"

            alerta_creada = Alerta(
                bovino_id=bovino.id,
                ganadero_id=ganadero_id,
                tipo="productiva",
                severidad=severidad_alerta,
                mensaje=(
                    f"Isolation Forest detecto valores productivos fuera de lo normal "
                    f"para '{bovino.nombre}' (score={resultado_iso['score']})"
                ),
                leida=False,
            )
            db.add(alerta_creada)

        # ── 3. Si la prediccion no es "Healthy" y la severidad es alta,
        #       tambien generamos una alerta clinica ─────────────────
        alerta_clinica = None
        if resultado_rf["enfermedad_codigo"] != "Healthy" and resultado_rf["severidad"] == "alta":
            alerta_clinica = Alerta(
                bovino_id=bovino.id,
                ganadero_id=ganadero_id,
                tipo="clinica",
                severidad="alta",
                mensaje=(
                    f"Random Forest detecto posible '{resultado_rf['enfermedad']}' "
                    f"en '{bovino.nombre}' con {resultado_rf['confianza']*100:.0f}% de confianza"
                ),
                leida=False,
            )
            db.add(alerta_clinica)

        db.commit()
        db.refresh(nuevo)
        db.refresh(prediccion)

        # ── 4. Notificaciones push via Firebase FCM ────────────────
        # Solo se envían si el ganadero tiene un fcm_token registrado.
        # Los errores de FCM son silenciosos (no rompen la respuesta).
        fcm_token = ganadero_obj.fcm_token if ganadero_obj else None
        if fcm_token:
            if alerta_creada:
                fcm_service.notify_alerta_productiva(
                    fcm_token=fcm_token,
                    bovino_nombre=bovino.nombre,
                    score=resultado_iso["score"],
                )
            if alerta_clinica:
                fcm_service.notify_alerta_clinica(
                    fcm_token=fcm_token,
                    bovino_nombre=bovino.nombre,
                    enfermedad=resultado_rf["enfermedad"],
                    confianza=resultado_rf["confianza"],
                )

        respuesta = {
            "mensaje": "Registro guardado y procesado por los modelos de IA",
            "registro": nuevo.to_dict(),
            "prediccion": prediccion.to_dict(),
            "anomalia_productiva": resultado_iso,
        }
        if alerta_creada:
            respuesta["alerta_productiva"] = alerta_creada.to_dict()
        if alerta_clinica:
            respuesta["alerta_clinica"] = alerta_clinica.to_dict()

        return respuesta

    # 9b. POST /api/ganadero/unirse-rancho
    @staticmethod
    def unirse_rancho(db: Session, ganadero_id: str, data: UnirseRanchoRequest):
        # Buscar rancho por código (case-insensitive: normalizamos a mayúsculas)
        codigo = data.codigo_invitacion.upper().strip()
        rancho = db.query(Rancho).filter(Rancho.codigo_invitacion == codigo).first()
        if not rancho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código inválido: no existe ningún rancho con ese código de invitación",
            )

        ganadero = db.query(Usuario).filter(Usuario.id == ganadero_id).first()

        # Verificar que no esté ya asignado al mismo rancho
        if ganadero.rancho_id == rancho.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto: ya estás asignado al rancho '{rancho.nombre}'",
            )

        # Asignar directamente (reemplaza si tenía otro rancho)
        ganadero.rancho_id = rancho.id
        db.commit()
        db.refresh(ganadero)

        return {
            "mensaje": f"Te uniste al rancho '{rancho.nombre}' exitosamente",
            "rancho": rancho.to_dict(),
        }

    @staticmethod
    def listar_veterinarios(db: Session, ganadero_id: str):
        """Devuelve los veterinarios del rancho al que pertenece el ganadero."""
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No encontrado: ganadero no existe")

        if not ganadero.rancho_id:
            return {"rancho": None, "total": 0, "veterinarios": []}

        rancho = db.query(Rancho).filter(Rancho.id == ganadero.rancho_id).first()
        if not rancho:
            return {"rancho": None, "total": 0, "veterinarios": []}

        vets = rancho.veterinarios
        return {
            "rancho": rancho.nombre,
            "total": len(vets),
            "veterinarios": [v.to_dict() for v in vets],
        }

    # 9. GET /api/ganadero/alertas
    @staticmethod
    def listar_alertas(db: Session, ganadero_id: str, bovino_id: str = None,
                          limit: int = 50, offset: int = 0):
        query = db.query(Alerta).filter(Alerta.ganadero_id == ganadero_id)

        if bovino_id is not None:
            bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
            if not bovino:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No encontrado: el bovino con id '{bovino_id}' no existe",
                )
            query = query.filter(Alerta.bovino_id == bovino_id)

        total = query.count()
        alertas = query.order_by(Alerta.creado_en.desc()).offset(offset).limit(limit).all()
        return {"total": total, "limit": limit, "offset": offset, "alertas": [a.to_dict() for a in alertas]}

    # 10. PATCH /api/ganadero/alertas/{alerta_id}
    @staticmethod
    def marcar_alerta(db: Session, alerta_id: str, ganadero_id: str, data: AlertaUpdate):
        alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: la alerta con id '{alerta_id}' no existe",
            )
        # BOLA: solo el ganadero dueno de la alerta puede marcarla
        if alerta.ganadero_id != ganadero_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: esta alerta no te pertenece",
            )

        alerta.leida = data.leida
        db.commit()
        db.refresh(alerta)
        return alerta.to_dict()

    # 11. GET /api/ganadero/bovinos/{bovino_id}/graficas
    @staticmethod
    def graficas_bovino(db: Session, bovino_id: str):
        """
        Series de tiempo del bovino, ordenadas por fecha ascendente.
        Cada lista contiene {fecha, valor} — los None se omiten para
        que la app no dibuje puntos vacíos en la gráfica.
        """
        bovino = db.query(Bovino).filter(Bovino.id == bovino_id).first()
        if not bovino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el bovino con id '{bovino_id}' no existe",
            )

        registros = (
            db.query(RegistroSintoma)
            .filter(RegistroSintoma.bovino_id == bovino_id)
            .order_by(RegistroSintoma.registrado_en.asc())
            .all()
        )

        temperatura, leche, alimento, agua, fc, fr, cc = [], [], [], [], [], [], []

        for r in registros:
            fecha = r.registrado_en.strftime("%Y-%m-%d") if r.registrado_en else None
            if not fecha:
                continue
            if r.temperatura        is not None: temperatura.append({"fecha": fecha, "valor": r.temperatura})
            if r.produccion_leche   is not None: leche.append({"fecha": fecha, "valor": r.produccion_leche})
            if r.consumo_alimento_kg is not None: alimento.append({"fecha": fecha, "valor": r.consumo_alimento_kg})
            if r.consumo_agua_l     is not None: agua.append({"fecha": fecha, "valor": r.consumo_agua_l})
            if r.frecuencia_cardiaca     is not None: fc.append({"fecha": fecha, "valor": r.frecuencia_cardiaca})
            if r.frecuencia_respiratoria is not None: fr.append({"fecha": fecha, "valor": r.frecuencia_respiratoria})
            if r.condicion_corporal      is not None: cc.append({"fecha": fecha, "valor": r.condicion_corporal})

        return {
            "bovino_id": bovino_id,
            "bovino_nombre": bovino.nombre,
            "total_registros": len(registros),
            "graficas": {
                "temperatura_corporal":    temperatura,
                "produccion_leche_litros": leche,
                "consumo_alimento_kg":     alimento,
                "consumo_agua_litros":     agua,
                "frecuencia_cardiaca":     fc,
                "frecuencia_respiratoria": fr,
                "condicion_corporal":      cc,
            },
        }

    # 12. GET /api/ganadero/colegas
    @staticmethod
    def listar_colegas(db: Session, ganadero_id: str):
        """Devuelve los otros ganaderos asignados al mismo rancho."""
        ganadero = db.query(Usuario).filter(
            Usuario.id == ganadero_id, Usuario.rol == "ganadero"
        ).first()
        if not ganadero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No encontrado: el ganadero con id '{ganadero_id}' no existe",
            )
        if not ganadero.rancho_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No estás asignado a ningún rancho",
            )

        colegas = db.query(Usuario).filter(
            Usuario.rancho_id == ganadero.rancho_id,
            Usuario.rol == "ganadero",
            Usuario.id != ganadero_id,
        ).all()

        rancho = db.query(Rancho).filter(Rancho.id == ganadero.rancho_id).first()
        return {
            "rancho": rancho.nombre if rancho else None,
            "total": len(colegas),
            "ganaderos": [g.to_dict(include_email=False) for g in colegas],
        }

    # 12. PUT /api/ganadero/{ganadero_id}/perfil
    @staticmethod
    def actualizar_perfil(db: Session, ganadero_id: str, data: GanaderoPerfilUpdate):
        """El ganadero actualiza su propio nombre, email y/o contraseña."""
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

        if "email" in updates:
            existe = db.query(Usuario).filter(
                Usuario.email == updates["email"],
                Usuario.id != ganadero_id,
            ).first()
            if existe:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflicto: ya existe un usuario con el correo '{updates['email']}'",
                )
            ganadero.email = updates["email"]

        if "nombre" in updates:
            ganadero.nombre = updates["nombre"]

        if "password" in updates:
            ganadero.password_hash = hash_password(updates["password"])

        db.commit()
        db.refresh(ganadero)
        return ganadero.to_dict()
