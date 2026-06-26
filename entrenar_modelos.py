"""
GANAJEC AI — Re-entrenamiento de modelos ML
Dataset: Training.csv / Testing.csv
(Cattle Disease Prediction — síntomas binarios reales)

Arquitectura:
  - 93 features binarias (síntomas veterinarios observables)
  - Data augmentation: síntomas parciales para evitar overfitting
  - Random Forest con class_weight='balanced'
  - HistGradientBoostingClassifier como modelo de apoyo
  - Isolation Forest entrenado solo con animales sanos
  - 26 enfermedades bovinas reales
"""

import pandas as pd
import numpy as np
import pickle, json
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

# ── 1. Cargar datos ──────────────────────────────────────────────
print("Cargando datasets...")
df_train = pd.read_csv("Training.csv")
df_test  = pd.read_csv("Testing.csv")
print(f"Train: {len(df_train)} filas | Test: {len(df_test)} filas")
print(f"Enfermedades: {df_train['prognosis'].nunique()}")

# ── 2. Features: 93 síntomas binarios ────────────────────────────
FEATURES = [c for c in df_train.columns if c != "prognosis"]
print(f"Features: {len(FEATURES)} síntomas binarios")

X_train_orig = df_train[FEATURES].values
y_train_raw  = df_train["prognosis"].values
X_test       = df_test[FEATURES].values
y_test_raw   = df_test["prognosis"].values

# ── 3. Codificar etiquetas ───────────────────────────────────────
le = LabelEncoder()
le.fit(np.concatenate([y_train_raw, y_test_raw]))
y_train_orig = le.transform(y_train_raw)
y_test       = le.transform(y_test_raw)
clases       = list(le.classes_)
print(f"Clases ({len(clases)}): {clases}")

# ── 4. Data Augmentation: síntomas parciales ─────────────────────
# El problema con 100% accuracy en datos perfectos es overfitting:
# el modelo memoriza combinaciones exactas y falla con síntomas parciales.
#
# Solución: por cada ejemplo real, generar N copias con síntomas
# eliminados al azar (el ganadero rara vez reporta TODOS los síntomas).
# Así el modelo aprende a diagnosticar con información incompleta.
print("\nAplicando data augmentation (síntomas parciales)...")

rng = np.random.default_rng(42)
augmented_X = [X_train_orig]
augmented_y = [y_train_orig]

COPIAS_POR_EJEMPLO = 15         # genera 15 versiones parciales por cada caso real
TASA_MIN = 0.2                  # elimina mínimo 20% de los síntomas activos
TASA_MAX = 0.7                  # elimina máximo 70% de los síntomas activos

for _ in range(COPIAS_POR_EJEMPLO):
    X_aug = X_train_orig.copy()
    for i in range(len(X_aug)):
        sintomas_activos = np.where(X_aug[i] == 1)[0]
        if len(sintomas_activos) == 0:
            continue
        tasa   = rng.uniform(TASA_MIN, TASA_MAX)
        n_drop = max(1, int(len(sintomas_activos) * tasa))
        n_drop = min(n_drop, len(sintomas_activos) - 1)
        if n_drop <= 0:
            continue
        a_eliminar = rng.choice(sintomas_activos, size=n_drop, replace=False)
        X_aug[i, a_eliminar] = 0
    augmented_X.append(X_aug)
    augmented_y.append(y_train_orig)

X_train = np.vstack(augmented_X)
y_train = np.concatenate(augmented_y)
idx = rng.permutation(len(X_train))
X_train, y_train = X_train[idx], y_train[idx]

print(f"Dataset original:  {len(X_train_orig)} filas")
print(f"Dataset aumentado: {len(X_train)} filas ({COPIAS_POR_EJEMPLO}x copias parciales + original)")
print(f"Test (sin aumentar): {len(X_test)} filas")

# ── 5. Random Forest (modelo principal) ─────────────────────────
print("\nEntrenando Random Forest...")
rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_leaf=1,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
)
rf.fit(X_train, y_train)
rf_acc = accuracy_score(y_test, rf.predict(X_test))
print(f"Random Forest accuracy: {rf_acc:.4f}")
print(classification_report(y_test, rf.predict(X_test), target_names=clases))

# ── 6. HistGradientBoosting (modelo de apoyo) ────────────────────
print("Entrenando HistGradientBoostingClassifier...")
hgb = HistGradientBoostingClassifier(
    max_iter=300,
    max_depth=None,
    learning_rate=0.1,
    min_samples_leaf=5,
    random_state=42,
)
hgb.fit(X_train, y_train)
hgb_acc = accuracy_score(y_test, hgb.predict(X_test))
print(f"HistGradientBoosting accuracy: {hgb_acc:.4f}")

