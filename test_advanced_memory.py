"""
Tests for advanced memory system components.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagotchi.advanced_memory import (
    EventRecord, Commitment, SemanticFact, RelationshipState, DailyDigest,
    CommitmentDetector, SalienceScorer, EventSegmenter, MemoryMetrics
)
from tamagotchi.advanced_memory_manager import AdvancedMemoryManager
from tamagotchi.memory_integration import HybridMemoryStore, format_context_for_prompt


class TestDataModels:
    """Test data model serialization and deserialization."""
    
    def test_event_record_serialization(self):
        """Test EventRecord to/from dict."""
        now = datetime.utcnow()
        event = EventRecord(
            event_id="test-123",
            title="Test Event",
            time_range=(now, now + timedelta(minutes=10)),
            summary="A test event summary",
            entities=["user", "pet"],
            emotions={"joy": 0.8},
            salience=0.7
        )
        
        # Serialize
        data = event.to_dict()
        assert data["event_id"] == "test-123"
        assert data["title"] == "Test Event"
        assert data["salience"] == 0.7
        
        # Deserialize
        restored = EventRecord.from_dict(data)
        assert restored.event_id == event.event_id
        assert restored.title == event.title
        assert restored.salience == event.salience
    
    def test_commitment_serialization(self):
        """Test Commitment to/from dict."""
        now = datetime.utcnow()
        commitment = Commitment(
            commitment_id="commit-456",
            desc="Vou te lembrar amanhã",
            made_at=now,
            status="active",
            reactivation_schedule=[now + timedelta(days=1)]
        )
        
        data = commitment.to_dict()
        assert data["commitment_id"] == "commit-456"
        assert data["status"] == "active"
        
        restored = Commitment.from_dict(data)
        assert restored.desc == commitment.desc
        assert restored.status == "active"
    
    def test_semantic_fact_serialization(self):
        """Test SemanticFact to/from dict."""
        now = datetime.utcnow()
        fact = SemanticFact(
            fact_id="fact-789",
            triple=("user", "name", "João"),
            confidence=1.0,
            importance=0.9,
            last_reinforced=now
        )
        
        data = fact.to_dict()
        assert data["fact_id"] == "fact-789"
        assert data["triple"] == ["user", "name", "João"]
        
        restored = SemanticFact.from_dict(data)
        assert restored.triple == fact.triple
        assert restored.confidence == 1.0


class TestCommitmentDetector:
    """Test commitment and correction detection."""
    
    def test_detect_simple_commitment(self):
        """Test detection of simple commitments."""
        detector = CommitmentDetector()
        
        # Test "vou" pattern
        result = detector.detect_commitment("Vou te lembrar amanhã!")
        assert result is not None
        assert "lembrar" in result.lower()
        
        # Test "posso" pattern
        result = detector.detect_commitment("Posso te ajudar com isso")
        assert result is not None
        assert "ajudar" in result.lower()
    
    def test_detect_commitment_with_condition(self):
        """Test conditional commitment detection."""
        detector = CommitmentDetector()
        
        result = detector.detect_commitment("Sempre que você precisar, vou estar aqui")
        assert result is not None
    
    def test_no_commitment_in_normal_text(self):
        """Test that normal conversation doesn't trigger false positives."""
        detector = CommitmentDetector()
        
        result = detector.detect_commitment("Olá, como você está?")
        assert result is None
        
        result = detector.detect_commitment("Isso é interessante!")
        assert result is None
    
    def test_detect_user_correction(self):
        """Test user correction detection."""
        detector = CommitmentDetector()
        
        # Name correction
        result = detector.detect_correction("Meu nome é João")
        assert result is not None
        assert result[0] == "name"
        assert result[1] == "joão"
        
        # Preference
        result = detector.detect_correction("Prefiro café a chá")
        assert result is not None
        assert result[0] == "preference"
    
    def test_detect_open_loop(self):
        """Test open loop (question) detection."""
        detector = CommitmentDetector()
        
        result = detector.detect_open_loop("Você sabe programar?")
        assert result is not None
        assert "?" in result
        
        result = detector.detect_open_loop("Poderia me explicar isso?")
        assert result is not None


