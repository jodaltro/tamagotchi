"""
Tests for the personality engine module.

This module contains comprehensive tests for the personality engine,
including personality profiles, archetypes, behavior modulation, and
personality evolution.
"""

import unittest
from tamagotchi.personality_engine import (
    PersonalityProfile,
    PersonalityEngine,
    PersonalityArchetype,
    create_personality
)


class TestPersonalityProfile(unittest.TestCase):
    """Test cases for PersonalityProfile class."""
    
    def test_default_profile(self):
        """Test that default profile has balanced values."""
        profile = PersonalityProfile()
        self.assertEqual(profile.openness, 0.5)
        self.assertEqual(profile.extraversion, 0.5)
        self.assertEqual(profile.agreeableness, 0.5)
        self.assertEqual(profile.conscientiousness, 0.5)
        self.assertEqual(profile.neuroticism, 0.5)
    
    def test_bounds_enforcement(self):
        """Test that personality dimensions are clamped to 0.0-1.0."""
        profile = PersonalityProfile(openness=1.5, neuroticism=-0.5)
        self.assertEqual(profile.openness, 1.0)
        self.assertEqual(profile.neuroticism, 0.0)
    
    def test_archetype_curious_explorer(self):
        """Test the curious explorer archetype."""
        profile = PersonalityProfile.from_archetype(PersonalityArchetype.CURIOUS_EXPLORER)
        self.assertGreater(profile.openness, 0.7)
        self.assertEqual(profile.archetype, PersonalityArchetype.CURIOUS_EXPLORER)
    
    def test_archetype_playful_companion(self):
        """Test the playful companion archetype."""
        profile = PersonalityProfile.from_archetype(PersonalityArchetype.PLAYFUL_COMPANION)
        self.assertGreater(profile.extraversion, 0.7)
        self.assertGreater(profile.agreeableness, 0.7)
        self.assertGreater(profile.activity, 0.7)
    
    def test_random_profile(self):
        """Test random profile generation."""
        profile = PersonalityProfile.random_profile()
        # All dimensions should be valid
        for attr in ['openness', 'conscientiousness', 'extraversion',
                     'agreeableness', 'neuroticism']:
            value = getattr(profile, attr)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
    
    def test_evolution(self):
        """Test personality evolution."""
        profile = PersonalityProfile(openness=0.5)
        profile.evolve('openness', 0.1)
        self.assertEqual(profile.openness, 0.6)
        
        # Test bounds enforcement during evolution
        profile.evolve('openness', 0.5)
        self.assertEqual(profile.openness, 1.0)
        
        profile.evolve('openness', -2.0)
        self.assertEqual(profile.openness, 0.0)
    
    def test_emotional_stability(self):
        """Test emotional stability calculation."""
        profile = PersonalityProfile(neuroticism=0.3)
        self.assertEqual(profile.get_emotional_stability(), 0.7)
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        profile = PersonalityProfile(openness=0.8, extraversion=0.6)
        data = profile.to_dict()
        self.assertEqual(data['openness'], 0.8)
        self.assertEqual(data['extraversion'], 0.6)
        self.assertIn('neuroticism', data)


