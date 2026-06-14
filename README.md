# GANAJEC AI — API v2 (MVC + ORM + MySQL)

API REST con arquitectura MVC, SQLAlchemy ORM y MySQL, alineada al ERD v3
(12 tablas) de GANAJEC AI — plataforma de prediccion de enfermedades bovinas.

## 1. Estructura del proyecto (MVC)

```
ganajec_api_v2/
├── app/
│   ├── main.py                    ← App + manejo de errores (404, 401, 403, 409, 422, 500)
│   ├── core/
│   │   ├── config.py              ← Lee .env (datos de conexion MySQL)
│   │   ├── database.py            ← Engine, Session, Base de SQLAlchemy
│   │   ├── security.py            ← hash/verify password + JWT
│   │   └── deps.py                ← get_current_user / require_role (auth)
│   ├── models/                     ← MODELOS ORM (12 tablas del ERD v3)
│   │   ├── usuario.py              → tabla usuarios
│   │   ├── rancho.py               → tabla ranchos
│   │   ├── bovino.py               → tabla bovinos
│   │   ├── registro_sintoma.py     → tablas registros_sintomas, predicciones
│   │   ├── historial_productivo.py → tabla historial_productivo
│   │   ├── alerta.py                → tablas alertas, notificaciones
│   │   ├── plan.py                  → tablas planes, suscripciones
│   │   └── configuracion_sistema.py → tablas auditoria_logs, configuracion_sistema
│   ├── schemas/                    ← Validacion de datos de entrada (Pydantic)
│   │   ├── auth_schema.py
│   │   ├── ganadero_schema.py
│   │   └── general_schema.py
│   ├── controllers/                ← LOGICA DE NEGOCIO
│   │   ├── auth_controller.py
│   │   ├── ganadero_controller.py
│   │   ├── dueno_controller.py
│   │   └── admin_controller.py
│   └── routes/                     ← RUTAS / ENDPOINTS
│       ├── auth_routes.py
│       ├── ganadero_routes.py
│       ├── dueno_routes.py
│       └── admin_routes.py
├── requirements.txt
├── .env.example                    ← copia a .env y llena tus datos de MySQL
├── seed.py                          ← crea las tablas + datos de prueba
└── run.py                           ← arranca el servidor
```

## 2. Para modificar algo, ve directo a:

| Quiero cambiar... | Edita este archivo |
|---|---|
| Los campos de una tabla (ej. agregar columna a BOVINOS) | `app/models/bovino.py` |
| Las validaciones de los datos que recibe la API | `app/schemas/*.py` |
| La logica de negocio / reglas | `app/controllers/*.py` |
| Las rutas / URLs disponibles | `app/routes/*.py` |
| Los mensajes de error (404, 500, etc.) | `app/main.py` |
| Datos de conexion a MySQL | `.env` |

## 3. Configurar MySQL

### 3.1. Crear la base de datos

```sql
CREATE DATABASE ganajec_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3.2. Configurar credenciales

Copia `.env.example` a `.env` y llena tus datos:

```bash
cp .env.example .env
```

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password
DB_NAME=ganajec_db

SECRET_KEY=cambia-esta-clave-por-una-larga-y-aleatoria
```

### 3.3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3.4. Crear tablas + datos de prueba

```bash
python seed.py
```

Esto crea las 12 tablas en MySQL **automaticamente con todos sus campos**
(gracias al ORM, no necesitas escribir SQL) y las llena con datos de ejemplo.

Al terminar, imprime usuarios de prueba:

```
admin@ganajec.ai    / admin1234     (admin)
sayuri@ganajec.ai   / dueno1234     (dueno)
jared@ganajec.ai    / ganadero1234  (ganadero)
carlos@ganajec.ai   / ganadero1234  (ganadero)
```

### 3.5. Ejecutar la API

```bash
python run.py
```

Disponible en `http://localhost:8000`
Documentacion interactiva (Swagger): `http://localhost:8000/docs`

## 4. Autenticacion

Todos los endpoints (excepto `/api/auth/*`) requieren un token JWT.

1. Haz login: `POST /api/auth/login` con `email` y `password`
2. Recibes `access_token`
3. Envialo en cada request: header `Authorization: Bearer {access_token}`

Cada endpoint valida el **rol** del usuario (ganadero/dueno/admin) automaticamente.
Si el rol no coincide, responde `403 Acceso denegado`.

## 5. Endpoints

### Autenticacion (`/api/auth`) — sin token

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/register` | Registra un nuevo usuario (ganadero/dueno/admin) |
| POST | `/login` | Login. Retorna `access_token` + datos del usuario |

### Ganadero (`/api/ganadero`) — requiere rol `ganadero`

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/{ganadero_id}` | Perfil del ganadero |
| GET | `/{ganadero_id}/bovinos` | Lista los bovinos a su cargo |
| GET | `/bovinos/{bovino_id}` | Detalle de un bovino |
| POST | `/bovinos` | Registra un nuevo bovino |
| PUT | `/bovinos/{bovino_id}` | Actualiza datos de un bovino |
| DELETE | `/bovinos/{bovino_id}` | Elimina un bovino |
| GET | `/bovinos/{bovino_id}/predicciones` | Predicciones ML/NLP de un bovino especifico |
| GET | `/{ganadero_id}/predicciones` | Historial global: predicciones de TODOS sus bovinos + estadisticas |
| POST | `/registros-sintomas` | Registra nota de campo / sintomas |
| GET | `/{ganadero_id}/alertas` | Lista alertas (filtro opcional `?bovino_id=`) |
| PATCH | `/alertas/{alerta_id}` | Marca una alerta como leida |

