"""
Autobiographical Memory (ABM) module for the organic virtual pet.

This module manages the pet's memories about itself - what it said, believes,
its communication style, limits, capabilities, and interaction commitments.
It prevents persona drift and maintains consistency across conversations.

Key Features:
- Pet Claims (C-PET): Factual statements the pet made about itself
- Voice & Style (VOICE): Stable speech patterns and tone preferences
- Principles & Limits (POLICY): What the pet does/doesn't do
- Skills & Tools (TOOLS): Declared capabilities
- Persona Commitments (C&C-PERSONA): How the pet promises to interact

All canonical items are kept concise (≤140 chars) for efficient retrieval.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ABMType(str, Enum):
    """Types of autobiographical memory items."""
    C_PET = "C-PET"  # Claims about self/functioning
    VOICE = "VOICE"  # Style and tone patterns
    POLICY = "POLICY"  # Principles and limits
    TOOLS = "TOOLS"  # Skills and capabilities
    C_AND_C_PERSONA = "C&C-PERSONA"  # Interaction commitments


class ABMStatus(str, Enum):
    """Status of an ABM item."""
    ACTIVE = "active"  # Currently valid
    REVISED = "revised"  # Superseded by newer item
    DROPPED = "dropped"  # No longer applicable


@dataclass
class ABMItem:
    """A single autobiographical memory item about the pet."""
    
    type: ABMType
    canonical_text: str  # Short phrase in 1st person (≤140 chars)
    source_event_id: str  # Event where it was said/established
    stability: float = 0.8  # How durable (0-1, high = slow decay)
    importance: float = 0.5  # Impact on dialogue (0-1)
    last_verified: datetime = field(default_factory=datetime.utcnow)
    status: ABMStatus = ABMStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    revision_reason: Optional[str] = None  # Why it was revised/dropped
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for storage."""
        return {
            "type": self.type.value,
            "canonical_text": self.canonical_text,
            "source_event_id": self.source_event_id,
            "stability": self.stability,
            "importance": self.importance,
            "last_verified": self.last_verified.isoformat(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "revision_reason": self.revision_reason
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'ABMItem':
        """Deserialize from dictionary."""
        return ABMItem(
            type=ABMType(data["type"]),
            canonical_text=data["canonical_text"],
            source_event_id=data["source_event_id"],
            stability=data.get("stability", 0.8),
            importance=data.get("importance", 0.5),
            last_verified=datetime.fromisoformat(data["last_verified"]),
            status=ABMStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            revision_reason=data.get("revision_reason")
        )
    
    def __repr__(self) -> str:
        return f"ABMItem({self.type.value}, '{self.canonical_text[:50]}...', {self.status.value})"


class AutobiographicalMemory:
    """
    Manages the pet's autobiographical memory - what it knows about itself.
    
    This ensures consistency by tracking:
    - What the pet has claimed about itself
    - Its communication style and tone
    - Its policies and boundaries  
    - Its capabilities and tools
    - Its commitments about how it interacts
    """
    
    def __init__(self):
        self.items: List[ABMItem] = []
        self.last_consolidation: datetime = datetime.utcnow()
    
    def add_claim(
        self,
        text: str,
        claim_type: ABMType,
        source_event_id: str,
        importance: float = 0.5,
        stability: float = 0.8
    ) -> ABMItem:
        """
        Add a new autobiographical claim.
        
        Args:
            text: Canonical text (≤140 chars, 1st person)
            claim_type: Type of claim
            source_event_id: ID of event where claim was made
            importance: Impact score (0-1)
            stability: Durability score (0-1)
        
        Returns:
            The created ABM item
        """
        # Ensure text is concise
        if len(text) > 140:
            logger.warning(f"⚠️ ABM text too long ({len(text)} chars), truncating: {text[:50]}...")
            text = text[:137] + "..."
        
        # Check for existing similar claims
        similar = self._find_similar_claim(text, claim_type)
        if similar:
            # Reinforce existing claim
            similar.importance = min(1.0, similar.importance + 0.1)
            similar.last_verified = datetime.utcnow()
            logger.info(f"💪 Reinforced existing ABM claim: {similar.canonical_text[:50]}...")
            return similar
        
        # Create new claim
        item = ABMItem(
            type=claim_type,
            canonical_text=text,
            source_event_id=source_event_id,
            importance=importance,
            stability=stability
        )
        self.items.append(item)
        logger.info(f"✨ Added new ABM item ({claim_type.value}): {text[:50]}...")
        return item
    
    def revise_claim(self, old_text: str, new_text: str, reason: str, source_event_id: str) -> Optional[ABMItem]:
        """
        Revise an existing claim, marking the old one as revised.
        
        Args:
            old_text: Text of claim to revise
            new_text: New canonical text
            reason: Brief explanation of why it changed
            source_event_id: Event ID where revision happened
        
        Returns:
            The new ABM item, or None if old claim not found
        """
        # Find the old claim
        old_item = None
        for item in self.items:
            if item.status == ABMStatus.ACTIVE and old_text.lower() in item.canonical_text.lower():
                old_item = item
                break
        
        if not old_item:
            logger.warning(f"⚠️ Could not find claim to revise: {old_text[:50]}...")
            return None
        
        # Mark old as revised
        old_item.status = ABMStatus.REVISED
        old_item.revision_reason = reason
        
        # Create new version
        new_item = ABMItem(
            type=old_item.type,
            canonical_text=new_text,
            source_event_id=source_event_id,
            importance=old_item.importance,
            stability=old_item.stability
        )
        self.items.append(new_item)
        
        logger.info(f"🔄 Revised ABM claim: '{old_text[:30]}...' → '{new_text[:30]}...' (reason: {reason})")
        return new_item
    
    def get_active_items(
        self,
        item_type: Optional[ABMType] = None,
        min_importance: float = 0.0
    ) -> List[ABMItem]:
        """
        Get active ABM items, optionally filtered by type and importance.
        
        Args:
            item_type: Filter by specific type (None = all types)
            min_importance: Minimum importance threshold
        
        Returns:
            List of active items matching criteria
        """
        items = [
            item for item in self.items
            if item.status == ABMStatus.ACTIVE
            and item.importance >= min_importance
            and (item_type is None or item.type == item_type)
        ]
        
        # Sort by importance (descending)
        items.sort(key=lambda x: x.importance, reverse=True)
        return items
    
    def get_top_items(self, top_k: int = 10) -> List[ABMItem]:
        """
        Get the most important active ABM items for prompt inclusion.
        
        Args:
            top_k: Maximum number of items to return
        
        Returns:
            Top K items sorted by importance
        """
        active = self.get_active_items()
        return active[:top_k]
    
    def _find_similar_claim(self, text: str, claim_type: ABMType) -> Optional[ABMItem]:
        """Find an active claim that is similar to the given text."""
        text_lower = text.lower()
        
        for item in self.items:
            if (item.status == ABMStatus.ACTIVE 
                and item.type == claim_type
                and (text_lower in item.canonical_text.lower() 
                     or item.canonical_text.lower() in text_lower)):
                return item
        
        return None
    
    def extract_from_response(self, response: str, event_id: str) -> List[ABMItem]:
        """
        Extract autobiographical claims from a pet response.
        
        Looks for patterns like:
        - "eu posso/não posso..."
        - "eu sou..."
        - "meu papel é..."
        - "vou sempre/nunca..."
        
        Args:
            response: The pet's response text
            event_id: ID of the event
        
        Returns:
            List of extracted ABM items
        """
        extracted = []
        response_lower = response.lower()
        
        # Patterns for self-claims (C-PET)
        c_pet_patterns = [
            ("eu posso", ABMType.C_PET),
            ("eu não posso", ABMType.C_PET),
            ("não tenho acesso", ABMType.C_PET),
            ("meu papel é", ABMType.C_PET),
            ("sou um", ABMType.C_PET),
        ]
        
        # Patterns for commitments (C&C-PERSONA)
        commitment_patterns = [
            ("vou sempre", ABMType.C_AND_C_PERSONA),
            ("vou te", ABMType.C_AND_C_PERSONA),
            ("sempre confirmo", ABMType.C_AND_C_PERSONA),
            ("nunca vou", ABMType.C_AND_C_PERSONA),
        ]
        
        # Patterns for policies (POLICY)
        policy_patterns = [
            ("não dou conselho", ABMType.POLICY),
            ("não faço", ABMType.POLICY),
            ("evito", ABMType.POLICY),
        ]
        
        all_patterns = c_pet_patterns + commitment_patterns + policy_patterns
        
        for pattern, claim_type in all_patterns:
            if pattern in response_lower:
                # Extract the sentence containing the pattern
                sentences = response.split('.')
                for sentence in sentences:
                    if pattern in sentence.lower():
                        # Clean and truncate
                        claim_text = sentence.strip()
                        if len(claim_text) > 5:  # Avoid trivial claims
                            item = self.add_claim(
                                claim_text,
                                claim_type,
                                event_id,
                                importance=0.7,  # Explicit claims are important
                                stability=0.9   # Explicit claims are stable
                            )
                            extracted.append(item)
                            break  # One claim per pattern
        
        if extracted:
            logger.info(f"📝 Extracted {len(extracted)} ABM claims from response")
        
        return extracted
    
    def to_dict(self) -> Dict:
        """Serialize ABM to dictionary for storage."""
        return {
            "items": [item.to_dict() for item in self.items],
            "last_consolidation": self.last_consolidation.isoformat()
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'AutobiographicalMemory':
        """Deserialize ABM from dictionary."""
        abm = AutobiographicalMemory()
        abm.items = [ABMItem.from_dict(item_data) for item_data in data.get("items", [])]
        if "last_consolidation" in data:
            abm.last_consolidation = datetime.fromisoformat(data["last_consolidation"])
        return abm
    
    def __repr__(self) -> str:
        active_count = len([i for i in self.items if i.status == ABMStatus.ACTIVE])
        return f"AutobiographicalMemory(active={active_count}, total={len(self.items)})"
