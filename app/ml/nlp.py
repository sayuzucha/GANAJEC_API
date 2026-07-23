"""
Módulo NLP de GANAJEC AI — BETO como motor principal.

Motor primario : dccuchile/bert-base-spanish-wwm-cased (BETO)
  - Embeddings de texto con mean-pooling sobre los hidden states.
  - Los embeddings de los ~20 síntomas se pre-computan al arrancar la API
    y se cachean; solo se hace 1 forward-pass por petición.
  - Similitud coseno texto → síntoma; umbral configurable (BETO_THRESHOLD).

Motor de respaldo : spaCy (es) + diccionario de reglas
  - Se activa automáticamente si BETO no se puede cargar (sin internet,
    sin torch/transformers, o fallo de red a HuggingFace).
  - Misma interfaz de retorno; el campo "modelo_nlp" indica cuál se usó.
"""

import re
import unicodedata
import logging
import spacy

logger = logging.getLogger(__name__)

_nlp_spacy = spacy.blank("es")

# ─────────────────────────────────────────────────────────────────────
# Diccionario de síntomas: código estandarizado → frases en español.
# Se usa tanto como vocabulario de referencia para BETO (embeddings)
# como fallback completo en el modo reglas.
# ─────────────────────────────────────────────────────────────────────
SYMPTOM_KEYWORDS: dict[str, list[str]] = {
    "fiebre": [
        "fiebre", "calentura", "temperatura alta", "esta caliente",
        "muy caliente", "tiene temperatura",
    ],
    "cojera": [
        "cojea", "cojera", "renco", "renguea", "no camina bien",
        "claudica", "pata coja", "cojeando",
    ],
    "decaimiento": [
        "decaido", "decaida", "debil", "debilidad", "sin energia",
        "apatico", "apatica", "letargo", "muy quieto", "no se mueve",
        "tirado", "echado todo el dia",
    ],
    "anorexia": [
        "no come", "no quiere comer", "dejo de comer",
        "perdida de apetito", "no tiene hambre", "deja de comer",
        "come poco",
    ],
    "diarrea": [
        "diarrea", "excremento liquido", "heces blandas",
        "popo liquido", "evacuaciones liquidas", "excremento aguado",
    ],
    "tos": [
        "tose", "tos seca", "tos constante", "tos", "tosiendo",
    ],
    "dificultad_respiratoria": [
        "respira con dificultad", "le falta el aire", "jadea", "jadeo",
        "respiracion agitada", "dificultad para respirar",
        "respira rapido", "respiracion pesada",
    ],
    "secrecion_nasal": [
        "mocos", "secrecion nasal", "flujo nasal", "nariz escurre",
        "moco en la nariz", "escurrimiento nasal",
    ],
    "secrecion_ocular": [
        "ojos llorosos", "lagañas", "secrecion en los ojos",
        "ojos irritados", "legañas", "ojos rojos",
    ],
    "hinchazon_ubre": [
        "ubre inflamada", "ubre hinchada", "ubre caliente",
        "leche con grumos", "leche con sangre", "leche cortada",
        "mastitis", "bulto en la ubre",
    ],
    "baja_produccion_leche": [
        "baja produccion", "produce menos leche", "dejo de producir",
        "menos leche de lo normal", "bajo la leche", "ya no da leche",
    ],
    "distension_abdominal": [
        "panza inflada", "vientre inflamado", "distension abdominal",
        "se hincho la panza", "timpanismo", "panza hinchada",
    ],
    "lesiones_piel": [
        "llagas", "ronchas", "ampollas", "lesiones en la piel",
        "heridas en la piel", "nodulos en la piel", "granos en la piel",
        "costras en la piel",
    ],
    "ampollas_boca": [
        "ampollas en la boca", "llagas en la boca", "boca con llagas",
        "ampollas en los labios", "lesiones en la boca",
        "ampollas en las pezuñas",
    ],
    "temblores": [
        "temblores", "tiembla", "convulsiones", "se sacude",
        "temblando",
    ],
    "salivacion_excesiva": [
        "babea mucho", "salivacion excesiva", "mucha saliva",
        "babeo constante", "babea demasiado",
    ],
    "hinchazon_cuello": [
        "hinchazon en el cuello", "se hincho el cuello",
        "inflamacion en el pecho", "hinchazon en el pecho",
        "crepita al tocar", "bulto en el cuello",
    ],
    "garrapatas": [
        "garrapatas", "tiene garrapatas", "lleno de garrapatas",
        "infestado de garrapatas", "con muchas garrapatas",
    ],
    "perdida_peso": [
        "bajo de peso", "perdida de peso", "esta muy flaco",
        "adelgazo", "se ve mas flaco", "perdiendo peso",
    ],
    "ganglios_inflamados": [
        "ganglios inflamados", "nodulos inflamados", "bolas en el cuello",
        "inflamacion de ganglios", "ganglios hinchados",
    ],
    "debilidad_posparto": [
        "no se puede levantar", "recien parida y debil",
        "se cayo despues del parto", "no se levanta",
        "no puede pararse",
    ],
    "aliento_cetonas": [
        "aliento dulce", "huele a acetona", "aliento a manzana",
        "aliento raro y dulce",
    ],
}

