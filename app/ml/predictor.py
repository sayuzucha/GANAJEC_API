"""
Modulo de Machine Learning de GANAJEC AI.

Carga los modelos entrenados (Random Forest + Isolation Forest) una sola vez
al iniciar la API, y expone funciones para:

- predecir_enfermedad(): a partir de los síntomas detectados por NLP y los
  vitales del registro, construye un vector binario de 93 síntomas y predice
  la enfermedad más probable, su confianza y severidad.
- detectar_anomalia(): determina si el conjunto de síntomas es anómalo.

Los modelos fueron entrenados con el dataset "Cattle Disease Prediction"
(Training.csv / Testing.csv) usando 93 síntomas veterinarios binarios
observables por el ganadero sin necesidad de sensores.
"""
import json
import os
import joblib
import numpy as np

_BASE_DIR   = os.path.dirname(__file__)
_MODELS_DIR = os.path.join(_BASE_DIR, "models")

# ── Carga de modelos (una sola vez, al importar el modulo) ──────────
_random_forest    = joblib.load(os.path.join(_MODELS_DIR, "random_forest.pkl"))
_isolation_forest = joblib.load(os.path.join(_MODELS_DIR, "isolation_forest.pkl"))
_label_encoder    = joblib.load(os.path.join(_MODELS_DIR, "label_encoder.pkl"))

with open(os.path.join(_MODELS_DIR, "metadata.json"), encoding="utf-8") as f:
    METADATA = json.load(f)

# Orden exacto de las 93 columnas con las que se entrenó el modelo.
_FEATURE_ORDER = METADATA["features"]

_UMBRAL_MODERADA = METADATA["umbrales_severidad"]["moderada"]
_UMBRAL_ALTA     = METADATA["umbrales_severidad"]["alta"]

# ── Traducción de nombres de enfermedad (inglés → español) ──────────
TRADUCCION_ENFERMEDADES = {
    "acetonaemia":                   "Acetonemia (cetosis)",
    "blackleg":                      "Carbón sintomático (pierna negra)",
    "bloat":                         "Timpanismo (meteorismo)",
    "calf_diphtheria":               "Difteria del becerro",
    "calf_pneumonia":                "Neumonía del becerro",
    "coccidiosis":                   "Coccidiosis",
    "cryptosporidiosis":             "Criptosporidiosis",
    "displaced_abomasum":            "Desplazamiento de abomaso",
    "fatty_liver_syndrome":          "Síndrome de hígado graso",
    "fog_fever":                     "Fiebre de pasto (enfisema pulmonar)",
    "foot_and_mouth":                "Fiebre aftosa",
    "foot_rot":                      "Pudrición de pezuña",
    "gut_worms":                     "Parásitos gastrointestinales",
    "infectious_bovine_rhinotracheitis": "Rinotraqueítis infecciosa bovina (IBR)",
    "listeriosis":                   "Listeriosis",
    "liver_fluke":                   "Fasciola hepática (distomatosis)",
    "mastitis":                      "Mastitis",
    "necrotic_enteritis":            "Enteritis necrótica",
    "peri_weaning_diarrhoea":        "Diarrea del destete",
    "ragwort_poisoning":             "Intoxicación por hierba cana",
    "rift_valley_fever":             "Fiebre del Valle del Rift",
    "rumen_acidosis":                "Acidosis ruminal",
    "schmallen_berg_virus":          "Virus Schmallenberg",
    "traumatic_reticulitis":         "Reticulitis traumática (enfermedad del clavo)",
    "trypanosomosis":                "Tripanosomosis",
    "wooden_tongue":                 "Actinobacilosis (lengua de madera)",
}

# ── Mapeo: síntoma NLP (español) → columnas del dataset (inglés) ────
# Cada síntoma detectado por NLP activa una o más columnas binarias.
_NLP_A_DATASET = {
    "fiebre":                ["fever", "high_temp", "intermittent_fever"],
    "cojera":                ["lameness", "unwillingness_to_move"],
    "decaimiento":           ["dull", "lethargy", "depression", "weakness"],
    "anorexia":              ["anorexia", "loss_of_appetite", "reduces_feed_intake"],
    "diarrea":               ["diarrhoea", "dysentery", "highly_diarrhoea", "mild_diarrhoea"],
    "tos":                   ["coughing", "pneumonia"],
    "dificultad_respiratoria": ["dyspnea", "diffculty_breath", "rapid_breathing",
                                "raised_breathing", "shallow_breathing"],
    "secrecion_nasal":       ["nasel_discharges"],
    "secrecion_ocular":      ["lacrimation", "conjunctivae"],
    "hinchazon_ubre":        ["udder_swelling", "udder_heat", "udder_hardeness",
                              "udder_redness", "udder_pain"],
    "baja_produccion_leche": ["reduction_milk_vields", "milk_flakes", "milk_watery", "milk_clots"],
    "distension_abdominal":  ["gaseous_stomach", "abdominal_pain", "stomach_pain", "rumenstasis"],
    "lesiones_piel":         ["blisters", "mucosal_lesions", "ulcers", "swelling"],
    "ampollas_boca":         ["blisters", "mucosal_lesions", "painful_tongue",
                              "swollen_tongue", "salivation", "saliva", "frothing"],
    "temblores":             ["encephalitis", "lack_of-coordination"],
    "salivacion_excesiva":   ["salivation", "saliva", "frothing", "frothing_of_mouth", "drooling"],
    "hinchazon_cuello":      ["swollen_pharyngeal", "swelling", "oedema"],
    "garrapatas":            ["anaemia", "blood_loss"],
    "perdida_peso":          ["weight_loss", "emaciation", "reduced_fat"],
    "ganglios_inflamados":   ["swollen_pharyngeal", "swelling", "oedema"],
    "debilidad_posparto":    ["weakness", "milk_fever", "lack_of-coordination"],
    "aliento_cetonas":       ["acetone", "ketosis"],
}

