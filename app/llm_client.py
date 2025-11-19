import json
import re
from functools import lru_cache
from typing import Any

from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL, PROMPTS_DIR, ensure_config_ok
from app.schemas import LlmCorrection, ValidationError


def get_groq_client() -> Groq:
    """
    Initialise et retourne un client Groq.
    La clé est lue dans le .env via config.py.
    """
    ensure_config_ok()
    return Groq(api_key=GROQ_API_KEY)


# =======================
# 1. Chargement du prompt système depuis un fichier
# =======================

@lru_cache(maxsize=1)
def build_system_prompt() -> str:
    """
    Lit le prompt système depuis prompts/system_debugger.txt.
    Utilise un cache pour éviter de relire le fichier à chaque appel.
    """
    prompt_file = PROMPTS_DIR / "system_debugger.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Fichier de prompt système introuvable : {prompt_file}"
        )
    return prompt_file.read_text(encoding="utf-8")


def build_user_prompt(
    file_path: str,
    code_source: str,
    traceback_text: str,
    return_code: int,
) -> str:
    """
    Prompt utilisateur : injecte le cas concret (code + erreur).
    """
    return (
        "Voici un script Python qui a échoué à l’exécution.\n\n"
        f"Contexte :\n"
        f"- Fichier : {file_path}\n"
        f"- Code de retour : {return_code}\n\n"
        "Code source :\n"
        "```python\n"
        f"{code_source}\n"
        "```\n\n"
        "Traceback (erreur complète) :\n"
        "```text\n"
        f"{traceback_text}\n"
        "```\n\n"
        "Tâche :\n"
        "- Analyse le code et le traceback.\n"
        "- Propose des corrections sous la forme du JSON décrit dans le message système.\n"
        "- N’oublie pas : pas de texte en dehors du JSON.\n"
    )


# =======================
# 2. Extraction robuste de JSON
# =======================

def extract_json_from_text(text: str) -> str:
    """
    Tente d'extraire un JSON valide à partir d'un texte.
    Gère les cas où le modèle met le JSON dans ```json ... ```.

    Stratégie :
    - Si un bloc ```json ... ``` est présent, on prend ce bloc.
    - Sinon, on cherche du premier '{' au dernier '}'.
    """
    # 1) Chercher un bloc ```json ... ```
    code_block_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 2) Fallback : tout ce qui est entre le premier '{' et le dernier '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        raise ValueError("Impossible de trouver un JSON dans la réponse du modèle.")

    return text[first_brace : last_brace + 1].strip()


# =======================
# 3. Appel au LLM + validation JSON
# =======================

def get_llm_correction(
    file_path: str,
    code_source: str,
    traceback_text: str,
    return_code: int,
) -> LlmCorrection:
    """
    Appelle le modèle Groq pour obtenir une proposition de correction,
    et renvoie un objet LlmCorrection validé par Pydantic.

    Exceptions possibles :
    - RuntimeError si configuration API invalide
    - ValueError si aucun JSON exploitable
    - json.JSONDecodeError si le JSON est mal formé
    - pydantic.ValidationError si le JSON ne respecte pas le schéma
    """
    client = get_groq_client()

    system_msg = build_system_prompt()
    user_msg = build_user_prompt(
        file_path=file_path,
        code_source=code_source,
        traceback_text=traceback_text,
        return_code=return_code,
    )

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        # max_completion_tokens=1024,  # optionnel
        # max_completion_tokens=1024,  # optionnel
        temperature=0.0,
    )

    raw_content = completion.choices[0].message.content or ""

    # Extraire et parser le JSON
    json_str = extract_json_from_text(raw_content)
    data: Any = json.loads(json_str)

    # Valider avec Pydantic
    correction = LlmCorrection.model_validate(data)
    return correction
