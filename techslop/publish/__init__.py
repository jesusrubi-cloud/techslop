"""Publication always requires explicit per-call approval."""
from __future__ import annotations


def require_approval(approved: bool = False) -> None:
    if approved is not True:
        raise PermissionError("Publicación bloqueada: se requiere aprobación explícita para este video.")
