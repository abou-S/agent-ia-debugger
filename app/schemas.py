from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError


# ============================
# Modèles pour les modifications de code (LLM)
# ============================

class Edit(BaseModel):
    """
    Représente une modification sur une ligne de code.
    """
    line: int = Field(..., description="Numéro de ligne (1-based) dans le fichier.")
    action: Literal["replace", "insert_before", "insert_after", "delete"]
    content: Optional[str] = Field(
        None,
        description="Nouveau code (obligatoire pour replace/insert_*)"
    )


class LlmCorrection(BaseModel):
    """
    Représente la réponse complète du LLM pour une correction.
    """
    summary: str = Field(..., description="Résumé court du bug.")
    file_path: Optional[str] = Field(
        None,
        description="Chemin du fichier corrigé, ou null si non pertinent."
    )
    edits: List[Edit] = Field(
        default_factory=list,
        description="Liste des modifications à appliquer."
    )
    no_fix_needed: bool = Field(
        default=False,
        description="True si aucune correction n'est nécessaire."
    )


# ============================
# Modèles pour l'exécution et l'orchestration
# ============================

class ExecutionResult(BaseModel):
    """
    Résultat de l'exécution d'un script Python via un interpréteur donné.
    """
    script_path: str = Field(..., description="Chemin du script exécuté.")
    success: bool = Field(..., description="True si le return code est 0.")
    stdout: str = Field(default="", description="Sortie standard.")
    stderr: str = Field(default="", description="Sortie erreur (traceback, etc.).")
    return_code: int = Field(..., description="Code de retour du process.")


class DebugResult(BaseModel):
    """
    Résultat complet du processus de debugging :
    - exécution brute du script original
    - correction proposée par le LLM (optionnelle)
    - chemin du fichier patché (optionnel)
    - exécution du fichier patché (optionnelle)
    """
    execution: ExecutionResult
    correction: Optional[LlmCorrection] = None
    patched_file: Optional[str] = Field(
        default=None,
        description="Chemin du fichier patché (si une correction a été appliquée).",
    )
    patched_execution: Optional[ExecutionResult] = Field(
        default=None,
        description="Résultat d'exécution du fichier patché, si un re-run a été effectué.",
    )


class AutoDebugReport(BaseModel):
    """
    Rapport global d'une session d'auto-debug :
    - success : True si au moins une exécution (originale ou patchée) a réussi
    - iterations : liste des DebugResult pour chaque tentative
    - max_iterations : borne supérieure du nombre de tentatives
    - stop_reason : raison pour laquelle on s'est arrêté
    """
    success: bool
    iterations: List[DebugResult]
    max_iterations: int
    stop_reason: str


__all__ = [
    "Edit",
    "LlmCorrection",
    "ExecutionResult",
    "DebugResult",
    "AutoDebugReport",
    "ValidationError",
]