# ─────────────────────────────────────────────────────────────────────
# Perfil de síntomas por enfermedad (para calcular concordancia).
# ─────────────────────────────────────────────────────────────────────
DISEASE_SYMPTOM_PROFILE: dict[str, set[str]] = {
    "acetonaemia":                   {"aliento_cetonas", "anorexia", "baja_produccion_leche", "decaimiento"},
    "blackleg":                      {"fiebre", "cojera", "hinchazon_cuello", "decaimiento"},
    "bloat":                         {"distension_abdominal", "decaimiento", "anorexia"},
    "calf_diphtheria":               {"salivacion_excesiva", "ampollas_boca", "fiebre", "anorexia"},
    "calf_pneumonia":                {"fiebre", "tos", "dificultad_respiratoria", "secrecion_nasal", "decaimiento"},
    "coccidiosis":                   {"diarrea", "decaimiento", "anorexia", "perdida_peso"},
    "cryptosporidiosis":             {"diarrea", "decaimiento", "anorexia"},
    "displaced_abomasum":            {"distension_abdominal", "anorexia", "baja_produccion_leche", "decaimiento"},
    "fatty_liver_syndrome":          {"anorexia", "decaimiento", "aliento_cetonas", "perdida_peso"},
    "fog_fever":                     {"dificultad_respiratoria", "fiebre", "decaimiento"},
    "foot_and_mouth":                {"fiebre", "cojera", "ampollas_boca", "salivacion_excesiva", "lesiones_piel"},
    "foot_rot":                      {"cojera", "lesiones_piel", "fiebre"},
    "gut_worms":                     {"diarrea", "perdida_peso", "decaimiento", "anorexia"},
    "infectious_bovine_rhinotracheitis": {"fiebre", "tos", "secrecion_nasal", "secrecion_ocular", "decaimiento"},
    "listeriosis":                   {"temblores", "decaimiento", "anorexia", "fiebre"},
    "liver_fluke":                   {"perdida_peso", "decaimiento", "ganglios_inflamados", "anorexia"},
    "mastitis":                      {"hinchazon_ubre", "fiebre", "baja_produccion_leche", "decaimiento"},
    "necrotic_enteritis":            {"diarrea", "decaimiento", "anorexia", "distension_abdominal"},
    "peri_weaning_diarrhoea":        {"diarrea", "decaimiento", "anorexia"},
    "ragwort_poisoning":             {"decaimiento", "perdida_peso", "anorexia"},
    "rift_valley_fever":             {"fiebre", "diarrea", "secrecion_nasal", "decaimiento"},
    "rumen_acidosis":                {"distension_abdominal", "diarrea", "anorexia", "salivacion_excesiva"},
    "schmallen_berg_virus":          {"fiebre", "diarrea", "decaimiento"},
    "traumatic_reticulitis":         {"anorexia", "distension_abdominal", "decaimiento"},
    "trypanosomosis":                {"fiebre", "decaimiento", "perdida_peso", "anorexia", "garrapatas"},
    "wooden_tongue":                 {"salivacion_excesiva", "ampollas_boca", "hinchazon_cuello", "anorexia"},
}

# ─────────────────────────────────────────────────────────────────────
# Estado de BETO
# ─────────────────────────────────────────────────────────────────────
_beto: dict = {
    "intentado": False,
    "disponible": False,
    "tokenizer": None,
    "model": None,
    "embeddings_sintomas": {},   # código → Tensor (1, hidden)
}

# Umbral de similitud coseno para considerar un síntoma detectado.
# BETO wwm-cased con mean-pooling suele dar ~0.88-0.95 para frases
# semánticamente idénticas y ~0.65-0.75 para frases no relacionadas.
BETO_THRESHOLD = 0.82


def _cargar_beto() -> bool:
    """Carga BETO una sola vez. Retorna True si está disponible."""
    if _beto["intentado"]:
        return _beto["disponible"]

    _beto["intentado"] = True
    try:
        from transformers import AutoTokenizer, AutoModel  # noqa: F401
        import torch  # noqa: F401

        logger.info("[NLP] Cargando BETO (dccuchile/bert-base-spanish-wwm-cased)…")
        tok = AutoTokenizer.from_pretrained("dccuchile/bert-base-spanish-wwm-cased")
        mod = AutoModel.from_pretrained("dccuchile/bert-base-spanish-wwm-cased")
        mod.eval()

        _beto["tokenizer"] = tok
        _beto["model"] = mod
        _beto["disponible"] = True

        # Pre-computar embeddings de síntomas al arrancar (se cachean)
        _precomputar_embeddings_sintomas()
        logger.info("[NLP] BETO cargado y embeddings de síntomas pre-computados.")
    except Exception as exc:
        logger.warning(f"[NLP] BETO no disponible ({exc}). Usando reglas.")
        _beto["disponible"] = False

    return _beto["disponible"]


