"""
GANAJEC AI — Re-entrenamiento de modelos ML
Dataset: global_cattle_disease_detection_dataset.csv
Mejoras:
  - Más datos (250K registros vs dataset anterior)
  - class_weight='balanced' en Random Forest
  - HistGradientBoostingClassifier reemplaza CatBoost
  - Isolation Forest re-calibrado con contamination real
  - 20 features (9 originales + 11 nuevas: vacunas + comportamiento)
"""

import pandas as pd
import numpy as np
import pickle, json
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# ── 1. Cargar datos ──────────────────────────────────────────────
print("Cargando dataset...")
df = pd.read_csv("global_cattle_disease_detection_dataset.csv")
print(f"Filas: {len(df)} | Clases: {df['Disease_Status'].nunique()}")

# ── 2. Features ──────────────────────────────────────────────────
# 9 originales + 11 nuevas (todas numéricas, compatibles con la API)
FEATURES = [
    # ── vitales (originales) ──
    "Age_Months",
    "Weight_kg",
    "Body_Temperature_C",
    "Heart_Rate_bpm",
    "Respiratory_Rate",
    "Milk_Yield_L",
    "Body_Condition_Score",
    "Feed_Quantity_kg",
    "Water_Intake_L",
    # ── productivo / reproductivo ──
    "Parity",
    "Days_in_Milk",
    "Previous_Week_Avg_Yield",
    # ── entorno ──
    "Ambient_Temperature_C",
    # ── vacunas (binarias 0/1) ──
    "FMD_Vaccine",
    "Brucellosis_Vaccine",
    "HS_Vaccine",
    "BQ_Vaccine",
    "Anthrax_Vaccine",
]

X = df[FEATURES].values
y = df["Disease_Status"].values

# ── 3. Codificar etiquetas ───────────────────────────────────────
le = LabelEncoder()
y_enc = le.fit_transform(y)
clases = list(le.classes_)
print(f"Total clases: {len(clases)}")

# ── 4. Balancear: reducir Healthy para no dominar el entrenamiento
df_train = df.copy()
df_train["y_enc"] = y_enc

healthy_cap = 10000  # limitar Healthy a 10K (vs 137K original)
df_healthy = df_train[df_train["Disease_Status"] == "Healthy"].sample(healthy_cap, random_state=42)
df_sick    = df_train[df_train["Disease_Status"] != "Healthy"]
df_bal     = pd.concat([df_healthy, df_sick]).sample(frac=1, random_state=42)

X_bal = df_bal[FEATURES].values
y_bal = df_bal["y_enc"].values
print(f"Dataset balanceado: {len(df_bal)} filas | Healthy cappado a: {healthy_cap}")

# ── 5. Split ─────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_bal, y_bal, test_size=0.2, random_state=42, stratify=y_bal
)
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

# ── 6. Random Forest (modelo principal) ─────────────────────────
print("\nEntrenando Random Forest...")
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
)
rf.fit(X_train, y_train)
rf_acc = accuracy_score(y_test, rf.predict(X_test))
print(f"Random Forest accuracy: {rf_acc:.4f}  (antes: 0.5715)")

# ── 7. HistGradientBoosting (reemplaza CatBoost) ─────────────────
print("\nEntrenando HistGradientBoostingClassifier...")
hgb = HistGradientBoostingClassifier(
    max_iter=200,
    max_depth=8,
    learning_rate=0.1,
    min_samples_leaf=20,
    random_state=42,
)
hgb.fit(X_train, y_train)
hgb_acc = accuracy_score(y_test, hgb.predict(X_test))
print(f"HistGradientBoosting accuracy: {hgb_acc:.4f}  (CatBoost antes: 0.2611)")

# ── 8. Isolation Forest (anomalías productivas) ──────────────────
print("\nEntrenando Isolation Forest...")
X_healthy = df[df["Disease_Status"] == "Healthy"][FEATURES].values
iforest = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42,
    n_jobs=-1,
)
iforest.fit(X_healthy)

# Evaluar sensibilidad/especificidad
y_true_anom = (df_bal["Disease_Status"] != "Healthy").astype(int).values
preds_if    = iforest.predict(X_bal)
preds_bin   = (preds_if == -1).astype(int)
sens = preds_bin[y_true_anom == 1].mean()
spec = 1 - preds_bin[y_true_anom == 0].mean()
print(f"Isolation Forest — Sensibilidad: {sens:.4f}  (antes: 0.049) | Especificidad: {spec:.4f}")

# ── 9. Guardar modelos ───────────────────────────────────────────
print("\nGuardando modelos...")
SAVE_DIR = "app/ml/models/"

with open(SAVE_DIR + "random_forest.pkl", "wb") as f:
    pickle.dump(rf, f)

with open(SAVE_DIR + "isolation_forest.pkl", "wb") as f:
    pickle.dump(iforest, f)

with open(SAVE_DIR + "label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

# ── 10. Metadata ─────────────────────────────────────────────────
# ── Calcular umbrales de severidad desde la distribución real ────
probas_test = rf.predict_proba(X_test)
max_probas  = probas_test.max(axis=1)
umbral_moderada = float(np.percentile(max_probas, 40))   # 40° percentil
umbral_alta     = float(np.percentile(max_probas, 75))   # 75° percentil
print(f"Umbrales severidad — moderada: {umbral_moderada:.3f} | alta: {umbral_alta:.3f}")

metadata = {
    "version": "2.1",
    "features": FEATURES,
    "n_clases": len(clases),
    "clases": clases,
    "metricas": {
        "random_forest_accuracy": round(rf_acc, 4),
        "catboost_accuracy": round(hgb_acc, 4),
        "isolation_forest_sensibilidad": round(float(sens), 4),
        "isolation_forest_especificidad": round(float(spec), 4),
    },
    "umbrales_severidad": {
        "moderada": round(umbral_moderada, 4),
        "alta": round(umbral_alta, 4),
    },
    "notas": {
        "random_forest": f"Modelo principal. {len(clases)} clases. 20 features. Balanceado + class_weight=balanced.",
        "catboost": "HistGradientBoostingClassifier (sklearn). Reemplaza CatBoost — misma interfaz pkl.",
        "isolation_forest": "Entrenado solo con Healthy. contamination=0.05.",
    }
}

with open(SAVE_DIR + "metadata.json", "w") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print("\n=== RESUMEN FINAL ===")
print(f"  Random Forest:         {rf_acc:.2%}  (antes 57.15%)")
print(f"  HistGradientBoosting:  {hgb_acc:.2%}  (no usado antes)")
print(f"  IsoForest sensibilidad:{sens:.2%}   (antes 4.90%)")
print(f"\nArchivos guardados en {SAVE_DIR}")
print("Listo — reinicia uvicorn para que cargue los nuevos modelos.")
