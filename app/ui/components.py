from pathlib import Path

import streamlit as st

from app.schemas import DebugResult


def show_execution_block(title: str, debug_result: DebugResult, use_patched: bool = False) -> None:
    """
    Affiche un bloc d'exécution (originale ou patchée) dans l'UI.
    """
    exec_result = debug_result.patched_execution if use_patched else debug_result.execution
    if exec_result is None:
        st.write("Aucune exécution disponible.")
        return

    st.subheader(title)
    st.markdown(f"**Script** : `{exec_result.script_path}`")
    st.markdown(f"**Succès** : `{exec_result.success}`")
    st.markdown(f"**Return code** : `{exec_result.return_code}`")

    with st.expander("STDOUT"):
        if exec_result.stdout.strip():
            st.code(exec_result.stdout, language="text")
        else:
            st.write("_(vide)_")

    with st.expander("STDERR"):
        if exec_result.stderr.strip():
            st.code(exec_result.stderr, language="text")
        else:
            st.write("_(vide)_")


def show_correction_block(debug_result: DebugResult) -> None:
    """
    Affiche les infos de correction d'un DebugResult.
    """
    if debug_result.correction is None:
        st.info("Aucune correction proposée par le LLM pour cette itération.")
        return

    corr = debug_result.correction
    st.subheader("Correction proposée par le LLM")
    st.markdown(f"**Résumé** : {corr.summary}")
    st.markdown(f"**No fix needed ?** `{corr.no_fix_needed}`")
    st.markdown(f"**Fichier ciblé (LLM)** : `{corr.file_path}`")
    st.markdown(f"**Nombre d'edits** : `{len(corr.edits)}`")

    if not corr.edits:
        return

    with st.expander("Détail des edits proposés"):
        for idx, edit in enumerate(corr.edits, start=1):
            st.markdown(f"**Edit {idx}** — ligne `{edit.line}`, action `{edit.action}`")
            if edit.content:
                st.code(edit.content, language="python")


def show_patched_file_block(debug_result: DebugResult) -> None:
    """
    Affiche le chemin et le contenu du fichier patché, si existant.
    """
    if debug_result.patched_file is None:
        st.info("Aucun fichier patché généré pour cette itération.")
        return

    patched_path = Path(debug_result.patched_file)
    st.markdown(f"**Fichier patché** : `{patched_path}`")

    if patched_path.exists():
        with st.expander("Contenu du fichier patché"):
            code = patched_path.read_text(encoding="utf-8")
            st.code(code, language="python")
    else:
        st.warning("Le fichier patché n'existe plus sur le disque.")
