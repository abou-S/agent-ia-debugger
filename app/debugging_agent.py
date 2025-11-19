from pathlib import Path
from typing import List

from .executor import run_script_with_venv
from .llm_client import get_llm_correction
from .patcher import apply_correction_to_file
from .schemas import DebugResult, ExecutionResult, LlmCorrection, AutoDebugReport


class DebuggingAgent:
    """
    Agent principal de debugging.

    - Connaît le chemin du python du venv.
    - Peut exécuter un script.
    - En cas d'erreur, interroge le LLM pour obtenir une correction.
    - Peut appliquer cette correction sur le fichier source (dans un fichier patché).
    - Peut ensuite re-exécuter le fichier patché.
    - Peut boucler automatiquement jusqu'à obtenir une exécution réussie ou atteindre une limite.
    """

    def __init__(self, venv_python_path: str | Path):
        venv_python = Path(venv_python_path)
        if not venv_python.exists():
            raise FileNotFoundError(f"Interpréteur Python du venv introuvable : {venv_python}")
        self.venv_python_path = venv_python

    # --- Méthode utilitaire, si tu veux pouvoir juste exécuter un script ---
    def run(self, script_path: str | Path) -> ExecutionResult:
        """
        Exécute un script sans LLM, juste via le venv.
        """
        return run_script_with_venv(
            venv_python_path=self.venv_python_path,
            script_path=script_path,
        )

    def debug_script(self, script_path: str | Path) -> DebugResult:
        """
        Exécute un script et, en cas d'erreur, utilise le LLM pour proposer une correction.

        Ne modifie PAS les fichiers. Retourne un DebugResult avec :
        - execution : ExecutionResult
        - correction : LlmCorrection ou None
        - patched_file : None
        - patched_execution : None
        """
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"Script introuvable : {script_path}")

        # 1) Exécuter le script
        execution: ExecutionResult = run_script_with_venv(
            venv_python_path=self.venv_python_path,
            script_path=script_path,
        )

        # 2) Si succès → pas besoin du LLM
        if execution.success:
            return DebugResult(
                execution=execution,
                correction=None,
                patched_file=None,
                patched_execution=None,
            )

        # 3) En cas d'échec → lire le code source et appeler le LLM
        code_source = script_path.read_text(encoding="utf-8")

        correction: LlmCorrection = get_llm_correction(
            file_path=str(script_path),
            code_source=code_source,
            traceback_text=execution.stderr,
            return_code=execution.return_code,
        )

        return DebugResult(
            execution=execution,
            correction=correction,
            patched_file=None,
            patched_execution=None,
        )

    def debug_and_patch(self, script_path: str | Path, *, output_suffix: str = ".patched") -> DebugResult:
        """
        Pipeline :
        - Exécute le script.
        - Si erreur, demande une correction au LLM.
        - Si correction utile, applique les edits dans un fichier patché.

        Retourne un DebugResult avec :
        - correction éventuellement remplie
        - patched_file éventuellement rempli
        - patched_execution = None (pas encore relancé)
        """
        script_path = Path(script_path)
        result = self.debug_script(script_path=script_path)

        if result.correction is None:
            # Pas de correction (script ok ou problème en amont)
            return result

        if result.correction.no_fix_needed or not result.correction.edits:
            # Le LLM estime qu'aucune correction n'est nécessaire
            return result

        # Appliquer la correction sur le fichier source
        patched_path = apply_correction_to_file(
            source_path=script_path,
            correction=result.correction,
            output_suffix=output_suffix,
        )

        result.patched_file = str(patched_path)
        return result

    def debug_patch_and_rerun(self, script_path: str | Path, *, output_suffix: str = ".patched") -> DebugResult:
        """
        Pipeline complet :
        - Exécute le script original.
        - Si erreur, demande une correction au LLM.
        - Si correction utile, applique les edits dans un fichier patché.
        - Puis ré-exécute le fichier patché.

        Retourne un DebugResult avec :
        - execution : exécution du script original
        - correction : réponse du LLM (si applicable)
        - patched_file : chemin du fichier patché (si créé)
        - patched_execution : exécution du fichier patché (si créée)
        """
        script_path = Path(script_path)

        # 1) Debug + patch
        result = self.debug_and_patch(script_path=script_path, output_suffix=output_suffix)

        # Si aucun fichier patché n'a été généré, on s'arrête là
        if result.patched_file is None:
            return result

        patched_path = Path(result.patched_file)
        if not patched_path.exists():
            # Sécurité : au cas où le fichier patché aurait disparu
            return result

        # 2) Re-run du fichier patché
        patched_exec = run_script_with_venv(
            venv_python_path=self.venv_python_path,
            script_path=patched_path,
        )

        result.patched_execution = patched_exec
        return result

    def auto_debug_until_success(
        self,
        script_path: str | Path,
        *,
        max_iterations: int = 3,
        output_suffix: str = ".patched",
    ) -> AutoDebugReport:
        """
        Boucle d'auto-debug :

        - On part d'un script original.
        - À chaque itération :
          - debug_patch_and_rerun sur le script courant
          - si exécution originale ou patchée réussie -> on s'arrête (success=True)
          - sinon, si un fichier patché existe, on recommence en prenant ce fichier comme nouveau script
          - sinon, on s'arrête (plus rien à faire)

        Les fichiers patchés successifs peuvent ressembler à :
        - script.patched.py
        - script.patched.patched.py
        - etc. (c'est ok pour un proto)
        """
        script_path = Path(script_path)
        iterations: List[DebugResult] = []
        success = False
        stop_reason = ""

        current_script = script_path

        for i in range(max_iterations):
            # Pour distinguer les suffixes entre itérations si tu veux :
            iter_suffix = output_suffix if i == 0 else f"{output_suffix}{i}"

            result = self.debug_patch_and_rerun(
                script_path=current_script,
                output_suffix=iter_suffix,
            )
            iterations.append(result)

            # 1) Si l'exécution originale a réussi (cas rare ici)
            if result.execution.success:
                success = True
                stop_reason = "original_succeeded"
                break

            # 2) Si le LLM n'a pas proposé de correction utile
            if result.correction is None or result.correction.no_fix_needed or not result.correction.edits:
                stop_reason = "no_correction_or_not_needed"
                break

            # 3) Si aucun fichier patché n'existe
            if result.patched_file is None:
                stop_reason = "no_patched_file"
                break

            # 4) Si le fichier patché a été lancé
            if result.patched_execution is not None:
                if result.patched_execution.success:
                    success = True
                    stop_reason = "patched_succeeded"
                    break
                else:
                    # On continue, mais en prenant le fichier patché comme nouveau script
                    current_script = Path(result.patched_file)
            else:
                # Pas d'exécution du patch (cas anormal)
                stop_reason = "no_patched_execution"
                break

        if not success and stop_reason == "":
            stop_reason = "max_iterations_reached"

        return AutoDebugReport(
            success=success,
            iterations=iterations,
            max_iterations=max_iterations,
            stop_reason=stop_reason,
        )
