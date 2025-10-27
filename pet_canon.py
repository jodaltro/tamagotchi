"""
PET-CANON module for consolidated pet identity.

The PET-CANON is a concise (5-10 sentences, ≤200-400 tokens) consolidated view
of who the pet is, derived from Autobiographical Memory (ABM). It's the first
thing retrieved in prompts to ensure consistent persona.

The canon covers:
- Role and purpose
- Capabilities and limits
- Communication style
- Core principles
- Interaction commitments
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging

from .autobiographical_memory import AutobiographicalMemory, ABMType

logger = logging.getLogger(__name__)


@dataclass
class PetCanon:
    """
    Consolidated identity of the pet - the essential "who I am".
    
    This is kept compact and updated only when significant changes occur.
    """
    
    role: str = ""  # Who the pet is and its purpose
    capabilities: List[str] = None  # What it can do
    limits: List[str] = None  # What it cannot/will not do
    style: str = ""  # How it communicates
    principles: List[str] = None  # Core values/policies
    commitments: List[str] = None  # How it promises to interact
    
    last_updated: datetime = None
    version: int = 1
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.limits is None:
            self.limits = []
        if self.principles is None:
            self.principles = []
        if self.commitments is None:
            self.commitments = []
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
    
    def to_prompt_text(self, max_sentences: int = 10) -> str:
        """
        Generate compact text for inclusion in prompts.
        
        Args:
            max_sentences: Maximum number of sentences to include
        
        Returns:
            Concise canon text for prompt
        """
        parts = []
        
        # Role (always include)
        if self.role:
            parts.append(self.role)
        
        # Capabilities (top 2)
        if self.capabilities:
            caps = self.capabilities[:2]
            if len(caps) == 1:
                parts.append(f"Eu posso {caps[0]}.")
            else:
                parts.append(f"Eu posso {' e '.join(caps)}.")
        
        # Limits (top 2)
        if self.limits:
            lims = self.limits[:2]
            if len(lims) == 1:
                parts.append(f"Eu não posso {lims[0]}.")
            else:
                parts.append(f"Eu não posso {' ou '.join(lims)}.")
        
        # Style (if defined)
        if self.style:
            parts.append(self.style)
        
        # Principles (top 2)
        if self.principles:
            princ = self.principles[:2]
            for p in princ:
                parts.append(p)
        
        # Commitments (top 2)
        if self.commitments:
            comms = self.commitments[:2]
            for c in comms:
                parts.append(c)
        
        # Limit to max sentences
        result = " ".join(parts[:max_sentences])
        
        logger.debug(f"📜 Generated canon text: {len(result)} chars, {len(parts)} sentences")
        return result
    
    def needs_update(self, abm: AutobiographicalMemory) -> bool:
        """
        Check if the canon needs updating based on ABM changes.
        
        Criteria:
        - New high-importance items (>0.7) added since last update
        - Revisions to critical claims
        - Significant accumulation of new claims
        
        Args:
            abm: Current autobiographical memory
        
        Returns:
            True if update recommended
        """
        # Get items created after last canon update
        new_items = [
            item for item in abm.items
            if item.created_at > self.last_updated
            and item.status.value == "active"
        ]
        
        # Check for high-importance new items
        high_importance_new = [
            item for item in new_items
            if item.importance > 0.7
        ]
        
        if high_importance_new:
            logger.info(f"🔔 Canon update needed: {len(high_importance_new)} high-importance new items")
            return True
        
        # Check for significant volume of changes (>5 new items)
        if len(new_items) > 5:
            logger.info(f"🔔 Canon update needed: {len(new_items)} new items accumulated")
            return True
        
        # Check for revisions
        revised_since_update = [
            item for item in abm.items
            if item.status.value == "revised"
            and item.last_verified > self.last_updated
        ]
        
        if revised_since_update:
            logger.info(f"🔔 Canon update needed: {len(revised_since_update)} items revised")
            return True
        
        return False
    
    def update_from_abm(self, abm: AutobiographicalMemory) -> bool:
        """
        Update the canon from current ABM state.
        
        Args:
            abm: Current autobiographical memory
        
        Returns:
            True if canon was updated
        """
        # Get active items by type
        c_pet_items = abm.get_active_items(ABMType.C_PET, min_importance=0.4)
        voice_items = abm.get_active_items(ABMType.VOICE, min_importance=0.4)
        policy_items = abm.get_active_items(ABMType.POLICY, min_importance=0.4)
        tool_items = abm.get_active_items(ABMType.TOOLS, min_importance=0.4)
        commitment_items = abm.get_active_items(ABMType.C_AND_C_PERSONA, min_importance=0.4)
        
        updated = False
        
        # Extract role from C-PET items
        role_claims = [item.canonical_text for item in c_pet_items if "sou um" in item.canonical_text.lower() or "meu papel" in item.canonical_text.lower()]
        if role_claims:
            new_role = role_claims[0]  # Most important one
            if new_role != self.role:
                self.role = new_role
                updated = True
        
        # Extract capabilities from TOOLS and C-PET
        capability_claims = []
        for item in tool_items + c_pet_items:
            if "posso" in item.canonical_text.lower() and "não posso" not in item.canonical_text.lower():
                # Extract what comes after "posso"
                text = item.canonical_text.lower()
                if "eu posso" in text:
                    cap = text.split("eu posso")[1].strip().rstrip('.')
                    if cap and len(cap) < 80:
                        capability_claims.append(cap)
        
        if capability_claims and capability_claims != self.capabilities:
            self.capabilities = capability_claims[:3]  # Top 3
            updated = True
        
        # Extract limits from C-PET and POLICY
        limit_claims = []
        for item in c_pet_items + policy_items:
            text = item.canonical_text.lower()
            if "não posso" in text or "não tenho" in text or "não faço" in text:
                # Extract the limitation
                for pattern in ["não posso", "não tenho", "não faço"]:
                    if pattern in text:
                        limit = text.split(pattern)[1].strip().rstrip('.')
                        if limit and len(limit) < 80:
                            limit_claims.append(limit)
                            break
        
        if limit_claims and limit_claims != self.limits:
            self.limits = limit_claims[:3]  # Top 3
            updated = True
        
        # Extract style from VOICE items
        if voice_items:
            style_texts = [item.canonical_text for item in voice_items[:2]]
            new_style = " ".join(style_texts)
            if new_style != self.style:
                self.style = new_style
                updated = True
        
        # Extract principles from POLICY
        principle_texts = [item.canonical_text for item in policy_items[:3]]
        if principle_texts and principle_texts != self.principles:
            self.principles = principle_texts
            updated = True
        
        # Extract commitments from C&C-PERSONA
        commitment_texts = [item.canonical_text for item in commitment_items[:3]]
        if commitment_texts and commitment_texts != self.commitments:
            self.commitments = commitment_texts
            updated = True
        
        if updated:
            self.last_updated = datetime.utcnow()
            self.version += 1
            logger.info(f"✨ PET-CANON updated to version {self.version}")
        
        return updated
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for storage."""
        return {
            "role": self.role,
            "capabilities": self.capabilities,
            "limits": self.limits,
            "style": self.style,
            "principles": self.principles,
            "commitments": self.commitments,
            "last_updated": self.last_updated.isoformat(),
            "version": self.version
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'PetCanon':
        """Deserialize from dictionary."""
        return PetCanon(
            role=data.get("role", ""),
            capabilities=data.get("capabilities", []),
            limits=data.get("limits", []),
            style=data.get("style", ""),
            principles=data.get("principles", []),
            commitments=data.get("commitments", []),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.utcnow(),
            version=data.get("version", 1)
        )
    
    def __repr__(self) -> str:
        return f"PetCanon(v{self.version}, {len(self.role)} char role, {len(self.capabilities)} caps, {len(self.limits)} limits)"
