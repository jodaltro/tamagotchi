"""
Echo-Trace module for tracking successful speech patterns.

Echo-Trace stores micro-patterns of speech that worked well in past
interactions. These patterns help maintain natural and consistent
communication style without verbatim repetition.

Patterns are short (≤120 chars) and categorized by context (greeting,
transition, confirmation, etc.). They serve as material for paraphrasing,
not literal quoting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PatternContext(str, Enum):
    """Context where a speech pattern was used successfully."""
    GREETING = "greeting"  # Opening/hello messages
    FAREWELL = "farewell"  # Closing/goodbye messages
    TRANSITION = "transition"  # Changing topics
    CONFIRMATION = "confirmation"  # Acknowledging/confirming
    QUESTION = "question"  # Asking for information
    EMPATHY = "empathy"  # Showing understanding/care
    ENTHUSIASM = "enthusiasm"  # Expressing excitement
    APOLOGY = "apology"  # Correcting/apologizing
    EXPLANATION = "explanation"  # Describing something
    HUMOR = "humor"  # Playful/funny responses


@dataclass
class EchoPattern:
    """A successful speech pattern from past interactions."""
    
    pattern_text: str  # The actual pattern (≤120 chars)
    context_tag: PatternContext  # When it was used
    success_signal: float = 0.5  # Implicit success score (0-1)
    usage_count: int = 1  # How many times used
    last_used: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for storage."""
        return {
            "pattern_text": self.pattern_text,
            "context_tag": self.context_tag.value,
            "success_signal": self.success_signal,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat(),
            "created_at": self.created_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'EchoPattern':
        """Deserialize from dictionary."""
        return EchoPattern(
            pattern_text=data["pattern_text"],
            context_tag=PatternContext(data["context_tag"]),
            success_signal=data.get("success_signal", 0.5),
            usage_count=data.get("usage_count", 1),
            last_used=datetime.fromisoformat(data["last_used"]),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        )
    
    def __repr__(self) -> str:
        return f"EchoPattern({self.context_tag.value}, '{self.pattern_text[:30]}...', used={self.usage_count})"


class EchoTrace:
    """
    Manages successful speech patterns for natural communication.
    
    Stores patterns that worked well and provides them for paraphrasing
    in future interactions. Helps maintain consistency without repetition.
    """
    
    def __init__(self, max_patterns: int = 50):
        self.patterns: List[EchoPattern] = []
        self.max_patterns = max_patterns
    
    def add_pattern(
        self,
        text: str,
        context: PatternContext,
        success_signal: float = 0.5
    ) -> Optional[EchoPattern]:
        """
        Add a new speech pattern or reinforce existing one.
        
        Args:
            text: The pattern text (≤120 chars)
            context: Context where it was used
            success_signal: Success score (0-1)
        
        Returns:
            The created or updated pattern
        """
        # Truncate if too long
        if len(text) > 120:
            logger.warning(f"⚠️ Pattern too long ({len(text)} chars), truncating")
            text = text[:117] + "..."
        
        # Ignore very short patterns
        if len(text) < 10:
            return None
        
        # Check for existing similar pattern
        existing = self._find_similar_pattern(text, context)
        if existing:
            # Reinforce existing
            existing.usage_count += 1
            existing.last_used = datetime.utcnow()
            existing.success_signal = (existing.success_signal + success_signal) / 2  # Average
            logger.info(f"💪 Reinforced echo pattern ({context.value}): '{text[:30]}...'")
            return existing
        
        # Create new pattern
        pattern = EchoPattern(
            pattern_text=text,
            context_tag=context,
            success_signal=success_signal
        )
        self.patterns.append(pattern)
        
        # Prune if too many patterns
        if len(self.patterns) > self.max_patterns:
            self._prune_patterns()
        
        logger.info(f"✨ Added echo pattern ({context.value}): '{text[:30]}...'")
        return pattern
    
    def get_patterns_for_context(
        self,
        context: PatternContext,
        top_k: int = 3,
        min_success: float = 0.3
    ) -> List[EchoPattern]:
        """
        Get successful patterns for a specific context.
        
        Args:
            context: The context to search for
            top_k: Maximum patterns to return
            min_success: Minimum success threshold
        
        Returns:
            List of matching patterns sorted by success
        """
        matching = [
            p for p in self.patterns
            if p.context_tag == context
            and p.success_signal >= min_success
        ]
        
        # Sort by success and recency
        matching.sort(
            key=lambda p: (p.success_signal * 0.7 + (p.usage_count / 10) * 0.3),
            reverse=True
        )
        
        return matching[:top_k]
    
    def extract_from_response(
        self,
        response: str,
        user_reaction_positive: bool = True
    ) -> List[EchoPattern]:
        """
        Extract potential patterns from a pet response.
        
        Identifies useful segments based on structure and user reaction.
        
        Args:
            response: The pet's response text
            user_reaction_positive: Whether user reacted positively
        
        Returns:
            List of extracted patterns
        """
        extracted = []
        
        # Success signal based on user reaction
        success = 0.7 if user_reaction_positive else 0.3
        
        # Detect context from content
        response_lower = response.lower()
        
        # Greetings
        greeting_markers = ["olá", "oi", "hey", "bom dia", "boa tarde", "boa noite"]
        if any(marker in response_lower for marker in greeting_markers):
            # Extract first sentence as greeting pattern
            first_sentence = response.split('.')[0].strip()
            if len(first_sentence) <= 120:
                pattern = self.add_pattern(first_sentence, PatternContext.GREETING, success)
                if pattern:
                    extracted.append(pattern)
        
        # Questions
        if "?" in response:
            # Extract question sentences
            sentences = response.split('.')
            for sentence in sentences:
                if "?" in sentence:
                    question = sentence.strip()
                    if len(question) <= 120:
                        pattern = self.add_pattern(question, PatternContext.QUESTION, success)
                        if pattern:
                            extracted.append(pattern)
                            break  # One question per response
        
        # Empathy/confirmation
        empathy_markers = ["entendo", "compreendo", "sei como", "imagino que", "deve ser"]
        if any(marker in response_lower for marker in empathy_markers):
            for sentence in response.split('.'):
                if any(marker in sentence.lower() for marker in empathy_markers):
                    empathy_text = sentence.strip()
                    if 10 < len(empathy_text) <= 120:
                        pattern = self.add_pattern(empathy_text, PatternContext.EMPATHY, success)
                        if pattern:
                            extracted.append(pattern)
                            break
        
        # Enthusiasm
        enthusiasm_markers = ["!", "adorei", "que legal", "incrível", "ótimo", "maravilha"]
        if any(marker in response_lower for marker in enthusiasm_markers) or response.count("!") >= 2:
            for sentence in response.split('.'):
                if any(marker in sentence.lower() for marker in enthusiasm_markers) or "!" in sentence:
                    enthusiasm_text = sentence.strip()
                    if 10 < len(enthusiasm_text) <= 120:
                        pattern = self.add_pattern(enthusiasm_text, PatternContext.ENTHUSIASM, success)
                        if pattern:
                            extracted.append(pattern)
                            break
        
        if extracted:
            logger.info(f"🎯 Extracted {len(extracted)} echo patterns from response")
        
        return extracted
    
    def _find_similar_pattern(self, text: str, context: PatternContext) -> Optional[EchoPattern]:
        """Find an existing pattern similar to the given text."""
        text_lower = text.lower()
        
        for pattern in self.patterns:
            if (pattern.context_tag == context
                and (text_lower in pattern.pattern_text.lower()
                     or pattern.pattern_text.lower() in text_lower)):
                return pattern
        
        return None
    
    def _prune_patterns(self):
        """Remove least successful patterns when limit exceeded."""
        # Sort by success and usage
        self.patterns.sort(
            key=lambda p: (p.success_signal * 0.6 + (p.usage_count / 10) * 0.4),
            reverse=True
        )
        
        # Keep only top max_patterns
        removed_count = len(self.patterns) - self.max_patterns
        self.patterns = self.patterns[:self.max_patterns]
        
        logger.info(f"🌿 Pruned {removed_count} low-success echo patterns")
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for storage."""
        return {
            "patterns": [p.to_dict() for p in self.patterns],
            "max_patterns": self.max_patterns
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'EchoTrace':
        """Deserialize from dictionary."""
        echo = EchoTrace(max_patterns=data.get("max_patterns", 50))
        echo.patterns = [EchoPattern.from_dict(p) for p in data.get("patterns", [])]
        return echo
    
    def __repr__(self) -> str:
        return f"EchoTrace({len(self.patterns)} patterns, max={self.max_patterns})"
