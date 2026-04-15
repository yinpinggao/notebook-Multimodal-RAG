"""VRAG: Vision-perception RAG — Multimodal retrieval and visual reasoning for open-notebook.

Modules:
    prompts: Prompt templates for VRAG agent
    utils: Image processing, bbox, base64 utilities
    search_engine: Multimodal search using OpenAI CLIP API
    indexer: PDF image extraction and CLIP embedding generation
    tools: search/bbox_crop/summarize/answer tools for the agent
    memory: Multimodal Memory Graph management
    agent: ReAct agent for visual reasoning
    workflow: LangGraph VRAG workflow
    checkpoint: DAG state persistence using SeekDB
    api: FastAPI router for VRAG endpoints
"""

from open_notebook.vrag.agent import VRAGAgent
from open_notebook.vrag.indexer import VRAGIndexer
from open_notebook.vrag.memory import MultimodalMemoryGraph
from open_notebook.vrag.search_engine import VRAGSearchEngine
from open_notebook.vrag.tools import VRAGTools
from open_notebook.vrag.workflow import create_vrag_graph, create_vrag_workflow

__all__ = [
    "create_vrag_graph",
    "create_vrag_workflow",
    "MultimodalMemoryGraph",
    "VRAGAgent",
    "VRAGSearchEngine",
    "VRAGIndexer",
    "VRAGTools",
]
