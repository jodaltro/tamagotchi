"""
Personality engine for the organic virtual pet.

This module implements a research-based personality system combining:
1. Big Five (OCEAN) personality model - the most validated framework in psychology
2. Temperament dimensions - emotional reactivity and regulation
3. Personality archetypes - predefined personality templates for variety
4. Dynamic personality evolution - subtle changes based on experiences

The personality engine modulates behavior selection, response generation,
and emotional expression to create unique and coherent virtual pets.

References:
- McCrae & Costa (2008). The Five-Factor Theory of Personality
- Rothbart & Bates (2006). Temperament in Children's Development
- Bates (1989). Temperament as an Emotional Construct
- Picard (1997). Affective Computing
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum


class PersonalityArchetype(Enum):
    """Predefined personality templates based on common character types."""
    CURIOUS_EXPLORER = "curious_explorer"
    PLAYFUL_COMPANION = "playful_companion"
    GENTLE_CAREGIVER = "gentle_caregiver"
    WISE_OBSERVER = "wise_observer"
    ENERGETIC_ENTHUSIAST = "energetic_enthusiast"
    CALM_PHILOSOPHER = "calm_philosopher"
    ARTISTIC_DREAMER = "artistic_dreamer"
    BALANCED_FRIEND = "balanced_friend"


@dataclass
class PersonalityProfile:
    """
    Personality profile based on the Big Five (OCEAN) model combined with
    temperament dimensions.
    
    Big Five Dimensions (range 0.0-1.0):
    - Openness: Curiosity, creativity, preference for novelty vs routine
    - Conscientiousness: Organization, responsibility, goal-directed behavior
    - Extraversion: Sociability, assertiveness, energy level
    - Agreeableness: Compassion, cooperation, trust
    - Neuroticism: Emotional stability, anxiety, stress reactivity (inverted)
    
    Temperament Dimensions (range 0.0-1.0):
    - Emotionality: Intensity of emotional responses
    - Activity: Energy level and preference for action
    - Sociability: Desire for social interaction
    - Adaptability: Ease of adjusting to changes
    
    All dimensions range from 0.0 (low) to 1.0 (high).
    """
    
    # Big Five (OCEAN) dimensions
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5  # High = more neurotic/anxious
    
    # Temperament dimensions
    emotionality: float = 0.5
    activity: float = 0.5
    sociability: float = 0.5
    adaptability: float = 0.5
    
    # Personality archetype (optional, for easier configuration)
    archetype: Optional[PersonalityArchetype] = None
    
    def __post_init__(self):
        """Ensure all dimensions are within valid range."""
        for attr in ['openness', 'conscientiousness', 'extraversion', 
                     'agreeableness', 'neuroticism', 'emotionality', 
                     'activity', 'sociability', 'adaptability']:
            value = getattr(self, attr)
            setattr(self, attr, max(0.0, min(1.0, value)))
    
    @classmethod
    def from_archetype(cls, archetype: PersonalityArchetype) -> 'PersonalityProfile':
        """Create a personality profile from a predefined archetype."""
        profiles = {
            PersonalityArchetype.CURIOUS_EXPLORER: cls(
                openness=0.9, conscientiousness=0.4, extraversion=0.6,
                agreeableness=0.6, neuroticism=0.3,
                emotionality=0.6, activity=0.7, sociability=0.6, adaptability=0.7,
                archetype=PersonalityArchetype.CURIOUS_EXPLORER
            ),
            PersonalityArchetype.PLAYFUL_COMPANION: cls(
                openness=0.7, conscientiousness=0.3, extraversion=0.8,
                agreeableness=0.8, neuroticism=0.2,
                emotionality=0.8, activity=0.9, sociability=0.9, adaptability=0.7,
                archetype=PersonalityArchetype.PLAYFUL_COMPANION
            ),
            PersonalityArchetype.GENTLE_CAREGIVER: cls(
                openness=0.5, conscientiousness=0.7, extraversion=0.5,
                agreeableness=0.9, neuroticism=0.3,
                emotionality=0.7, activity=0.4, sociability=0.7, adaptability=0.6,
                archetype=PersonalityArchetype.GENTLE_CAREGIVER
            ),
            PersonalityArchetype.WISE_OBSERVER: cls(
                openness=0.8, conscientiousness=0.6, extraversion=0.3,
                agreeableness=0.7, neuroticism=0.2,
                emotionality=0.4, activity=0.3, sociability=0.4, adaptability=0.5,
                archetype=PersonalityArchetype.WISE_OBSERVER
            ),
            PersonalityArchetype.ENERGETIC_ENTHUSIAST: cls(
                openness=0.7, conscientiousness=0.5, extraversion=0.9,
                agreeableness=0.7, neuroticism=0.3,
                emotionality=0.8, activity=0.9, sociability=0.8, adaptability=0.8,
                archetype=PersonalityArchetype.ENERGETIC_ENTHUSIAST
            ),
            PersonalityArchetype.CALM_PHILOSOPHER: cls(
                openness=0.8, conscientiousness=0.7, extraversion=0.3,
                agreeableness=0.6, neuroticism=0.1,
                emotionality=0.3, activity=0.3, sociability=0.4, adaptability=0.5,
                archetype=PersonalityArchetype.CALM_PHILOSOPHER
            ),
            PersonalityArchetype.ARTISTIC_DREAMER: cls(
                openness=0.95, conscientiousness=0.4, extraversion=0.5,
                agreeableness=0.7, neuroticism=0.5,
                emotionality=0.9, activity=0.5, sociability=0.5, adaptability=0.6,
                archetype=PersonalityArchetype.ARTISTIC_DREAMER
            ),
            PersonalityArchetype.BALANCED_FRIEND: cls(
                openness=0.6, conscientiousness=0.6, extraversion=0.6,
                agreeableness=0.7, neuroticism=0.4,
                emotionality=0.5, activity=0.5, sociability=0.6, adaptability=0.6,
                archetype=PersonalityArchetype.BALANCED_FRIEND
            ),
        }
        return profiles[archetype]
    
    @classmethod
    def random_profile(cls, variation: float = 0.3) -> 'PersonalityProfile':
        """
        Generate a random personality profile with natural variation.
        
        Args:
            variation: Controls how much profiles vary from the mean (0.0-1.0).
                      Higher values create more extreme personalities.
        """
        def random_trait(mean: float = 0.5) -> float:
            """Generate a random trait value with normal distribution."""
            import random
            # Use triangular distribution for more natural variation
            value = random.triangular(0.0, 1.0, mean)
            # Apply variation factor
            value = mean + (value - mean) * variation
            return max(0.0, min(1.0, value))
        
        return cls(
            openness=random_trait(0.6),
            conscientiousness=random_trait(0.5),
            extraversion=random_trait(0.6),
            agreeableness=random_trait(0.7),
            neuroticism=random_trait(0.3),
            emotionality=random_trait(0.5),
            activity=random_trait(0.6),
            sociability=random_trait(0.6),
            adaptability=random_trait(0.6)
        )
    
    def evolve(self, dimension: str, delta: float) -> None:
        """
        Gradually modify a personality dimension based on experiences.
        
        Personality is relatively stable but can change slowly over time,
        especially in response to consistent environmental influences.
        This simulates neuroplasticity and learning.
        
        Args:
            dimension: Name of the personality dimension to modify
            delta: Amount to change (typically small, e.g., ±0.01 to ±0.05)
        """
        if hasattr(self, dimension):
            current = getattr(self, dimension)
            new_value = max(0.0, min(1.0, current + delta))
            setattr(self, dimension, new_value)
    
    def get_emotional_stability(self) -> float:
        """Calculate emotional stability (inverse of neuroticism)."""
        return 1.0 - self.neuroticism
    
    def to_dict(self) -> Dict[str, float]:
        """Export personality profile as a dictionary."""
        return {
            'openness': self.openness,
            'conscientiousness': self.conscientiousness,
            'extraversion': self.extraversion,
            'agreeableness': self.agreeableness,
            'neuroticism': self.neuroticism,
            'emotionality': self.emotionality,
            'activity': self.activity,
            'sociability': self.sociability,
            'adaptability': self.adaptability,
        }


class PersonalityEngine:
    """
    Main personality engine that modulates pet behavior based on personality.
    
    This engine uses the personality profile to:
    1. Modulate action selection (some personalities prefer certain actions)
    2. Influence response style (tone, word choice, expressiveness)
    3. Affect drive dynamics (how quickly drives change)
    4. Guide personality evolution (learning from experiences)
    """
    
    def __init__(self, profile: Optional[PersonalityProfile] = None):
        """
        Initialize the personality engine.
        
        Args:
            profile: PersonalityProfile instance. If None, creates a balanced profile.
        """
        self.profile = profile or PersonalityProfile()
    
    def modulate_action_utilities(
        self, 
        actions: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """
        Adjust action utilities based on personality traits.
        
        Different personalities prefer different types of actions:
        - High Openness: Prefers novel/curious actions
        - High Extraversion: Prefers social/expressive actions
        - High Agreeableness: Prefers caring/cooperative actions
        - High Conscientiousness: Prefers structured/purposeful actions
        - Low Neuroticism: More stable/predictable action selection
        
        Args:
            actions: List of (action_name, utility) tuples
            
        Returns:
            Modified list of (action_name, utility) tuples
        """
        modulated = []
        
        for action, utility in actions:
            modifier = 1.0
            
            # Openness influences curiosity-driven actions
            if action in ["ask_question", "explore", "learn"]:
                modifier *= (0.8 + 0.4 * self.profile.openness)
            
            # Extraversion influences social actions
            if action in ["express_affection", "tell_joke", "request_game"]:
                modifier *= (0.8 + 0.4 * self.profile.extraversion)
            
            # Agreeableness influences cooperative/caring actions
            if action in ["express_affection", "help", "comfort"]:
                modifier *= (0.8 + 0.4 * self.profile.agreeableness)
            
            # Conscientiousness influences structured actions
            if action in ["share_fact", "teach", "organize"]:
                modifier *= (0.8 + 0.4 * self.profile.conscientiousness)
            
            # Neuroticism adds variability (high neuroticism = more random)
            noise_factor = 0.05 + 0.15 * self.profile.neuroticism
            modifier *= random.uniform(1.0 - noise_factor, 1.0 + noise_factor)
            
            modulated.append((action, utility * modifier))
        
        # Re-sort by modified utility
        modulated.sort(key=lambda x: x[1], reverse=True)
        return modulated
    
    def get_response_style_modifiers(self) -> Dict[str, any]:
        """
        Generate response style parameters based on personality.
        
        Returns a dictionary of modifiers that can be used to adjust
        language generation, including:
        - expressiveness: How emotional/expressive responses should be
        - formality: How formal vs casual the language should be
        - verbosity: How detailed/wordy responses should be
        - humor_level: How much humor to include
        - warmth: How warm/friendly the tone should be
        """
        return {
            'expressiveness': 0.3 + 0.7 * self.profile.emotionality,
            'formality': self.profile.conscientiousness * 0.5,
            'verbosity': 0.5 + 0.3 * self.profile.openness,
            'humor_level': 0.2 + 0.6 * (1.0 - self.profile.neuroticism) * self.profile.extraversion,
            'warmth': 0.4 + 0.6 * self.profile.agreeableness,
            'energy': 0.3 + 0.7 * self.profile.activity,
            'curiosity': 0.3 + 0.7 * self.profile.openness,
        }
    
    def generate_personality_prompt(self) -> str:
        """
        Generate a natural language description of the personality
        to be used as part of the system prompt for language generation.
        
        This helps the LLM generate responses that match the personality.
        """
        # Determine dominant traits (>0.7) and weak traits (<0.3)
        traits_desc = []
        
        # Big Five descriptions
        if self.profile.openness > 0.7:
            traits_desc.append("muito curioso e criativo, sempre interessado em novas ideias")
        elif self.profile.openness < 0.3:
            traits_desc.append("mais tradicional e prático, preferindo o que é familiar")
        
        if self.profile.conscientiousness > 0.7:
            traits_desc.append("organizado e responsável")
        elif self.profile.conscientiousness < 0.3:
            traits_desc.append("espontâneo e flexível")
        
        if self.profile.extraversion > 0.7:
            traits_desc.append("muito sociável e energético")
        elif self.profile.extraversion < 0.3:
            traits_desc.append("mais reservado e calmo")
        
        if self.profile.agreeableness > 0.7:
            traits_desc.append("gentil, compassivo e cooperativo")
        elif self.profile.agreeableness < 0.3:
            traits_desc.append("direto e independente")
        
        if self.profile.neuroticism > 0.6:
            traits_desc.append("sensível e expressivo emocionalmente")
        elif self.profile.neuroticism < 0.3:
            traits_desc.append("emocionalmente estável e tranquilo")
        
        # Temperament descriptions
        if self.profile.activity > 0.7:
            traits_desc.append("cheio de energia e gosta de ação")
        
        # Build the prompt
        if traits_desc:
            personality_text = ", ".join(traits_desc)
            return f"Você tem uma personalidade única: você é {personality_text}."
        else:
            return "Você tem uma personalidade equilibrada e adaptável."
    
    def process_interaction_feedback(
        self, 
        interaction_type: str, 
        user_response_quality: float
    ) -> None:
        """
        Adjust personality slightly based on interaction outcomes.
        
        This simulates personality evolution through experience (neuroplasticity).
        Changes are very small to maintain personality stability.
        
        Args:
            interaction_type: Type of interaction ("positive", "negative", "neutral")
            user_response_quality: Score 0.0-1.0 indicating interaction success
        """
        # Very small learning rate to ensure personality stability
        learning_rate = 0.002
        
        if interaction_type == "positive" and user_response_quality > 0.7:
            # Positive interactions slightly increase agreeableness and extraversion
            self.profile.evolve('agreeableness', learning_rate)
            self.profile.evolve('extraversion', learning_rate * 0.5)
            # Reduce neuroticism slightly
            self.profile.evolve('neuroticism', -learning_rate * 0.3)
        
        elif interaction_type == "negative" and user_response_quality < 0.3:
            # Negative interactions might increase neuroticism slightly
            self.profile.evolve('neuroticism', learning_rate * 0.5)
            # And reduce extraversion slightly
            self.profile.evolve('extraversion', -learning_rate * 0.3)
        
        # Frequent interactions increase adaptability
        if user_response_quality > 0.5:
            self.profile.evolve('adaptability', learning_rate * 0.5)
    
    def calculate_drive_decay_rate(self, drive_name: str) -> float:
        """
        Calculate how quickly a drive should decay based on personality.
        
        Different personalities have different emotional regulation capabilities.
        
        Args:
            drive_name: Name of the drive
            
        Returns:
            Decay rate modifier (1.0 = normal, <1.0 = slower, >1.0 = faster)
        """
        base_rate = 1.0
        
        # Emotional stability affects all drive decay
        emotional_stability = self.profile.get_emotional_stability()
        base_rate *= (0.8 + 0.4 * emotional_stability)
        
        # Conscientiousness affects order-related drives
        if drive_name == "order":
            base_rate *= (0.9 + 0.2 * self.profile.conscientiousness)
        
        # Activity level affects energy-related drives
        if drive_name in ["curiosity", "sociability", "achievement", "creativity"]:
            base_rate *= (0.85 + 0.3 * self.profile.activity)
        
        # Negative drives affected by neuroticism
        if drive_name in ["anxiety", "frustration", "loneliness", "boredom"]:
            # Higher neuroticism = slower decay of negative emotions
            base_rate *= (0.7 + 0.6 * self.profile.neuroticism)
        
        # Agreeableness affects social drives
        if drive_name in ["affection", "acceptance"]:
            base_rate *= (0.85 + 0.3 * self.profile.agreeableness)
        
        # Openness affects creative and curious drives
        if drive_name in ["creativity", "idealism"]:
            base_rate *= (0.85 + 0.3 * self.profile.openness)
        
        return base_rate
    
    def should_initiate_interaction(self, hours_since_last: float) -> bool:
        """
        Determine if the pet should proactively initiate an interaction.
        
        Extraverted and high-activity personalities are more likely to
        initiate contact.
        
        Args:
            hours_since_last: Hours since the last user interaction
            
        Returns:
            True if the pet should initiate, False otherwise
        """
        # Base probability increases with time
        base_prob = min(0.8, hours_since_last / 24.0)
        
        # Extraversion and activity boost proactivity
        personality_factor = (
            0.3 * self.profile.extraversion +
            0.3 * self.profile.activity +
            0.2 * self.profile.sociability +
            0.2 * (1.0 - self.profile.neuroticism)
        )
        
        probability = base_prob * personality_factor
        return random.random() < probability


def create_personality(
    archetype: Optional[str] = None,
    random_variation: bool = False
) -> PersonalityEngine:
    """
    Factory function to create a personality engine.
    
    Args:
        archetype: Name of a personality archetype (e.g., "curious_explorer")
                  If None and random_variation is False, creates balanced personality
        random_variation: If True, creates a random personality profile
        
    Returns:
        PersonalityEngine instance with the specified personality
    """
    if random_variation:
        profile = PersonalityProfile.random_profile()
    elif archetype:
        try:
            arch_enum = PersonalityArchetype(archetype)
            profile = PersonalityProfile.from_archetype(arch_enum)
        except ValueError:
            # Invalid archetype name, use balanced profile
            profile = PersonalityProfile()
    else:
        profile = PersonalityProfile()
    
    return PersonalityEngine(profile)