def _mean_pool(last_hidden_state, attention_mask):
    """Mean pooling sobre los token embeddings (excluye padding)."""
    import torch
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    return torch.sum(last_hidden_state * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)


def _embed(texto: str):
    """Embedding BETO con mean-pooling para un texto dado."""
    import torch
    import torch.nn.functional as F
    tok = _beto["tokenizer"]
    mod = _beto["model"]
    inputs = tok(
        texto,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=64,
    )
    with torch.no_grad():
        out = mod(**inputs)
    emb = _mean_pool(out.last_hidden_state, inputs["attention_mask"])
    return F.normalize(emb, p=2, dim=1)  # normalizado → cosine = dot product


def _precomputar_embeddings_sintomas():
    """
    Pre-computa el embedding BETO de cada síntoma como la media de los
    embeddings de sus 3 primeras frases representativas.
    Se llama una sola vez al cargar el módulo.
    """
    import torch
    cache = _beto["embeddings_sintomas"]
    for codigo, frases in SYMPTOM_KEYWORDS.items():
        embs = [_embed(f) for f in frases[:3]]
        cache[codigo] = torch.mean(torch.stack(embs), dim=0)


def _extraer_con_beto(texto_libre: str) -> list[str]:
    """
    Extrae síntomas usando BETO:
    1. Embedding del texto completo (mean-pool, normalizado).
    2. Similitud coseno contra cada embedding de síntoma pre-computado.
    3. Se reporta el síntoma si similitud ≥ BETO_THRESHOLD.

    Solo 1 forward-pass de BETO por petición.
    """
    import torch

    cache = _beto["embeddings_sintomas"]
    emb_texto = _embed(texto_libre)           # (1, hidden)

    detectados = []
    for codigo, emb_sint in cache.items():
        # Ambos están normalizados → similitud coseno = producto punto
        sim = torch.mm(emb_texto, emb_sint.t()).item()
        if sim >= BETO_THRESHOLD:
            detectados.append(codigo)

    return detectados


# ─────────────────────────────────────────────────────────────────────
# Modo fallback: spaCy + diccionario de reglas
# ─────────────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return f" {texto} "


def _extraer_con_reglas(texto_libre: str) -> list[str]:
    doc = _nlp_spacy(texto_libre.lower())
    texto_norm = _normalizar(" ".join(t.text for t in doc if not t.is_space))

    detectados = []
    for codigo, frases in SYMPTOM_KEYWORDS.items():
        for frase in frases:
            frase_norm = _normalizar(frase).strip()
            if frase_norm and (frase_norm in texto_norm or f" {frase_norm} " in texto_norm):
                detectados.append(codigo)
                break

    return detectados


# ─────────────────────────────────────────────────────────────────────
# API pública del módulo
# ─────────────────────────────────────────────────────────────────────

def extraer_sintomas(texto_libre: str) -> list[str]:
    """
    Extrae síntomas del texto libre.
    Motor: BETO si está disponible, reglas en caso contrario.
    """
    if not texto_libre:
        return []
    if _cargar_beto():
        try:
            return _extraer_con_beto(texto_libre)
        except Exception as exc:
            logger.warning(f"[NLP] Error en BETO, usando reglas: {exc}")
    return _extraer_con_reglas(texto_libre)


def calcular_concordancia(sintomas_detectados: list[str], enfermedad_codigo: str) -> float | None:
    """
    Proporción de síntomas del perfil típico de la enfermedad que
    aparecen en los síntomas detectados (0.0–1.0).
    Retorna None si la enfermedad no tiene perfil definido.
    """
    perfil = DISEASE_SYMPTOM_PROFILE.get(enfermedad_codigo)
    if perfil is None:
        return None

    if enfermedad_codigo == "Healthy":
        if not sintomas_detectados:
            return 1.0
        return max(0.0, 1.0 - 0.2 * len(sintomas_detectados))

    if not perfil:
        return None

    interseccion = set(sintomas_detectados) & perfil
    return round(len(interseccion) / len(perfil), 4)


def analizar_texto(texto_libre: str) -> dict:
    """
    Punto de entrada principal del módulo NLP.

    Retorna:
        {
            "sintomas_detectados": ["anorexia", "secrecion_ocular", ...],
            "modelo_nlp": "BETO (dccuchile/bert-base-spanish-wwm-cased)" | "spaCy + reglas",
            "beto_disponible": bool,
            "concordancia_con_prediccion": float | None,  # se rellena en el controller
        }
    """
    beto_ok = _cargar_beto()
    sintomas = extraer_sintomas(texto_libre)

    return {
        "sintomas_detectados": sintomas,
        "modelo_nlp": (
            "BETO (dccuchile/bert-base-spanish-wwm-cased)"
            if beto_ok
            else "spaCy (es) + diccionario de síntomas veterinarios"
        ),
        "beto_disponible": beto_ok,
        # concordancia_con_prediccion se agrega en ganadero_controller
        # después de obtener el resultado de Random Forest
    }