# ── Índice de columnas para acceso rápido ────────────────────────────
_COL_INDEX = {col: i for i, col in enumerate(_FEATURE_ORDER)}


def _build_feature_vector(datos: dict) -> np.ndarray:
    """
    Construye el vector binario de 93 síntomas a partir de:
    - sintomas_nlp: list[str]  — síntomas detectados por NLP (español)
    - temperatura, frecuencia_cardiaca, etc. — vitales para derivar síntomas objetivos

    Si un síntoma NLP activa múltiples columnas del dataset, todas se ponen a 1.
    Las vitales se convierten a síntomas mediante umbrales clínicos bovinos.
    """
    vec = np.zeros(len(_FEATURE_ORDER), dtype=float)

    def activar(col: str):
        if col in _COL_INDEX:
            vec[_COL_INDEX[col]] = 1.0

    # ── 1. Síntomas detectados por NLP ──────────────────────────
    for sintoma in datos.get("sintomas_nlp", []):
        for col in _NLP_A_DATASET.get(sintoma, []):
            activar(col)

    # ── 2. Vitales → síntomas objetivos (umbrales clínicos bovinos) ──
    temp = datos.get("temperatura")
    if temp is not None:
        if temp >= 39.5:
            activar("fever"); activar("high_temp")
        if temp >= 40.5:
            activar("intermittent_fever")

    fc = datos.get("frecuencia_cardiaca")
    if fc is not None and fc > 100:
        activar("high_pulse_rate"); activar("tachycardia")

    fr = datos.get("frecuencia_respiratoria")
    if fr is not None and fr > 40:
        activar("rapid_breathing"); activar("raised_breathing"); activar("dyspnea")

    ccs = datos.get("condicion_corporal")
    if ccs is not None and ccs < 2.5:
        activar("emaciation"); activar("weight_loss")

    leche = datos.get("produccion_leche")
    if leche is not None and leche < 5.0:
        activar("reduction_milk_vields")

    return np.array([vec])


def predecir_enfermedad(datos: dict) -> dict:
    """
    Ejecuta Random Forest sobre el vector de síntomas.

    `datos` debe incluir:
      - sintomas_nlp: list[str]  — de nlp.extraer_sintomas()
      - temperatura, frecuencia_cardiaca, frecuencia_respiratoria,
        condicion_corporal, produccion_leche  (todos opcionales)

    Retorna:
        {
            "enfermedad": str,
            "enfermedad_codigo": str,
            "confianza": float,
            "severidad": "leve" | "moderada" | "alta",
            "features_nlp": dict,
        }
    """
    X = _build_feature_vector(datos)

    pred_idx = _random_forest.predict(X)[0]
    probas   = _random_forest.predict_proba(X)[0]
    confianza = float(probas.max())

    enfermedad_codigo = _label_encoder.inverse_transform([pred_idx])[0]
    enfermedad_es     = TRADUCCION_ENFERMEDADES.get(enfermedad_codigo, enfermedad_codigo)

    if confianza >= _UMBRAL_ALTA:
        severidad = "alta"
    elif confianza >= _UMBRAL_MODERADA:
        severidad = "moderada"
    else:
        severidad = "leve"

    # Top 3 para contexto en features_nlp
    top_idx = np.argsort(probas)[::-1][:3]
    top3 = [
        {
            "enfermedad": TRADUCCION_ENFERMEDADES.get(
                _label_encoder.inverse_transform([i])[0],
                _label_encoder.inverse_transform([i])[0],
            ),
            "probabilidad": round(float(probas[i]), 4),
        }
        for i in top_idx
    ]

    sintomas_activos = [
        _FEATURE_ORDER[j] for j in range(len(_FEATURE_ORDER)) if X[0][j] == 1.0
    ]

    return {
        "enfermedad":       enfermedad_es,
        "enfermedad_codigo": enfermedad_codigo,
        "confianza":        round(confianza, 4),
        "severidad":        severidad,
        "features_nlp": {
            "modelo":            "RandomForest",
            "version_modelo":    METADATA.get("version", "3.0"),
            "sintomas_activos":  sintomas_activos,
            "top_3_predicciones": top3,
            "variables_usadas":  f"{len(_FEATURE_ORDER)} síntomas binarios",
        },
    }


def detectar_anomalia(datos: dict) -> dict:
    """
    Ejecuta Isolation Forest sobre el vector de síntomas.
    Un animal con síntomas activos será detectado como anómalo.

    Retorna:
        {
            "es_anomalia": bool,
            "score": float,
        }
    """
    X = _build_feature_vector(datos)

    pred  = _isolation_forest.predict(X)[0]
    score = float(_isolation_forest.score_samples(X)[0])

    return {
        "es_anomalia": bool(pred == -1),
        "score":       round(score, 4),
    }