class TestSalienceScorer:
    """Test salience scoring algorithm."""
    
    def test_recent_event_high_salience(self):
        """Test that recent events have higher salience."""
        scorer = SalienceScorer()
        
        # Event from 1 hour ago
        recent_score = scorer.calculate_salience(
            timestamp=datetime.utcnow() - timedelta(hours=1),
            repetition_count=1,
            is_novel=False,
            emotion_intensity=0.5,
            is_explicit=False
        )
        
        # Event from 1 week ago
        old_score = scorer.calculate_salience(
            timestamp=datetime.utcnow() - timedelta(days=7),
            repetition_count=1,
            is_novel=False,
            emotion_intensity=0.5,
            is_explicit=False
        )
        
        assert recent_score > old_score
    
    def test_explicit_events_highest_salience(self):
        """Test that explicit events (corrections, promises) have highest salience."""
        scorer = SalienceScorer()
        
        # Explicit event
        explicit_score = scorer.calculate_salience(
            timestamp=datetime.utcnow(),
            repetition_count=1,
            is_novel=False,
            emotion_intensity=0.0,
            is_explicit=True
        )
        
        # Non-explicit event
        normal_score = scorer.calculate_salience(
            timestamp=datetime.utcnow(),
            repetition_count=1,
            is_novel=False,
            emotion_intensity=0.0,
            is_explicit=False
        )
        
        assert explicit_score > normal_score
    
    def test_repetition_increases_salience(self):
        """Test that repetition increases salience (when not novel)."""
        scorer = SalienceScorer()
        
        # First mention (not novel)
        first_score = scorer.calculate_salience(
            timestamp=datetime.utcnow(),
            repetition_count=1,
            is_novel=False,
            emotion_intensity=0.0,
            is_explicit=False
        )
        
        # After 5 repetitions (not novel)
        repeated_score = scorer.calculate_salience(
            timestamp=datetime.utcnow(),
            repetition_count=5,
            is_novel=False,
            emotion_intensity=0.0,
            is_explicit=False
        )
        
        # Repetition should increase score
        assert repeated_score > first_score


class TestEventSegmenter:
    """Test event segmentation logic."""
    
    def test_segments_after_time_gap(self):
        """Test that large time gaps trigger segmentation."""
        segmenter = EventSegmenter(time_gap_minutes=10.0)
        
        # Add 3 turns
        now = datetime.utcnow()
        for i in range(3):
            segmenter.add_turn(
                user_msg=f"Message {i}",
                pet_msg=f"Response {i}",
                timestamp=now + timedelta(minutes=i)
            )
        
        # Should not segment yet
        assert not segmenter.should_segment(None, now + timedelta(minutes=3))
        
        # Large time gap should trigger segmentation
        assert segmenter.should_segment(None, now + timedelta(minutes=20))
    
    def test_segments_after_max_turns(self):
        """Test that reaching max turns triggers segmentation."""
        segmenter = EventSegmenter()
        
        now = datetime.utcnow()
        for i in range(10):
            segmenter.add_turn(
                user_msg=f"Message {i}",
                pet_msg=f"Response {i}",
                timestamp=now + timedelta(minutes=i)
            )
        
        # Should force segmentation at 10 turns
        assert segmenter.should_segment(None, now + timedelta(minutes=11))
    
    def test_creates_event_from_turns(self):
        """Test event creation from conversation turns."""
        segmenter = EventSegmenter()
        
        now = datetime.utcnow()
        for i in range(5):
            segmenter.add_turn(
                user_msg=f"User message {i}",
                pet_msg=f"Pet response {i}",
                timestamp=now + timedelta(minutes=i)
            )
        
        event = segmenter.create_event(event_id="test-event")
        
        assert event is not None
        assert event.event_id == "test-event"
        assert "Conversa" in event.title
        assert event.time_range[0] == now
        
        # After creating event, turns should be cleared
        assert len(segmenter.current_turns) == 0


class TestMemoryMetrics:
    """Test metrics tracking."""
    
    def test_commitment_resolution_rate(self):
        """Test commitment resolution rate calculation."""
        metrics = MemoryMetrics()
        
        # No commitments
        assert metrics.get_commitment_resolution_rate() == 0.0
        
        # 3 made, 2 fulfilled
        metrics.record_commitment_made()
        metrics.record_commitment_made()
        metrics.record_commitment_made()
        metrics.record_commitment_fulfilled()
        metrics.record_commitment_fulfilled()
        
        assert metrics.get_commitment_resolution_rate() == 2/3
    
    def test_thread_closure_latency(self):
        """Test thread closure latency calculation."""
        metrics = MemoryMetrics()
        
        # Record some closures
        metrics.record_loop_closed(2.0)  # 2 hours
        metrics.record_loop_closed(4.0)  # 4 hours
        metrics.record_loop_closed(6.0)  # 6 hours
        
        assert metrics.get_thread_closure_latency() == 4.0  # Average
    
    def test_tokens_per_turn(self):
        """Test average tokens per turn calculation."""
        metrics = MemoryMetrics()
        
        metrics.record_turn(100)
        metrics.record_turn(150)
        metrics.record_turn(125)
        
        assert metrics.get_avg_tokens_per_turn() == 125.0


