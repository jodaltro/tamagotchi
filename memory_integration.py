"""
Integration layer for advanced memory system with existing virtual pet.

This module provides backward-compatible integration of the advanced memory
system with the existing MemoryStore and VirtualPet classes.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .advanced_memory_manager import AdvancedMemoryManager
from .memory_store import MemoryStore, MemoryItem

logger = logging.getLogger(__name__)


class HybridMemoryStore(MemoryStore):
    """
    Enhanced MemoryStore that uses both legacy and advanced memory systems.
    
    Provides backward compatibility while leveraging advanced features:
    - Event segmentation
    - Commitment tracking
    - Hierarchical consolidation
    - Hybrid retrieval
    """
    
    def __init__(self, user_id: str, firestore_client=None):
        """
        Initialize hybrid memory store.
        
        Args:
            user_id: User identifier
            firestore_client: Optional Firestore client
        """
        super().__init__()
        self.user_id = user_id
        self.advanced_manager = AdvancedMemoryManager(user_id, firestore_client)
        self._last_user_message: Optional[str] = None
        self._last_pet_response: Optional[str] = None
    
    def add_episode(self, text: str, salience: float = 0.5, importance_score: float = 0.5) -> None:
        """
        Add episodic memory with advanced memory tracking.
        
        Override to capture conversation flow for event segmentation.
        """
        # Call parent method for legacy support
        super().add_episode(text, salience, importance_score)
        
        # Track for advanced memory (will be processed in process_conversation_turn)
        if text.startswith("disse:") or "usuário" in text.lower():
            # User message
            self._last_user_message = text
        else:
            # Pet response
            self._last_pet_response = text
    
    def process_conversation_turn(
        self,
        user_message: str,
        pet_response: str,
        user_embedding: Optional[List[float]] = None,
        pet_embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Process a complete conversation turn with advanced memory analysis.
        
        Args:
            user_message: User's message
            pet_response: Pet's response
            user_embedding: Optional embedding vector for user message
            pet_embedding: Optional embedding vector for pet response
        
        Returns:
            Dictionary with analysis results
        """
        result = self.advanced_manager.process_turn(
            user_message=user_message,
            pet_response=pet_response,
            user_embedding=user_embedding,
            pet_embedding=pet_embedding
        )
        
        # Also add to legacy episodic memory for backward compatibility
        super().add_episode(f"Usuário disse: {user_message}", salience=0.5, importance_score=0.6)
        super().add_episode(f"Eu respondi: {pet_response}", salience=0.4, importance_score=0.5)
        
        return result
    
    def get_context_for_response(
        self,
        query: str,
        max_tokens: int = 1200,
        query_embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve context using advanced hybrid retrieval.
        
        Args:
            query: Query text (usually last user message)
            max_tokens: Maximum tokens for context
            query_embedding: Optional query embedding
        
        Returns:
            Structured context dictionary
        """
        return self.advanced_manager.retrieve_context(
            query=query,
            max_tokens=max_tokens,
            query_embedding=query_embedding
        )
    
    def consolidate_session(self) -> Dict[str, Any]:
        """
        Run end-of-session consolidation with reflection.
        
        Returns:
            Consolidation summary
        """
        # Run legacy consolidation
        super().consolidate(threshold=0.6)
        
        # Run advanced consolidation
        return self.advanced_manager.consolidate_session()
    
    def generate_daily_digest(self, date: Optional[str] = None):
        """Generate daily digest card."""
        return self.advanced_manager.generate_daily_digest(date)
    
    def mark_commitment_done(self, commitment_id: str):
        """Mark a commitment as fulfilled."""
        self.advanced_manager.mark_commitment_done(commitment_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get memory system metrics."""
        return self.advanced_manager.get_metrics()
    
    def get_active_commitments(self) -> List[str]:
        """
        Get list of active commitments for display.
        
        Returns:
            List of commitment descriptions
        """
        return [
            c.desc for c in self.advanced_manager.commitments_cache
            if c.status == "active"
        ]
    
    def get_relationship_stage(self) -> str:
        """Get current relationship stage."""
        return self.advanced_manager.relationship_state.stage
    
    def update_relationship_stage(self, new_stage: str):
        """Update relationship stage."""
        self.advanced_manager.relationship_state.stage = new_stage
        logger.info(f"🤝 Relationship stage updated: {new_stage}")


def create_hybrid_memory_store(user_id: str, firestore_client=None) -> HybridMemoryStore:
    """
    Factory function to create a hybrid memory store.
    
    Args:
        user_id: User identifier
        firestore_client: Optional Firestore client
    
    Returns:
        HybridMemoryStore instance
    """
    return HybridMemoryStore(user_id=user_id, firestore_client=firestore_client)


def format_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format retrieved context into a prompt-friendly string.
    
    Args:
        context: Context dictionary from retrieve_context()
    
    Returns:
        Formatted context string for inclusion in prompts
    """
    parts = []
    
    # Commitments (highest priority)
    if context.get("commitments"):
        parts.append("COMPROMISSOS ATIVOS:")
        for commitment in context["commitments"]:
            parts.append(f"- {commitment}")
    
    # Semantic facts
    if context.get("semantic_facts"):
        parts.append("\nO QUE VOCÊ SABE:")
        for fact in context["semantic_facts"]:
            parts.append(f"- {fact}")
    
    # Recent events
    if context.get("recent_events"):
        parts.append("\nCONTEXTO RECENTE:")
        for event in context["recent_events"]:
            parts.append(f"- {event}")
    
    # Relationship state
    if context.get("relationship_state"):
        rel_state = context["relationship_state"]
        stage = rel_state.get("stage", "stranger")
        parts.append(f"\nRELACIONAMENTO: {stage}")
    
    return "\n".join(parts)


# Export key classes and functions
__all__ = [
    'HybridMemoryStore',
    'create_hybrid_memory_store',
    'format_context_for_prompt'
]
