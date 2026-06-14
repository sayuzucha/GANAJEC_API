"""
Modulo de Machine Learning de GANAJEC AI.

Carga los modelos entrenados (Random Forest + Isolation Forest) una sola vez
al iniciar la API, y expone funciones para:

- predecir_enfermedad(): a partir de los datos de un registro de sintomas,
  predice la enfermedad mas probable, su confianza y severidad.
- detectar_anomalia(): determina si los valores productivos del registro
  son anomalos respecto a un bovino sano (para generar alertas).

Los modelos fueron entrenados con el dataset "Global Cattle Disease Detection"
usando solo variables que el ganadero puede registrar sin sensores:
edad, peso, temperatura, frecuencia cardiaca, frecuencia respiratoria,
produccion de leche, condicion corporal, consumo de alimento y de agua.
"""
import json
import os
import joblib
import numpy as np

_BASE_DIR = os.path.dirname(__file__)
_MODELS_DIR = os.path.join(_BASE_DIR, "models")

# ── Carga de modelos (una sola vez, al importar el modulo) ──────────
_random_forest = joblib.load(os.path.join(_MODELS_DIR, "random_forest.pkl"))
_isolation_forest = joblib.load(os.path.join(_MODELS_DIR, "isolation_forest.pkl"))
_label_encoder = joblib.load(os.path.join(_MODELS_DIR, "label_encoder.pkl"))

with open(os.path.join(_MODELS_DIR, "metadata.json"), encoding="utf-8") as f:
    METADATA = json.load(f)

# Orden exacto de columnas con el que se entrenaron los modelos.
# Debe coincidir con app/ml/models/random_forest.pkl e isolation_forest.pkl
_FEATURE_ORDER = [
    "Age_Months",
    "Weight_kg",
    "Body_Temperature_C",
    "Heart_Rate_bpm",
    "Respiratory_Rate",
    "Milk_Yield_L",
    "Body_Condition_Score",
    "Feed_Quantity_kg",
    "Water_Intake_L",
]

# Umbrales calibrados con la distribucion real de confianzas del modelo
# (media ~0.14 con 23 clases). Ver app/ml/models/metadata.json
_UMBRAL_MODERADA = METADATA["umbrales_severidad"]["moderada"]
_UMBRAL_ALTA = METADATA["umbrales_severidad"]["alta"]

# Traduccion de nombres de enfermedad (ingles del dataset -> español para la app)
TRADUCCION_ENFERMEDADES = {
    "Healthy": "Sin anomalias detectadas",
    "Mastitis_Clinical": "Mastitis clinica",
    "Mastitis_Subclinical": "Mastitis subclinica",
    "Foot_and_Mouth": "Fiebre aftosa",
    "Foot_Rot": "Pudricion de pezuna",
    "Laminitis": "Laminitis",
    "Lameness_Clinical": "Cojera clinica",
    "Pneumonia": "Neumonia",
    "Bovine_Respiratory_Disease": "Enfermedad respiratoria bovina",
    "Diarrhea": "Diarrea",
    "Bloat": "Timpanismo (meteorismo)",
    "Acidosis": "Acidosis ruminal",
    "Anaplasmosis": "Anaplasmosis",
    "Babesiosis": "Babesiosis (garrapata)",
    "Internal_Parasites": "Parasitos internos",
    "Brucellosis": "Brucelosis",
    "Bovine_Tuberculosis": "Tuberculosis bovina",
    "Milk_Fever": "Fiebre de leche (hipocalcemia)",
    "Ketosis_Clinical": "Cetosis clinica",
    "Heat_Stress": "Estres calorico",
    "Anthrax": "Carbon bacteridiano (antrax)",
    "Black_Quarter": "Carbon sintomatico",
    "Haemorrhagic_Septicemia": "Septicemia hemorragica",
}


