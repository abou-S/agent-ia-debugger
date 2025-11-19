import subprocess
from pathlib import Path

from .schemas import ExecutionResult


def run_script_with_venv(venv_python_path: str | Path, script_path: str | Path) -> ExecutionResult:
    """
    Exécute un script Python en utilisant l'interpréteur d'un virtualenv.

    - venv_python_path : chemin vers le binaire python du venv
      ex : ".venv/bin/python" (Linux/macOS) ou ".venv/Scripts/python.exe" (Windows)
    - script_path : chemin vers le script à exécuter

    Retourne un ExecutionResult avec stdout, stderr, return_code, success.
    """
    venv_python = Path(venv_python_path)
    script_path = Path(script_path)

    if not venv_python.exists():
        raise FileNotFoundError(f"Interpréteur Python du venv introuvable : {venv_python}")

    if not script_path.exists():
        raise FileNotFoundError(f"Script introuvable : {script_path}")

    command = [str(venv_python), str(script_path)]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as e:
        # En cas d'erreur "système" (permissions, etc.), on encapsule dans ExecutionResult
        return ExecutionResult(
            script_path=str(script_path),
            success=False,
            stdout="",
            stderr=f"Erreur lors de l'exécution du processus : {e}",
            return_code=-1,
        )

    success = (result.returncode == 0)

    return ExecutionResult(
        script_path=str(script_path),
        success=success,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )
