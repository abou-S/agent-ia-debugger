import sys
from pathlib import Path

# === Ajouter la racine du projet au PYTHONPATH ===
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.debugging_agent import DebuggingAgent  # noqa: E402


if __name__ == "__main__":
    venv_python = Path(".venv/bin/python")  # adapte si Windows

    agent = DebuggingAgent(venv_python_path=venv_python)

    script_path = Path("scripts/sample_bug.py")

    report = agent.auto_debug_until_success(
        script_path=script_path,
        max_iterations=3,
        output_suffix=".patched",
    )

    print("=== AutoDebug Report ===")
    print("Success :", report.success)
    print("Stop reason :", report.stop_reason)
    print("Max iterations :", report.max_iterations)
    print("Nombre d'itérations réalisées :", len(report.iterations))

    for idx, it in enumerate(report.iterations, start=1):
        print(f"\n--- Iteration {idx} ---")
        print("[Original] success:", it.execution.success, "return code:", it.execution.return_code)
        print("STDERR (original):")
        print(it.execution.stderr)

        if it.correction is None:
            print("Aucune correction proposée.")
        else:
            print("Résumé correction :", it.correction.summary)
            print("No fix needed :", it.correction.no_fix_needed)
            print("Nombre d'edits :", len(it.correction.edits))

        print("Patched file :", it.patched_file)

        if it.patched_execution is not None:
            print("[Patched] success:", it.patched_execution.success, "return code:", it.patched_execution.return_code)
            print("STDERR (patched):")
            print(it.patched_execution.stderr)
        else:
            print("Pas d'exécution du fichier patché pour cette itération.")