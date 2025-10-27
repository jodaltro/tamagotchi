"""
Advanced hierarchical memory system with event segmentation, commitments tracking,
and hybrid retrieval for improved pet consistency and reduced token usage.

This module implements:
- Event segmentation (EventSegmenter) with structured summaries
- Commitments & Claims (C&C) tracking
- Hierarchical consolidation (session, daily, weekly)
- Salience scoring policy
- Hybrid retrieval (dense + sparse BM25)
- Spaced repetition for selective reactivation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import logging
import re
import math

logger = logging.getLogger(__name__)


@dataclass
class EventRecord:
    """
    Segmented event record representing 3-10 conversation turns.
    Replaces raw logs with structured summary and metadata.
    """
    event_id: str
    title: str  # ≤80 chars, verb-based (e.g., "Combinamos treino matinal")
    time_range: Tuple[datetime, datetime]  # (start, end)
    summary: str  # 300-500 chars
    entities: List[str]  # Names, objects, topics
    emotions: Dict[str, float] = field(default_factory=dict)  # emotion -> intensity
    open_loops: List[Dict[str, str]] = field(default_factory=list)  # [{desc, status}]
    pet_commitments: List[Dict[str, Any]] = field(default_factory=list)  # [{desc, due, status}]
    user_facts: List[Dict[str, Any]] = field(default_factory=list)  # [{triple, confidence}]
    salience: float = 0.5  # 0-1
    embeddings: Optional[List[float]] = None  # Vector of summary
    
    def to_dict(self) -> Dict:
        """Serialize for Firestore storage."""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "time_range": [self.time_range[0].isoformat(), self.time_range[1].isoformat()],
            "summary": self.summary,
            "entities": self.entities,
            "emotions": self.emotions,
            "open_loops": self.open_loops,
            "pet_commitments": self.pet_commitments,
            "user_facts": self.user_facts,
            "salience": self.salience,
            "embeddings": self.embeddings or []
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EventRecord':
        """Deserialize from Firestore."""
        time_range = (
            datetime.fromisoformat(data["time_range"][0]),
            datetime.fromisoformat(data["time_range"][1])
        )
        return cls(
            event_id=data["event_id"],
            title=data["title"],
            time_range=time_range,
            summary=data["summary"],
            entities=data.get("entities", []),
            emotions=data.get("emotions", {}),
            open_loops=data.get("open_loops", []),
            pet_commitments=data.get("pet_commitments", []),
            user_facts=data.get("user_facts", []),
            salience=data.get("salience", 0.5),
            embeddings=data.get("embeddings")
        )


@dataclass
class Commitment:
    """
    Pet commitment or promise tracking.
    Supports spaced repetition for verification.
    """
    commitment_id: str
    desc: str
    made_at: datetime
    due: Optional[datetime] = None
    status: str = "active"  # active, done, expired
    evidence_event_id: Optional[str] = None
    reactivation_schedule: List[datetime] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Serialize for Firestore storage."""
        return {
            "commitment_id": self.commitment_id,
            "desc": self.desc,
            "made_at": self.made_at.isoformat(),
            "due": self.due.isoformat() if self.due else None,
            "status": self.status,
            "evidence_event_id": self.evidence_event_id,
            "reactivation_schedule": [d.isoformat() for d in self.reactivation_schedule]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Commitment':
        """Deserialize from Firestore."""
        return cls(
            commitment_id=data["commitment_id"],
            desc=data["desc"],
            made_at=datetime.fromisoformat(data["made_at"]),
            due=datetime.fromisoformat(data["due"]) if data.get("due") else None,
            status=data.get("status", "active"),
            evidence_event_id=data.get("evidence_event_id"),
            reactivation_schedule=[datetime.fromisoformat(d) for d in data.get("reactivation_schedule", [])]
        )


@dataclass
class SemanticFact:
    """
    Triple-based semantic fact with confidence tracking.
    """
    fact_id: str
    triple: Tuple[str, str, str]  # (subject, relation, object)
    confidence: float  # 0-1
    importance: float  # 0-1
    last_reinforced: datetime
    source_event_ids: List[str] = field(default_factory=list)
    embeddings: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        """Serialize for Firestore storage."""
        return {
            "fact_id": self.fact_id,
            "triple": list(self.triple),
            "confidence": self.confidence,
            "importance": self.importance,
            "last_reinforced": self.last_reinforced.isoformat(),
            "source_event_ids": self.source_event_ids,
            "embeddings": self.embeddings or []
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SemanticFact':
        """Deserialize from Firestore."""
        return cls(
            fact_id=data["fact_id"],
            triple=tuple(data["triple"]),
            confidence=data["confidence"],
            importance=data["importance"],
            last_reinforced=datetime.fromisoformat(data["last_reinforced"]),
            source_event_ids=data.get("source_event_ids", []),
            embeddings=data.get("embeddings")
        )


@dataclass
class RelationshipState:
    """
    Current relationship state between user and pet.
    """
    stage: str = "stranger"  # stranger, acquaintance, friend, close_friend
    pet_name: Optional[str] = None
    topics_history: List[str] = field(default_factory=list)
    tone: str = "neutral"
    
    def to_dict(self) -> Dict:
        """Serialize for Firestore storage."""
        return {
            "stage": self.stage,
            "pet_name": self.pet_name,
            "topics_history": self.topics_history,
            "tone": self.tone
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RelationshipState':
        """Deserialize from Firestore."""
        return cls(
            stage=data.get("stage", "stranger"),
            pet_name=data.get("pet_name"),
            topics_history=data.get("topics_history", []),
            tone=data.get("tone", "neutral")
        )


@dataclass
class DailyDigest:
    """
    Daily consolidated card with key information.
    """
    date: str  # YYYY-MM-DD
    daily_card: str  # ≤700 tokens summary
    new_facts: List[str] = field(default_factory=list)
    active_commitments: List[str] = field(default_factory=list)
    open_topics: List[str] = field(default_factory=list)
    next_step: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Serialize for Firestore storage."""
        return {
            "date": self.date,
            "daily_card": self.daily_card,
            "new_facts": self.new_facts,
            "active_commitments": self.active_commitments,
            "open_topics": self.open_topics,
            "next_step": self.next_step
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DailyDigest':
        """Deserialize from Firestore."""
        return cls(
            date=data["date"],
            daily_card=data["daily_card"],
            new_facts=data.get("new_facts", []),
            active_commitments=data.get("active_commitments", []),
            open_topics=data.get("open_topics", []),
            next_step=data.get("next_step")
        )


class CommitmentDetector:
    """
    Detects pet commitments and user corrections in conversation.
    """
    
    # Patterns for commitment detection
    COMMITMENT_PATTERNS = [
        r"vou\s+(?:te\s+)?(.+)",
        r"posso\s+(?:te\s+)?(.+)",
        r"a\s+partir\s+de\s+agora\s+(.+)",
        r"sempre\s+que\s+(.+),\s*(?:vou|farei)\s+(.+)",
        r"prometo\s+(.+)",
        r"vamos\s+(.+)",
    ]
    
    # Patterns for user corrections
    CORRECTION_PATTERNS = [
        r"na\s+verdade\s+(.+)",
        r"(?:meu|o)\s+nome\s+(?:é|eh)\s+(\w+)",
        r"prefiro\s+(.+)",
        r"não\s+gosto\s+(?:de\s+)?(.+)",
        r"(?:me\s+chamo|chamo-me)\s+(\w+)",
    ]
    
    # Patterns for open loops (questions/pending tasks)
    QUESTION_PATTERNS = [
        r"(.+)\?$",
        r"(?:poderia|pode|consegue)\s+(.+)",
        r"(?:você\s+)?(?:sabe|conhece)\s+(.+)",
    ]
    
    @staticmethod
    def detect_commitment(pet_message: str) -> Optional[str]:
        """
        Detect if pet made a commitment/promise.
        
        Returns:
            Commitment description or None
        """
        for pattern in CommitmentDetector.COMMITMENT_PATTERNS:
            match = re.search(pattern, pet_message.lower())
            if match:
                commitment = match.group(1) if match.lastindex >= 1 else match.group(0)
                logger.info(f"🤝 Detected commitment: {commitment}")
                return commitment.strip()
        return None
    
    @staticmethod
    def detect_correction(user_message: str) -> Optional[Tuple[str, str]]:
        """
        Detect user corrections/preferences.
        
        Returns:
            Tuple of (type, value) or None
            Examples: ("name", "João"), ("preference", "prefiro café")
        """
        for pattern in CommitmentDetector.CORRECTION_PATTERNS:
            match = re.search(pattern, user_message.lower())
            if match:
                if "nome" in pattern:
                    return ("name", match.group(1).strip())
                elif "prefiro" in pattern or "gosto" in pattern:
                    return ("preference", match.group(1).strip())
                else:
                    return ("correction", match.group(1).strip())
        return None
    
    @staticmethod
    def detect_open_loop(user_message: str) -> Optional[str]:
        """
        Detect open loops (unanswered questions, pending tasks).
        
        Returns:
            Description of open loop or None
        """
        for pattern in CommitmentDetector.QUESTION_PATTERNS:
            match = re.search(pattern, user_message)
            if match:
                question = match.group(0).strip()
                logger.info(f"🔄 Detected open loop: {question}")
                return question
        return None


class SalienceScorer:
    """
    Calculate salience scores based on multiple factors.
    
    score = α·recency + β·repetition + γ·novelty + δ·emotion + ε·explicit
    """
    
    def __init__(
        self,
        alpha: float = 0.25,  # recency weight
        beta: float = 0.15,   # repetition weight
        gamma: float = 0.2,   # novelty weight
        delta: float = 0.15,  # emotion weight
        epsilon: float = 0.25 # explicit weight
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.epsilon = epsilon
    
    def calculate_salience(
        self,
        timestamp: datetime,
        repetition_count: int,
        is_novel: bool,
        emotion_intensity: float,
        is_explicit: bool
    ) -> float:
        """
        Calculate salience score for an event or fact.
        
        Args:
            timestamp: When the event occurred
            repetition_count: Number of times reinforced
            is_novel: Whether this is new/unique information
            emotion_intensity: Emotional intensity (0-1)
            is_explicit: Whether explicitly marked important (corrections, promises)
        
        Returns:
            Salience score (0-1)
        """
        # Recency: exponential decay
        hours_ago = (datetime.utcnow() - timestamp).total_seconds() / 3600.0
        recency_score = math.exp(-hours_ago / 24.0)  # 24h half-life
        
        # Repetition: log scale (diminishing returns)
        repetition_score = min(1.0, math.log(1 + repetition_count) / math.log(10))
        
        # Novelty: binary
        novelty_score = 1.0 if is_novel else 0.0
        
        # Emotion: direct mapping
        emotion_score = min(1.0, emotion_intensity)
        
        # Explicit: binary, highest weight
        explicit_score = 1.0 if is_explicit else 0.0
        
        # Weighted sum
        salience = (
            self.alpha * recency_score +
            self.beta * repetition_score +
            self.gamma * novelty_score +
            self.delta * emotion_score +
            self.epsilon * explicit_score
        )
        
        return min(1.0, max(0.0, salience))


class EventSegmenter:
    """
    Segments conversation turns into cohesive EventRecords.
    
    Criteria for segmentation:
    - Topic change (embedding distance > threshold)
    - Time gap > 10 minutes
    - Intention change (planning → small talk)
    """
    
    def __init__(self, topic_threshold: float = 0.3, time_gap_minutes: float = 10.0):
        self.topic_threshold = topic_threshold
        self.time_gap_minutes = time_gap_minutes
        self.current_turns: List[Dict] = []
        self.last_embedding: Optional[List[float]] = None
        self.last_timestamp: Optional[datetime] = None
    
    def add_turn(self, user_msg: str, pet_msg: str, timestamp: datetime, embedding: Optional[List[float]] = None):
        """Add a conversation turn to the current segment."""
        self.current_turns.append({
            "user": user_msg,
            "pet": pet_msg,
            "timestamp": timestamp,
            "embedding": embedding
        })
        # Update tracking for segmentation decisions
        self.last_timestamp = timestamp
        if embedding:
            self.last_embedding = embedding
    
    def should_segment(self, new_embedding: Optional[List[float]], new_timestamp: datetime) -> bool:
        """
        Determine if current turns should be segmented into an event.
        
        Returns:
            True if segmentation should occur
        """
        # Not enough turns yet
        if len(self.current_turns) < 3:
            return False
        
        # Too many turns, force segmentation
        if len(self.current_turns) >= 10:
            return True
        
        # Time gap check
        if self.last_timestamp:
            time_gap = (new_timestamp - self.last_timestamp).total_seconds() / 60.0
            if time_gap > self.time_gap_minutes:
                logger.info(f"⏰ Segmenting due to time gap: {time_gap:.1f} minutes")
                return True
        
        # Topic change check (using embedding distance)
        if self.last_embedding and new_embedding:
            distance = self._cosine_distance(self.last_embedding, new_embedding)
            if distance > self.topic_threshold:
                logger.info(f"📊 Segmenting due to topic change: distance={distance:.3f}")
                return True
        
        return False
    
    def _cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine distance between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 1.0
        
        similarity = dot_product / (magnitude1 * magnitude2)
        return 1.0 - similarity
    
    def create_event(self, event_id: str, summarizer_fn=None) -> Optional[EventRecord]:
        """
        Create an EventRecord from current turns.
        
        Args:
            event_id: Unique ID for the event
            summarizer_fn: Optional function to generate AI summary
        
        Returns:
            EventRecord or None if no turns
        """
        if not self.current_turns:
            return None
        
        start_time = self.current_turns[0]["timestamp"]
        end_time = self.current_turns[-1]["timestamp"]
        
        # Generate summary (AI or simple concatenation)
        if summarizer_fn:
            summary_data = summarizer_fn(self.current_turns)
            title = summary_data.get("title", "Conversa")
            summary = summary_data.get("summary", "")
            entities = summary_data.get("entities", [])
            emotions = summary_data.get("emotions", {})
            open_loops = summary_data.get("open_loops", [])
            pet_commitments = summary_data.get("pet_commitments", [])
            user_facts = summary_data.get("user_facts", [])
            embeddings = summary_data.get("embeddings")
        else:
            # Fallback: simple summary
            title = f"Conversa ({len(self.current_turns)} turnos)"
            messages = [f"{t['user'][:50]}..." for t in self.current_turns[:3]]
            summary = " | ".join(messages)
            entities = []
            emotions = {}
            open_loops = []
            pet_commitments = []
            user_facts = []
            embeddings = None
        
        event = EventRecord(
            event_id=event_id,
            title=title[:80],  # Enforce max length
            time_range=(start_time, end_time),
            summary=summary[:500],  # Enforce max length
            entities=entities,
            emotions=emotions,
            open_loops=open_loops,
            pet_commitments=pet_commitments,
            user_facts=user_facts,
            embeddings=embeddings
        )
        
        # Clear current turns
        self.current_turns = []
        self.last_embedding = None
        self.last_timestamp = None
        
        logger.info(f"📦 Created event: {event.title}")
        return event


class MemoryMetrics:
    """
    Track metrics for memory system validation.
    """
    
    def __init__(self):
        self.commitments_made = 0
        self.commitments_fulfilled = 0
        self.open_loops_created = 0
        self.open_loops_closed = 0
        self.loop_closure_times: List[float] = []  # hours
        self.contradictions_detected = 0
        self.turns_processed = 0
        self.tokens_per_turn: List[int] = []
        self.recall_hits = 0
        self.recall_attempts = 0
    
    def record_commitment_made(self):
        """Record a new commitment."""
        self.commitments_made += 1
    
    def record_commitment_fulfilled(self):
        """Record a fulfilled commitment."""
        self.commitments_fulfilled += 1
    
    def record_open_loop(self):
        """Record a new open loop."""
        self.open_loops_created += 1
    
    def record_loop_closed(self, hours_to_close: float):
        """Record a closed loop."""
        self.open_loops_closed += 1
        self.loop_closure_times.append(hours_to_close)
    
    def record_contradiction(self):
        """Record a detected contradiction."""
        self.contradictions_detected += 1
    
    def record_turn(self, tokens_used: int):
        """Record a conversation turn."""
        self.turns_processed += 1
        self.tokens_per_turn.append(tokens_used)
    
    def record_recall(self, was_useful: bool):
        """Record a recall attempt."""
        self.recall_attempts += 1
        if was_useful:
            self.recall_hits += 1
    
    def get_commitment_resolution_rate(self) -> float:
        """Calculate commitment resolution rate."""
        if self.commitments_made == 0:
            return 0.0
        return self.commitments_fulfilled / self.commitments_made
    
    def get_thread_closure_latency(self) -> float:
        """Calculate average thread closure latency in hours."""
        if not self.loop_closure_times:
            return 0.0
        return sum(self.loop_closure_times) / len(self.loop_closure_times)
    
    def get_self_consistency_score(self) -> float:
        """Calculate self-consistency (contradictions per 100 turns)."""
        if self.turns_processed == 0:
            return 0.0
        return (self.contradictions_detected / self.turns_processed) * 100
    
    def get_recall_utility(self) -> float:
        """Calculate recall utility (% of useful recalls)."""
        if self.recall_attempts == 0:
            return 0.0
        return self.recall_hits / self.recall_attempts
    
    def get_avg_tokens_per_turn(self) -> float:
        """Calculate average tokens per turn."""
        if not self.tokens_per_turn:
            return 0.0
        return sum(self.tokens_per_turn) / len(self.tokens_per_turn)
    
    def to_dict(self) -> Dict:
        """Export metrics as dictionary."""
        return {
            "commitment_resolution_rate": self.get_commitment_resolution_rate(),
            "thread_closure_latency_hours": self.get_thread_closure_latency(),
            "self_consistency_per_100_turns": self.get_self_consistency_score(),
            "recall_utility": self.get_recall_utility(),
            "avg_tokens_per_turn": self.get_avg_tokens_per_turn(),
            "commitments_made": self.commitments_made,
            "commitments_fulfilled": self.commitments_fulfilled,
            "open_loops_active": self.open_loops_created - self.open_loops_closed,
            "turns_processed": self.turns_processed
        }
