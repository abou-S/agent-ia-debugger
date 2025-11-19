from pathlib import Path
import difflib  # <--- nouveau

import streamlit as st

from app.config import BASE_DIR
from app.debugging_agent import DebuggingAgent
from app.schemas import AutoDebugReport, DebugResult
from app.ui.config_ui import (
    get_default_venv_python,
    get_scripts_list,
    create_agent,
    save_uploaded_script,
)
from app.ui.components import (
    show_execution_block,
    show_correction_block,
    show_patched_file_block,
)
from app.patcher import apply_edits_to_content, apply_correction_in_place  # <--- nouveau


from pathlib import Path

import streamlit as st

from app.config import BASE_DIR
from app.debugging_agent import DebuggingAgent
from app.schemas import AutoDebugReport, DebugResult
from app.ui.config_ui import (
    get_default_venv_python,
    get_scripts_list,
    create_agent,
    save_uploaded_script,
)
from app.ui.components import (
    show_execution_block,
    show_correction_block,
    show_patched_file_block,
)


def run_single_mode(agent: DebuggingAgent, script_path: Path, mode: str, max_iterations: int) -> None:
    """
    Exécute le pipeline en fonction du mode choisi et affiche les résultats.
    """
    if mode == "Exécuter seulement":
        exec_result = agent.run(script_path)
        dummy_debug = DebugResult(
            execution=exec_result,
            correction=None,
            patched_file=None,
            patched_execution=None,
        )
        show_execution_block("Exécution simple", dummy_debug, use_patched=False)

    elif mode == "Debug (prévisualiser et modifier le fichier original)":
        # 1) On fait un debug "sec" : exécution + correction LLM, mais pas d'écriture.
        result = agent.debug_script(script_path=script_path)

        show_execution_block("Exécution originale", result, use_patched=False)
        st.markdown("---")
        show_correction_block(result)

        if result.correction is None:
            st.info("Aucune correction proposée par le LLM, rien à prévisualiser.")
            return

        # 2) Calcul du code patché en mémoire (sans écrire sur le disque)
        try:
            original_code = script_path.read_text(encoding="utf-8")
        except Exception as e:
            st.error(f"Impossible de lire le fichier source : {e}")
            return

        try:
            patched_code = apply_edits_to_content(original_code, result.correction.edits)
        except Exception as e:
            st.error(f"Erreur lors de l'application des edits : {e}")
            return

        st.markdown("### Aperçu des changements proposés")

        tab1, tab2, tab3 = st.tabs(["Code original", "Proposition du LLM", "Diff"])

        with tab1:
            st.code(original_code, language="python")

        with tab2:
            st.code(patched_code, language="python")

        with tab3:
            original_lines = original_code.splitlines(keepends=True)
            patched_lines = patched_code.splitlines(keepends=True)
            diff = "".join(
                difflib.unified_diff(
                    original_lines,
                    patched_lines,
                    fromfile="original",
                    tofile="proposition",
                )
            )
            if diff.strip():
                st.code(diff, language="diff")
            else:
                st.info("Aucune différence détectée entre le code original et la proposition.")

        st.markdown("---")
        # 3) Bouton pour appliquer réellement les changements sur le fichier original
        if st.button("✅ Appliquer ces changements au fichier original (backup .bak)"):
            try:
                backup_path = apply_correction_in_place(
                    source_path=script_path,
                    correction=result.correction,
                    backup_suffix=".bak",
                )
                st.success(
                    f"Modifications appliquées au fichier `{script_path}`.\n\n"
                    f"Une sauvegarde de l'ancienne version a été créée : `{backup_path}`"
                )
            except Exception as e:
                st.error(f"Erreur lors de l'application des modifications : {e}")

    elif mode == "Debug + patch + re-run (1 itération)":
        result = agent.debug_patch_and_rerun(script_path=script_path, output_suffix=".patched")

        show_execution_block("Exécution originale", result, use_patched=False)
        st.markdown("---")
        show_correction_block(result)
        st.markdown("---")
        show_patched_file_block(result)
        st.markdown("---")
        show_execution_block("Exécution du fichier patché", result, use_patched=True)

    elif mode == "Auto-debug (jusqu'à succès)":
        report: AutoDebugReport = agent.auto_debug_until_success(
            script_path=script_path,
            max_iterations=max_iterations,
            output_suffix=".patched",
        )

        st.subheader("Résumé global (auto-debug)")
        st.markdown(f"**Succès global** : `{report.success}`")
        st.markdown(f"**Raison d'arrêt** : `{report.stop_reason}`")
        st.markdown(f"**Max iterations** : `{report.max_iterations}`")
        st.markdown(f"**Itérations effectuées** : `{len(report.iterations)}`")

        for idx, it in enumerate(report.iterations, start=1):
            with st.expander(f"Iteration {idx}"):
                show_execution_block("Exécution originale", it, use_patched=False)
                st.markdown("---")
                show_correction_block(it)
                st.markdown("---")
                show_patched_file_block(it)
                st.markdown("---")
                if it.patched_execution is not None:
                    show_execution_block("Exécution du fichier patché", it, use_patched=True)
                else:
                    st.info("Le fichier patché n'a pas été relancé pour cette itération.")


