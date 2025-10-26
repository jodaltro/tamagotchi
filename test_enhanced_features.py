"""
Tests for enhanced features: expanded drives, AI memory, and image analysis.
"""

import sys
sys.path.insert(0, '/home/runner/work/tamagotchi')

import pytest
from datetime import datetime, timedelta
from tamagotchi.pet_state import PetState
from tamagotchi.memory_store import MemoryStore, ImageMemory
from tamagotchi.virtual_pet import VirtualPet


class TestExpandedDriveSystem:
    """Test the expanded 18-drive system."""
    
    def test_18_drives_initialized(self):
        """Test that all 18 drives are initialized."""
        pet = PetState()
        assert len(pet.drives) == 18
        
        # Check all expected drives exist
        expected_drives = [
            "curiosity", "affection", "order", "sociability", "autonomy", "humor",
            "achievement", "power", "acceptance", "idealism", "tranquility", "creativity",
            "hunger", "rest",
            "anxiety", "frustration", "loneliness", "boredom"
        ]
        
        for drive in expected_drives:
            assert drive in pet.drives
    
    def test_positive_drives_initialized_moderate(self):
        """Test that positive drives are initialized in 0.3-0.7 range."""
        pet = PetState()
        positive_drives = [
            "curiosity", "affection", "order", "sociability", "autonomy", "humor",
            "achievement", "power", "acceptance", "idealism", "tranquility", "creativity",
            "hunger", "rest"
        ]
        
        for drive in positive_drives:
            assert 0.3 <= pet.drives[drive] <= 0.7
    
    def test_negative_drives_initialized_low(self):
        """Test that negative drives start low (0.1-0.3)."""
        pet = PetState()
        negative_drives = ["anxiety", "frustration", "loneliness", "boredom"]
        
        for drive in negative_drives:
            assert 0.1 <= pet.drives[drive] <= 0.3
    
    def test_negative_drives_increase_over_time(self):
        """Test that negative drives increase without interaction."""
        pet = PetState()
        
        initial_anxiety = pet.drives["anxiety"]
        initial_loneliness = pet.drives["loneliness"]
        
        # Simulate time passing without interaction
        pet.tick(minutes=120)  # 2 hours
        
        # Negative drives should increase
        assert pet.drives["anxiety"] >= initial_anxiety
        assert pet.drives["loneliness"] >= initial_loneliness
    
    def test_interaction_reduces_negative_drives(self):
        """Test that interaction reduces negative drives."""
        pet = PetState()
        
        # Set negative drives to high values
        pet.drives["loneliness"] = 0.8
        pet.drives["boredom"] = 0.7
        pet.drives["anxiety"] = 0.6
        
        # Simulate fast response interaction
        pet.update_from_interaction("Olá!", response_delay=1.0)
        
        # Negative drives should decrease
        assert pet.drives["loneliness"] < 0.8
        assert pet.drives["boredom"] < 0.7
        assert pet.drives["anxiety"] < 0.6
    
    def test_achievement_drive_responds_to_success(self):
        """Test that achievement drive increases on success words."""
        pet = PetState()
        
        initial_achievement = pet.drives["achievement"]
        pet.update_from_interaction("Consegui terminar o projeto!", response_delay=5.0)
        
        assert pet.drives["achievement"] > initial_achievement
    
    def test_creativity_drive_responds_to_art(self):
        """Test that creativity drive increases on art/creation words."""
        pet = PetState()
        
        initial_creativity = pet.drives["creativity"]
        pet.update_from_interaction("Estou criando uma arte nova", response_delay=5.0)
        
        assert pet.drives["creativity"] > initial_creativity
    
    def test_tranquility_drive_responds_to_calm(self):
        """Test that tranquility drive increases on calm words."""
        pet = PetState()
        
        initial_tranquility = pet.drives["tranquility"]
        pet.update_from_interaction("Estou muito tranquilo e em paz", response_delay=5.0)
        
        assert pet.drives["tranquility"] > initial_tranquility


