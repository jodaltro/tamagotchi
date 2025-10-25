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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from .memory_store import MemoryStore
from .personality_engine import PersonalityEngine, PersonalityProfile

@dataclass
class PetState:
    drives: Dict[str, float] = field(
        default_factory=lambda: {
            "curiosity": 0.5,
            "affection": 0.5,
            "order": 0.5,
            "sociability": 0.5,
            "autonomy": 0.5,
            "humor": 0.5,
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
        # Responsiveness influences sociability and affection
        if response_delay < self.habits["average_response_time"] * 0.5:
            self.drives["affection"] = min(1.0, self.drives["affection"] + 0.05)
            self.drives["sociability"] = min(1.0, self.drives["sociability"] + 0.05)
        else:
            self.drives["sociability"] = max(0.0, self.drives["sociability"] - 0.02)

        # Content influences traits
        lower = text.lower()
        if any(word in lower for word in ["music", "música"]):
            self.traits["musical"] = min(1.0, self.traits["musical"] + 0.1)
        if any(word in lower for word in ["jogo", "brincar", "game"]):
            self.traits["ludico"] = min(1.0, self.traits["ludico"] + 0.1)

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

    def generate_intentions(self) -> List[Tuple[str, float]]:
        """Generate candidate actions with utilities based on drives and traits."""
        actions = [
            "ask_question",
            "share_fact",
            "tell_joke",
            "request_game",
            "express_affection",
        ]
        intentions = []
        now = datetime.utcnow()
        hour = now.hour
        active_factor = 1.0 if self.habits["active_start"] <= hour <= self.habits["active_end"] else 0.5
        noise = lambda: random.uniform(-0.05, 0.05)
        for action in actions:
            if action == "ask_question":
                util = self.drives["curiosity"] * 0.5 + self.drives["sociability"] * 0.3
            elif action == "share_fact":
                util = self.traits["curioso"] * 0.5 + self.drives["autonomy"] * 0.2
            elif action == "tell_joke":
                util = self.drives["humor"] * 0.6 + self.traits["ludico"] * 0.3
            elif action == "request_game":
                util = self.traits["ludico"] * 0.6 + self.drives["curiosity"] * 0.2
            elif action == "express_affection":
                util = self.drives["affection"] * 0.7 + self.traits["afetuoso"] * 0.3
            else:
                util = 0.1
            util = util * active_factor + noise()
            intentions.append((action, util))
        
        # Apply personality modulation if available
        if self.personality:
            intentions = self.personality.modulate_action_utilities(intentions)
        else:
            intentions.sort(key=lambda x: x[1], reverse=True)
        
        return intentions

    def select_action(self) -> str:
        """Select the highest-utility action."""
        intentions = self.generate_intentions()
        return intentions[0][0] if intentions else "idle"
    
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
