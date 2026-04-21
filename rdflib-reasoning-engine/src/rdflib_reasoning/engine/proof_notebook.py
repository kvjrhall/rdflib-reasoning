# mypy: disable-error-code="import-not-found"

from __future__ import annotations

try:
    from IPython.display import Markdown, display  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "Notebook proof rendering requires optional dependency support. "
        "Install `rdflib-reasoning-engine[notebook]` to use "
        "`rdflib_reasoning.engine.proof_notebook`."
    ) from exc

from dataclasses import dataclass

from rdflib.namespace import NamespaceManager

from .proof import DirectProof
from .proof_rendering import render_proof_markdown, render_proof_mermaid


@dataclass(frozen=True)
class NotebookProofRenderer:
    """Notebook display adapter for markdown and Mermaid proof renderings."""

    namespace_manager: NamespaceManager | None = None

    def markdown(self, proof: DirectProof) -> str:
        """Display markdown rendering in a notebook output cell."""
        rendered = render_proof_markdown(
            proof, namespace_manager=self.namespace_manager
        )
        display(Markdown(rendered))
        return rendered

    def mermaid(self, proof: DirectProof) -> str:
        """Display Mermaid rendering in a notebook output cell."""
        mermaid = render_proof_mermaid(proof, namespace_manager=self.namespace_manager)
        fenced = f"```mermaid\n{mermaid}\n```"
        display(Markdown(fenced))
        return mermaid


def display_proof_markdown(
    proof: DirectProof, *, namespace_manager: NamespaceManager | None = None
) -> None:
    """Render and display a direct proof as markdown."""
    NotebookProofRenderer(namespace_manager=namespace_manager).markdown(proof)


def display_proof_mermaid(
    proof: DirectProof, *, namespace_manager: NamespaceManager | None = None
) -> None:
    """Render and display a direct proof as Mermaid."""
    NotebookProofRenderer(namespace_manager=namespace_manager).mermaid(proof)


__all__ = [
    "NotebookProofRenderer",
    "display_proof_markdown",
    "display_proof_mermaid",
]
