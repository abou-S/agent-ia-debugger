import subprocess
from pathlib import Path

def run_script_with_venv(venv_python_path: str, script_path: str):
    """
    Exécute un script Python en utilisant le python d'un virtualenv.
    Retourne stdout, stderr et returncode.
    """

    command = [venv_python_path, script_path]

    try:
        result = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True  # outputs en str au lieu de bytes
                    )
    except FileNotFoundError:
        print("❌ Erreur : le binaire Python du venv est introuvable.")
    except Exception as e:
        print("❌ Exception imprévue :", e)

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True  # outputs en str au lieu de bytes
    )

    return result.stdout, result.stderr, result.returncode

def execute_and_report(venv_python_path, script_path):
    stdout, stderr, code = run_script_with_venv(venv_python_path, script_path)

    if code == 0:
        print("✔️ Script exécuté sans erreur.")
        return {
            "success": True,
            "stdout": stdout
        }
    else:
        print("❌ Le script a échoué.")
        return {
            "success": False,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": code
        }
    


if __name__ == "__main__":

    res = execute_and_report(
            venv_python_path="/Users/abou/Hetic/agent-ia-debugger/.venv/bin/python",
            script_path="/Users/abou/Hetic/agent-ia-debugger/test_bug.py"
            )

    print("STDOUT :", res["stdout"])
    print("STDERR :", res['stderr'])
    print("RETURN CODE :", res["returncode"])
