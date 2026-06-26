# GANAJEC AI API v2 — Documentación Técnica

API REST para predicción de enfermedades bovinas con Machine Learning.

---

## Índice

1. [Arquitectura General](#1-arquitectura-general)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Modelo de Datos (12 tablas)](#3-modelo-de-datos)
4. [Endpoints de la API](#4-endpoints-de-la-api)
5. [Autenticación y Autorización](#5-autenticación-y-autorización)
6. [Flujo de ML / NLP](#6-flujo-de-ml--nlp)
7. [Validación y Manejo de Errores](#7-validación-y-manejo-de-errores)
8. [Seed y Configuración Inicial](#8-seed-y-configuración-inicial)

---

## 1. Arquitectura General

```
Cliente (App Móvil / Web / curl)
        │
        ▼
  [run.py]  uvicorn :8000
        │
        ▼
  [app/main.py]  FastAPI
        │
        ├── CORS (abierto a todos los orígenes)
        ├── Manejadores de errores (HTTP, validación, BD, genérico)
        │
        ├── /api/auth/* ────── AuthController ─────── Usuario
        │     (sin autenticación)
        │
        ├── /api/ganadero/* ── GanaderoController ─── Bovino, RegistroSintoma,
        │     rol: ganadero    │                       Prediccion, Alerta
        │                      ├── predictor.py (Random Forest + Isolation Forest)
        │                      └── nlp.py (spaCy + diccionario de síntomas)
        │
        ├── /api/dueno/* ───── DuenoController ────── Rancho, Ganadero, Suscripcion
        │     rol: dueno
        │
        └── /api/admin/* ──── AdminController ─────── Usuario, Rancho,
              rol: admin                              AuditoriaLog, Configuracion
                                │
                                ▼
                        [SQLAlchemy ORM]
                                │
                                ▼
                     MySQL (12 tablas)
```

**Patrón:** MVC (Modelos → Controladores → Rutas) con inyección de dependencias de FastAPI.

**Stack:**

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.115 |
| Servidor | Uvicorn 0.30 |
| ORM | SQLAlchemy 2.0 |
| BD | MySQL (vía PyMySQL) |
| Validación | Pydantic 2.9 |
| Auth | JWT + bcrypt |
| ML | scikit-learn 1.5 (Random Forest, Isolation Forest) |
| NLP | spaCy 3.8 (modelo `es_core_news_sm`) |

---

## 2. Estructura del Proyecto

```
GANAJEC_API/
├── run.py                          # Punto de entrada: uvicorn.run()
├── seed.py                         # Poblador de BD (tablas + datos de prueba)
├── requirements.txt                # Dependencias Python
├── .env                            # Variables de entorno (DB, JWT secret)
│
└── app/
    ├── main.py                     # Fábrica de la app FastAPI
    │
    ├── core/                       # Capa base
    │   ├── config.py               # Settings: DB URL, SECRET_KEY, etc.
    │   ├── database.py             # Engine, SessionLocal, Base, get_db
    │   ├── security.py             # bcrypt (hash/verify) + JWT (create/decode)
    │   └── deps.py                 # Dependencias: get_current_user, require_role
    │
    ├── models/                     # Modelos SQLAlchemy (ORM)
    │   ├── base.py                 # UUIDMixin (PK con UUID para todas las tablas)
    │   ├── usuario.py              # Usuarios del sistema
    │   ├── rancho.py               # Ranchos / fincas
    │   ├── bovino.py               # Bovinos (animales)
    │   ├── registro_sintoma.py     # Registro de síntomas + Prediccion (1:1)
    │   ├── historial_productivo.py # Historial de producción
    │   ├── alerta.py               # Alertas + Notificacion
    │   ├── plan.py                 # Planes de suscripción
    │   └── configuracion_sistema.py # Configuración + AuditoriaLog
    │
    ├── schemas/                    # Esquemas Pydantic (validación I/O)
    │   ├── auth_schema.py          # RegisterRequest, LoginRequest, TokenResponse
    │   ├── ganadero_schema.py      # BovinoCreate/Update, RegistroSintomaCreate, AlertaUpdate
    │   └── general_schema.py       # RanchoUpdate, GanaderoCreate/Update, etc.
    │
    ├── controllers/                # Lógica de negocio (stateless, @staticmethod)
    │   ├── auth_controller.py      # register(), login()
    │   ├── ganadero_controller.py  # CRUD bovinos + síntomas + predicciones + alertas
    │   ├── dueno_controller.py     # Ranchos, ganaderos, suscripción
    │   └── admin_controller.py     # Usuarios, configuración, auditoría
    │
    ├── routes/                     # Rutas FastAPI (thin layer)
    │   ├── auth_routes.py          # POST /register, POST /login
    │   ├── ganadero_routes.py      # 10 endpoints (rol ganadero)
    │   ├── dueno_routes.py         # 8 endpoints (rol dueño)
    │   └── admin_routes.py         # 7 endpoints (rol admin)
    │
    └── ml/                         # Módulo de Machine Learning
        ├── predictor.py            # Random Forest + Isolation Forest
        ├── nlp.py                  # spaCy + diccionario de síntomas veterinarios
        └── models/
            ├── random_forest.pkl   # Clasificador (23 clases)
            ├── isolation_forest.pkl # Detector de anomalías
            ├── label_encoder.pkl   # Codificador de etiquetas
            └── metadata.json       # Métricas umbrales y features
```

---

## 3. Modelo de Datos

Todas las tablas usan **UUID** como llave primaria (CHAR(36)) vía `UUIDMixin`.

### 3.1 `usuarios`
| Campo | Tipo | Detalle |
|---|---|---|
| id | CHAR(36) PK | UUID |
| nombre | VARCHAR(150) | |
| email | VARCHAR(150) | UNIQUE, INDEX |
| password_hash | VARCHAR(255) | bcrypt |
| rol | ENUM('ganadero','dueno','admin') | |
| activo | BOOLEAN | Default TRUE |
| creado_en | DATETIME | Autogenerado |

### 3.2 `ranchos`
| Campo | Tipo | Detalle |
|---|---|---|
| id | CHAR(36) PK | UUID |
| nombre | VARCHAR(150) | |
| municipio | VARCHAR(100) | |
| estado | VARCHAR(100) | |
| dueno_id | CHAR(36) FK → usuarios.id | |
| creado_en | DATETIME | Autogenerado |

### 3.3 `bovinos`
| Campo | Tipo | Detalle |
|---|---|---|
| id | CHAR(36) PK | UUID |
| rancho_id | CHAR(36) FK → ranchos.id | |
| ganadero_id | CHAR(36) FK → usuarios.id | |
| nombre | VARCHAR(100) | |
| raza | VARCHAR(100) | |
| sexo | ENUM('hembra','macho') | |
| categoria | ENUM('vaca','toro','becerro','becerra','novillo','vaquilla','torete') | |
| proposito | ENUM('leche','carne','doble','cria') | |
| fecha_nacimiento | DATE | Nullable |
| peso_kg | FLOAT | |
| id_externo | VARCHAR(50) | UNIQUE, nullable |
| creado_en | DATETIME | Autogenerado |

*Borrado en cascada:* registros_sintomas, historial_productivo, alertas.

### 3.4 `registros_sintomas`
| Campo | Tipo | Detalle |
|---|---|---|
| id | CHAR(36) PK | UUID |
| bovino_id | CHAR(36) FK → bovinos.id | |
| ganadero_id | CHAR(36) FK → usuarios.id | |
| texto_libre | TEXT | Descripción en texto natural |
| temperatura | FLOAT | Nullable |
| produccion_leche | FLOAT | Nullable |
| frecuencia_cardiaca | FLOAT | bpm, nullable |
| frecuencia_respiratoria | FLOAT | nullable |
| condicion_corporal | FLOAT | 1.0–5.0, nullable |
| consumo_alimento_kg | FLOAT | Nullable |
| consumo_agua_l | FLOAT | Nullable |
| sintomas_seleccionados | JSON | Arreglo de códigos |
| registrado_en | DATETIME | Autogenerado |

Relación 1:1 con `Prediccion`.

### 3.5 `predicciones`
| Campo | Tipo | Detalle |
|---|---|---|
| id | CHAR(36) PK | UUID |
| registro_id | CHAR(36) FK → registros_sintomas.id | UNIQUE |
| enfermedad | VARCHAR(150) | Nombre de la enfermedad |
| confianza | FLOAT | 0.0–1.0 |
| severidad | ENUM('leve','moderada','alta') | |
| features_nlp | JSON | Top 3 predicciones + análisis NLP |
| generado_en | DATETIME | Autogenerado |

### 3.6 `historial_productivo`
| Campo | Tipo |
|---|---|
| id | CHAR(36) PK |
| bovino_id | CHAR(36) FK |
| fecha | DATE |
| litros_leche | FLOAT |
| kg_alimento | FLOAT |
| ganancia_peso_kg | FLOAT |
| temperatura | FLOAT |
| anomalia_detectada | BOOLEAN |

### 3.7 `alertas`
| Campo | Tipo | Detalle |
|---|---|---|
| id | CHAR(36) PK | |
| bovino_id | CHAR(36) FK | |
| ganadero_id | CHAR(36) FK | |
| tipo | ENUM('productiva','clinica') | |
| severidad | ENUM('baja','media','alta') | |
| mensaje | TEXT | |
| leida | BOOLEAN | Default FALSE |
| creado_en | DATETIME | |

*Borrado en cascada:* notificaciones.

### 3.8 `notificaciones`
| Campo | Tipo |
|---|---|
| id | CHAR(36) PK |
| usuario_id | CHAR(36) FK |
| alerta_id | CHAR(36) FK |
| enviada | BOOLEAN |
| enviado_en | DATETIME |

### 3.9 `planes`
| Campo | Tipo |
|---|---|
| id | CHAR(36) PK |
| nombre | VARCHAR(100) |
| precio_mensual | FLOAT |
| limite_bovinos | INTEGER |
| permisos | JSON |
| activo | BOOLEAN |
| actualizado_en | DATETIME |

### 3.10 `suscripciones`
| Campo | Tipo |
|---|---|
| id | CHAR(36) PK |
| usuario_id | CHAR(36) FK |
| plan_id | CHAR(36) FK |
| inicio | DATE |
| fin | DATE |
| activa | BOOLEAN |

### 3.11 `auditoria_logs`
| Campo | Tipo |
|---|---|
| id | CHAR(36) PK |
| usuario_id | CHAR(36) FK |
| accion | VARCHAR(150) |
| entidad_afectada | VARCHAR(100) |
| detalle | JSON |
| ip | VARCHAR(45) |
| creado_en | DATETIME |

### 3.12 `configuracion_sistema`
| Campo | Tipo |
|---|---|
| id | CHAR(36) PK |
| clave | VARCHAR(100) | UNIQUE |
| valor | VARCHAR(255) |
| descripcion | VARCHAR(255) |
| actualizado_por | CHAR(36) FK |
| actualizado_en | DATETIME |

---

## 4. Endpoints de la API

### 4.1 Autenticación — `/api/auth` (público)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register` | Registro de usuario. Body: `{nombre, email, password, rol}`. Devuelve JWT + usuario. |
| POST | `/api/auth/login` | Inicio de sesión. Body: `{email, password}`. Devuelve JWT + usuario. |

### 4.2 Ganadero — `/api/ganadero` (rol: `ganadero`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/{ganadero_id}` | Perfil del ganadero + total bovinos |
| GET | `/{ganadero_id}/bovinos` | Lista de bovinos a su cargo |
| GET | `/bovinos/{bovino_id}` | Detalle de un bovino |
| POST | `/bovinos` | Registrar un nuevo bovino |
| PUT | `/bovinos/{bovino_id}` | Actualizar datos del bovino |
| DELETE | `/bovinos/{bovino_id}` | Eliminar bovino (cascada) |
| GET | `/bovinos/{bovino_id}/predicciones` | Predicciones de un bovino |
| GET | `/{ganadero_id}/predicciones` | Historial global de predicciones |
| POST | `/registros-sintomas` | **Registrar síntoma → dispara ML+NLP+alertas** |
| GET | `/{ganadero_id}/alertas` | Listar alertas (?bovino_id= opcional) |
| PATCH | `/alertas/{alerta_id}` | Marcar alerta como leída |

### 4.3 Dueño — `/api/dueno` (rol: `dueno`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/{dueno_id}` | Perfil + lista de ranchos |
| GET | `/ranchos/{rancho_id}` | Dashboard del rancho (resumen, bovinos por categoría) |
| PUT | `/ranchos/{rancho_id}` | Actualizar datos del rancho |
| GET | `/ranchos/{rancho_id}/ganaderos` | Ganaderos asignados al rancho |
| POST | `/ganaderos` | Registrar un ganadero en el rancho |
| PUT | `/ganaderos/{ganadero_id}` | Actualizar / desactivar ganadero |
| GET | `/ranchos/{rancho_id}/bovinos` | Todos los bovinos del rancho |
| GET | `/{dueno_id}/suscripcion` | Plan de suscripción actual |

### 4.4 Administrador — `/api/admin` (rol: `admin`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/{admin_id}` | Perfil del admin |
| GET | `/usuarios` | Listar usuarios (?rol= opcional) |
| PUT | `/usuarios/{usuario_id}` | Actualizar usuario (status/rol) — registra auditoría |
| DELETE | `/usuarios/{usuario_id}` | Eliminar usuario — registra auditoría |
| GET | `/ranchos` | Todos los ranchos del sistema |
| GET | `/sistema/estado` | Estadísticas + logs de auditoría + estado de modelos ML |
| PUT | `/configuracion/{clave}` | Actualizar configuración del sistema — registra auditoría |

> **Nota:** En `admin_routes.py`, las rutas literales (`/usuarios`, `/ranchos`, `/sistema/estado`) se definen **antes** del wildcard `/{admin_id}` para evitar colisiones.

---

## 5. Autenticación y Autorización

### 5.1 Registro de usuario
- `POST /api/auth/register` con `{nombre, email, password, rol}`
- Se valida email (EmailStr), password (mín. 8 caracteres), rol (`^(ganadero|dueno|admin)$`)
- Se hashea la contraseña con **bcrypt**
- Se crea el usuario en BD con `activo = True`
- Se genera un JWT y se devuelve junto con los datos del usuario

### 5.2 Inicio de sesión
- `POST /api/auth/login` con `{email, password}`
- Se verifica el email exista y el usuario esté activo
- Se verifica la contraseña con bcrypt
- Se genera un **JWT HS256** con payload `{sub: user_id, rol: user_role, exp: now + 24h}`
- Se devuelve `{access_token, token_type: "bearer", usuario: {...}}`

### 5.3 Protección de rutas
- `get_current_user`: extrae el token del header `Authorization: Bearer`, lo decodifica, busca el usuario en BD y verifica que esté activo.
- `require_role("ganadero")`, `require_role("dueno")`, `require_role("admin")`: fábrica de dependencias que verifica que el rol del usuario coincida. Si no coincide → 403 Forbidden.

### 5.4 Flujo de autenticación
```
Cliente                   Servidor
  │                         │
  │  POST /api/auth/login   │
  │  {email, password}      │
  │────────────────────────>│
  │                         ├─ verifica credenciales
  │                         ├─ genera JWT (24h)
  │  {access_token, ...}    │
  │<────────────────────────│
  │                         │
  │  GET /api/ganadero/...  │
  │  Authorization: Bearer  │
  │────────────────────────>│
  │                         ├─ decodifica JWT
  │                         ├─ busca usuario
  │                         ├─ verifica rol
  │                         ├─ ejecuta controlador
  │  {datos}               │
  │<────────────────────────│
```

---

## 6. Flujo de ML / NLP

El endpoint clave es **`POST /api/ganadero/registros-sintomas`**, que ejecuta esta cadena:

### 6.1 Entrada
```json
{
  "bovino_id": "uuid",
  "texto_libre": "La vaca tiene fiebre alta, no come y tiene diarrea",
  "temperatura": 40.5,
  "produccion_leche": null,
  "frecuencia_cardiaca": 85,
  "frecuencia_respiratoria": null,
  "condicion_corporal": 2.5,
  "consumo_alimento_kg": null,
  "consumo_agua_l": null,
  "sintomas_seleccionados": ["fiebre", "diarrea"]
}
```

### 6.2 Paso 1 — NLP (app/ml/nlp.py)
- Tokeniza el `texto_libre` con **spaCy** (modelo español)
- Busca coincidencias en un diccionario de 22 síntomas con expresiones coloquiales mexicanas
- Fusiona síntomas detectados por NLP con `sintomas_seleccionados` (unión, sin duplicados)
- Opcionalmente usa **DistilBETO** (BERT español) para similitud semántica si está disponible
- Devuelve vector de síntomas + concordancia

### 6.3 Paso 2 — Random Forest (app/ml/predictor.py)
- Construye un vector de 9 features: temperatura, frecuencia cardíaca/repiratoria, condición corporal, consumo de alimento/agua, producción de leche, peso, edad
- Los valores `None` se reemplazan con medias poblacionales
- Predice enfermedad entre **23 clases** (22 enfermedades + "sano")
- Asigna **severidad**: leve (< 0.12 confianza), moderada (0.12–0.20), alta (> 0.20)
- Devuelve top 3 predicciones

### 6.4 Paso 3 — Isolation Forest
- Evalúa el mismo vector en busca de anomalías productivas
- Si score < -0.08 → genera alerta **productiva** (severidad según qué tan negativo)

### 6.5 Paso 4 — Generación de alertas
- Si hay anomalía → `Alerta` tipo `productiva`
- Si la enfermedad predecida no es "sano" y severidad es `alta` → `Alerta` tipo `clinica`

### 6.6 Paso 5 — Concordancia NLP
- Compara los síntomas detectados por NLP contra el perfil de la enfermedad
- Devuelve un score 0.0–1.0 indicando qué tan bien el texto respalda la predicción

### 6.7 Salida
```json
{
  "registro": { ... },
  "prediccion": {
    "enfermedad": "Fiebre de Garrapatas",
    "confianza": 0.87,
    "severidad": "alta",
    "features_nlp": {
      "sintomas_detectados": [...],
      "top_3_predicciones": [...],
      "concordancia": 0.92,
      "respaldo_nlp": "ALTO"
    }
  },
  "alertas_generadas": [...]
}
```

---

## 7. Validación y Manejo de Errores

### 7.1 Validación de entrada (Pydantic)
- Email válido via `EmailStr`
- Password con mínimo 8 caracteres
- `sexo` solo `hembra|macho`
- `categoria` dentro del enum
- `peso_kg` > 0
- `condicion_corporal` entre 1.0 y 5.0

### 7.2 Formato de error consistente
```json
{
  "status": 404,
  "error": "No encontrado",
  "message": "No encontrado",
  "detail": "No encontrado: el bovino con id 'xxxx' no existe",
  "path": "/api/ganadero/bovinos/xxxx"
}
```

### 7.3 Manejadores registrados
| Excepción | Código | Descripción |
|---|---|---|
| StarletteHTTPException | 400/401/403/404/405/409 | Errores HTTP estándar |
| RequestValidationError | 422 | Datos inválidos (Pydantic) |
| IntegrityError | 409 | Violación de unicidad en BD |
| SQLAlchemyError | 500 | Error general de BD |
| Exception | 500 | Error no esperado (catch-all) |

---

## 8. Seed y Configuración Inicial

`seed.py` puebla la BD con datos de prueba:

- **4 usuarios**: 1 admin, 1 dueño, 2 ganaderos
- **1 rancho** asociado al dueño
- **3 bovinos** distribuidos entre los ganaderos
- **1 registro de síntoma** con su predicción
- **1 historial productivo** de ejemplo
- **1 alerta + 1 notificación**
- **2 planes de suscripción**:
  - Básico ($499/mes, 50 bovinos)
  - Premium ($999/mes, bovinos ilimitados)
- **2 configuraciones del sistema**:
  - `umbral_isolation_forest` → -0.08
  - `umbral_confianza_prediccion` → 0.5
- **1 log de auditoría** inicial

### 8.1 Cómo ejecutar

```bash
# 1. Configurar .env con credenciales de MySQL
# 2. Crear la base de datos en MySQL
python seed.py     # Crea tablas + inserta datos
python run.py      # Inicia el servidor en :8000
```
