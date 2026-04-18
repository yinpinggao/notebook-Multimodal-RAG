"""Evidence-layer helpers for project evidence QA."""

from .citation_service import build_citation_text, build_internal_ref
from .evidence_card_service import build_evidence_cards

__all__ = [
    "build_citation_text",
    "build_internal_ref",
    "build_evidence_cards",
]