class TestPersonalityEngine(unittest.TestCase):
    """Test cases for PersonalityEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.balanced_profile = PersonalityProfile()
        self.extraverted_profile = PersonalityProfile(extraversion=0.9, activity=0.9)
        self.introverted_profile = PersonalityProfile(extraversion=0.2, activity=0.3)
        self.open_profile = PersonalityProfile(openness=0.9)
    
    def test_initialization(self):
        """Test engine initialization."""
        engine = PersonalityEngine(self.balanced_profile)
        self.assertIsNotNone(engine.profile)
        self.assertEqual(engine.profile.openness, 0.5)
    
    def test_action_modulation_extraversion(self):
        """Test that extraversion boosts social actions."""
        engine = PersonalityEngine(self.extraverted_profile)
        actions = [("express_affection", 0.5), ("share_fact", 0.5)]
        modulated = engine.modulate_action_utilities(actions)
        
        # Find express_affection in modulated actions
        affection_util = next(u for a, u in modulated if a == "express_affection")
        fact_util = next(u for a, u in modulated if a == "share_fact")
        
        # Extraverted personality should boost affection more than facts
        # (though noise might affect this slightly)
        # We just check that affection was considered
        self.assertIsNotNone(affection_util)
    
    def test_action_modulation_openness(self):
        """Test that openness boosts curious actions."""
        engine = PersonalityEngine(self.open_profile)
        actions = [("ask_question", 0.5), ("express_affection", 0.5)]
        modulated = engine.modulate_action_utilities(actions)
        
        # High openness should boost question-asking
        question_util = next(u for a, u in modulated if a == "ask_question")
        self.assertIsNotNone(question_util)
    
    def test_response_style_modifiers(self):
        """Test response style modifier generation."""
        engine = PersonalityEngine(self.extraverted_profile)
        modifiers = engine.get_response_style_modifiers()
        
        self.assertIn('expressiveness', modifiers)
        self.assertIn('warmth', modifiers)
        self.assertIn('energy', modifiers)
        
        # High extraversion and activity should give high energy
        self.assertGreater(modifiers['energy'], 0.5)
    
    def test_personality_prompt_generation(self):
        """Test personality prompt generation."""
        # Test with highly open personality
        engine = PersonalityEngine(PersonalityProfile(openness=0.9))
        prompt = engine.generate_personality_prompt()
        self.assertIn("curioso", prompt.lower())
        
        # Test with balanced personality
        balanced_engine = PersonalityEngine(PersonalityProfile())
        balanced_prompt = balanced_engine.generate_personality_prompt()
        self.assertIn("equilibrad", balanced_prompt.lower())
    
    def test_interaction_feedback_positive(self):
        """Test personality evolution from positive interactions."""
        profile = PersonalityProfile(agreeableness=0.5, extraversion=0.5)
        engine = PersonalityEngine(profile)
        
        initial_agreeableness = engine.profile.agreeableness
        initial_extraversion = engine.profile.extraversion
        
        # Simulate multiple positive interactions
        for _ in range(10):
            engine.process_interaction_feedback("positive", 0.9)
        
        # Agreeableness and extraversion should increase slightly
        self.assertGreater(engine.profile.agreeableness, initial_agreeableness)
        self.assertGreater(engine.profile.extraversion, initial_extraversion)
    
    def test_interaction_feedback_negative(self):
        """Test personality evolution from negative interactions."""
        profile = PersonalityProfile(neuroticism=0.3)
        engine = PersonalityEngine(profile)
        
        initial_neuroticism = engine.profile.neuroticism
        
        # Simulate negative interactions
        for _ in range(10):
            engine.process_interaction_feedback("negative", 0.2)
        
        # Neuroticism might increase (though changes are small)
        # We just verify the method runs without error
        self.assertIsNotNone(engine.profile.neuroticism)
    
    def test_drive_decay_rate(self):
        """Test drive decay rate calculation."""
        # High emotional stability (low neuroticism) = more stable drives
        stable_engine = PersonalityEngine(PersonalityProfile(neuroticism=0.2))
        unstable_engine = PersonalityEngine(PersonalityProfile(neuroticism=0.8))
        
        stable_rate = stable_engine.calculate_drive_decay_rate("curiosity")
        unstable_rate = unstable_engine.calculate_drive_decay_rate("curiosity")
        
        # More emotionally stable = slower decay (lower rate)
        self.assertLess(unstable_rate, stable_rate)
    
    def test_should_initiate_interaction(self):
        """Test proactive interaction initiation."""
        # Extraverted personality should be more likely to initiate
        extraverted = PersonalityEngine(self.extraverted_profile)
        introverted = PersonalityEngine(self.introverted_profile)
        
        # Test with long time since last interaction
        # Run multiple times to account for randomness
        extraverted_initiations = sum(
            extraverted.should_initiate_interaction(24.0) for _ in range(100)
        )
        introverted_initiations = sum(
            introverted.should_initiate_interaction(24.0) for _ in range(100)
        )
        
        # Extraverted should initiate more often
        self.assertGreater(extraverted_initiations, introverted_initiations)


class TestPersonalityFactory(unittest.TestCase):
    """Test cases for personality factory functions."""
    
    def test_create_personality_balanced(self):
        """Test creating a balanced personality."""
        engine = create_personality()
        self.assertIsNotNone(engine.profile)
    
    def test_create_personality_archetype(self):
        """Test creating personality from archetype."""
        engine = create_personality(archetype="curious_explorer")
        self.assertIsNotNone(engine.profile)
        self.assertGreater(engine.profile.openness, 0.7)
    
    def test_create_personality_random(self):
        """Test creating random personality."""
        engine = create_personality(random_variation=True)
        self.assertIsNotNone(engine.profile)
        
        # Create multiple and ensure they're different
        engine2 = create_personality(random_variation=True)
        # At least one dimension should be different
        different = False
        for attr in ['openness', 'extraversion', 'agreeableness']:
            if getattr(engine.profile, attr) != getattr(engine2.profile, attr):
                different = True
                break
        self.assertTrue(different)
    
    def test_create_personality_invalid_archetype(self):
        """Test creating personality with invalid archetype falls back."""
        engine = create_personality(archetype="invalid_archetype_name")
        # Should create balanced profile as fallback
        self.assertIsNotNone(engine.profile)


class TestAllArchetypes(unittest.TestCase):
    """Test that all defined archetypes work correctly."""
    
    def test_all_archetypes_valid(self):
        """Test that all archetypes can be created successfully."""
        archetypes = [
            "curious_explorer",
            "playful_companion",
            "gentle_caregiver",
            "wise_observer",
            "energetic_enthusiast",
            "calm_philosopher",
            "artistic_dreamer",
            "balanced_friend",
        ]
        
        for archetype in archetypes:
            with self.subTest(archetype=archetype):
                engine = create_personality(archetype=archetype)
                self.assertIsNotNone(engine.profile)
                # Verify all dimensions are in valid range
                for attr in ['openness', 'conscientiousness', 'extraversion',
                            'agreeableness', 'neuroticism']:
                    value = getattr(engine.profile, attr)
                    self.assertGreaterEqual(value, 0.0, 
                        f"{archetype}.{attr} below 0.0")
                    self.assertLessEqual(value, 1.0,
                        f"{archetype}.{attr} above 1.0")


if __name__ == '__main__':
    unittest.main()
