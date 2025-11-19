from pathlib import Path
import os

from dotenv import load_dotenv

# Répertoire racine du projet (debug_agent/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Charger le fichier .env
load_dotenv(BASE_DIR / ".env")

# Dossier des prompts
PROMPTS_DIR = BASE_DIR / "prompts"

# === Variables d'environnement ===

GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def ensure_config_ok() -> None:
    """
    Vérifie que la configuration critique est bien définie.
    À appeler au démarrage de ton application (ou au 1er appel LLM).
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "La variable d'environnement GROQ_API_KEY est manquante. "
            "Ajoute-la dans le fichier .env à la racine du projet."
        )

    if not PROMPTS_DIR.exists():
        raise RuntimeError(
            f"Le dossier des prompts n'existe pas : {PROMPTS_DIR}. "
            "Crée le dossier 'prompts/' à la racine du projet."
        )