# ── 7. Isolation Forest (detección de anomalías) ─────────────────
print("\nEntrenando Isolation Forest...")
X_sano = np.zeros((500, len(FEATURES)))
iforest = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42,
    n_jobs=-1,
)
iforest.fit(X_sano)
preds_enfermos = iforest.predict(X_test)
sens = float((preds_enfermos == -1).mean())
print(f"Isolation Forest — detección de enfermos: {sens:.4f}")

# ── 8. Guardar modelos ───────────────────────────────────────────
print("\nGuardando modelos...")
SAVE_DIR = "app/ml/models/"

with open(SAVE_DIR + "random_forest.pkl", "wb") as f:
    pickle.dump(rf, f)

with open(SAVE_DIR + "isolation_forest.pkl", "wb") as f:
    pickle.dump(iforest, f)

with open(SAVE_DIR + "label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

# ── 9. Calcular umbrales de severidad ────────────────────────────
probas_test = rf.predict_proba(X_test)
max_probas  = probas_test.max(axis=1)
umbral_mod  = float(np.percentile(max_probas, 33))
umbral_alta = float(np.percentile(max_probas, 66))
print(f"Umbrales severidad — moderada: {umbral_mod:.3f} | alta: {umbral_alta:.3f}")

# ── 10. Metadata ─────────────────────────────────────────────────
metadata = {
    "version": "3.1",
    "dataset": "Training.csv / Testing.csv + data augmentation",
    "features": FEATURES,
    "n_features": len(FEATURES),
    "n_clases": len(clases),
    "clases": clases,
    "augmentation": {
        "copias_por_ejemplo": COPIAS_POR_EJEMPLO,
        "tasa_eliminacion_min": TASA_MIN,
        "tasa_eliminacion_max": TASA_MAX,
        "filas_totales": len(X_train),
    },
    "metricas": {
        "random_forest_accuracy": round(rf_acc, 4),
        "hgb_accuracy": round(hgb_acc, 4),
        "isolation_forest_deteccion_enfermos": round(sens, 4),
    },
    "umbrales_severidad": {
        "moderada": round(umbral_mod, 4),
        "alta":     round(umbral_alta, 4),
    },
    "notas": {
        "random_forest": f"Modelo principal. {len(clases)} clases. {len(FEATURES)} síntomas binarios. Entrenado con síntomas parciales.",
        "hgb": "HistGradientBoostingClassifier — modelo de apoyo.",
        "isolation_forest": "Entrenado con animales sanos (todos síntomas=0).",
    }
}

with open(SAVE_DIR + "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

# ── 11. Prueba con síntomas parciales (simula uso real del ganadero) ─
# El ganadero rara vez describe TODOS los síntomas. Esta prueba simula
# qué accuracy tiene el modelo cuando solo se reportan algunos síntomas.
print("\n── Prueba con síntomas parciales (uso real) ──")

resultados_parciales = {}
for porcentaje_visible in [0.75, 0.50, 0.30]:
    accs = []
    for _ in range(20):   # 20 repeticiones para estabilizar el resultado
        X_parcial = X_test.copy()
        for i in range(len(X_parcial)):
            activos = np.where(X_parcial[i] == 1)[0]
            if len(activos) == 0:
                continue
            n_mantener = max(1, int(len(activos) * porcentaje_visible))
            a_ocultar  = rng.choice(activos, size=len(activos) - n_mantener, replace=False)
            X_parcial[i, a_ocultar] = 0
        accs.append(accuracy_score(y_test, rf.predict(X_parcial)))
    acc_media = float(np.mean(accs))
    resultados_parciales[f"{int(porcentaje_visible*100)}%"] = round(acc_media, 4)
    print(f"  Síntomas visibles: {int(porcentaje_visible*100)}%  →  Accuracy: {acc_media:.2%}")

# Guardar en metadata
metadata["metricas"]["accuracy_sintomas_parciales"] = resultados_parciales

with open(SAVE_DIR + "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print("\n=== RESUMEN FINAL ===")
print(f"  Random Forest (síntomas completos): {rf_acc:.2%}")
print(f"  HistGradientBoosting:               {hgb_acc:.2%}")
print(f"  IsoForest (enfermos):               {sens:.2%}")
print(f"\n  Accuracy con síntomas parciales (uso real del ganadero):")
for pct, acc in resultados_parciales.items():
    print(f"    El ganadero describe el {pct} de síntomas → {acc:.2%} accuracy")
print(f"\nArchivos guardados en {SAVE_DIR}")
print("Listo — reinicia uvicorn para que cargue los nuevos modelos.")
