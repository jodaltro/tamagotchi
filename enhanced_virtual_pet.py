"""
Enhanced Virtual Pet with Advanced Memory System.

This module provides an enhanced VirtualPet that uses the advanced memory system
while maintaining backward compatibility with the existing API.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .virtual_pet import VirtualPet
from .memory_integration import HybridMemoryStore, format_context_for_prompt
from .firestore_store import get_firestore_client

logger = logging.getLogger(__name__)


class EnhancedVirtualPet(VirtualPet):
    """
    Enhanced Virtual Pet with advanced memory capabilities.
    
    Features:
    - Event segmentation for conversation history
    - Commitment tracking and fulfillment
    - Hierarchical memory consolidation
    - Hybrid retrieval with salience scoring
    - Spaced repetition for important facts
    - Metrics tracking for validation
    """
    
    def __init__(self, user_id: str, personality_archetype: Optional[str] = None):
        """
        Initialize enhanced virtual pet with advanced memory.
        
        Args:
            user_id: User identifier for memory persistence
            personality_archetype: Optional personality archetype
        """
        # Initialize base pet
        super().__init__(personality_archetype=personality_archetype)
        
        self.user_id = user_id
        
        # Replace standard memory with hybrid memory store
        firestore_client = get_firestore_client()
        self.state.memory = HybridMemoryStore(user_id, firestore_client)
        
        logger.info(f"✨ Initialized enhanced pet for user: {user_id}")
    
    def user_message(self, text: str, delay: Optional[float] = None) -> None:
        """
        Process user message with advanced memory tracking.
        
        This extends the base method to capture the conversation turn
        for advanced processing.
        """
        # Call parent implementation
        super().user_message(text, delay)
        
        # Store for turn processing
        self._last_user_message = text
    
    def pet_response(self) -> str:
        """
        Generate pet response using advanced memory context.
        
        This extends the base method to use hybrid retrieval and
        process the complete conversation turn.
        """
        # Generate response using parent method
        response = super().pet_response()
        
        # Process the complete turn with advanced memory
        if hasattr(self, '_last_user_message'):
            user_msg = self._last_user_message
            
            # Process turn for commitment detection, segmentation, etc.
            self.state.memory.process_conversation_turn(
                user_message=user_msg,
                pet_response=response,
                user_embedding=None,  # TODO: Add embedding generation
                pet_embedding=None
            )
            
            # Clear cached message
            delattr(self, '_last_user_message')
        
        return response
    
    def get_enhanced_context(self, query: str, max_tokens: int = 1200) -> Dict[str, Any]:
        """
        Get enhanced context using hybrid retrieval.
        
        Args:
            query: Query text (usually last user message)
            max_tokens: Maximum tokens for context
        
        Returns:
            Structured context dictionary
        """
        return self.state.memory.get_context_for_response(
            query=query,
            max_tokens=max_tokens,
            query_embedding=None  # TODO: Add embedding generation
        )
    
    def format_context_for_prompt(self, query: str) -> str:
        """
        Format context as a string for prompt inclusion.
        
        Args:
            query: Query text
        
        Returns:
            Formatted context string
        """
        context = self.get_enhanced_context(query)
        return format_context_for_prompt(context)
    
    def end_session(self) -> Dict[str, Any]:
        """
        End conversation session with consolidation.
        
        This should be called at the end of a conversation session
        to trigger reflection and consolidation.
        
        Returns:
            Consolidation summary
        """
        logger.info("📝 Ending session and consolidating memories")
        return self.state.memory.consolidate_session()
    
    def get_daily_digest(self, date: Optional[str] = None):
        """
        Get or generate daily digest.
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
        
        Returns:
            DailyDigest object
        """
        return self.state.memory.generate_daily_digest(date)
    
    def get_active_commitments(self) -> List[str]:
        """
        Get list of active pet commitments.
        
        Returns:
            List of commitment descriptions
        """
        return self.state.memory.get_active_commitments()
    
    def mark_commitment_done(self, commitment_id: str):
        """
        Mark a commitment as fulfilled.
        
        Args:
            commitment_id: Commitment identifier
        """
        self.state.memory.mark_commitment_done(commitment_id)
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        Get current memory system metrics.
        
        Returns:
            Dictionary with metrics:
            - commitment_resolution_rate
            - thread_closure_latency_hours
            - self_consistency_per_100_turns
            - recall_utility
            - avg_tokens_per_turn
        """
        return self.state.memory.get_metrics()
    
    def get_relationship_stage(self) -> str:
        """Get current relationship stage with user."""
        return self.state.memory.get_relationship_stage()
    
    def set_relationship_stage(self, stage: str):
        """
        Update relationship stage.
        
        Args:
            stage: New stage (stranger, acquaintance, friend, close_friend)
        """
        self.state.memory.update_relationship_stage(stage)


def create_enhanced_pet(
    user_id: str,
    personality_archetype: Optional[str] = None
) -> EnhancedVirtualPet:
    """
    Factory function to create an enhanced virtual pet.
    
    Args:
        user_id: User identifier
        personality_archetype: Optional personality archetype
    
    Returns:
        EnhancedVirtualPet instance
    """
    return EnhancedVirtualPet(user_id=user_id, personality_archetype=personality_archetype)


# Example usage
if __name__ == "__main__":
    # Create enhanced pet
    pet = create_enhanced_pet(user_id="demo_user", personality_archetype="curious")
    
    # Simulate conversation
    print("=== Enhanced Pet Conversation Demo ===\n")
    
    # Turn 1
    pet.user_message("Olá! Meu nome é João.")
    response = pet.pet_response()
    print(f"Usuário: Olá! Meu nome é João.")
    print(f"Pet: {response}\n")
    
    # Turn 2
    pet.user_message("Você pode me lembrar de comprar leite amanhã?")
    response = pet.pet_response()
    print(f"Usuário: Você pode me lembrar de comprar leite amanhã?")
    print(f"Pet: {response}\n")
    
    # Turn 3
    pet.user_message("O que você sabe sobre mim?")
    response = pet.pet_response()
    print(f"Usuário: O que você sabe sobre mim?")
    print(f"Pet: {response}\n")
    
    # Show active commitments
    commitments = pet.get_active_commitments()
    print(f"Compromissos ativos: {commitments}\n")
    
    # Show metrics
    metrics = pet.get_memory_metrics()
    print(f"Métricas: {metrics}\n")
    
    # End session
    consolidation = pet.end_session()
    print(f"Consolidação de sessão: {consolidation}\n")
    
    # Get daily digest
    digest = pet.get_daily_digest()
    print(f"Resumo do dia: {digest.daily_card}\n")
    print(f"Novos fatos: {digest.new_facts}\n")
    print(f"Compromissos ativos: {digest.active_commitments}\n")
