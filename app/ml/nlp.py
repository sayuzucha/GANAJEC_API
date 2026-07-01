"""
Modulo de Procesamiento de Lenguaje Natural (NLP) de GANAJEC AI.

Procesa el campo `texto_libre` que el ganadero escribe al registrar
sintomas (ej. "el animal tiene fiebre y no quiere comer") y extrae una
lista de sintomas estandarizados.

Arquitectura:
- spaCy (es): tokenizacion y normalizacion del texto en español.
  Usa `spacy.blank("es")`, que NO requiere descargar un modelo entrenado
  (los modelos pre-entrenados de spaCy no son descargables en este entorno
  por restricciones de red, pero el paquete base si incluye tokenizador
  y stopwords en español).
- Diccionario de sintomas: ~20 sintomas veterinarios comunes en bovinos,
  con sus variantes/expresiones coloquiales en español de Mexico.
- Perfil de enfermedades: relaciona cada enfermedad del modelo Random Forest
  con los sintomas que tipicamente la acompañan, para calcular que tan bien
  el texto del ganadero "concuerda" con la prediccion de Random Forest.
- DistilBETO (opcional): si en el servidor de despliegue estan instalados
  `transformers` + `torch` y hay acceso a internet a huggingface.co, se
  activa automaticamente un analisis semantico adicional con el modelo
  "dccuchile/distilbert-base-spanish-uncased". Si no esta disponible
  (como en este entorno de desarrollo), el modulo sigue funcionando solo
  con spaCy + el diccionario de reglas.
"""
import re
import unicodedata
import spacy

_nlp = spacy.blank("es")

