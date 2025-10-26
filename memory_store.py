"""
Memory management for the organic virtual pet.

This module defines the `MemoryStore` class, which manages episodic and semantic
memories with AI-driven importance detection, reinforcement learning, and
advanced image memory capabilities. Episodic memories are recent experiences 
annotated with a salience score, while semantic memories are consolidated facts 
or preferences that persist long-term. The system supports memory decay, 
reinforcement, and intelligent extraction of important information.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    kind: str
    text: str
    salience: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0  # For reinforcement learning
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    importance_score: float = 0.5  # AI-determined importance

    def __repr__(self) -> str:
        return f"MemoryItem(kind={self.kind}, text={self.text[:30]}..., salience={self.salience:.2f}, importance={self.importance_score:.2f})"


@dataclass
class ImageMemory:
    """Enhanced image memory with detailed AI-extracted information."""
    features: List[float]
    labels: List[str]
    timestamp: datetime
    ai_description: str = ""  # Detailed AI-generated description
    detected_entities: Dict[str, str] = field(default_factory=dict)  # e.g., {"person": "user", "style": "casual"}
    context: str = ""  # Conversation context when image was sent
    importance_score: float = 0.5
    
    def __repr__(self) -> str:
        return f"ImageMemory(labels={self.labels}, entities={len(self.detected_entities)}, importance={self.importance_score:.2f})"


@dataclass
class MemoryStore:
    """Stores episodic, semantic, and visual memories for a virtual pet with AI enhancement."""

    # Recent experiences with salience scores and reinforcement
    episodic: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Consolidated facts/preferences mapped to (weight, last_reinforced, access_count)
    semantic: Dict[str, Tuple[float, datetime, int]] = field(default_factory=dict)
    
    # Enhanced photographic memory with AI descriptions
    images: List[ImageMemory] = field(default_factory=list)
    
    # Memory decay tracking
    last_decay_time: datetime = field(default_factory=datetime.utcnow)

    def add_episode(self, text: str, salience: float = 0.5, importance_score: float = 0.5) -> None:
        """Add a new episodic memory to the buffer with AI-determined importance."""
        self.episodic.append(MemoryItem(
            kind="episode", 
            text=text, 
            salience=salience,
            importance_score=importance_score
        ))
        logger.debug(f"🧠 Added episodic memory: {text[:50]}... (importance: {importance_score:.2f})")

    def add_image_memory(
        self, 
        features: List[float], 
        labels: List[str],
        ai_description: str = "",
        detected_entities: Optional[Dict[str, str]] = None,
        context: str = "",
        importance_score: float = 0.5
    ) -> None:
        """Store an enhanced photographic memory with AI analysis."""
        image_memory = ImageMemory(
            features=features,
            labels=labels,
            timestamp=datetime.utcnow(),
            ai_description=ai_description,
            detected_entities=detected_entities or {},
            context=context,
            importance_score=importance_score
        )
        self.images.append(image_memory)
        logger.info(f"🖼️ Added image memory: {labels} | Entities: {detected_entities} | Importance: {importance_score:.2f}")

    # Legacy method for backward compatibility
    def add_image(self, features: list[float], labels: List[str]) -> None:
        """Store a photographic memory (legacy method for backward compatibility)."""
        self.add_image_memory(features, labels)

    def consolidate(self, threshold: float = 0.6) -> None:
        """Promote highly salient and important episodes into semantic memory."""
        consolidated_count = 0
        for m in list(self.episodic):
            # Consider both salience and AI-determined importance
            combined_score = (m.salience * 0.4 + m.importance_score * 0.6)
            
            if combined_score >= threshold:
                key = m.text.lower().strip()
                
                # Update semantic memory with reinforcement
                if key in self.semantic:
                    old_weight, _, old_count = self.semantic[key]
                    # Reinforcement: increase weight based on repetition
                    new_weight = min(1.0, old_weight + combined_score * 0.3)
                    self.semantic[key] = (new_weight, datetime.utcnow(), old_count + 1)
                    logger.debug(f"🔄 Reinforced memory: {key[:50]}... (weight: {old_weight:.2f} → {new_weight:.2f})")
                else:
                    self.semantic[key] = (combined_score, datetime.utcnow(), 1)
                    consolidated_count += 1
                    logger.debug(f"✨ Consolidated new memory: {key[:50]}... (weight: {combined_score:.2f})")
                
                # Reduce salience to prevent repetitive promotion
                m.salience *= 0.1
        
        if consolidated_count > 0:
            logger.info(f"🧠 Consolidated {consolidated_count} new memories into semantic store")

    def apply_memory_decay(self, hours_elapsed: float = 24.0) -> None:
        """Apply decay to memories based on time and lack of access (forgetting)."""
        current_time = datetime.utcnow()
        decay_factor = hours_elapsed / (24.0 * 7.0)  # Weekly decay cycle
        
        # Decay semantic memories that haven't been accessed
        decayed_count = 0
        forgotten_keys = []
        
        for key, (weight, last_accessed, access_count) in list(self.semantic.items()):
            hours_since_access = (current_time - last_accessed).total_seconds() / 3600.0
            
            # Less accessed memories decay faster
            access_factor = 1.0 / (1.0 + access_count * 0.2)  # More accesses = slower decay
            time_factor = min(1.0, hours_since_access / (24.0 * 30.0))  # Normalize to monthly
            
            decay_amount = decay_factor * access_factor * time_factor * 0.1
            new_weight = max(0.0, weight - decay_amount)
            
            if new_weight < 0.1:
                # Forget memories that have decayed too much
                forgotten_keys.append(key)
                decayed_count += 1
            else:
                self.semantic[key] = (new_weight, last_accessed, access_count)
        
        # Remove forgotten memories
        for key in forgotten_keys:
            del self.semantic[key]
        
        if decayed_count > 0:
            logger.info(f"🌫️ Forgot {decayed_count} decayed memories")
        
        self.last_decay_time = current_time

    def reinforce_memory(self, memory_text: str, boost: float = 0.2) -> bool:
        """Reinforce a memory when it's mentioned again (reinforcement learning)."""
        key = memory_text.lower().strip()
        
        if key in self.semantic:
            old_weight, _, old_count = self.semantic[key]
            new_weight = min(1.0, old_weight + boost)
            self.semantic[key] = (new_weight, datetime.utcnow(), old_count + 1)
            logger.info(f"💪 Reinforced memory: {key[:50]}... ({old_weight:.2f} → {new_weight:.2f})")
            return True
        
        return False

    def recall(self, query: Optional[str] = None, top_k: int = 3) -> List[str]:
        """Recall memories based on a query or return recent episodic entries.
        
        Updates access count and last_accessed timestamp for reinforcement learning.
        """
        if query:
            key = query.lower().strip()
            matches = []
            
            for text, (weight, last_accessed, access_count) in self.semantic.items():
                if key in text or text in key:
                    matches.append((text, weight))
                    # Update access tracking for reinforcement
                    self.semantic[text] = (weight, datetime.utcnow(), access_count + 1)
            
            matches.sort(key=lambda x: x[1], reverse=True)
            return [text for text, _ in matches[:top_k]]
        else:
            # Return recent memories in reverse chronological order (newest first)
            recent = list(self.episodic)[-top_k:]
            return [m.text for m in reversed(recent)]
    
    def get_semantic_facts(self, min_weight: float = 0.3) -> List[str]:
        """Get all semantic facts above a minimum weight threshold."""
        facts = [(text, weight) for text, (weight, _, _) in self.semantic.items() if weight >= min_weight]
        facts.sort(key=lambda x: x[1], reverse=True)
        return [text for text, _ in facts]

    def find_similar_image(self, features: list[float], top_k: int = 1) -> List[List[str]]:
        """Find images in memory most similar to the provided features."""
        if not self.images:
            return []
        import math
        
        def distance(a: list[float], b: list[float]) -> float:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        
        distances = [
            (distance(features, img.features), img.labels)
            for img in self.images
        ]
        distances.sort(key=lambda x: x[0])
        return [labels for _, labels in distances[:top_k]]
    
    def get_image_memories_with_context(self, top_k: int = 5) -> List[Dict]:
        """Get recent image memories with full context for AI analysis."""
        sorted_images = sorted(self.images, key=lambda x: x.timestamp, reverse=True)[:top_k]
        
        return [
            {
                "labels": img.labels,
                "description": img.ai_description,
                "entities": img.detected_entities,
                "context": img.context,
                "timestamp": img.timestamp.isoformat(),
                "importance": img.importance_score
            }
            for img in sorted_images
        ]

    def __str__(self) -> str:
        semantic_count = len(self.semantic)
        high_importance_count = sum(1 for _, (weight, _, _) in self.semantic.items() if weight > 0.7)
        
        return (
            f"MemoryStore(episodic={len(self.episodic)}, "
            f"semantic={semantic_count} ({high_importance_count} important), "
            f"images={len(self.images)})"
        )
