"""
GANAJEC AI — Script de datos de prueba
Ejecutar con: python seed_datos_prueba.py
Requiere que uvicorn esté corriendo en localhost:8000
"""
import requests, json, sys

BASE = "http://localhost:8000"

def post(url, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{BASE}{url}", json=data, headers=headers)
    if r.status_code not in (200, 201):
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        return None
    return r.json()

def get(url, token):
    r = requests.get(f"{BASE}{url}", headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.ok else None

def patch(url, data, token):
    r = requests.patch(f"{BASE}{url}", json=data,
                       headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return r.json() if r.ok else None

print("=" * 55)
print("  GANAJEC AI — Cargando datos de prueba")
print("=" * 55)

# ── 1. Registrar usuarios ─────────────────────────────────
print("\n[1] Registrando usuarios...")

admin = post("/api/auth/register", {
    "nombre": "Administrador Sistema",
    "email": "admin@ganajec.mx",
    "password": "Test1234",
    "rol": "admin"
})
if not admin:
    print("  -> Intentando login (ya existe)...")
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": "admin@ganajec.mx", "password": "Test1234"},
                      headers={"Content-Type": "application/json"})
    admin = r.json() if r.ok else None
print(f"  Admin: {admin.get('nombre') if admin else 'ERROR'}")

dueno = post("/api/auth/register", {
    "nombre": "Dueno Rancho Demo",
    "email": "dueno@ganajec.mx",
    "password": "Test1234",
    "rol": "dueno"
})
if not dueno:
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": "dueno@ganajec.mx", "password": "Test1234"},
                      headers={"Content-Type": "application/json"})
    dueno = r.json().get("usuario") | {"token": r.json().get("token")} if r.ok else None
    if r.ok:
        dueno = {**r.json()["usuario"], "token": r.json()["token"]}
print(f"  Dueno: {dueno.get('nombre') if dueno else 'ERROR'}")
DUENO_TOKEN = dueno["token"]
DUENO_ID    = dueno["id"]

ganadero = post("/api/auth/register", {
    "nombre": "Ganadero Demo",
    "email": "ganadero@ganajec.mx",
    "password": "Test1234",
    "rol": "ganadero"
})
if not ganadero:
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": "ganadero@ganajec.mx", "password": "Test1234"},
                      headers={"Content-Type": "application/json"})
    if r.ok:
        ganadero = {**r.json()["usuario"], "token": r.json()["token"]}
print(f"  Ganadero: {ganadero.get('nombre') if ganadero else 'ERROR'}")
GANADERO_TOKEN = ganadero["token"]
GANADERO_ID    = ganadero["id"]

# ── 2. Crear rancho ───────────────────────────────────────
print("\n[2] Creando rancho...")
rancho = post("/api/dueno/ranchos", {
    "nombre": "Rancho El Potrero",
    "ubicacion": "Chiapas, Mexico",
    "descripcion": "Rancho de produccion mixta — datos de prueba"
}, DUENO_TOKEN)
if not rancho:
    sys.exit("ERROR creando rancho")

RANCHO_ID  = rancho["id"]
CODIGO_INV = rancho.get("codigo_invitacion", "")
print(f"  Rancho: {rancho['nombre']} | Codigo: {CODIGO_INV}")

# ── 3. Ganadero se une al rancho ──────────────────────────
print("\n[3] Ganadero uniendose al rancho...")
r = post("/api/ganadero/unirse-rancho",
         {"codigo_invitacion": CODIGO_INV}, GANADERO_TOKEN)
print(f"  {r.get('mensaje') if r else 'ERROR o ya estaba unido'}")

# ── 4. Crear bovinos ──────────────────────────────────────
print("\n[4] Registrando bovinos...")
bovinos_data = [
    {"nombre": "estrella",   "raza": "Holstein",   "sexo": "hembra", "categoria": "vaca",     "proposito": "leche",  "fecha_nacimiento": "2020-05-10", "peso_kg": 490.0, "id_externo": "HOL-001"},
    {"nombre": "tornado",    "raza": "Angus",      "sexo": "macho",  "categoria": "toro",     "proposito": "carne",  "fecha_nacimiento": "2019-08-22", "peso_kg": 680.0, "id_externo": "ANG-001"},
    {"nombre": "luna",       "raza": "Simmental",  "sexo": "hembra", "categoria": "vaca",     "proposito": "leche",  "fecha_nacimiento": "2021-03-14", "peso_kg": 440.0, "id_externo": "SIM-001"},
    {"nombre": "relamido",   "raza": "Cebu",       "sexo": "macho",  "categoria": "becerro",  "proposito": "carne",  "fecha_nacimiento": "2024-01-07", "peso_kg": 120.0, "id_externo": "CEB-001"},
    {"nombre": "canela",     "raza": "Holstein",   "sexo": "hembra", "categoria": "vaquilla", "proposito": "leche",  "fecha_nacimiento": "2023-06-18", "peso_kg": 280.0, "id_externo": "HOL-002"},
]

