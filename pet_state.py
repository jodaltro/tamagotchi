"""
Core logic for the organic virtual pet.

The `PetState` class encapsulates internal drives, personality traits, habits,
and a memory store. Drives motivate behavior (e.g., curiosity, affection),
traits capture personality tendencies (e.g., ludico, musical), habits record
user interaction patterns, and the memory store logs experiences. Methods
include ticking time to decay drives, updating state from user interactions,
generating intentions, and selecting the best action.
"""

import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from .memory_store import MemoryStore
from .personality_engine import PersonalityEngine, PersonalityProfile
from .ai_memory_analyzer import analyze_conversation_importance, analyze_drive_impact

# Configure logging for pet state debugging
logger = logging.getLogger(__name__)

@dataclass
class PetState:
    drives: Dict[str, float] = field(
        default_factory=lambda: {
            # Drives positivos principais
            "curiosidade": random.uniform(0.3, 0.7),    # Desejo de aprender e explorar
            "afeto": random.uniform(0.3, 0.7),          # Necessidade de amor e conexão
            "ordem": random.uniform(0.3, 0.7),          # Necessidade de organização
            "sociabilidade": random.uniform(0.3, 0.7),  # Desejo de interação social
            "autonomia": random.uniform(0.3, 0.7),      # Necessidade de independência
            "humor": random.uniform(0.3, 0.7),          # Alegria e diversão
            
            # Drives motivacionais
            "conquista": random.uniform(0.3, 0.7),      # Desejo de realizar e ter sucesso
            "poder": random.uniform(0.3, 0.7),          # Desejo de influência e controle
            "aceitacao": random.uniform(0.3, 0.7),      # Necessidade de aprovação
            "idealismo": random.uniform(0.3, 0.7),      # Desejo de justiça e correção
            "tranquilidade": random.uniform(0.3, 0.7),  # Necessidade de paz e segurança
            "criatividade": random.uniform(0.3, 0.7),   # Expressão artística e imaginativa
            
            # Drives físicos/neutros
            "fome": random.uniform(0.3, 0.7),           # Necessidades físicas (metafóricas)
            "descanso": random.uniform(0.3, 0.7),       # Necessidade de relaxamento
            
            # Drives negativos (valores baixos = bom estado)
            "ansiedade": random.uniform(0.1, 0.3),      # Preocupação e apreensão
            "frustracao": random.uniform(0.1, 0.3),     # Irritação com obstáculos
            "solidao": random.uniform(0.1, 0.3),        # Sentimento de isolamento
            "tedio": random.uniform(0.1, 0.3),          # Falta de estímulo
        }
    )
    traits: Dict[str, float] = field(
        default_factory=lambda: {
            "ludico": 0.5,
            "curioso": 0.5,
            "afetuoso": 0.5,
            "musical": 0.5,
        }
    )
    habits: Dict[str, float] = field(
        default_factory=lambda: {
            "active_start": 19.0,
            "active_end": 23.0,
            "average_response_time": 10.0,
        }
    )
    stage: str = "infante"
    last_user_message: datetime = field(default_factory=datetime.utcnow)
    memory: MemoryStore = field(default_factory=MemoryStore)
    personality: Optional[PersonalityEngine] = None
    # Store personality profile data for serialization
    personality_data: Dict[str, float] = field(default_factory=dict)

    def tick(self, minutes: float = 30.0) -> None:
        """Advance time and decay drives toward equilibrium.
        
        Positive drives decay toward 0.5 (equilibrium) SLOWLY.
        Negative drives (anxiety, frustration, loneliness, boredom) increase over time
        without interaction, representing natural accumulation of negative states.
        """
        # Much slower decay rate to maintain personality longer
        decay = minutes / (48 * 60)  # fraction of 2 days (slower decay)
        
        # Negative drives that increase without interaction
        negative_drives = {"anxiety", "frustration", "loneliness", "boredom"}
        
        # Apply personality-modulated decay if personality engine is available
        if self.personality:
            for k, v in self.drives.items():
                decay_rate = self.personality.calculate_drive_decay_rate(k)
                # Reduce decay rate further to maintain drives longer
                adjusted_decay = decay * decay_rate * 0.3  # Even slower
                
                if k in negative_drives:
                    # Negative drives increase over time (move toward 0.6, not 1.0 to avoid extremes)
                    target = 0.6
                    self.drives[k] = max(0.0, min(1.0, v + (target - v) * adjusted_decay * 0.5))
                else:
                    # Positive drives decay toward equilibrium VERY slowly
                    self.drives[k] = max(0.0, min(1.0, v + (0.5 - v) * adjusted_decay * 0.2))
        else:
            for k, v in self.drives.items():
                if k in negative_drives:
                    # Negative drives increase over time
                    target = 0.6
                    self.drives[k] = max(0.0, min(1.0, v + (target - v) * decay * 0.3))
                else:
                    # Positive drives decay toward equilibrium VERY slowly
                    self.drives[k] = max(0.0, min(1.0, v + (0.5 - v) * decay * 0.1))

    def update_from_interaction(self, text: str, response_delay: float) -> None:
        """Update drives, traits, and habits based on user input and response time using AI analysis."""
        logger.info("📝 Processing interaction: '%s' (delay: %.1f min)", text[:50], response_delay)
        logger.info("📊 Drives before update: %s", {k: round(v, 2) for k, v in self.drives.items()})
        
        # Basic interaction effects (reduce negative drives)
        self.drives["solidao"] = max(0.0, self.drives["solidao"] - 0.15)
        self.drives["tedio"] = max(0.0, self.drives["tedio"] - 0.1)
        
        # Response timing affects social drives
        if response_delay < self.habits["average_response_time"] * 0.5:
            self.drives["afeto"] = min(1.0, self.drives["afeto"] + 0.05)
            self.drives["sociabilidade"] = min(1.0, self.drives["sociabilidade"] + 0.05)
            self.drives["aceitacao"] = min(1.0, self.drives["aceitacao"] + 0.03)
            self.drives["ansiedade"] = max(0.0, self.drives["ansiedade"] - 0.05)
        else:
            self.drives["sociabilidade"] = max(0.0, self.drives["sociabilidade"] - 0.02)
            self.drives["ansiedade"] = min(1.0, self.drives["ansiedade"] + 0.02)

        # AI-driven drive analysis for intelligent emotional responses
        try:
            drive_changes = analyze_drive_impact(text, self.drives)
            if drive_changes:
                logger.info(f"🤖 AI Drive Analysis: {drive_changes}")
                for drive_name, change in drive_changes.items():
                    if drive_name in self.drives:
                        old_value = self.drives[drive_name]
                        self.drives[drive_name] = max(0.0, min(1.0, self.drives[drive_name] + change))
                        if abs(change) > 0.05:  # Only log significant changes
                            logger.info(f"Drive '{drive_name}': {old_value:.2f} -> {self.drives[drive_name]:.2f} (change: {change:+.2f})")
            else:
                logger.info("🔄 Using fallback content analysis")
                self._apply_fallback_content_analysis(text)
                
        except Exception as e:
            logger.error(f"❌ Error in AI drive analysis, using fallback: {e}")
            self._apply_fallback_content_analysis(text)

        # Extract user information using AI
        self._extract_user_info(text)
        
        # Update habit: average response time via exponential moving average
        alpha = 0.3
        self.habits["average_response_time"] = (
            alpha * response_delay + (1 - alpha) * self.habits["average_response_time"]
        )

        # Record the interaction in memory
        self.memory.add_episode(text, salience=0.5)
        self.last_user_message = datetime.utcnow()
        
        # Apply memory decay periodically
        hours_since_last_decay = (datetime.utcnow() - self.memory.last_decay_time).total_seconds() / 3600.0
        if hours_since_last_decay >= 24.0:
            self.memory.apply_memory_decay(hours_since_last_decay)
        
        # Update personality based on interaction if personality engine is available
        if self.personality:
            quality = 1.0 if response_delay < self.habits["average_response_time"] else 0.5
            interaction_type = "positive" if quality > 0.7 else "neutral"
            self.personality.process_interaction_feedback(interaction_type, quality)
            
        logger.info("📊 Drives after update: %s", {k: round(v, 2) for k, v in self.drives.items()})

    def _apply_fallback_content_analysis(self, text: str):
        """Fallback content analysis when AI is unavailable"""
        lower = text.lower()
        
        # Positive interactions
        if any(word in lower for word in ['obrigado', 'thanks', 'legal', 'incrível', 'show', 'massa']):
            self.drives['afeto'] = min(1.0, self.drives['afeto'] + 0.1)
            self.drives['aceitacao'] = min(1.0, self.drives['aceitacao'] + 0.1)
        
        # Humor and playfulness
        if any(word in lower for word in ['kkk', 'haha', 'piada', 'joke', 'kkkk', 'diversão']):
            self.drives['humor'] = min(1.0, self.drives['humor'] + 0.15)
            self.drives['ansiedade'] = max(0.0, self.drives['ansiedade'] - 0.1)
        
        # Learning and curiosity
        if any(word in lower for word in ['como', 'por que', 'o que', 'onde', 'quando', 'aprender', '?']):
            self.drives['curiosidade'] = min(1.0, self.drives['curiosidade'] + 0.1)
            self.drives['tedio'] = max(0.0, self.drives['tedio'] - 0.1)
        
        # Social interaction
        if any(word in lower for word in ['conversa', 'chat', 'amigo', 'junto', 'companhia']):
            self.drives['sociabilidade'] = min(1.0, self.drives['sociabilidade'] + 0.1)
            self.drives['solidao'] = max(0.0, self.drives['solidao'] - 0.15)
        
        # Achievements
        if any(word in lower for word in ['consegui', 'venci', 'sucesso', 'conquista']):
            self.drives['conquista'] = min(1.0, self.drives['conquista'] + 0.1)
            self.drives['frustracao'] = max(0.0, self.drives['frustracao'] - 0.1)
        
        # Problems/frustration
        if any(word in lower for word in ['problema', 'difícil', 'não consigo', 'frustrado']):
            self.drives['frustracao'] = min(1.0, self.drives['frustracao'] + 0.08)
            self.drives['tranquilidade'] = max(0.0, self.drives['tranquilidade'] - 0.05)
        
        # Creativity
        if any(word in lower for word in ['criar', 'arte', 'desenho', 'ideia', 'música']):
            self.drives['criatividade'] = min(1.0, self.drives['criatividade'] + 0.08)

    def _extract_user_info(self, text: str) -> None:
        """Extract and store semantic information about the user using AI-powered analysis."""
        current_time = datetime.utcnow()
        
        # Get existing facts for context
        existing_facts = self.memory.get_semantic_facts(min_weight=0.3)
        
        # Use AI to analyze conversation and extract facts
        # The AI returns an overall importance score for the message and a list of extracted facts
        importance_score, extracted_facts = analyze_conversation_importance(text, existing_facts)
        
        logger.info(f"🤖 AI extracted {len(extracted_facts)} facts with importance {importance_score:.2f}")
        
        # Add extracted facts to semantic memory
        for fact in extracted_facts:
            fact_key = fact.lower().strip()
            # Check if this reinforces existing memory
            if not self.memory.reinforce_memory(fact_key, boost=0.3):
                # New fact - use AI-determined importance score for the message
                # Note: All facts from the same message share the same importance score.
                # This is intentional as the AI evaluates the overall message importance.
                self.memory.semantic[fact_key] = (importance_score, current_time, 1)
                logger.info(f"🧠 Learned new fact: {fact}")

    def generate_intentions(self) -> List[Tuple[str, float]]:
        """Generate candidate actions with utilities based on drives and traits."""
        actions = [
            "contextual_response",  # Just respond naturally to what the user said
        ]
        intentions = []
        
        # Simplified: just return one main action that relies on AI intelligence
        util = 1.0  # Always high utility for contextual response
        intentions.append(("contextual_response", util))
        
        return intentions

    def select_action(self) -> str:
        """Select the highest-utility action."""
        intentions = self.generate_intentions()
        
        # Debug logging
        logger.info("🎯 Action selection - Current drives: %s", 
                   {k: round(v, 2) for k, v in self.drives.items()})
        logger.info("🎯 Action utilities: %s", 
                   [(action, round(util, 3)) for action, util in intentions[:3]])
        
        selected_action = intentions[0][0] if intentions else "idle"
        logger.info("🎯 Selected action: %s", selected_action)
        
        return selected_action
    
    def initialize_personality(
        self, 
        archetype: Optional[str] = None,
        profile_data: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Initialize the personality engine for this pet.
        
        Args:
            archetype: Optional personality archetype name
            profile_data: Optional dictionary of personality dimension values
        """
        from .personality_engine import create_personality, PersonalityProfile
        
        if profile_data:
            # Restore personality from saved data
            profile = PersonalityProfile(**profile_data)
            self.personality = PersonalityEngine(profile)
            self.personality_data = profile_data
        elif archetype:
            # Create personality from archetype
            self.personality = create_personality(archetype=archetype)
            self.personality_data = self.personality.profile.to_dict()
        else:
            # Create random personality with higher variation for uniqueness
            profile = PersonalityProfile.random_profile(variation=0.8)
            self.personality = PersonalityEngine(profile)
            self.personality_data = self.personality.profile.to_dict()
    
    def get_personality_description(self) -> str:
        """Get a natural language description of the pet's personality."""
        if self.personality:
            return self.personality.generate_personality_prompt()
        return ""
    
    def save_personality_state(self) -> Dict[str, float]:
        """Save personality state for persistence."""
        if self.personality:
            self.personality_data = self.personality.profile.to_dict()
        return self.personality_data
