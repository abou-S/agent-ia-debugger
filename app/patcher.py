from pathlib import Path
from typing import Iterable

from .schemas import Edit, LlmCorrection


def _content_to_lines(content: str) -> list[str]:
    """
    Convertit un bloc de texte en liste de lignes avec '\n' conservés.
    S'assure que la dernière ligne se termine par un newline.
    """
    if content == "":
        return []

    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    return lines


def apply_edits_to_content(source_code: str, edits: Iterable[Edit]) -> str:
    """
    Applique une liste d'Edit sur le contenu source (string) et renvoie le nouveau contenu.

    Important :
    - Les numéros de lignes sont 1-based (ligne 1 = première ligne).
    - On applique les edits en ordre décroissant de ligne pour éviter les décalages.
    """
    lines = source_code.splitlines(keepends=True)

    # Tri des edits par numéro de ligne décroissant (pour éviter les décalages)
    sorted_edits = sorted(edits, key=lambda e: e.line, reverse=True)

    for edit in sorted_edits:
        line_idx = edit.line - 1  # passer en index 0-based

        if edit.action in {"replace", "insert_before", "insert_after"} and (edit.content is None or edit.content == ""):
            raise ValueError(
                f"Edit sur la ligne {edit.line} avec action '{edit.action}' "
                "nécessite un contenu non vide."
            )

        if edit.action == "replace":
            if not (0 <= line_idx < len(lines)):
                raise IndexError(f"Numéro de ligne invalide pour replace: {edit.line}")

            new_lines = _content_to_lines(edit.content or "")
            # Remplacer UNE ligne par N lignes
            lines[line_idx : line_idx + 1] = new_lines

        elif edit.action == "insert_before":
            if not (0 <= line_idx <= len(lines)):
                raise IndexError(f"Numéro de ligne invalide pour insert_before: {edit.line}")

            new_lines = _content_to_lines(edit.content or "")
            lines[line_idx:line_idx] = new_lines

        elif edit.action == "insert_after":
            if not (0 <= line_idx < len(lines)):
                raise IndexError(f"Numéro de ligne invalide pour insert_after: {edit.line}")

            insert_pos = line_idx + 1
            new_lines = _content_to_lines(edit.content or "")
            lines[insert_pos:insert_pos] = new_lines

        elif edit.action == "delete":
            if not (0 <= line_idx < len(lines)):
                raise IndexError(f"Numéro de ligne invalide pour delete: {edit.line}")
            lines[line_idx : line_idx + 1] = []

        else:
            raise ValueError(f"Action d'edit inconnue : {edit.action}")

    return "".join(lines)


def apply_correction_to_file(
    source_path: str | Path,
    correction: LlmCorrection,
    *,
    output_suffix: str = ".patched",
) -> Path:
    """
    Applique une correction LLM sur un fichier et écrit le résultat dans un nouveau fichier.

    - source_path : fichier source à patcher
    - correction : LlmCorrection (doit contenir une liste d'edits)
    - output_suffix : suffixe ajouté au nom du fichier avant l'extension
      ex : "script.py" -> "script.patched.py" si suffix=".patched"

    Retourne le chemin du fichier patché.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Fichier source introuvable : {source_path}")

    if correction.no_fix_needed or not correction.edits:
        # Rien à faire, on renvoie simplement le chemin original
        return source_path

    original_code = source_path.read_text(encoding="utf-8")
    new_code = apply_edits_to_content(original_code, correction.edits)

    # Construire le nom du fichier patché :
    # ex: script.py -> script.patched.py
    patched_name = f"{source_path.stem}{output_suffix}{source_path.suffix}"
    patched_path = source_path.with_name(patched_name)

    patched_path.write_text(new_code, encoding="utf-8")

    return patched_path


def apply_correction_in_place(
    source_path: str | Path,
    correction: LlmCorrection,
    *,
    backup_suffix: str = ".bak",
) -> Path:
    """
    Applique une correction LLM directement sur le fichier source.

    - Crée d'abord une sauvegarde : script.py -> script.py.bak (par défaut).
    - Écrit ensuite la version corrigée dans le fichier original.

    Retourne le chemin du fichier de backup.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Fichier source introuvable : {source_path}")

    if correction.no_fix_needed or not correction.edits:
        # Rien à faire, on ne touche pas au fichier
        return source_path

    original_code = source_path.read_text(encoding="utf-8")
    new_code = apply_edits_to_content(original_code, correction.edits)

    # Créer un backup : script.py -> script.py.bak
    backup_path = source_path.with_name(source_path.name + backup_suffix)
    backup_path.write_text(original_code, encoding="utf-8")

    # Écraser le fichier original avec le nouveau contenu
    source_path.write_text(new_code, encoding="utf-8")

    return backup_path
