"""
Script para crear todas las tablas en MySQL y poblar datos de ejemplo.

Uso:
    python seed.py

Requiere que la base de datos exista (CREATE DATABASE ganajec_db;)
y que las credenciales en .env sean correctas.
"""
import datetime

from app.core.database import engine, SessionLocal, Base
from app.core.security import hash_password
from app.models import (
    Usuario, Rancho, Bovino, RegistroSintoma, Prediccion,
    HistorialProductivo, Alerta, Notificacion, Plan, Suscripcion,
    AuditoriaLog, ConfiguracionSistema,
)


def crear_tablas():
    print("Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente.")


def poblar_datos():
    db = SessionLocal()
    try:
        if db.query(Usuario).count() > 0:
            print("Ya existen datos, no se vuelve a poblar.")
            return

        print("Insertando datos de ejemplo...")

        # ── Usuarios ──────────────────────────────
        admin = Usuario(
            nombre="Admin GANAJEC", email="admin@ganajec.ai",
            password_hash=hash_password("admin1234"), rol="admin", activo=True,
        )
        dueno = Usuario(
            nombre="Sayuri Zuniga", email="sayuri@ganajec.ai",
            password_hash=hash_password("dueno1234"), rol="dueno", activo=True,
        )
        jared = Usuario(
            nombre="Jared Torres Morga", email="jared@ganajec.ai",
            password_hash=hash_password("ganadero1234"), rol="ganadero", activo=True,
        )
        carlos = Usuario(
            nombre="Carlos Ramos Molina", email="carlos@ganajec.ai",
            password_hash=hash_password("ganadero1234"), rol="ganadero", activo=True,
        )
        db.add_all([admin, dueno, jared, carlos])
        db.commit()

        # ── Rancho ────────────────────────────────
        rancho = Rancho(
            nombre="Rancho El Tesoro", municipio="Tuxtla Gutierrez",
            estado="Chiapas", dueno_id=dueno.id,
        )
        db.add(rancho)
        db.commit()

        # ── Bovinos ───────────────────────────────
        b1 = Bovino(
            rancho_id=rancho.id, ganadero_id=jared.id, nombre="Lupita",
            raza="Holstein", sexo="hembra", categoria="vaca", proposito="leche",
            fecha_nacimiento=datetime.date(2023, 3, 10), peso_kg=480.5, id_externo="MX-0001",
        )
        b2 = Bovino(
            rancho_id=rancho.id, ganadero_id=jared.id, nombre="Toribio",
            raza="Brahman", sexo="macho", categoria="toro", proposito="cria",
            fecha_nacimiento=datetime.date(2022, 6, 18), peso_kg=620.0, id_externo="MX-0002",
        )
        b3 = Bovino(
            rancho_id=rancho.id, ganadero_id=carlos.id, nombre="Pecas",
            raza="Angus", sexo="macho", categoria="novillo", proposito="carne",
            fecha_nacimiento=datetime.date(2024, 1, 5), peso_kg=410.2, id_externo="MX-0003",
        )
        db.add_all([b1, b2, b3])
        db.commit()

        # ── Registro de sintomas + prediccion ──────
        registro = RegistroSintoma(
            bovino_id=b3.id, ganadero_id=carlos.id,
            texto_libre="El animal presenta cojera en la pata trasera derecha desde ayer, "
                        "y se ve decaido, no quiere comer bien",
            temperatura=39.8,
            produccion_leche=None,
            frecuencia_cardiaca=88.0,
            frecuencia_respiratoria=32.0,
            condicion_corporal=2.5,
            consumo_alimento_kg=6.0,
            consumo_agua_l=30.0,
            sintomas_seleccionados=["cojera", "decaimiento", "fiebre"],
        )
        db.add(registro)
        db.commit()

        prediccion = Prediccion(
            registro_id=registro.id, enfermedad="Fiebre aftosa",
            confianza=0.87, severidad="alta",
            features_nlp={"sintomas_detectados": ["cojera", "fiebre", "decaimiento"], "modelo": "RandomForest"},
        )
        db.add(prediccion)

        # ── Historial productivo ───────────────────
        hist = HistorialProductivo(
            bovino_id=b1.id, fecha=datetime.date(2026, 6, 10),
            litros_leche=18.5, kg_alimento=12.0, ganancia_peso_kg=0.5,
            temperatura=38.4, anomalia_detectada=False,
        )
        db.add(hist)

        # ── Alerta ──────────────────────────────────
        alerta = Alerta(
            bovino_id=b3.id, ganadero_id=carlos.id, tipo="clinica",
            severidad="alta", mensaje="Isolation Forest detecto comportamiento anomalo en Pecas",
            leida=False,
        )
        db.add(alerta)
        db.commit()

        notif = Notificacion(usuario_id=carlos.id, alerta_id=alerta.id, enviada=True,
                              enviado_en=datetime.datetime.utcnow())
        db.add(notif)

        # ── Planes y suscripcion ───────────────────
        plan_basico = Plan(
            nombre="Basico", precio_mensual=499.0, limite_bovinos=20,
            permisos={"alertas": True, "predicciones": True, "reportes": False}, activo=True,
        )
        plan_premium = Plan(
            nombre="Premium", precio_mensual=999.0, limite_bovinos=100,
            permisos={"alertas": True, "predicciones": True, "reportes": True}, activo=True,
        )
        db.add_all([plan_basico, plan_premium])
        db.commit()

        suscripcion = Suscripcion(
            usuario_id=dueno.id, plan_id=plan_basico.id,
            inicio=datetime.date(2026, 6, 1), fin=None, activa=True,
        )
        db.add(suscripcion)

        # ── Configuracion del sistema ──────────────
        config1 = ConfiguracionSistema(
            clave="umbral_isolation_forest", valor="0.75",
            descripcion="Umbral de sensibilidad para deteccion de anomalias",
        )
        config2 = ConfiguracionSistema(
            clave="umbral_confianza_prediccion", valor="0.60",
            descripcion="Confianza minima para mostrar una prediccion al usuario",
        )
        db.add_all([config1, config2])

        # ── Log de auditoria inicial ───────────────
        log = AuditoriaLog(
            usuario_id=admin.id, accion="inicializacion_sistema",
            entidad_afectada="sistema", detalle={"mensaje": "Base de datos inicializada con seed.py"},
        )
        db.add(log)

        db.commit()
        print("Datos de ejemplo insertados correctamente.")
        print("")
        print("Usuarios de prueba (email / password):")
        print("  admin@ganajec.ai    / admin1234     (admin)")
        print("  sayuri@ganajec.ai   / dueno1234     (dueno)")
        print("  jared@ganajec.ai    / ganadero1234  (ganadero)")
        print("  carlos@ganajec.ai   / ganadero1234  (ganadero)")
        print("")
        print(f"Rancho ID: {rancho.id}")

    finally:
        db.close()


if __name__ == "__main__":
    crear_tablas()
    poblar_datos()
