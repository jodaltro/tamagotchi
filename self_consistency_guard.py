"""
Self-Consistency Guard (SCG) module for contradiction detection.

The SCG checks draft responses against the pet's autobiographical memory
to prevent contradictions, tone inconsistencies, and broken promises.
It runs before sending responses and can suggest corrections.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

from .autobiographical_memory import AutobiographicalMemory, ABMType, ABMItem
from .pet_canon import PetCanon

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyIssue:
    """An inconsistency detected in a draft response."""
    
    issue_type: str  # "contradiction", "tone_shift", "broken_promise"
    severity: float  # 0-1, how serious it is
    description: str  # What's wrong
    conflicting_abm_item: Optional[ABMItem] = None  # Which ABM item conflicts
    suggested_correction: Optional[str] = None  # How to fix it
    
    def __repr__(self) -> str:
        return f"ConsistencyIssue({self.issue_type}, severity={self.severity:.2f}, '{self.description[:50]}...')"


class SelfConsistencyGuard:
    """
    Checks draft responses for consistency with the pet's autobiographical memory.
    
    Prevents:
    - Contradictions with established claims
    - Tone shifts from established voice
    - Breaking commitments/promises
    - Violating policies
    """
    
    def __init__(self):
        self.check_count = 0
        self.issue_count = 0
    
    def check_response(
        self,
        draft_response: str,
        abm: AutobiographicalMemory,
        canon: Optional[PetCanon] = None
    ) -> Tuple[bool, List[ConsistencyIssue]]:
        """
        Check a draft response for consistency issues.
        
        Args:
            draft_response: The response to check
            abm: Current autobiographical memory
            canon: Optional pet canon for quick checks
        
        Returns:
            Tuple of (is_consistent, list of issues)
        """
        self.check_count += 1
        issues: List[ConsistencyIssue] = []
        
        draft_lower = draft_response.lower()
        
        # Get active ABM items for checking
        c_pet_items = abm.get_active_items(ABMType.C_PET, min_importance=0.4)
        policy_items = abm.get_active_items(ABMType.POLICY, min_importance=0.4)
        tool_items = abm.get_active_items(ABMType.TOOLS, min_importance=0.4)
        commitment_items = abm.get_active_items(ABMType.C_AND_C_PERSONA, min_importance=0.4)
        
        # 1. Check for contradictions with capabilities/limits
        issues.extend(self._check_capability_contradictions(
            draft_lower, c_pet_items + tool_items
        ))
        
        # 2. Check for policy violations
        issues.extend(self._check_policy_violations(
            draft_lower, policy_items
        ))
        
        # 3. Check for broken commitments
        issues.extend(self._check_commitment_violations(
            draft_lower, commitment_items
        ))
        
        # 4. Check for tone consistency (if canon available)
        if canon and canon.style:
            issues.extend(self._check_tone_consistency(
                draft_response, canon.style
            ))
        
        # Count issues
        if issues:
            self.issue_count += len(issues)
            logger.warning(f"⚠️ Found {len(issues)} consistency issues in draft response")
            for issue in issues:
                logger.warning(f"  - {issue.issue_type}: {issue.description}")
        else:
            logger.info("✅ Draft response passed consistency check")
        
        is_consistent = len(issues) == 0
        return is_consistent, issues
    
    def _check_capability_contradictions(
        self,
        draft_lower: str,
        capability_items: List[ABMItem]
    ) -> List[ConsistencyIssue]:
        """Check if draft contradicts established capabilities/limits."""
        issues = []
        
        for item in capability_items:
            item_lower = item.canonical_text.lower()
            
            # Check for "can" claims
            if "posso" in item_lower and "não posso" not in item_lower:
                # Pet claims it CAN do something
                # Check if draft says it CAN'T
                capability = self._extract_after_pattern(item_lower, "posso")
                if capability and f"não posso {capability}" in draft_lower:
                    issues.append(ConsistencyIssue(
                        issue_type="contradiction",
                        severity=0.9,
                        description=f"Response says 'não posso {capability}' but ABM says 'posso {capability}'",
                        conflicting_abm_item=item,
                        suggested_correction=f"Lembre que você PODE {capability}. Corrija a resposta."
                    ))
            
            # Check for "can't" claims
            if "não posso" in item_lower:
                # Pet claims it CAN'T do something
                # Check if draft says it CAN
                limitation = self._extract_after_pattern(item_lower, "não posso")
                if limitation and f"posso {limitation}" in draft_lower and f"não posso {limitation}" not in draft_lower:
                    issues.append(ConsistencyIssue(
                        issue_type="contradiction",
                        severity=0.95,
                        description=f"Response says 'posso {limitation}' but ABM says 'não posso {limitation}'",
                        conflicting_abm_item=item,
                        suggested_correction=f"Lembre que você NÃO PODE {limitation}. Corrija a resposta."
                    ))
            
            # Check for "don't have access" claims
            if "não tenho acesso" in item_lower:
                resource = self._extract_after_pattern(item_lower, "não tenho acesso")
                if resource and (f"tenho acesso {resource}" in draft_lower or f"vejo {resource}" in draft_lower):
                    issues.append(ConsistencyIssue(
                        issue_type="contradiction",
                        severity=0.9,
                        description=f"Response implies access to {resource}, but ABM says 'não tenho acesso'",
                        conflicting_abm_item=item,
                        suggested_correction=f"Lembre que você não tem acesso a {resource}."
                    ))
        
        return issues
    
    def _check_policy_violations(
        self,
        draft_lower: str,
        policy_items: List[ABMItem]
    ) -> List[ConsistencyIssue]:
        """Check if draft violates established policies."""
        issues = []
        
        for item in policy_items:
            item_lower = item.canonical_text.lower()
            
            # Check for "don't give advice" type policies
            if "não dou conselho" in item_lower:
                advice_indicators = ["você deve", "recomendo que", "sugiro que", "é melhor você"]
                if any(indicator in draft_lower for indicator in advice_indicators):
                    issues.append(ConsistencyIssue(
                        issue_type="broken_policy",
                        severity=0.8,
                        description="Response appears to give advice, violating 'não dou conselho' policy",
                        conflicting_abm_item=item,
                        suggested_correction="Reformule para evitar dar conselhos diretos."
                    ))
            
            # Check for "don't do X" policies
            if "não faço" in item_lower:
                action = self._extract_after_pattern(item_lower, "não faço")
                if action and (f"vou {action}" in draft_lower or f"faço {action}" in draft_lower):
                    issues.append(ConsistencyIssue(
                        issue_type="broken_policy",
                        severity=0.85,
                        description=f"Response says will do '{action}', but policy says 'não faço {action}'",
                        conflicting_abm_item=item,
                        suggested_correction=f"Lembre que você não faz {action}."
                    ))
        
        return issues
    
    def _check_commitment_violations(
        self,
        draft_lower: str,
        commitment_items: List[ABMItem]
    ) -> List[ConsistencyIssue]:
        """Check if draft violates interaction commitments."""
        issues = []
        
        for item in commitment_items:
            item_lower = item.canonical_text.lower()
            
            # Check for "always confirm" type commitments
            if "sempre confirmo" in item_lower:
                action = self._extract_after_pattern(item_lower, "sempre confirmo")
                # This is harder to detect programmatically, log for manual review
                logger.debug(f"💭 Check if draft confirms: {action}")
            
            # Check for "never" commitments
            if "nunca vou" in item_lower or "nunca faço" in item_lower:
                pattern = "nunca vou" if "nunca vou" in item_lower else "nunca faço"
                action = self._extract_after_pattern(item_lower, pattern)
                if action and (f"vou {action}" in draft_lower or f"faço {action}" in draft_lower):
                    issues.append(ConsistencyIssue(
                        issue_type="broken_promise",
                        severity=0.9,
                        description=f"Response violates commitment '{pattern} {action}'",
                        conflicting_abm_item=item,
                        suggested_correction=f"Lembre do compromisso: {pattern} {action}."
                    ))
        
        return issues
    
    def _check_tone_consistency(
        self,
        draft: str,
        canonical_style: str
    ) -> List[ConsistencyIssue]:
        """Check if draft tone matches canonical style (simple heuristics)."""
        issues = []
        
        canonical_lower = canonical_style.lower()
        draft_lower = draft.lower()
        
        # Check formality shift
        if "formal" in canonical_lower:
            informal_markers = ["né", "tá", "pô", "cara", "mano"]
            if any(marker in draft_lower for marker in informal_markers):
                issues.append(ConsistencyIssue(
                    issue_type="tone_shift",
                    severity=0.5,
                    description="Draft uses informal language, but style indicates formal tone",
                    suggested_correction="Use linguagem mais formal."
                ))
        
        if "informal" in canonical_lower or "casual" in canonical_lower:
            # Overly formal markers
            formal_markers = ["portanto", "ademais", "outrossim", "destarte"]
            if any(marker in draft_lower for marker in formal_markers):
                issues.append(ConsistencyIssue(
                    issue_type="tone_shift",
                    severity=0.5,
                    description="Draft uses overly formal language, but style is casual",
                    suggested_correction="Use linguagem mais casual e natural."
                ))
        
        # Check brevity vs verbosity
        if "conciso" in canonical_lower or "curto" in canonical_lower:
            if len(draft) > 500:  # Somewhat arbitrary
                issues.append(ConsistencyIssue(
                    issue_type="tone_shift",
                    severity=0.4,
                    description="Draft is long, but style indicates concise responses",
                    suggested_correction="Encurte a resposta para ser mais conciso."
                ))
        
        return issues
    
    def _extract_after_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Extract text that comes after a pattern."""
        if pattern not in text:
            return None
        
        parts = text.split(pattern, 1)
        if len(parts) < 2:
            return None
        
        after = parts[1].strip().rstrip('.').strip()
        # Get first few words
        words = after.split()[:5]
        return " ".join(words) if words else None
    
    def correct_response(
        self,
        draft_response: str,
        issues: List[ConsistencyIssue]
    ) -> str:
        """
        Attempt automatic correction of draft response.
        
        For high-severity issues, prepends a correction statement.
        
        Args:
            draft_response: Original draft
            issues: List of detected issues
        
        Returns:
            Corrected response (may be unchanged if no auto-correction possible)
        """
        if not issues:
            return draft_response
        
        # Get highest severity issue
        issues.sort(key=lambda x: x.severity, reverse=True)
        top_issue = issues[0]
        
        # For high-severity contradictions, prepend correction
        if top_issue.severity >= 0.8 and top_issue.issue_type in ["contradiction", "broken_policy"]:
            correction_prefix = self._generate_correction_prefix(top_issue)
            if correction_prefix:
                corrected = f"{correction_prefix} {draft_response}"
                logger.info(f"🔧 Auto-corrected response with prefix: {correction_prefix[:50]}...")
                return corrected
        
        # Otherwise return original with warning
        logger.warning(f"⚠️ Could not auto-correct issue: {top_issue.description}")
        return draft_response
    
    def _generate_correction_prefix(self, issue: ConsistencyIssue) -> Optional[str]:
        """Generate a brief correction statement to prepend to response."""
        if not issue.conflicting_abm_item:
            return None
        
        abm_text = issue.conflicting_abm_item.canonical_text
        
        # Generate appropriate correction
        if "não posso" in abm_text.lower():
            return "Corrigindo: na verdade, " + abm_text.split('.')[0] + "."
        elif "não tenho acesso" in abm_text.lower():
            return "Importante lembrar: " + abm_text.split('.')[0] + "."
        elif "não faço" in abm_text.lower() or "não dou" in abm_text.lower():
            return "Só para esclarecer: " + abm_text.split('.')[0] + "."
        
        return None
    
    def get_stats(self) -> dict:
        """Get statistics about consistency checking."""
        return {
            "total_checks": self.check_count,
            "total_issues": self.issue_count,
            "issue_rate": self.issue_count / max(1, self.check_count)
        }
    
    def __repr__(self) -> str:
        return f"SelfConsistencyGuard(checks={self.check_count}, issues={self.issue_count})"
