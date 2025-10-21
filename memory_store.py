"""
Memory management for the organic virtual pet.

This module defines the `MemoryStore` class, which manages episodic and semantic
memories. Episodic memories are recent experiences annotated with a salience
score, while semantic memories are consolidated facts or preferences that
persist long-term. Methods support adding new memories, consolidating salient
experiences, and recalling memories by keyword or recency.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class MemoryItem:
    kind: str
    text: str
    salience: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"MemoryItem(kind={self.kind}, text={self.text}, salience={self.salience:.2f})"


@dataclass
class MemoryStore:
    """Stores episodic, semantic, and visual memories for a virtual pet."""

    # Recent experiences with salience scores
    episodic: deque = field(default_factory=lambda: deque(maxlen=100))
    # Consolidated facts/preferences mapped to weights
    semantic: Dict[str, float] = field(default_factory=dict)
    # Photographic memory: pairs of (feature vector, labels)
    images: List[tuple[list[float], List[str]]] = field(default_factory=list)

    def add_episode(self, text: str, salience: float = 0.5) -> None:
        """Add a new episodic memory to the buffer."""
        self.episodic.append(MemoryItem(kind="episode", text=text, salience=salience))

    def add_image(self, features: list[float], labels: List[str]) -> None:
        """Store a photographic memory (features and labels) in the buffer.

        The features should be a list of floats (e.g., from ``extract_features``)
        representing the downsampled image, and labels are semantic tags from
        the Vision API or other classifier. The photographic memory is kept
        separate from episodic/semantic memories but can inform responses.
        """
        self.images.append((features, labels))

    def consolidate(self, threshold: float = 0.6) -> None:
        """Promote highly salient episodes into semantic memory."""
        for m in list(self.episodic):
            if m.salience >= threshold:
                key = m.text.lower().strip()
                self.semantic[key] = self.semantic.get(key, 0.0) + m.salience
                m.salience *= 0.1  # reduce salience to prevent repetitive promotion

    def recall(self, query: Optional[str] = None, top_k: int = 3) -> List[str]:
        """Recall memories based on a query or return recent episodic entries."""
        if query:
            key = query.lower().strip()
            matches = [
                (text, weight)
                for text, weight in self.semantic.items()
                if key in text
            ]
            matches.sort(key=lambda x: x[1], reverse=True)
            return [text for text, _ in matches[:top_k]]
        else:
            return [m.text for m in list(self.episodic)[-top_k:]]

    def find_similar_image(self, features: list[float], top_k: int = 1) -> List[List[str]]:
        """Find images in memory most similar to the provided features.

        Computes the Euclidean distance between the provided feature vector and
        each stored feature vector. Returns the labels of the top ``top_k``
        closest images. If no images are stored, returns an empty list.

        Args:
            features: A list of floats representing the query image.
            top_k: The number of similar images to return.

        Returns:
            A list of label lists for the most similar images.
        """
        if not self.images:
            return []
        import math
        def distance(a: list[float], b: list[float]) -> float:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        distances = [
            (distance(features, feat), labels)
            for feat, labels in self.images
        ]
        distances.sort(key=lambda x: x[0])
        return [labels for _, labels in distances[:top_k]]

    def __str__(self) -> str:
        return (
            f"MemoryStore(episodic={len(self.episodic)}, "
            f"semantic={len(self.semantic)}, images={len(self.images)})"
        )