def _build_feature_vector(datos: dict) -> np.ndarray:
    """
    Construye el vector de caracteristicas en el orden correcto a partir
    de un diccionario con llaves en español (las de REGISTROS_SINTOMAS + BOVINOS).

    Si algun valor es None, se rellena con un valor neutro (promedio aproximado
    del dataset de entrenamiento) para no romper la prediccion.
    """
    defaults = {
        "Age_Months": 60.0,
        "Weight_kg": 450.0,
        "Body_Temperature_C": 38.5,
        "Heart_Rate_bpm": 65.0,
        "Respiratory_Rate": 25.0,
        "Milk_Yield_L": 8.0,
        "Body_Condition_Score": 3.0,
        "Feed_Quantity_kg": 12.0,
        "Water_Intake_L": 60.0,
    }

    mapping = {
        "Age_Months": datos.get("edad_meses"),
        "Weight_kg": datos.get("peso_kg"),
        "Body_Temperature_C": datos.get("temperatura"),
        "Heart_Rate_bpm": datos.get("frecuencia_cardiaca"),
        "Respiratory_Rate": datos.get("frecuencia_respiratoria"),
        "Milk_Yield_L": datos.get("produccion_leche"),
        "Body_Condition_Score": datos.get("condicion_corporal"),
        "Feed_Quantity_kg": datos.get("consumo_alimento_kg"),
        "Water_Intake_L": datos.get("consumo_agua_l"),
    }

    valores = []
    for col in _FEATURE_ORDER:
        v = mapping[col]
        valores.append(float(v) if v is not None else defaults[col])

    return np.array([valores])


def predecir_enfermedad(datos: dict) -> dict:
    """
    Ejecuta Random Forest sobre los datos del registro de sintomas.

    `datos` debe ser un dict que puede incluir las llaves:
    edad_meses, peso_kg, temperatura, frecuencia_cardiaca,
    frecuencia_respiratoria, produccion_leche, condicion_corporal,
    consumo_alimento_kg, consumo_agua_l (todas opcionales).

    Retorna:
        {
            "enfermedad": str,          # nombre en español
            "enfermedad_codigo": str,   # nombre original del dataset (ingles)
            "confianza": float,         # 0.0 - 1.0
            "severidad": "leve" | "moderada" | "alta",
            "features_nlp": dict,       # info de soporte para PREDICCIONES.features_nlp
        }
    """
    X = _build_feature_vector(datos)

    pred_idx = _random_forest.predict(X)[0]
    probas = _random_forest.predict_proba(X)[0]
    confianza = float(probas.max())

    enfermedad_codigo = _label_encoder.inverse_transform([pred_idx])[0]
    enfermedad_es = TRADUCCION_ENFERMEDADES.get(enfermedad_codigo, enfermedad_codigo)

    if enfermedad_codigo == "Healthy":
        # Si el modelo predice "sano", la severidad siempre es leve,
        # sin importar que tan alta sea la confianza de esa prediccion.
        severidad = "leve"
    elif confianza >= _UMBRAL_ALTA:
        severidad = "alta"
    elif confianza >= _UMBRAL_MODERADA:
        severidad = "moderada"
    else:
        severidad = "leve"

    # Top 3 enfermedades mas probables, para dar contexto en features_nlp
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

    return {
        "enfermedad": enfermedad_es,
        "enfermedad_codigo": enfermedad_codigo,
        "confianza": round(confianza, 4),
        "severidad": severidad,
        "features_nlp": {
            "modelo": "RandomForest",
            "version_modelo": METADATA.get("version", "1.0"),
            "top_3_predicciones": top3,
            "variables_usadas": _FEATURE_ORDER,
        },
    }


def detectar_anomalia(datos: dict) -> dict:
    """
    Ejecuta Isolation Forest sobre los datos productivos del registro.

    Retorna:
        {
            "es_anomalia": bool,
            "score": float,   # mas negativo = mas anomalo
        }
    """
    X = _build_feature_vector(datos)

    pred = _isolation_forest.predict(X)[0]   # -1 = anomalia, 1 = normal
    score = float(_isolation_forest.score_samples(X)[0])

    return {
        "es_anomalia": bool(pred == -1),
        "score": round(score, 4),
    }