# ─────────────────────────────────────────────────────────────────────
# Diccionario de sintomas: codigo estandarizado -> frases en español
# que indican ese sintoma. Las frases ya estan normalizadas (minusculas,
# sin acentos) para comparar contra el texto normalizado.
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
        "tose", "tos seca", "tos constante", " tos ", "tosiendo",
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
# Perfil de sintomas por enfermedad. Usa los mismos codigos de
# `Disease_Status` del dataset (los que produce Random Forest en
# app/ml/predictor.py). "Healthy" = sin sintomas esperados.
# ─────────────────────────────────────────────────────────────────────
DISEASE_SYMPTOM_PROFILE = {
    # ── Enfermedades del dataset Training.csv (26 clases) ──────────
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


def _normalizar(texto: str) -> str:
    """Minusculas, sin acentos, espacios colapsados."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return f" {texto} "  # padding para que " tos " no choque con "tos" dentro de otra palabra


def extraer_sintomas(texto_libre: str) -> list[str]:
    """
    Tokeniza el texto con spaCy y busca coincidencias del diccionario
    SYMPTOM_KEYWORDS sobre el texto normalizado.

    Retorna una lista (sin duplicados, orden estable) de codigos de
    sintoma detectados, ej: ["fiebre", "decaimiento", "anorexia"]
    """
    if not texto_libre:
        return []

    # spaCy tokeniza y normaliza espacios/puntuacion antes de la busqueda
    doc = _nlp(texto_libre.lower())
    texto_tokenizado = " ".join(t.text for t in doc if not t.is_space)
    texto_norm = _normalizar(texto_tokenizado)

    detectados = []
    for codigo, frases in SYMPTOM_KEYWORDS.items():
        for frase in frases:
            if _normalizar(frase).strip() and _normalizar(frase) in texto_norm or f" {frase} " in texto_norm:
                detectados.append(codigo)
                break

    return detectados


def calcular_concordancia(sintomas_detectados: list[str], enfermedad_codigo: str) -> float | None:
    """
    Calcula que tan bien los sintomas detectados en el texto coinciden
    con el perfil tipico de la enfermedad predicha por Random Forest.

    Retorna un valor entre 0.0 y 1.0, o None si la enfermedad no tiene
    perfil definido.

    - Para "Healthy": 1.0 si no se detecto ningun sintoma, decreciendo
      por cada sintoma detectado (un texto con muchos sintomas no
      concuerda con "sano").
    - Para enfermedades: proporcion del perfil tipico que aparece en
      los sintomas detectados.
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
# DistilBETO (opcional) — analisis semantico adicional.
#
# Requiere `pip install transformers torch` y acceso a internet a
# huggingface.co para descargar "dccuchile/distilbert-base-spanish-uncased"
# la primera vez. En este entorno de desarrollo NO esta disponible
# (la descarga del modelo esta bloqueada por la red del sandbox), por lo
# que `distilbeto_disponible` sera False y el analisis se basa solo en
# spaCy + el diccionario de reglas. En el servidor de despliegue, si las
# dependencias estan instaladas, se activa automaticamente.
# ─────────────────────────────────────────────────────────────────────
_distilbeto_estado = {"intentado": False, "disponible": False, "tokenizer": None, "model": None}


def _cargar_distilbeto():
    if _distilbeto_estado["intentado"]:
        return _distilbeto_estado["disponible"]

    _distilbeto_estado["intentado"] = True
    try:
        from transformers import AutoTokenizer, AutoModel  # noqa: F401
        import torch  # noqa: F401

        tokenizer = AutoTokenizer.from_pretrained("dccuchile/distilbert-base-spanish-uncased")
        model = AutoModel.from_pretrained("dccuchile/distilbert-base-spanish-uncased")
        model.eval()

        _distilbeto_estado["tokenizer"] = tokenizer
        _distilbeto_estado["model"] = model
        _distilbeto_estado["disponible"] = True
    except Exception:
        _distilbeto_estado["disponible"] = False

    return _distilbeto_estado["disponible"]


def _similitud_distilbeto(texto: str, frases: list[str]) -> dict:
    """
    Calcula la similitud coseno entre el embedding de `texto` y el de
    cada frase en `frases`, usando los embeddings [CLS] de DistilBETO.
    Solo se llama si _cargar_distilbeto() retorno True.
    """
    import torch

    tokenizer = _distilbeto_estado["tokenizer"]
    model = _distilbeto_estado["model"]

    def embed(s: str):
        tokens = tokenizer(s, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            out = model(**tokens)
        return out.last_hidden_state[:, 0, :]  # embedding del token [CLS]

    emb_texto = embed(texto)
    resultados = {}
    for frase in frases:
        emb_frase = embed(frase)
        sim = torch.nn.functional.cosine_similarity(emb_texto, emb_frase).item()
        resultados[frase] = round(sim, 4)

    return resultados


def analizar_texto(texto_libre: str, enfermedad_codigo: str = None) -> dict:
    """
    Punto de entrada principal del modulo NLP.

    Retorna:
        {
            "sintomas_detectados": [...],
            "modelo_nlp": "spaCy (es) + diccionario de sintomas",
            "distilbeto_disponible": bool,
            "concordancia_con_prediccion": float | None,
        }
    """
    sintomas = extraer_sintomas(texto_libre)

    resultado = {
        "sintomas_detectados": sintomas,
        "modelo_nlp": "spaCy (es) + diccionario de sintomas veterinarios",
        "distilbeto_disponible": _cargar_distilbeto(),
    }

    if enfermedad_codigo is not None:
        resultado["concordancia_con_prediccion"] = calcular_concordancia(sintomas, enfermedad_codigo)

    # Si DistilBETO esta disponible (servidor con internet), agrega un
    # analisis semantico adicional comparando el texto contra los
    # nombres de los sintomas detectados.
    if resultado["distilbeto_disponible"] and sintomas:
        try:
            frases_referencia = [SYMPTOM_KEYWORDS[s][0] for s in sintomas]
            resultado["similitud_semantica_distilbeto"] = _similitud_distilbeto(texto_libre, frases_referencia)
        except Exception:
            pass

    return resultado
