import platform
from pathlib import Path
from typing import List, Optional

from app.config import BASE_DIR
from app.debugging_agent import DebuggingAgent


def get_default_venv_python() -> Path:
    """
    Devine le chemin du python du venv en fonction de l'OS.
    """
    if platform.system() == "Windows":
        return BASE_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        return BASE_DIR / ".venv" / "bin" / "python"


def get_scripts_list() -> List[Path]:
    """
    Retourne la liste des scripts Python disponibles dans le dossier 'scripts/'.
    """
    scripts_dir = BASE_DIR / "scripts"
    if not scripts_dir.exists():
        return []
    return sorted(scripts_dir.glob("*.py"))


def create_agent(venv_python_path: Path) -> DebuggingAgent:
    """
    Initialise le DebuggingAgent à partir d'un chemin de python de venv.
    Laisse remonter les erreurs si le chemin est invalide.
    """
    return DebuggingAgent(venv_python_path=venv_python_path)


def save_uploaded_script(uploaded_file) -> Optional[Path]:
    """
    Sauvegarde un fichier .py uploadé par l'utilisateur dans un dossier 'uploaded_scripts/'.

    - uploaded_file : objet retourné par st.file_uploader
    - retourne le Path du fichier sauvegardé, ou None si aucun fichier.
    """
    if uploaded_file is None:
        return None

    upload_dir = BASE_DIR / "uploaded_scripts"
    upload_dir.mkdir(exist_ok=True)

    dest_path = upload_dir / uploaded_file.name
    content = uploaded_file.read()
    dest_path.write_bytes(content)

    return dest_path