bovino_ids = []
for b in bovinos_data:
    res = post("/api/ganadero/bovinos", b, GANADERO_TOKEN)
    if res:
        bovino_ids.append(res["id"])
        print(f"  + {b['nombre']} ({b['raza']}) — id: {res['id'][:8]}...")
    else:
        print(f"  ! Error con {b['nombre']}")

# ── 5. Registrar síntomas y generar predicciones ──────────
print("\n[5] Registrando sintomas y generando predicciones...")

registros = [
    # estrella — diarrea + fiebre (coccidiosis probable)
    (bovino_ids[0], "La vaca tiene diarrea fuerte y mucha fiebre, no quiere comer nada desde ayer por la manana", 40.5, 92, 38, 5.5, 2.5, ["fiebre","diarrea","anorexia"]),
    # estrella — segundo registro (seguimiento)
    (bovino_ids[0], "Sigue con diarrea aunque ya come un poco, temperatura mas baja que ayer", 39.8, 78, 28, 7.0, 2.8, ["diarrea","decaimiento"]),
    # tornado — cojera
    (bovino_ids[1], "El toro esta cojeando de la pata delantera derecha, no quiere apoyarla bien", 38.9, 72, 24, None, 3.0, ["cojera","decaimiento"]),
    # luna — mastitis
    (bovino_ids[2], "La ubre izquierda esta muy inflamada y dura, la leche sale con grumos y la vaca no deja ordenar", 39.6, 80, 30, 2.0, 3.0, ["hinchazon_ubre","baja_produccion_leche"]),
    # luna — segundo registro mastitis
    (bovino_ids[2], "La ubre sigue inflamada pero la vaca ya esta mas tranquila, la leche todavia tiene grumos", 39.2, 76, 26, 3.5, 3.2, ["hinchazon_ubre","baja_produccion_leche"]),
    # canela — vientre hinchado (timpanismo)
    (bovino_ids[4], "La vaquilla tiene el vientre muy hinchado del lado izquierdo, no rumia y esta muy quieta", 38.7, 88, 36, None, 3.5, ["distension_abdominal","decaimiento"]),
    # relamido — tos y secrecion nasal (neumonia becerro)
    (bovino_ids[3], "El becerro lleva dos dias con tos y tiene moco en la nariz, se ve decaido y no mama bien", 40.1, 95, 42, None, None, ["tos","secrecion_nasal","decaimiento","fiebre"]),
]

for bov_id, texto, temp, fc, fr, leche, cc, sintomas in registros:
    payload = {
        "bovino_id": bov_id,
        "texto_libre": texto,
        "temperatura": temp,
        "frecuencia_cardiaca": fc,
        "frecuencia_respiratoria": fr,
        "sintomas_seleccionados": sintomas,
    }
    if leche is not None:
        payload["produccion_leche"] = leche
    if cc is not None:
        payload["condicion_corporal"] = cc

    res = post("/api/ganadero/registros-sintomas", payload, GANADERO_TOKEN)
    if res:
        pred = res.get("prediccion", {})
        anom = res.get("anomalia_productiva", {})
        print(f"  -> {pred.get('enfermedad','?')[:35]:<35} | {pred.get('severidad','?'):<8} | anomalia={anom.get('es_anomalia','?')}")
    else:
        print(f"  ! Error en registro")

# ── 6. Marcar algunas alertas como leidas ────────────────
print("\n[6] Marcando alertas como leidas...")
alertas = get(f"/api/ganadero/{GANADERO_ID}/alertas?limit=10", GANADERO_TOKEN)
if alertas and alertas.get("alertas"):
    primera = alertas["alertas"][0]
    patch(f"/api/ganadero/alertas/{primera['id']}", {"leida": True}, GANADERO_TOKEN)
    print(f"  Alerta '{primera['tipo']}' marcada como leida")

print("\n" + "=" * 55)
print("  DATOS DE PRUEBA CARGADOS CORRECTAMENTE")
print("=" * 55)
print(f"""
URL base:     http://localhost:8000
Swagger:      http://localhost:8000/docs

Usuario ganadero:
  Email:      ganadero@ganajec.mx
  Password:   Test1234

Usuario dueno:
  Email:      dueno@ganajec.mx
  Password:   Test1234

Usuario admin:
  Email:      admin@ganajec.mx
  Password:   Test1234

Bovinos creados:  {len(bovino_ids)}
Predicciones:     {len(registros)}
Rancho:           Rancho El Potrero
Codigo invitacion: {CODIGO_INV}
""")
