"""
Advanced Memory Manager - Orchestrates the hierarchical memory system.

This manager integrates:
- Firestore storage for all memory types
- Hybrid retrieval (dense + BM25)
- Consolidation pipelines
- Spaced repetition scheduling
- Metrics tracking
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import math

from .advanced_memory import (
    EventRecord, Commitment, SemanticFact, RelationshipState, DailyDigest,
    CommitmentDetector, SalienceScorer, EventSegmenter, MemoryMetrics
)

logger = logging.getLogger(__name__)


class AdvancedMemoryManager:
    """
    Main memory management system with Firestore integration.
    """
    
    def __init__(self, user_id: str, firestore_client=None):
        """
        Initialize the advanced memory manager.
        
        Args:
            user_id: User identifier
            firestore_client: Optional Firestore client (None for in-memory mode)
        """
        self.user_id = user_id
        self.firestore_client = firestore_client
        
        # Core components
        self.detector = CommitmentDetector()
        self.scorer = SalienceScorer()
        self.segmenter = EventSegmenter()
        self.metrics = MemoryMetrics()
        
        # In-memory caches (for performance)
        self.events_cache: List[EventRecord] = []
        self.commitments_cache: List[Commitment] = []
        self.semantic_cache: List[SemanticFact] = []
        self.relationship_state = RelationshipState()
        
        # Session tracking
        self.session_turns: List[Dict] = []
        self.session_start = datetime.utcnow()
        
        # Load existing data
        self._load_from_firestore()
    
    def _load_from_firestore(self):
        """Load existing memories from Firestore."""
        if not self.firestore_client:
            logger.info("📦 Running in-memory mode (no Firestore)")
            return
        
        try:
            # Load events (last 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)
            events_ref = self.firestore_client.collection(f"users/{self.user_id}/memories/events")
            for doc in events_ref.stream():
                event_data = doc.to_dict()
                event = EventRecord.from_dict(event_data)
                if event.time_range[1] >= cutoff:
                    self.events_cache.append(event)
            
            # Load active commitments
            commitments_ref = self.firestore_client.collection(f"users/{self.user_id}/memories/commitments")
            for doc in commitments_ref.where("status", "==", "active").stream():
                commitment_data = doc.to_dict()
                commitment = Commitment.from_dict(commitment_data)
                self.commitments_cache.append(commitment)
            
            # Load semantic facts
            semantic_ref = self.firestore_client.collection(f"users/{self.user_id}/memories/semantic")
            for doc in semantic_ref.stream():
                fact_data = doc.to_dict()
                fact = SemanticFact.from_dict(fact_data)
                self.semantic_cache.append(fact)
            
            # Load relationship state
            relationship_ref = self.firestore_client.collection(f"users/{self.user_id}/memories").document("relationship_state")
            relationship_doc = relationship_ref.get()
            if relationship_doc.exists:
                self.relationship_state = RelationshipState.from_dict(relationship_doc.to_dict())
            
            logger.info(f"✅ Loaded: {len(self.events_cache)} events, {len(self.commitments_cache)} commitments, {len(self.semantic_cache)} facts")
        
        except Exception as e:
            logger.error(f"❌ Error loading from Firestore: {e}")
    
    def process_turn(
        self,
        user_message: str,
        pet_response: str,
        user_embedding: Optional[List[float]] = None,
        pet_embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Process a conversation turn with full memory analysis.
        
        Returns:
            Dictionary with detected patterns and updates
        """
        timestamp = datetime.utcnow()
        turn_data = {
            "user": user_message,
            "pet": pet_response,
            "timestamp": timestamp,
            "embedding": user_embedding
        }
        
        # Add to session
        self.session_turns.append(turn_data)
        
        # Detect commitments from pet
        commitment_desc = self.detector.detect_commitment(pet_response)
        if commitment_desc:
            self._create_commitment(commitment_desc, timestamp)
        
        # Detect user corrections
        correction = self.detector.detect_correction(user_message)
        if correction:
            self._handle_correction(correction, timestamp)
        
        # Detect open loops
        open_loop = self.detector.detect_open_loop(user_message)
        if open_loop:
            self._track_open_loop(open_loop, timestamp)
        
        # Check if segmentation is needed
        if self.segmenter.should_segment(user_embedding, timestamp):
            event = self.segmenter.create_event(
                event_id=str(uuid.uuid4()),
                summarizer_fn=None  # TODO: Add AI summarization
            )
            if event:
                self._save_event(event)
        
        # Add turn to segmenter
        self.segmenter.add_turn(user_message, pet_response, timestamp, user_embedding)
        
        # Update metrics
        self.metrics.record_turn(tokens_used=self._estimate_tokens(user_message + pet_response))
        
        return {
            "commitment_detected": commitment_desc is not None,
            "correction_detected": correction is not None,
            "open_loop_detected": open_loop is not None
        }
    
    def _create_commitment(self, desc: str, timestamp: datetime):
        """Create a new commitment with reactivation schedule."""
        commitment_id = str(uuid.uuid4())
        
        # Schedule reactivations: +1d, +3d, +7d, +30d
        reactivation_schedule = [
            timestamp + timedelta(days=1),
            timestamp + timedelta(days=3),
            timestamp + timedelta(days=7),
            timestamp + timedelta(days=30)
        ]
        
        commitment = Commitment(
            commitment_id=commitment_id,
            desc=desc,
            made_at=timestamp,
            status="active",
            reactivation_schedule=reactivation_schedule
        )
        
        self.commitments_cache.append(commitment)
        self.metrics.record_commitment_made()
        
        # Save to Firestore
        if self.firestore_client:
            ref = self.firestore_client.collection(f"users/{self.user_id}/memories/commitments").document(commitment_id)
            ref.set(commitment.to_dict())
        
        logger.info(f"🤝 Created commitment: {desc[:50]}...")
    
    def _handle_correction(self, correction: Tuple[str, str], timestamp: datetime):
        """Handle user correction with high importance."""
        correction_type, value = correction
        
        # Create semantic fact with high importance
        fact_id = str(uuid.uuid4())
        triple = ("user", correction_type, value)
        
        fact = SemanticFact(
            fact_id=fact_id,
            triple=triple,
            confidence=1.0,  # User corrections are definitive
            importance=0.95,  # Very high importance
            last_reinforced=timestamp
        )
        
        # Check if we need to update existing fact
        existing_fact = self._find_semantic_fact(triple[0], triple[1])
        if existing_fact:
            existing_fact.triple = triple
            existing_fact.confidence = 1.0
            existing_fact.importance = 0.95
            existing_fact.last_reinforced = timestamp
            logger.info(f"✏️ Updated fact: {triple}")
        else:
            self.semantic_cache.append(fact)
            logger.info(f"📝 New correction fact: {triple}")
        
        # Save to Firestore
        if self.firestore_client:
            ref = self.firestore_client.collection(f"users/{self.user_id}/memories/semantic").document(fact_id)
            ref.set(fact.to_dict())
    
    def _track_open_loop(self, description: str, timestamp: datetime):
        """Track an open loop (pending question/task)."""
        # Store in current event segment
        self.metrics.record_open_loop()
        logger.info(f"🔄 Tracking open loop: {description[:50]}...")
    
    def _find_semantic_fact(self, subject: str, relation: str) -> Optional[SemanticFact]:
        """Find an existing semantic fact by subject and relation."""
        for fact in self.semantic_cache:
            if fact.triple[0] == subject and fact.triple[1] == relation:
                return fact
        return None
    
    def _save_event(self, event: EventRecord):
        """Save event to cache and Firestore."""
        self.events_cache.append(event)
        
        # Keep only recent events in cache (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        self.events_cache = [e for e in self.events_cache if e.time_range[1] >= cutoff]
        
        if self.firestore_client:
            ref = self.firestore_client.collection(f"users/{self.user_id}/memories/events").document(event.event_id)
            ref.set(event.to_dict())
        
        logger.info(f"💾 Saved event: {event.title}")
    
    def retrieve_context(
        self,
        query: str,
        max_tokens: int = 1200,
        query_embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for prompt generation.
        
        Uses hybrid retrieval (dense + BM25) with type-based ranking:
        C&C > Semantic Facts > Events
        
        Returns:
            Dictionary with structured context
        """
        context = {
            "commitments": [],
            "semantic_facts": [],
            "recent_events": [],
            "relationship_state": self.relationship_state.to_dict(),
            "estimated_tokens": 0
        }
        
        token_budget = max_tokens
        
        # 1. Always include active commitments (highest priority)
        active_commitments = [c for c in self.commitments_cache if c.status == "active"]
        for commitment in active_commitments[:5]:  # Top 5 commitments
            commitment_str = f"Compromisso: {commitment.desc}"
            tokens = self._estimate_tokens(commitment_str)
            if token_budget - tokens > 0:
                context["commitments"].append(commitment_str)
                token_budget -= tokens
        
        # 2. Retrieve relevant semantic facts
        relevant_facts = self._retrieve_semantic_facts(query, query_embedding, top_k=10)
        for fact in relevant_facts:
            fact_str = f"{fact.triple[0]} {fact.triple[1]} {fact.triple[2]}"
            tokens = self._estimate_tokens(fact_str)
            if token_budget - tokens > 0:
                context["semantic_facts"].append(fact_str)
                token_budget -= tokens
        
        # 3. Retrieve relevant events (last resort)
        relevant_events = self._retrieve_events(query, query_embedding, top_k=3)
        for event in relevant_events[:2]:  # Maximum 2 events
            event_str = f"Evento: {event.title} - {event.summary}"
            tokens = self._estimate_tokens(event_str)
            if token_budget - tokens > 0:
                context["recent_events"].append(event_str)
                token_budget -= tokens
        
        context["estimated_tokens"] = max_tokens - token_budget
        
        logger.info(f"🔍 Retrieved context: {len(context['commitments'])} commitments, "
                   f"{len(context['semantic_facts'])} facts, {len(context['recent_events'])} events "
                   f"(~{context['estimated_tokens']} tokens)")
        
        return context
    
    def _retrieve_semantic_facts(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        top_k: int = 10
    ) -> List[SemanticFact]:
        """
        Retrieve semantic facts using hybrid search.
        """
        if not self.semantic_cache:
            return []
        
        # Score facts by importance and recency
        scored_facts = []
        for fact in self.semantic_cache:
            # Base score: importance
            score = fact.importance
            
            # Recency boost
            hours_ago = (datetime.utcnow() - fact.last_reinforced).total_seconds() / 3600.0
            recency_boost = math.exp(-hours_ago / (24.0 * 7))  # 1 week half-life
            score += recency_boost * 0.3
            
            # BM25-like text matching
            query_lower = query.lower()
            fact_text = f"{fact.triple[0]} {fact.triple[1]} {fact.triple[2]}".lower()
            if any(word in fact_text for word in query_lower.split()):
                score += 0.4
            
            # Embedding similarity (if available)
            if query_embedding and fact.embeddings:
                similarity = self._cosine_similarity(query_embedding, fact.embeddings)
                score += similarity * 0.3
            
            scored_facts.append((score, fact))
        
        # Sort by score and return top k
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return [fact for score, fact in scored_facts[:top_k]]
    
    def _retrieve_events(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        top_k: int = 5
    ) -> List[EventRecord]:
        """
        Retrieve events using hybrid search with salience weighting.
        """
        if not self.events_cache:
            return []
        
        # Recent events first (last 14 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=14)
        recent_events = [e for e in self.events_cache if e.time_range[1] >= recent_cutoff]
        
        if not recent_events:
            recent_events = self.events_cache[-10:]  # Last 10 events
        
        # Score events
        scored_events = []
        for event in recent_events:
            # Base score: salience
            score = event.salience
            
            # Recency boost
            hours_ago = (datetime.utcnow() - event.time_range[1]).total_seconds() / 3600.0
            recency_boost = math.exp(-hours_ago / (24.0 * 3))  # 3 day half-life
            score += recency_boost * 0.4
            
            # Text matching
            query_lower = query.lower()
            event_text = f"{event.title} {event.summary}".lower()
            if any(word in event_text for word in query_lower.split()):
                score += 0.3
            
            # Embedding similarity
            if query_embedding and event.embeddings:
                similarity = self._cosine_similarity(query_embedding, event.embeddings)
                score += similarity * 0.3
            
            scored_events.append((score, event))
        
        # Sort and return top k
        scored_events.sort(key=lambda x: x[0], reverse=True)
        return [event for score, event in scored_events[:top_k]]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 chars)."""
        return len(text) // 4
    
    def consolidate_session(self) -> Dict[str, Any]:
        """
        Run end-of-session reflection and consolidation.
        
        Returns:
            Summary of consolidation results
        """
        if not self.session_turns:
            return {"events_created": 0, "facts_promoted": 0, "commitments_updated": 0}
        
        logger.info(f"🔄 Starting session consolidation: {len(self.session_turns)} turns")
        
        # Force segmentation of remaining turns
        if self.segmenter.current_turns:
            event = self.segmenter.create_event(
                event_id=str(uuid.uuid4()),
                summarizer_fn=None
            )
            if event:
                # Calculate salience
                event.salience = self.scorer.calculate_salience(
                    timestamp=event.time_range[1],
                    repetition_count=1,
                    is_novel=True,
                    emotion_intensity=sum(event.emotions.values()) / max(len(event.emotions), 1) if event.emotions else 0.0,
                    is_explicit=len(event.pet_commitments) > 0 or len(event.user_facts) > 0
                )
                self._save_event(event)
        
        # Check for commitments due for reactivation
        now = datetime.utcnow()
        for commitment in self.commitments_cache:
            if commitment.status == "active" and commitment.reactivation_schedule:
                next_check = commitment.reactivation_schedule[0]
                if next_check <= now:
                    logger.info(f"⏰ Commitment due for reactivation: {commitment.desc[:50]}...")
                    # Remove the past date
                    commitment.reactivation_schedule = commitment.reactivation_schedule[1:]
        
        # Clear session
        results = {
            "events_created": len(self.events_cache),
            "facts_promoted": len(self.semantic_cache),
            "commitments_updated": len([c for c in self.commitments_cache if c.status == "active"])
        }
        
        self.session_turns = []
        self.session_start = datetime.utcnow()
        
        logger.info(f"✅ Session consolidated: {results}")
        return results
    
    def generate_daily_digest(self, date: Optional[str] = None) -> DailyDigest:
        """
        Generate a daily digest card.
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
        
        Returns:
            DailyDigest object
        """
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Get events from today
        target_date = datetime.fromisoformat(date)
        today_events = [
            e for e in self.events_cache
            if e.time_range[0].date() == target_date.date()
        ]
        
        # Summarize events
        event_summaries = [e.summary for e in today_events]
        daily_card = " | ".join(event_summaries[:3]) if event_summaries else "Nenhum evento hoje"
        
        # Collect new facts
        new_facts = [
            f"{f.triple[0]} {f.triple[1]} {f.triple[2]}"
            for f in self.semantic_cache
            if f.last_reinforced.date() == target_date.date()
        ]
        
        # Active commitments
        active_commitments = [
            f"{c.desc} (até {c.due.strftime('%d/%m')})" if c.due else c.desc
            for c in self.commitments_cache
            if c.status == "active"
        ]
        
        # Open topics (from recent events)
        open_topics = []
        for event in today_events:
            open_topics.extend([loop["desc"] for loop in event.open_loops if loop.get("status") == "open"])
        
        digest = DailyDigest(
            date=date,
            daily_card=daily_card[:700],  # Enforce max length
            new_facts=new_facts[:10],
            active_commitments=active_commitments[:5],
            open_topics=open_topics[:5],
            next_step="Continuar conversação" if today_events else "Iniciar nova conversa"
        )
        
        # Save to Firestore
        if self.firestore_client:
            ref = self.firestore_client.collection(f"users/{self.user_id}/memories/digests").document(date)
            ref.set(digest.to_dict())
        
        logger.info(f"📅 Generated daily digest for {date}")
        return digest
    
    def mark_commitment_done(self, commitment_id: str):
        """Mark a commitment as fulfilled."""
        for commitment in self.commitments_cache:
            if commitment.commitment_id == commitment_id:
                commitment.status = "done"
                self.metrics.record_commitment_fulfilled()
                
                # Update in Firestore
                if self.firestore_client:
                    ref = self.firestore_client.collection(f"users/{self.user_id}/memories/commitments").document(commitment_id)
                    ref.update({"status": "done"})
                
                logger.info(f"✅ Marked commitment as done: {commitment.desc[:50]}...")
                break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return self.metrics.to_dict()