### Dueno del rancho (`/api/dueno`) — requiere rol `dueno`

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/{dueno_id}` | Perfil del dueno + sus ranchos |
| GET | `/ranchos/{rancho_id}` | Dashboard del rancho (resumen por categoria) |
| PUT | `/ranchos/{rancho_id}` | Actualiza datos del rancho |
| GET | `/ranchos/{rancho_id}/ganaderos` | Lista ganaderos del rancho |
| POST | `/ganaderos` | Registra un nuevo ganadero |
| PUT | `/ganaderos/{ganadero_id}` | Actualiza/desactiva un ganadero |
| GET | `/ranchos/{rancho_id}/bovinos` | Lista todos los bovinos del rancho |
| GET | `/{dueno_id}/suscripcion` | Plan y suscripcion actual |

### Administrador (`/api/admin`) — requiere rol `admin`

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/{admin_id}` | Perfil del admin |
| GET | `/usuarios` | Lista usuarios (filtro opcional `?rol=`) |
| PUT | `/usuarios/{usuario_id}` | Actualiza estado/rol de un usuario |
| DELETE | `/usuarios/{usuario_id}` | Elimina un usuario |
| GET | `/ranchos` | Lista todos los ranchos del sistema |
| GET | `/sistema/estado` | Estadisticas + logs de auditoria + estado de modelos ML |
| PUT | `/configuracion/{clave}` | Actualiza un valor de configuracion del sistema |

## 6. Manejo de errores

Todos los errores devuelven el mismo formato JSON consistente,
listo para mostrarse "bonito" en el frontend (ej. "No encontrado"):

```json
{
  "status": 404,
  "error": "No encontrado",
  "message": "No encontrado",
  "detail": "No encontrado: el bovino con id 'xxxx' no existe",
  "path": "/api/ganadero/bovinos/xxxx"
}
```

| Codigo | Cuando ocurre |
|---|---|
| 400 | Datos validos en formato pero invalidos en logica (ej. rol invalido) |
| 401 | Falta token, token invalido/expirado, credenciales incorrectas |
| 403 | Token valido pero rol incorrecto, o accion prohibida |
| 404 | Recurso (bovino, rancho, usuario...) o ruta no existe |
| 409 | Conflicto (email duplicado, integridad de BD) |
| 422 | Datos de entrada invalidos (Pydantic) |
| 500 | Error inesperado / error de base de datos |

## 7. Ejemplo de flujo completo

```bash
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jared@ganajec.ai","password":"ganadero1234"}'

# Respuesta: { "access_token": "eyJ...", "usuario": { "id": "...", ... } }

# 2. Usar el token
curl http://localhost:8000/api/ganadero/{ganadero_id}/bovinos \
  -H "Authorization: Bearer eyJ..."
```

## 9. Modelos de Machine Learning integrados

La API incluye 2 modelos entrenados en `app/ml/models/`:

| Modelo | Archivo | Funcion |
|---|---|---|
| Random Forest | `random_forest.pkl` (23 MB) | Predice la enfermedad mas probable (23 clases: 22 enfermedades + sano) |
| Isolation Forest | `isolation_forest.pkl` (2 MB) | Detecta anomalias en los valores productivos |

### Como se activan

Cada vez que se llama `POST /api/ganadero/registros-sintomas`, la API:

1. Guarda el registro en `REGISTROS_SINTOMAS`
2. Calcula la edad del bovino (a partir de `fecha_nacimiento`)
3. Ejecuta **Random Forest** → guarda una fila en `PREDICCIONES` con `enfermedad`, `confianza` y `severidad`
4. Ejecuta **Isolation Forest** → si detecta anomalia, crea una `ALERTA` tipo `productiva`
5. Si Random Forest predice una enfermedad (no "sano") con severidad alta, crea ademas una `ALERTA` tipo `clinica`

Todos los campos numericos del registro son **opcionales**: si el ganadero no
los llena, se usan valores promedio (neutros) para que el modelo siempre pueda predecir.

### Variables que usan los modelos

Provienen de `BOVINOS` (edad, peso) y de `REGISTROS_SINTOMAS` (los demas):

```
edad_meses, peso_kg, temperatura, frecuencia_cardiaca,
frecuencia_respiratoria, produccion_leche, condicion_corporal,
consumo_alimento_kg, consumo_agua_l
```

### Metricas de los modelos

Ver `app/ml/models/metadata.json`:
- Random Forest: **47.4% accuracy** en 23 clases (vs. ~4.3% si fuera al azar)
- Isolation Forest: **95% especificidad** (rara vez marca a un bovino sano como anomalo)

