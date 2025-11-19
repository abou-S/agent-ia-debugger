import sys
from pathlib import Path

# === Forcer la racine du projet dans PYTHONPATH ===
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.llm_client import get_llm_correction


if __name__ == "__main__":
    file_path = "scripts/sample_bug.py"
    code_source = """\
x = 10
print(x / 0)
"""
    traceback_text = """\
Traceback (most recent call last):
  File "scripts/sample_bug.py", line 2, in <module>
    print(x / 0)
ZeroDivisionError: division by zero
"""
    return_code = 1

    correction = get_llm_correction(
        file_path=file_path,
        code_source=code_source,
        traceback_text=traceback_text,
        return_code=return_code,
    )

    print("Résumé :", correction.summary)
    print("No fix needed ?", correction.no_fix_needed)
    print("Édits :")
    for edit in correction.edits:
        print(f"- line {edit.line} | action={edit.action}")
        if edit.content:
            print(edit.content)
            print("----")
