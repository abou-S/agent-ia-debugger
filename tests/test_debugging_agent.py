import sys
from pathlib import Path

# === Ajouter la racine du projet au PYTHONPATH ===
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.debugging_agent import DebuggingAgent  # noqa: E402


if __name__ == "__main__":
    # Adapter ce chemin selon ton OS :
    # - macOS / Linux : ".venv/bin/python"
    # - Windows : ".venv/Scripts/python.exe"
    venv_python = Path(".venv/bin/python")

    agent = DebuggingAgent(venv_python_path=venv_python)

    script_path = Path("scripts/sample_bug.py")

    result = agent.debug_patch_and_rerun(
        script_path=script_path,
        output_suffix=".patched",
    )

    print("=== Résultat d'exécution (original) ===")
    print("Script :", result.execution.script_path)
    print("Success :", result.execution.success)
    print("Return code :", result.execution.return_code)
    print("STDOUT :")
    print(result.execution.stdout)
    print("STDERR :")
    print(result.execution.stderr)

    if result.correction is None:
        print("\nAucune correction proposée (script OK ou pas d'erreur détectée).")
    else:
        print("\n=== Correction proposée par le LLM ===")
        print("Résumé :", result.correction.summary)
        print("No fix needed :", result.correction.no_fix_needed)
        print("File path (LLM) :", result.correction.file_path)
        print("Édits :")
        for edit in result.correction.edits:
            print(f"- line {edit.line} | action={edit.action}")
            if edit.content:
                print(edit.content)
                print("----")

    print("\n=== Fichier patché ===")
    if result.patched_file is None:
        print("Aucun fichier patché généré.")
    else:
        print("Fichier patché :", result.patched_file)

    print("\n=== Exécution du fichier patché ===")
    if result.patched_execution is None:
        print("Le fichier patché n'a pas été relancé (pas de patch ou erreur amont).")
    else:
        print("Script patched :", result.patched_execution.script_path)
        print("Success :", result.patched_execution.success)
        print("Return code :", result.patched_execution.return_code)
        print("STDOUT (patched) :")
        print(result.patched_execution.stdout)
        print("STDERR (patched) :")
        print(result.patched_execution.stderr)
