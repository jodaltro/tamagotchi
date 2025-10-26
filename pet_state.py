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
from .ai_memory_analyzer import analyze_conversation_importance

# Configure logging for pet state debugging
logger = logging.getLogger(__name__)

@dataclass
class PetState:
    drives: Dict[str, float] = field(
        default_factory=lambda: {
            # Original 6 drives (positive)
            "curiosity": random.uniform(0.3, 0.7),      # Desire to learn and explore
            "affection": random.uniform(0.3, 0.7),      # Need for love and connection
            "order": random.uniform(0.3, 0.7),          # Need for organization and structure
            "sociability": random.uniform(0.3, 0.7),    # Desire for social interaction
            "autonomy": random.uniform(0.3, 0.7),       # Need for independence
            "humor": random.uniform(0.3, 0.7),          # Playfulness and fun
            
            # New positive drives (based on Reiss's 16 Basic Desires & Panksepp's systems)
            "achievement": random.uniform(0.3, 0.7),    # Drive to accomplish and succeed
            "power": random.uniform(0.3, 0.7),          # Desire for influence and control
            "acceptance": random.uniform(0.3, 0.7),     # Need for approval and belonging
            "idealism": random.uniform(0.3, 0.7),       # Desire for justice and fairness
            "tranquility": random.uniform(0.3, 0.7),    # Need for peace and safety
            "creativity": random.uniform(0.3, 0.7),     # Artistic and imaginative expression
            
            # Balanced/neutral drives
            "hunger": random.uniform(0.3, 0.7),         # Physical needs (metaphorical)
            "rest": random.uniform(0.3, 0.7),           # Need for downtime and recovery
            
            # Negative drives (with safeguards - lower initial values)
            "anxiety": random.uniform(0.1, 0.3),        # Worry and apprehension (low = good)
            "frustration": random.uniform(0.1, 0.3),    # Obstacles and setbacks (low = good)
            "loneliness": random.uniform(0.1, 0.3),     # Feeling isolated (low = good)
            "boredom": random.uniform(0.1, 0.3),        # Lack of stimulation (low = good)
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
        
        Positive drives decay toward 0.5 (equilibrium).
        Negative drives (anxiety, frustration, loneliness, boredom) increase over time
        without interaction, representing natural accumulation of negative states.
        """
        decay = minutes / (24 * 60)  # fraction of a day
        
        # Negative drives that increase without interaction
        negative_drives = {"anxiety", "frustration", "loneliness", "boredom"}
        
        # Apply personality-modulated decay if personality engine is available
        if self.personality:
            for k, v in self.drives.items():
                decay_rate = self.personality.calculate_drive_decay_rate(k)
                adjusted_decay = decay * decay_rate
                
                if k in negative_drives:
                    # Negative drives increase over time (move toward 0.6, not 1.0 to avoid extremes)
                    target = 0.6
                    self.drives[k] = max(0.0, min(1.0, v + (target - v) * adjusted_decay * 0.5))
                else:
                    # Positive drives decay toward equilibrium (0.5)
                    self.drives[k] = max(0.0, min(1.0, v + (0.5 - v) * adjusted_decay))
        else:
            for k, v in self.drives.items():
                if k in negative_drives:
                    # Negative drives increase over time
                    target = 0.6
                    self.drives[k] = max(0.0, min(1.0, v + (target - v) * decay * 0.5))
                else:
                    # Positive drives decay toward equilibrium
                    self.drives[k] = max(0.0, min(1.0, v + (0.5 - v) * decay))

    def update_from_interaction(self, text: str, response_delay: float) -> None:
        """Update drives, traits, and habits based on user input and response time."""
        logger.info("📝 Processing interaction: '%s' (delay: %.1f min)", text[:50], response_delay)
        logger.info("📊 Drives before update: %s", {k: round(v, 2) for k, v in self.drives.items()})
        
        # Interaction reduces negative drives (loneliness, boredom significantly)
        self.drives["loneliness"] = max(0.0, self.drives["loneliness"] - 0.15)
        self.drives["boredom"] = max(0.0, self.drives["boredom"] - 0.1)
        
        # Responsiveness influences sociability, affection, and anxiety
        if response_delay < self.habits["average_response_time"] * 0.5:
            self.drives["affection"] = min(1.0, self.drives["affection"] + 0.05)
            self.drives["sociability"] = min(1.0, self.drives["sociability"] + 0.05)
            self.drives["acceptance"] = min(1.0, self.drives["acceptance"] + 0.03)
            self.drives["anxiety"] = max(0.0, self.drives["anxiety"] - 0.05)
        else:
            self.drives["sociability"] = max(0.0, self.drives["sociability"] - 0.02)
            self.drives["anxiety"] = min(1.0, self.drives["anxiety"] + 0.02)

        # Enhanced content analysis for better learning
        lower = text.lower()
        
        # Extract key information about the user
        self._extract_user_info(text)
        
        # Content influences drives and traits
        if any(word in lower for word in ["music", "música", "cantar", "tocar"]):
            self.traits["musical"] = min(1.0, self.traits["musical"] + 0.1)
            self.drives["creativity"] = min(1.0, self.drives["creativity"] + 0.05)
            
        if any(word in lower for word in ["jogo", "brincar", "game", "diversão"]):
            self.traits["ludico"] = min(1.0, self.traits["ludico"] + 0.1)
            self.drives["humor"] = min(1.0, self.drives["humor"] + 0.05)
            
        if any(word in lower for word in ["pergunta", "curiosidade", "saber", "aprender", "?"]):
            self.drives["curiosity"] = min(1.0, self.drives["curiosity"] + 0.05)
            self.traits["curioso"] = min(1.0, self.traits["curioso"] + 0.05)
            
        # New drive interactions
        if any(word in lower for word in ["obrigado", "obrigada", "agradeço", "valeu"]):
            self.drives["affection"] = min(1.0, self.drives["affection"] + 0.08)
            self.drives["acceptance"] = min(1.0, self.drives["acceptance"] + 0.05)
            
        if any(word in lower for word in ["conquista", "consegui", "venci", "sucesso"]):
            self.drives["achievement"] = min(1.0, self.drives["achievement"] + 0.1)
            self.drives["frustration"] = max(0.0, self.drives["frustration"] - 0.1)
            
        if any(word in lower for word in ["difícil", "problema", "não consigo", "frustrado"]):
            self.drives["frustration"] = min(1.0, self.drives["frustration"] + 0.08)
            self.drives["tranquility"] = max(0.0, self.drives["tranquility"] - 0.05)
            
        if any(word in lower for word in ["calma", "paz", "tranquilo", "relaxar"]):
            self.drives["tranquility"] = min(1.0, self.drives["tranquility"] + 0.1)
            self.drives["anxiety"] = max(0.0, self.drives["anxiety"] - 0.08)
            
        if any(word in lower for word in ["criar", "arte", "desenho", "ideia"]):
            self.drives["creativity"] = min(1.0, self.drives["creativity"] + 0.08)
            
        if any(word in lower for word in ["sozinho", "só", "isolado"]):
            self.drives["loneliness"] = min(1.0, self.drives["loneliness"] + 0.1)
            
        if any(word in lower for word in ["junto", "amigos", "companhia"]):
            self.drives["loneliness"] = max(0.0, self.drives["loneliness"] - 0.12)
            self.drives["sociability"] = min(1.0, self.drives["sociability"] + 0.08)

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
            # Estimate interaction quality based on responsiveness
            quality = 1.0 if response_delay < self.habits["average_response_time"] else 0.5
            interaction_type = "positive" if quality > 0.7 else "neutral"
            self.personality.process_interaction_feedback(interaction_type, quality)
            
        logger.info("📊 Drives after update: %s", {k: round(v, 2) for k, v in self.drives.items()})

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
