"""
Memory retrieval module for prompt assembly.

This module implements the memory retrieval pipeline with the following priority:
1. PET-CANON (5-10 concise canonical sentences)
2. C&C (Commitments & Claims - active items)
3. Semantic facts (3-5 highest importance)
4. Episodic events (1 most relevant)
5. Echo-Trace (max 1 speech pattern)

Total budget: ≤1000 tokens
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetrievedContext:
    """Context retrieved from memory for prompt assembly."""
    pet_canon: str = ""
    commitments: List[str] = None
    semantic_facts: List[str] = None
    episodic_event: str = ""
    echo_trace: str = ""
    total_tokens_estimate: int = 0
    
    def __post_init__(self):
        if self.commitments is None:
            self.commitments = []
        if self.semantic_facts is None:
            self.semantic_facts = []


class MemoryRetriever:
    """
    Retrieves memory context for prompt assembly.
    
    Implements priority-based retrieval with token budget management.
    """
    
    def __init__(self, token_budget: int = 1000):
        """
        Initialize memory retriever.
        
        Args:
            token_budget: Maximum tokens to use for context (default: 1000)
        """
        self.token_budget = token_budget
        self.retrievals_count = 0
        
        logger.info(f"🧠 MemoryRetriever initialized with {token_budget} token budget")
    
    def retrieve(
        self,
        pet_state,
        user_message: str
    ) -> RetrievedContext:
        """
        Retrieve memory context for the current interaction.
        
        Args:
            pet_state: PetState instance with memory
            user_message: Current user message (for relevance)
        
        Returns:
            RetrievedContext with retrieved items
        """
        self.retrievals_count += 1
        context = RetrievedContext()
        remaining_tokens = self.token_budget
        
        logger.info(f"🔍 Retrieving memory context (budget: {self.token_budget} tokens)")
        
        # 1. PET-CANON (highest priority, ~200-400 tokens)
        if hasattr(pet_state.memory, 'pet_canon') and pet_state.memory.pet_canon:
            canon_text = pet_state.memory.pet_canon.to_prompt_text(max_sentences=10)
            canon_tokens = self._estimate_tokens(canon_text)
            
            if canon_tokens <= remaining_tokens:
                context.pet_canon = canon_text
                remaining_tokens -= canon_tokens
                logger.info(f"📜 PET-CANON: {canon_tokens} tokens")
            else:
                # Truncate to fit
                context.pet_canon = self._truncate_to_tokens(canon_text, remaining_tokens)
                remaining_tokens = 0
                logger.warning(f"⚠️ PET-CANON truncated to fit budget")
        
        # 2. C&C - Commitments & Claims (high priority, ~100-200 tokens)
        if hasattr(pet_state.memory, 'abm') and pet_state.memory.abm:
            from .autobiographical_memory import ABMType
            
            # Get active C&C items
            cc_items = pet_state.memory.abm.get_active_items(ABMType.C_AND_C_PERSONA, min_importance=0.4)
            
            for item in cc_items[:5]:  # Max 5 commitments
                item_text = item.canonical_text
                item_tokens = self._estimate_tokens(item_text)
                
                if item_tokens <= remaining_tokens:
                    context.commitments.append(item_text)
                    remaining_tokens -= item_tokens
                else:
                    break
            
            if context.commitments:
                logger.info(f"🤝 C&C: {len(context.commitments)} items, ~{sum(self._estimate_tokens(c) for c in context.commitments)} tokens")
        
        # 3. Semantic facts (3-5 highest importance, ~150-200 tokens)
        if hasattr(pet_state.memory, 'semantic') and pet_state.memory.semantic:
            # Get top semantic facts by importance
            facts = pet_state.memory.get_semantic_facts(min_weight=0.3)
            
            # Sort by importance (weight)
            facts_with_importance = []
            for fact, (weight, timestamp, access_count) in facts.items():
                facts_with_importance.append((fact, weight))
            
            facts_with_importance.sort(key=lambda x: x[1], reverse=True)
            
            # Take top 3-5 facts that fit in budget
            for fact, importance in facts_with_importance[:5]:
                fact_tokens = self._estimate_tokens(fact)
                
                if fact_tokens <= remaining_tokens:
                    context.semantic_facts.append(fact)
                    remaining_tokens -= fact_tokens
                else:
                    break
            
            if context.semantic_facts:
                logger.info(f"💭 Semantic: {len(context.semantic_facts)} facts, ~{sum(self._estimate_tokens(f) for f in context.semantic_facts)} tokens")
        
        # 4. Episodic event (1 most relevant, ~150-250 tokens)
        if hasattr(pet_state.memory, 'episodic') and pet_state.memory.episodic:
            # Get most recent or most relevant event
            if pet_state.memory.episodic:
                # For now, just take the most recent high-importance event
                recent_events = sorted(
                    pet_state.memory.episodic,
                    key=lambda x: (x.importance_score, x.timestamp),
                    reverse=True
                )
                
                if recent_events:
                    event = recent_events[0]
                    event_summary = f"{event.kind}: {event.text}"
                    event_tokens = self._estimate_tokens(event_summary)
                    
                    if event_tokens <= remaining_tokens:
                        context.episodic_event = event_summary
                        remaining_tokens -= event_tokens
                        logger.info(f"📝 Episode: 1 event, ~{event_tokens} tokens")
                    else:
                        # Truncate event to fit
                        context.episodic_event = self._truncate_to_tokens(event_summary, remaining_tokens)
                        remaining_tokens = 0
        
        # 5. Echo-Trace (max 1 pattern, ~50-100 tokens)
        if hasattr(pet_state.memory, 'echo_trace') and pet_state.memory.echo_trace:
            pattern = pet_state.memory.echo_trace.get_dominant_pattern()
            if pattern:
                pattern_tokens = self._estimate_tokens(pattern)
                
                if pattern_tokens <= remaining_tokens:
                    context.echo_trace = pattern
                    remaining_tokens -= pattern_tokens
                    logger.info(f"🔊 Echo-Trace: 1 pattern, ~{pattern_tokens} tokens")
        
        # Calculate total tokens used
        context.total_tokens_estimate = self.token_budget - remaining_tokens
        
        logger.info(f"✅ Retrieved context: ~{context.total_tokens_estimate}/{self.token_budget} tokens used")
        
        return context
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Simple heuristic: ~4 chars per token for Portuguese/English mix.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Simple approximation: 1 token ≈ 4 characters
        return max(1, len(text) // 4)
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token budget.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
        
        Returns:
            Truncated text
        """
        if not text:
            return ""
        
        max_chars = max_tokens * 4  # Approximate
        
        if len(text) <= max_chars:
            return text
        
        # Truncate at word boundary
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def assemble_prompt(
        self,
        context: RetrievedContext,
        user_message: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Assemble the final prompt from retrieved context.
        
        Args:
            context: Retrieved context
            user_message: Current user message
            system_instruction: Optional system-level instruction
        
        Returns:
            Assembled prompt string
        """
        parts = []
        
        # System instruction (if provided)
        if system_instruction:
            parts.append(f"INSTRUÇÃO: {system_instruction}")
            parts.append("")
        
        # PET-CANON (who I am)
        if context.pet_canon:
            parts.append("IDENTIDADE (PET-CANON):")
            parts.append(context.pet_canon)
            parts.append("")
        
        # Commitments & Claims
        if context.commitments:
            parts.append("COMPROMISSOS ATIVOS:")
            for i, commitment in enumerate(context.commitments, 1):
                parts.append(f"  {i}. {commitment}")
            parts.append("")
        
        # Semantic facts
        if context.semantic_facts:
            parts.append("FATOS IMPORTANTES SOBRE O USUÁRIO:")
            for i, fact in enumerate(context.semantic_facts, 1):
                parts.append(f"  - {fact}")
            parts.append("")
        
        # Episodic event
        if context.episodic_event:
            parts.append("CONTEXTO RECENTE:")
            parts.append(f"  {context.episodic_event}")
            parts.append("")
        
        # Echo-Trace pattern
        if context.echo_trace:
            parts.append("PADRÃO DE COMUNICAÇÃO:")
            parts.append(f"  {context.echo_trace}")
            parts.append("")
        
        # User message
        parts.append("MENSAGEM DO USUÁRIO:")
        parts.append(user_message)
        parts.append("")
        parts.append("RESPOSTA:")
        
        prompt = "\n".join(parts)
        
        logger.debug(f"📝 Assembled prompt: {len(prompt)} chars")
        
        return prompt
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "retrievals_count": self.retrievals_count,
            "token_budget": self.token_budget
        }
