"""VRAG memory — Multimodal Memory Graph management.

Adapted from VRAG/demo/vimrag_utils.py — calculate_intuitive_memory_energy
and generate_multimodal_messages functions.
"""

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryNode:
    """A single node in the multimodal memory graph.

    Represents either a search action, bbox_crop action, or a reasoning step.
    """
    id: str
    type: str  # "search" | "bbox_crop" | "summarize" | "answer"
    summary: str  # Text summary of what this node represents
    parent_ids: list[str] = field(default_factory=list)
    child_ids: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)  # image paths
    bboxes: list[list[float]] = field(default_factory=list)  # normalized bboxes
    priority: float = 0.0  # 0-1, higher = more important
    is_useful: bool = True  # Whether this node contributes to the answer
    key_insight: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class MultimodalMemoryGraph:
    """Manages the DAG of reasoning nodes accumulated during VRAG inference.

    The memory graph tracks all search, bbox_crop, and reasoning actions
    with their relationships, enabling:
    - Intuitive reasoning: track energy/importance through the graph
    - Multi-turn context: accumulate visual evidence across turns
    - Answer generation: retrieve relevant visual evidence for final answer
    """

    def __init__(self):
        self.nodes: dict[str, MemoryNode] = {}
        self.node_order: list[str] = []  # Insertion order for deterministic rendering

    def add_node(
        self,
        node_type: str,
        summary: str,
        parent_ids: Optional[list[str]] = None,
        images: Optional[list[str]] = None,
        bboxes: Optional[list[list[float]]] = None,
        priority: float = 0.5,
        is_useful: bool = True,
        key_insight: str = "",
    ) -> str:
        """Add a new node to the memory graph.

        Args:
            node_type: Type of the node (search/bbox_crop/summarize/answer).
            summary: Text summary of the node.
            parent_ids: IDs of parent nodes.
            images: List of image paths associated with this node.
            bboxes: List of bbox coordinates used in this node.
            priority: Priority score (0-1).
            is_useful: Whether this node is useful for the answer.
            key_insight: Key insight from this node.

        Returns:
            The ID of the newly created node.
        """
        node_id = f"{node_type}_{len(self.nodes)}"

        parent_ids = parent_ids or []
        # Get last node as implicit parent if not specified
        if not parent_ids and self.node_order:
            parent_ids = [self.node_order[-1]]

        node = MemoryNode(
            id=node_id,
            type=node_type,
            summary=summary,
            parent_ids=parent_ids,
            images=images or [],
            bboxes=bboxes or [],
            priority=priority,
            is_useful=is_useful,
            key_insight=key_insight,
        )

        self.nodes[node_id] = node
        self.node_order.append(node_id)

        # Update parent nodes' child_ids
        for parent_id in parent_ids:
            if parent_id in self.nodes:
                if node_id not in self.nodes[parent_id].child_ids:
                    self.nodes[parent_id].child_ids.append(node_id)

        logger.debug(f"Added memory node: {node_id} (type={node_type}, parents={parent_ids})")
        return node_id

    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_useful_nodes(self) -> list[MemoryNode]:
        """Get all useful nodes for answer generation."""
        return [n for n in self.nodes.values() if n.is_useful]

    def get_recent_nodes(self, n: int = 5) -> list[MemoryNode]:
        """Get the N most recent nodes."""
        node_ids = self.node_order[-n:]
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_node_chain(self, node_id: str) -> list[MemoryNode]:
        """Get the chain of ancestors leading to a node."""
        chain = []
        current_id = node_id
        visited = set()

        while current_id and current_id not in visited:
            node = self.nodes.get(current_id)
            if not node:
                break
            chain.append(node)
            visited.add(current_id)
            current_id = node.parent_ids[0] if node.parent_ids else None

        return chain

    def calculate_intuitive_memory_energy(self, node_id: str) -> float:
        """Calculate the "intuitive energy" of a memory node.

        This measures how important/useful a node is based on:
        1. Its own priority score
        2. The energy flowing from its children (if any)
        3. Distance from leaf nodes (closer to leaves = more refined)

        Adapted from VRAG/demo/vimrag_utils.py: calculate_intuitive_memory_energy

        Args:
            node_id: ID of the node to calculate energy for.

        Returns:
            Energy score in [0, 1].
        """
        node = self.nodes.get(node_id)
        if not node:
            return 0.0

        # Base energy from the node's own priority and usefulness
        base_energy = node.priority * (1.0 if node.is_useful else 0.1)

        if not node.child_ids:
            # Leaf node: energy = base energy
            return base_energy

        # Non-leaf node: energy flows from children
        child_energies = []
        for child_id in node.child_ids:
            child_energy = self.calculate_intuitive_memory_energy(child_id)
            child_energies.append(child_energy)

        # Energy is a weighted combination of base and child energies
        # Children contribute more energy (refined reasoning)
        avg_child_energy = sum(child_energies) / len(child_energies) if child_energies else 0.0

        # Energy decays with depth — leaf nodes have more refined energy
        energy = base_energy * 0.3 + avg_child_energy * 0.7

        return min(1.0, max(0.0, energy))

    def get_sorted_by_energy(self) -> list[tuple[MemoryNode, float]]:
        """Get all nodes sorted by their intuitive energy.

        Returns:
            List of (node, energy) tuples, sorted by energy descending.
        """
        results = []
        for node_id in self.node_order:
            node = self.nodes.get(node_id)
            if node:
                energy = self.calculate_intuitive_memory_energy(node_id)
                results.append((node, energy))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def generate_multimodal_messages(
        self,
        max_images: int = 8,
        max_texts: int = 5,
        include_reasoning: bool = True,
    ) -> list[dict]:
        """Generate messages for LLM consumption from the memory graph.

        Adapted from VRAG/demo/vimrag_utils.py: generate_multimodal_messages

        Args:
            max_images: Maximum number of images to include.
            max_texts: Maximum number of text descriptions to include.
            include_reasoning: Include reasoning/summary text from nodes.

        Returns:
            List of message dictionaries for LLM context.
        """
        messages = []
        included_images = 0
        included_texts = 0

        # Get nodes sorted by energy (most important first)
        sorted_nodes = self.get_sorted_by_energy()

        for node, energy in sorted_nodes:
            if not node.is_useful and energy < 0.3:
                continue

            # Add reasoning text
            if include_reasoning and node.summary:
                messages.append({
                    "role": "system",
                    "content": f"[{node.type.upper()}] {node.summary}",
                })

            # Add images (as data URLs or paths)
            for img_path in node.images:
                if included_images >= max_images:
                    break
                messages.append({
                    "role": "system",
                    "content": f"[IMAGE] {img_path}",
                })
                included_images += 1

            # Add text summaries
            if included_texts < max_texts and node.key_insight:
                messages.append({
                    "role": "system",
                    "content": f"[INSIGHT] {node.key_insight}",
                })
                included_texts += 1

        return messages

    def to_dict(self) -> dict:
        """Serialize the memory graph to a dictionary."""
        return {
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "node_order": self.node_order,
            "total_nodes": len(self.nodes),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultimodalMemoryGraph":
        """Deserialize a memory graph from a dictionary."""
        graph = cls()
        for node_id, node_dict in data.get("nodes", {}).items():
            graph.nodes[node_id] = MemoryNode(**node_dict)
        graph.node_order = data.get("node_order", [])
        return graph

    def to_dag_json(self) -> dict:
        """Export the memory graph as a DAG structure for frontend visualization.

        Returns:
            Dict with nodes and edges arrays suitable for vis.js or D3.
        """
        nodes = []
        edges = []

        for node in self.nodes.values():
            # Calculate energy for the node
            energy = self.calculate_intuitive_memory_energy(node.id)
            node_images = [image for image in node.images if image]

            nodes.append({
                "id": node.id,
                "label": f"[{node.type}]\n{node.summary[:50]}...",
                "type": node.type,
                "summary": node.summary,
                "parent_ids": list(node.parent_ids),
                "images": node_images,
                "priority": node.priority,
                "is_useful": node.is_useful,
                "key_insight": node.key_insight,
                "energy": energy,
                "image_count": len(node_images),
                "created_at": node.created_at,
            })

            for parent_id in node.parent_ids:
                edges.append({
                    "source": parent_id,
                    "target": node.id,
                    "relation": "depends_on",
                    "from": parent_id,
                    "to": node.id,
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    def get_context_for_answer(self) -> str:
        """Get a text summary of the memory graph for answer generation."""
        sorted_nodes = self.get_sorted_by_energy()
        useful_nodes = [(n, e) for n, e in sorted_nodes if n.is_useful]

        if not useful_nodes:
            return "No useful visual evidence found."

        parts = []
        for node, energy in useful_nodes[:10]:
            part = f"- [{node.type}] {node.summary}"
            if node.key_insight:
                part += f"\n  Insight: {node.key_insight}"
            if node.images:
                part += f"\n  Images: {len(node.images)}"
            parts.append(part)

        return "\n".join(parts)