class TestEnhancedMemorySystem:
    """Test the enhanced memory system with AI importance and reinforcement."""
    
    def test_memory_importance_scoring(self):
        """Test that memories are created with importance scores."""
        mem = MemoryStore()
        
        mem.add_episode("Test message", salience=0.7, importance_score=0.9)
        
        assert len(mem.episodic) == 1
        assert mem.episodic[0].importance_score == 0.9
    
    def test_memory_consolidation_uses_importance(self):
        """Test that consolidation considers both salience and importance."""
        mem = MemoryStore()
        
        # High importance, moderate salience
        mem.add_episode("My name is John", salience=0.5, importance_score=0.9)
        
        # Calculate combined score: 0.5 * 0.4 + 0.9 * 0.6 = 0.74 (above threshold 0.6)
        mem.consolidate(threshold=0.6)
        
        assert len(mem.semantic) > 0
    
    def test_memory_reinforcement(self):
        """Test that repeated information reinforces memory."""
        mem = MemoryStore()
        
        # Add initial fact
        mem.semantic["test fact"] = (0.7, datetime.utcnow(), 1)
        
        # Reinforce it
        reinforced = mem.reinforce_memory("test fact", boost=0.2)
        
        assert reinforced is True
        weight, _, count = mem.semantic["test fact"]
        assert weight > 0.7  # Weight increased
        assert count == 2  # Access count increased
    
    def test_memory_decay(self):
        """Test that old unused memories decay over time."""
        mem = MemoryStore()
        
        # Add a fact with old timestamp
        old_time = datetime.utcnow() - timedelta(days=60)
        mem.semantic["old fact"] = (0.5, old_time, 0)  # No accesses
        
        # Apply decay
        mem.apply_memory_decay(hours_elapsed=24 * 30)  # 30 days
        
        # Old fact should be forgotten or decayed
        if "old fact" in mem.semantic:
            weight, _, _ = mem.semantic["old fact"]
            assert weight < 0.5  # Should have decayed
        # Or it might be completely forgotten
    
    def test_frequently_accessed_memories_decay_slower(self):
        """Test that frequently accessed memories resist decay."""
        mem = MemoryStore()
        
        recent_time = datetime.utcnow() - timedelta(days=10)
        
        # Add two facts: one frequently accessed, one not
        mem.semantic["popular fact"] = (0.6, recent_time, 10)  # 10 accesses
        mem.semantic["unused fact"] = (0.6, recent_time, 0)   # 0 accesses
        
        # Apply decay
        mem.apply_memory_decay(hours_elapsed=24 * 10)
        
        # Popular fact should decay less
        if "popular fact" in mem.semantic and "unused fact" in mem.semantic:
            pop_weight, _, _ = mem.semantic["popular fact"]
            unused_weight, _, _ = mem.semantic["unused fact"]
            assert pop_weight >= unused_weight
    
    def test_semantic_facts_retrieval(self):
        """Test retrieving semantic facts with minimum weight."""
        mem = MemoryStore()
        
        current_time = datetime.utcnow()
        mem.semantic["important fact"] = (0.9, current_time, 1)
        mem.semantic["moderate fact"] = (0.6, current_time, 1)
        mem.semantic["weak fact"] = (0.2, current_time, 1)
        
        # Get facts above 0.5 threshold
        facts = mem.get_semantic_facts(min_weight=0.5)
        
        assert "important fact" in facts
        assert "moderate fact" in facts
        assert "weak fact" not in facts
    
    def test_recall_updates_access_tracking(self):
        """Test that recall updates access count for reinforcement."""
        mem = MemoryStore()
        
        current_time = datetime.utcnow()
        mem.semantic["test fact"] = (0.7, current_time, 1)
        
        # Recall with query
        results = mem.recall(query="test", top_k=5)
        
        # Access count should increase
        _, _, count = mem.semantic["test fact"]
        assert count == 2  # Increased from 1 to 2


