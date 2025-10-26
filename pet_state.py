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

# Configure logging for pet state debugging
logger = logging.getLogger(__name__)

@dataclass
class PetState:
    drives: Dict[str, float] = field(
        default_factory=lambda: {
            "curiosity": random.uniform(0.3, 0.7),
            "affection": random.uniform(0.3, 0.7),
            "order": random.uniform(0.3, 0.7),
            "sociability": random.uniform(0.3, 0.7),
            "autonomy": random.uniform(0.3, 0.7),
            "humor": random.uniform(0.3, 0.7),
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
        """Advance time and decay drives toward equilibrium."""
        decay = minutes / (24 * 60)  # fraction of a day
        
        # Apply personality-modulated decay if personality engine is available
        if self.personality:
            for k, v in self.drives.items():
                decay_rate = self.personality.calculate_drive_decay_rate(k)
                adjusted_decay = decay * decay_rate
                self.drives[k] = max(0.0, min(1.0, v + (0.5 - v) * adjusted_decay))
        else:
            for k, v in self.drives.items():
                self.drives[k] = max(0.0, min(1.0, v + (0.5 - v) * decay))

    def update_from_interaction(self, text: str, response_delay: float) -> None:
        """Update drives, traits, and habits based on user input and response time."""
        logger.info("📝 Processing interaction: '%s' (delay: %.1f min)", text[:50], response_delay)
        logger.info("📊 Drives before update: %s", {k: round(v, 2) for k, v in self.drives.items()})
        
        # Responsiveness influences sociability and affection
        if response_delay < self.habits["average_response_time"] * 0.5:
            self.drives["affection"] = min(1.0, self.drives["affection"] + 0.05)
            self.drives["sociability"] = min(1.0, self.drives["sociability"] + 0.05)
        else:
            self.drives["sociability"] = max(0.0, self.drives["sociability"] - 0.02)

        # Enhanced content analysis for better learning
        lower = text.lower()
        
        # Extract key information about the user
        self._extract_user_info(text)
        
        # Content influences traits
        if any(word in lower for word in ["music", "música", "cantar", "tocar"]):
            self.traits["musical"] = min(1.0, self.traits["musical"] + 0.1)
        if any(word in lower for word in ["jogo", "brincar", "game", "diversão"]):
            self.traits["ludico"] = min(1.0, self.traits["ludico"] + 0.1)
        if any(word in lower for word in ["pergunta", "curiosidade", "saber", "aprender"]):
            self.drives["curiosity"] = min(1.0, self.drives["curiosity"] + 0.05)

        # Update habit: average response time via exponential moving average
        alpha = 0.3
        self.habits["average_response_time"] = (
            alpha * response_delay + (1 - alpha) * self.habits["average_response_time"]
        )

        # Record the interaction in memory
        self.memory.add_episode(text, salience=0.5)
        self.last_user_message = datetime.utcnow()
        
        # Update personality based on interaction if personality engine is available
        if self.personality:
            # Estimate interaction quality based on responsiveness
            quality = 1.0 if response_delay < self.habits["average_response_time"] else 0.5
            interaction_type = "positive" if quality > 0.7 else "neutral"
            self.personality.process_interaction_feedback(interaction_type, quality)
            
        logger.info("📊 Drives after update: %s", {k: round(v, 2) for k, v in self.drives.items()})

    def _extract_user_info(self, text: str) -> None:
        """Extract and store semantic information about the user."""
        import re
        lower = text.lower()
        
        # Extract name
        name_patterns = [
            r"(?:sou|me chamo|meu nome é|eu sou) (\w+)",
            r"oi.*sou (\w+)",
            r"olá.*sou (\w+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, lower)
            if match:
                name = match.group(1).capitalize()
                self.memory.semantic[f"nome: {name}"] = 1.0
                logger.info("🧠 Learned user name: %s", name)
        
        # Extract age
        age_match = re.search(r"tenho (\d+) anos?", lower)
        if age_match:
            age = age_match.group(1)
            self.memory.semantic[f"idade: {age} anos"] = 1.0
            logger.info("🧠 Learned user age: %s", age)
        
        # Extract profession/work
        work_patterns = [
            r"trabalho (?:como|de) ([^,.!?]+)",
            r"sou ([^,.!?]+(?:desenvolvedor|programador|engenheiro|professor|médico|designer))",
            r"profissão.* ([^,.!?]+)"
        ]
        for pattern in work_patterns:
            match = re.search(pattern, lower)
            if match:
                work = match.group(1).strip()
                self.memory.semantic[f"profissão: {work}"] = 1.0
                logger.info("🧠 Learned user profession: %s", work)
        
        # Extract hobbies/interests
        hobby_patterns = [
            r"gosto de ([^,.!?]+)",
            r"adoro ([^,.!?]+)",
            r"hobby[s]? (?:são|é) ([^,.!?]+)",
            r"nas horas livres ([^,.!?]+)"
        ]
        for pattern in hobby_patterns:
            match = re.search(pattern, lower)
            if match:
                hobby = match.group(1).strip()
                self.memory.semantic[f"gosta de: {hobby}"] = 0.8
                logger.info("🧠 Learned user interest: %s", hobby)
        
        # Extract location
        location_patterns = [
            r"moro em ([^,.!?]+)",
            r"(?:sou|vivo) (?:de|em) ([^,.!?]+)",
            r"cidade.* ([^,.!?]+)"
        ]
        for pattern in location_patterns:
            match = re.search(pattern, lower)
            if match:
                location = match.group(1).strip()
                self.memory.semantic[f"mora em: {location}"] = 1.0
                logger.info("🧠 Learned user location: %s", location)

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
        from .personality_engine import create_personality
        
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
            # Create random personality for uniqueness
            self.personality = create_personality(random_variation=True)
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