class TestAdvancedMemoryManager:
    """Test the advanced memory manager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = AdvancedMemoryManager(user_id="test-user", firestore_client=None)
        
        assert manager.user_id == "test-user"
        assert manager.detector is not None
        assert manager.scorer is not None
        assert manager.segmenter is not None
        assert manager.metrics is not None
    
    def test_process_turn_with_commitment(self):
        """Test processing a turn that contains a commitment."""
        manager = AdvancedMemoryManager(user_id="test-user", firestore_client=None)
        
        result = manager.process_turn(
            user_message="Me ajude com isso",
            pet_response="Vou te ajudar amanhã!"
        )
        
        assert result["commitment_detected"] is True
        assert len(manager.commitments_cache) == 1
        assert "ajudar" in manager.commitments_cache[0].desc.lower()
    
    def test_process_turn_with_correction(self):
        """Test processing a turn with user correction."""
        manager = AdvancedMemoryManager(user_id="test-user", firestore_client=None)
        
        result = manager.process_turn(
            user_message="Meu nome é Maria",
            pet_response="Olá Maria!"
        )
        
        assert result["correction_detected"] is True
        assert len(manager.semantic_cache) >= 1
    
    def test_retrieve_context_prioritizes_commitments(self):
        """Test that context retrieval prioritizes commitments."""
        manager = AdvancedMemoryManager(user_id="test-user", firestore_client=None)
        
        # Add a commitment
        manager.process_turn(
            user_message="Pode me lembrar?",
            pet_response="Vou te lembrar amanhã"
        )
        
        # Retrieve context
        context = manager.retrieve_context(query="lembrar", max_tokens=1200)
        
        assert "commitments" in context
        assert len(context["commitments"]) > 0
    
    def test_consolidate_session(self):
        """Test session consolidation."""
        manager = AdvancedMemoryManager(user_id="test-user", firestore_client=None)
        
        # Add some turns
        for i in range(5):
            manager.process_turn(
                user_message=f"Message {i}",
                pet_response=f"Response {i}"
            )
        
        results = manager.consolidate_session()
        
        assert "events_created" in results
        assert "facts_promoted" in results
        assert "commitments_updated" in results
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly."""
        manager = AdvancedMemoryManager(user_id="test-user", firestore_client=None)
        
        # Process a turn with commitment
        manager.process_turn(
            user_message="Preciso de ajuda",
            pet_response="Vou te ajudar"
        )
        
        metrics = manager.get_metrics()
        
        assert metrics["turns_processed"] > 0
        assert metrics["commitments_made"] > 0


class TestHybridMemoryStore:
    """Test the hybrid memory store integration."""
    
    def test_initialization(self):
        """Test hybrid store initialization."""
        store = HybridMemoryStore(user_id="test-user", firestore_client=None)
        
        assert store.user_id == "test-user"
        assert store.advanced_manager is not None
    
    def test_backward_compatibility(self):
        """Test that legacy MemoryStore methods still work."""
        store = HybridMemoryStore(user_id="test-user", firestore_client=None)
        
        # Legacy method should work
        store.add_episode("Test episode", salience=0.7)
        
        assert len(store.episodic) > 0
    
    def test_get_context_for_response(self):
        """Test context retrieval for response generation."""
        store = HybridMemoryStore(user_id="test-user", firestore_client=None)
        
        # Add some data
        store.process_conversation_turn(
            user_message="Olá",
            pet_response="Oi! Como vai?"
        )
        
        context = store.get_context_for_response(query="olá", max_tokens=1200)
        
        assert "commitments" in context
        assert "semantic_facts" in context
        assert "recent_events" in context
    
    def test_get_active_commitments(self):
        """Test getting active commitments."""
        store = HybridMemoryStore(user_id="test-user", firestore_client=None)
        
        # Add a commitment
        store.process_conversation_turn(
            user_message="Me ajude",
            pet_response="Vou te ajudar amanhã"
        )
        
        commitments = store.get_active_commitments()
        assert len(commitments) > 0


class TestContextFormatting:
    """Test context formatting for prompts."""
    
    def test_format_context_with_all_fields(self):
        """Test formatting context with all fields present."""
        context = {
            "commitments": ["Vou te lembrar amanhã", "Vou te ajudar"],
            "semantic_facts": ["user name João", "user gosta café"],
            "recent_events": ["Evento: Conversa sobre café"],
            "relationship_state": {"stage": "friend"}
        }
        
        formatted = format_context_for_prompt(context)
        
        assert "COMPROMISSOS ATIVOS:" in formatted
        assert "O QUE VOCÊ SABE:" in formatted
        assert "CONTEXTO RECENTE:" in formatted
        assert "RELACIONAMENTO: friend" in formatted
    
    def test_format_context_with_empty_fields(self):
        """Test formatting context with empty fields."""
        context = {
            "commitments": [],
            "semantic_facts": [],
            "recent_events": [],
            "relationship_state": {"stage": "stranger"}
        }
        
        formatted = format_context_for_prompt(context)
        
        # Should still include relationship
        assert "RELACIONAMENTO: stranger" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