### Reentrenar los modelos

Si quieres reentrenar con mas datos, usa `scikit-learn` con el mismo orden
de columnas (`_FEATURE_ORDER` en `app/ml/predictor.py`) y reemplaza los
archivos `.pkl` en `app/ml/models/`. No requiere cambios de codigo si
mantienes el mismo `LabelEncoder` (mismas clases de enfermedad).

### Ejemplo de respuesta

```json
{
  "mensaje": "Registro guardado y procesado por los modelos de IA",
  "registro": { "...": "...", "sintomas_seleccionados": ["fiebre", "cojera", "lesiones_piel"] },
  "prediccion": {
    "enfermedad": "Fiebre aftosa",
    "confianza": 0.21,
    "severidad": "moderada",
    "features_nlp": {
      "modelo": "RandomForest",
      "top_3_predicciones": [ "..." ],
      "analisis_texto": {
        "sintomas_detectados": ["fiebre", "cojera", "lesiones_piel"],
        "modelo_nlp": "spaCy (es) + diccionario de sintomas veterinarios",
        "distilbeto_disponible": false,
        "concordancia_con_prediccion": 0.83
      }
    }
  },
  "anomalia_productiva": { "es_anomalia": true, "score": -0.42 },
  "alerta_productiva": { "...": "..." }
}
```

## 10. Modulo NLP (procesamiento del texto libre)

Cuando el ganadero escribe `texto_libre` (ej. *"el animal tiene fiebre y esta
cojeando, le salieron ampollas en la boca"*), `app/ml/nlp.py` lo procesa asi:

1. **spaCy (es)** tokeniza y normaliza el texto (minusculas, sin acentos).
   Usa `spacy.blank("es")`, que no requiere descargar ningun modelo — el
   tokenizador y las stopwords en español vienen incluidos en el paquete
   `spacy` (solo se necesita `pip install spacy`, sin `spacy download`).

2. **Diccionario de sintomas**: ~22 sintomas veterinarios estandarizados
   (fiebre, cojera, decaimiento, anorexia, diarrea, tos, dificultad
   respiratoria, hinchazon de ubre, ampollas en la boca, garrapatas, etc.),
   cada uno con sus expresiones coloquiales en español de Mexico. El texto
   normalizado se compara contra este diccionario para detectar sintomas.

3. **Fusion de sintomas**: los sintomas detectados automaticamente se
   combinan (union, sin duplicados) con los que el ganadero marco
   manualmente en `sintomas_seleccionados`, y el resultado se guarda en
   `REGISTROS_SINTOMAS.sintomas_seleccionados`.

4. **Concordancia con la prediccion**: cada enfermedad de Random Forest
   tiene un "perfil" de sintomas tipicos (`DISEASE_SYMPTOM_PROFILE`). Se
   calcula que proporcion de ese perfil aparece en el texto del ganadero
   (0.0 a 1.0). Un valor alto significa que el texto respalda la prediccion
   de Random Forest; un valor bajo (o 0) indica que los sintomas descritos
   no coinciden con lo que predijo el modelo numerico — util para que el
   ganadero sepa cuando revisar el caso con mas cuidado.

5. **DistilBETO (opcional)**: el codigo intenta cargar
   `dccuchile/distilbert-base-spanish-uncased` via `transformers` + `torch`
   para un analisis semantico adicional (similitud de significado, no solo
   coincidencia de palabras). Esto requiere internet hacia huggingface.co
   en el servidor de despliegue. Si no esta disponible (como en desarrollo),
   `distilbeto_disponible: false` y el modulo sigue funcionando solo con
   spaCy + el diccionario — no rompe nada.

   Para activarlo en produccion:
   ```bash
   pip install transformers torch
   ```
   La primera llamada descargara el modelo (~250 MB) automaticamente.



| Tabla | Modelo Python | Campos clave |
|---|---|---|
| usuarios | `Usuario` | id, nombre, email, password_hash, rol, activo |
| ranchos | `Rancho` | id, nombre, municipio, estado, dueno_id |
| bovinos | `Bovino` | id, rancho_id, ganadero_id, nombre, raza, sexo, **categoria**, **proposito**, peso_kg |
| registros_sintomas | `RegistroSintoma` | id, bovino_id, ganadero_id, texto_libre, sintomas_seleccionados |
| predicciones | `Prediccion` | id, registro_id, enfermedad, confianza, severidad |
| historial_productivo | `HistorialProductivo` | id, bovino_id, litros_leche, **ganancia_peso_kg**, anomalia_detectada |
| alertas | `Alerta` | id, bovino_id, ganadero_id, tipo, severidad, mensaje, leida |
| notificaciones | `Notificacion` | id, usuario_id, alerta_id, enviada |
| planes | `Plan` | id, nombre, precio_mensual, **limite_bovinos**, permisos |
| suscripciones | `Suscripcion` | id, usuario_id, plan_id, inicio, fin, activa |
| auditoria_logs | `AuditoriaLog` | id, usuario_id, accion, entidad_afectada, detalle |
| configuracion_sistema | `ConfiguracionSistema` | id, clave, valor, descripcion |