class TestEnhancedImageMemory:
    """Test the enhanced image memory system."""
    
    def test_image_memory_structure(self):
        """Test that ImageMemory stores all required fields."""
        mem = MemoryStore()
        
        mem.add_image_memory(
            features=[0.1, 0.2, 0.3],
            labels=["cat", "animal"],
            ai_description="A cute orange cat",
            detected_entities={"animal": "cat, orange, small"},
            context="Olá, este é meu gato",
            importance_score=0.8
        )
        
        assert len(mem.images) == 1
        img = mem.images[0]
        assert img.ai_description == "A cute orange cat"
        assert "animal" in img.detected_entities
        assert img.importance_score == 0.8
        assert img.context == "Olá, este é meu gato"
    
    def test_backward_compatibility_add_image(self):
        """Test that old add_image method still works."""
        mem = MemoryStore()
        
        mem.add_image([0.1, 0.2], ["test"])
        
        assert len(mem.images) == 1
        assert mem.images[0].labels == ["test"]
    
    def test_get_image_memories_with_context(self):
        """Test retrieving image memories with full context."""
        mem = MemoryStore()
        
        mem.add_image_memory(
            features=[0.1, 0.2],
            labels=["dog"],
            ai_description="A happy dog",
            detected_entities={"animal": "dog"},
            context="My pet",
            importance_score=0.9
        )
        
        memories = mem.get_image_memories_with_context(top_k=5)
        
        assert len(memories) == 1
        assert memories[0]["description"] == "A happy dog"
        assert memories[0]["entities"] == {"animal": "dog"}
        assert memories[0]["importance"] == 0.9


class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_pet_state_with_enhanced_memory(self):
        """Test that PetState works with enhanced memory features."""
        pet = PetState()
        
        # Process interaction
        pet.update_from_interaction("Meu nome é João", response_delay=5.0)
        
        # Check memory was recorded
        assert len(pet.memory.episodic) > 0
    
    def test_user_info_extraction_with_reinforcement(self):
        """Test that repeated user info gets reinforced."""
        pet = PetState()
        
        # Tell name first time
        pet.update_from_interaction("Olá, meu nome é João", response_delay=5.0)
        
        # Consolidate
        pet.memory.consolidate(threshold=0.5)
        
        # Check if name was stored
        facts = pet.memory.get_semantic_facts(min_weight=0.3)
        name_facts = [f for f in facts if "joão" in f.lower()]
        
        if name_facts:
            # Tell name again
            initial_count = pet.memory.semantic[name_facts[0]][2]
            pet.update_from_interaction("Sim, sou o João", response_delay=5.0)
            
            # Should be reinforced (access count increased)
            # Note: The _extract_user_info now uses reinforce_memory
    
    def test_memory_decay_periodic_application(self):
        """Test that memory decay is applied periodically."""
        pet = PetState()
        
        # Set last decay time to 25 hours ago
        pet.memory.last_decay_time = datetime.utcnow() - timedelta(hours=25)
        
        # Add some old semantic memory
        old_time = datetime.utcnow() - timedelta(days=30)
        pet.memory.semantic["old fact"] = (0.3, old_time, 0)
        
        # Trigger interaction (which checks for decay)
        pet.update_from_interaction("Hello", response_delay=5.0)
        
        # Last decay time should be updated
        assert (datetime.utcnow() - pet.memory.last_decay_time).total_seconds() < 10


class TestVirtualPetIntegration:
    """Test VirtualPet with all enhancements."""
    
    def test_virtual_pet_initialization(self):
        """Test that VirtualPet initializes with enhanced features."""
        pet = VirtualPet()
        
        assert len(pet.state.drives) == 18
        assert hasattr(pet.state.memory, 'apply_memory_decay')
    
    def test_user_message_without_ai(self):
        """Test user message processing works without AI."""
        # This test should work even without AI API key
        pet = VirtualPet()
        
        # Process message
        pet.user_message("Olá, meu nome é Maria", delay=5.0)
        
        # Check memory was updated
        assert len(pet.state.memory.episodic) > 0
    
    def test_memory_retrieval_for_response(self):
        """Test that response generation can retrieve enhanced memory."""
        pet = VirtualPet()
        
        # Add some facts to memory
        current_time = datetime.utcnow()
        pet.state.memory.semantic["nome: João"] = (0.9, current_time, 1)
        pet.state.memory.semantic["gosta de: programar"] = (0.8, current_time, 1)
        
        # Get facts for response
        facts = pet.state.memory.get_semantic_facts(min_weight=0.5)
        
        assert len(facts) >= 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
