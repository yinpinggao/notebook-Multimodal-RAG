"""Canonical Visual RAG subsystem for Open Notebook."""

from .indexer import VisualAssetIndexer
from .search_engine import VisualAssetSearchEngine

__all__ = ["VisualAssetIndexer", "VisualAssetSearchEngine"]