def main() -> None:
    st.set_page_config(
        page_title="Agent de Debugging Python",
        page_icon="🛠️",
        layout="wide",
    )

    st.title("🛠️ Agent de Debugging Python (Groq + LLM)")
    st.write(
        "Interface pour exécuter un script Python via un virtualenv, "
        "analyser les erreurs avec un LLM (Groq) et proposer des corrections."
    )

    # === SIDEBAR : configuration ===
    st.sidebar.header("Configuration")

    # 1) Sélection de l'environnement (python du venv)
    default_venv_python = get_default_venv_python()
    st.sidebar.caption("### Environnement Python du projet à débugger")
    venv_python_input = st.sidebar.text_input(
        "Chemin du python du venv",
        value=str(default_venv_python),
        help=(
            "Indique le chemin du python de l'environnement virtuel du PROJET à débugger.\n"
            "Exemples :\n"
            "- .venv/bin/python (Linux/macOS)\n"
            "- .venv/Scripts/python.exe (Windows)\n"
            "- /Users/abou/mon-projet/.venv/bin/python"
        ),
    )

    # 2) Source du script : dossier local vs upload
    st.sidebar.markdown("---")
    st.sidebar.caption("### Source du script à analyser")
    script_source = st.sidebar.radio(
        "Source du script",
        options=[
            "Dossier scripts/ du projet",
            "Uploader un fichier .py",
        ],
        index=0,
    )

    scripts = []
    script_labels = []
    uploaded_file = None
    script_path: Path | None = None

    if script_source == "Dossier scripts/ du projet":
        scripts = get_scripts_list()
        script_labels = [str(p.relative_to(BASE_DIR)) for p in scripts]

        selected_script_label = st.sidebar.selectbox(
            "Script dans le dossier scripts/",
            options=script_labels if script_labels else ["(Aucun script trouvé dans scripts/)"],
        )

        if scripts:
            script_index = script_labels.index(selected_script_label) if selected_script_label in script_labels else 0
            script_path = scripts[script_index]
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Choisir un fichier .py à uploader",
            type=["py"],
            help="Ce fichier sera exécuté sur le serveur avec le python du venv indiqué.",
        )

    # 3) Mode de fonctionnement
    st.sidebar.markdown("---")
    mode = st.sidebar.radio(
    "Mode",
    options=[
        "Exécuter seulement",
        "Debug (prévisualiser et modifier le fichier original)",
        "Debug + patch + re-run (1 itération)",
        "Auto-debug (jusqu'à succès)",
    ],
    index=1,
    )


    max_iterations = st.sidebar.number_input(
        "Max iterations (mode auto-debug)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )

    st.sidebar.markdown("---")
    run_button = st.sidebar.button("🚀 Lancer")

    # === MAIN AREA ===

    if script_source == "Dossier scripts/ du projet":
        if not scripts:
            st.warning("Aucun script .py trouvé dans le dossier 'scripts/'. Crée-en un ou utilise l'upload.")
        else:
            st.markdown(f"**Script sélectionné** : `{script_path.relative_to(BASE_DIR)}`")
    else:
        if uploaded_file is not None:
            st.markdown(f"**Fichier uploadé** : `{uploaded_file.name}`")
        else:
            st.info("Uploader un fichier .py dans la barre latérale pour commencer.")

    if not run_button:
        return

    # --- Vérifications avant exécution ---
    venv_python_path = Path(venv_python_input)
    if not venv_python_path.exists():
        st.error(f"Le binaire Python du venv est introuvable : `{venv_python_path}`")
        return

    # Déterminer le script_path final
    if script_source == "Dossier scripts/ du projet":
        if script_path is None or not script_path.exists():
            st.error("Le script sélectionné est introuvable ou non défini.")
            return
        final_script_path = script_path
    else:
        if uploaded_file is None:
            st.error("Aucun fichier .py uploadé.")
            return
        saved_path = save_uploaded_script(uploaded_file)
        if saved_path is None or not saved_path.exists():
            st.error("Impossible de sauvegarder le fichier uploadé.")
            return
        final_script_path = saved_path
        st.success(f"Fichier uploadé sauvegardé sous : `{final_script_path}`")

    # Initialisation de l'agent
    try:
        agent = create_agent(venv_python_path=venv_python_path)
    except Exception as e:
        st.error(f"Impossible d'initialiser le DebuggingAgent : {e}")
        return

    # Exécution du pipeline
    try:
        run_single_mode(agent, final_script_path, mode, max_iterations)
    except Exception as e:
        st.error(f"Une erreur est survenue pendant l'exécution : {e}")
