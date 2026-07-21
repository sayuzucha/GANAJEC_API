"""
Modulo de Procesamiento de Lenguaje Natural (NLP) de GANAJEC AI.

Procesa el campo `texto_libre` que el ganadero escribe al registrar
sintomas (ej. "el animal tiene fiebre y no quiere comer") y extrae una
lista de sintomas estandarizados.

Arquitectura:
- BETO primario: dccuchile/bert-base-spanish-wwm-cased.
  Genera embeddings de oracion (mean-pooling) y compara por similitud
  coseno el texto libre contra las frases de referencia de cada sintoma.
  El modelo se carga de forma diferida (lazy) en la primera llamada y
  los embeddings de referencia se pre-computan una sola vez al inicio.
- Diccionario de sintomas: ~22 sintomas veterinarios con variantes
  coloquiales en español de Mexico. Se usa como banco de frases de
  referencia para el calculo de similitud, y como metodo de matching
  directo cuando BETO no esta disponible.
- Perfil de enfermedades: relaciona las 26 clases del Random Forest
  con los sintomas esperados para calcular concordancia NLP vs prediccion.
- Fallback: si transformers/torch no estan instalados o no hay red,
  la extraccion cae a matching directo sobre texto normalizado.
"""
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Diccionario de sintomas: codigo estandarizado -> frases de referencia
# ─────────────────────────────────────────────────────────────────────
SYMPTOM_KEYWORDS = {
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
# Perfil de sintomas por enfermedad (26 clases del Random Forest)
# ─────────────────────────────────────────────────────────────────────
DISEASE_SYMPTOM_PROFILE = {
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
# BETO — modelo principal
# dccuchile/bert-base-spanish-wwm-cased
# ─────────────────────────────────────────────────────────────────────
_BETO_MODEL = "dccuchile/bert-base-spanish-wwm-cased"
_UMBRAL_SIMILITUD = 0.80   # umbral de similitud coseno para detectar sintoma

_beto = {
    "intentado": False,
    "disponible": False,
    "tokenizer": None,
    "model": None,
    "emb_sintomas": None,  # dict[str, list[Tensor]] pre-computados
}


def _cargar_beto() -> bool:
    """Carga BETO de forma diferida. Solo lo intenta una vez."""
    if _beto["intentado"]:
        return _beto["disponible"]

    _beto["intentado"] = True
    try:
        from transformers import AutoTokenizer, AutoModel

        logger.info("Cargando BETO (%s)...", _BETO_MODEL)
        tokenizer = AutoTokenizer.from_pretrained(_BETO_MODEL)
        model = AutoModel.from_pretrained(_BETO_MODEL)
        model.eval()

        _beto["tokenizer"] = tokenizer
        _beto["model"] = model
        _beto["emb_sintomas"] = _precomputar_embeddings(tokenizer, model)
        _beto["disponible"] = True
        logger.info("BETO listo. Embeddings de %d sintomas pre-computados.", len(_beto["emb_sintomas"]))
    except Exception as exc:
        logger.warning("BETO no disponible (%s). Usando fallback de diccionario.", exc)
        _beto["disponible"] = False

    return _beto["disponible"]


def _embed(tokenizer, model, texto: str):
    """Embedding de oracion via BETO (mean-pooling sobre tokens validos)."""
    import torch

    inputs = tokenizer(
        texto,
        return_tensors="pt",
        truncation=True,
        max_length=128,
        padding=True,
    )
    with torch.no_grad():
        out = model(**inputs)

    # Mean pooling
    token_embs = out.last_hidden_state          # (1, seq_len, hidden)
    mask = inputs["attention_mask"].unsqueeze(-1).expand(token_embs.size()).float()
    return (token_embs * mask).sum(1) / mask.sum(1).clamp(min=1e-9)   # (1, hidden)


def _precomputar_embeddings(tokenizer, model) -> dict:
    """
    Pre-computa embeddings para TODAS las frases de referencia de cada sintoma.
    Devuelve  dict[codigo -> list[Tensor]].
    Solo se ejecuta una vez al cargar el modelo.
    """
    embs = {}
    for codigo, frases in SYMPTOM_KEYWORDS.items():
        embs[codigo] = [_embed(tokenizer, model, f) for f in frases]
    return embs


# ─────────────────────────────────────────────────────────────────────
# Utilidades de texto
# ─────────────────────────────────────────────────────────────────────
def _normalizar(texto: str) -> str:
    """Minusculas, sin acentos, espacios colapsados."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return f" {texto} "


# ─────────────────────────────────────────────────────────────────────
# Extraccion de sintomas
# ─────────────────────────────────────────────────────────────────────
def extraer_sintomas(texto_libre: str) -> list[str]:
    """
    Extrae sintomas del texto libre.

    - Primario: BETO (similitud semantica, umbral=_UMBRAL_SIMILITUD).
    - Fallback: matching directo sobre texto normalizado si BETO no esta disponible.

    Retorna lista sin duplicados de codigos de sintoma detectados,
    ej: ["fiebre", "decaimiento", "anorexia"].
    """
    if not texto_libre:
        return []

    if _cargar_beto():
        return _extraer_beto(texto_libre)

    return _extraer_diccionario(texto_libre)


def _extraer_beto(texto: str) -> list[str]:
    """
    Compara el embedding del texto contra los embeddings pre-computados
    de cada sintoma. Detecta el sintoma si la similitud maxima
    entre el texto y cualquiera de sus frases de referencia >= _UMBRAL_SIMILITUD.
    """
    import torch

    tokenizer = _beto["tokenizer"]
    model     = _beto["model"]
    emb_sints = _beto["emb_sintomas"]

    emb_texto = _embed(tokenizer, model, texto)

    detectados = []
    for codigo, embs_frases in emb_sints.items():
        similitudes = [
            torch.nn.functional.cosine_similarity(emb_texto, emb_f).item()
            for emb_f in embs_frases
        ]
        if max(similitudes) >= _UMBRAL_SIMILITUD:
            detectados.append(codigo)

    return detectados


def _extraer_diccionario(texto: str) -> list[str]:
    """
    Fallback sin BETO: matching exacto de frases sobre texto normalizado.
    No requiere ninguna dependencia externa.
    """
    texto_norm = _normalizar(texto)
    detectados = []
    for codigo, frases in SYMPTOM_KEYWORDS.items():
        for frase in frases:
            frase_norm = _normalizar(frase).strip()
            if frase_norm and frase_norm in texto_norm:
                detectados.append(codigo)
                break
    return detectados


# ─────────────────────────────────────────────────────────────────────
# Concordancia NLP vs prediccion Random Forest
# ─────────────────────────────────────────────────────────────────────
def calcular_concordancia(sintomas_detectados: list[str], enfermedad_codigo: str) -> float | None:
    """
    Proporcion de sintomas tipicos de la enfermedad que aparecen
    en el texto del ganadero.

    - "Healthy": 1.0 si no hay ningun sintoma, decrece 0.2 por cada uno.
    - Enfermedades: |interseccion| / |perfil_tipico|.
    - Retorna None si la enfermedad no tiene perfil definido.
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


# ─────────────────────────────────────────────────────────────────────
# Punto de entrada principal
# ─────────────────────────────────────────────────────────────────────
def analizar_texto(texto_libre: str, enfermedad_codigo: str = None) -> dict:
    """
    Analiza el texto libre del ganadero y devuelve sintomas detectados
    y (opcionalmente) concordancia con la prediccion del Random Forest.

    Interfaz compatible con ganadero_controller.py:
        resultado_nlp = nlp.analizar_texto(data.texto_libre)

    Retorna:
        {
            "sintomas_detectados": list[str],
            "modelo_nlp": str,
            "beto_disponible": bool,
            "concordancia_con_prediccion": float | None,  # solo si se pasa enfermedad_codigo
        }
    """
    sintomas = extraer_sintomas(texto_libre)
    beto_ok = _beto["disponible"]  # ya se intento dentro de extraer_sintomas()

    resultado = {
        "sintomas_detectados": sintomas,
        "modelo_nlp": (
            f"BETO ({_BETO_MODEL}) - similitud semantica"
            if beto_ok
            else "Diccionario de keywords (BETO no disponible)"
        ),
        "beto_disponible": beto_ok,
    }

    if enfermedad_codigo is not None:
        resultado["concordancia_con_prediccion"] = calcular_concordancia(
            sintomas, enfermedad_codigo
        )

    return resultado
