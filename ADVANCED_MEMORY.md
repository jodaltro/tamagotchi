# Advanced Memory System

## Overview

The Advanced Memory System provides a hierarchical, efficient memory architecture for the virtual pet that improves consistency, reduces token usage, and maintains conversation fluidity across topics.

## Key Features

### 1. Event Segmentation
- **Purpose**: Compress 3-10 conversation turns into cohesive EventRecords
- **Benefits**: Replace raw logs with structured summaries + metadata
- **Triggers**:
  - Topic change (embedding distance > threshold)
  - Time gap > 10 minutes
  - Maximum 10 turns reached

### 2. Commitments & Claims (C&C)
- **Purpose**: Track pet promises and user corrections
- **Detection Patterns**:
  - Pet commitments: "vou...", "posso te...", "prometo...", "sempre que X, farei Y"
  - User corrections: "na verdade...", "meu nome é...", "prefiro X"
  - Open loops: Questions, pending tasks
- **Lifecycle**: active → done/expired
- **Reactivation**: Spaced repetition (1d, 3d, 7d, 30d)

### 3. Hierarchical Consolidation
- **Session End**: Reflection pass to promote salient items
- **Daily Digest**: Summary card with new facts, active commitments, open topics
- **Weekly Digest**: Conditional generation for significant activity

### 4. Salience Scoring
Formula: `score = α·recency + β·repetition + γ·novelty + δ·emotion + ε·explicit`

Weights:
- α = 0.25 (recency)
- β = 0.15 (repetition)
- γ = 0.20 (novelty)
- δ = 0.15 (emotion)
- ε = 0.25 (explicit - highest priority for corrections and promises)

### 5. Hybrid Retrieval
- **Dense Search**: Embedding-based similarity (cosine)
- **Sparse Search**: BM25-like keyword matching
- **Ranking Priority**: C&C > Semantic Facts > Events
- **Token Budget**: ≤1200 tokens (configurable)

### 6. Metrics & Telemetry
Tracked metrics:
- **Commitment Resolution Rate**: Fulfilled / Created
- **Thread Closure Latency**: Average time to close open loops
- **Self-Consistency**: Contradictions per 100 turns
- **Recall Utility**: % of useful memory retrievals
- **Tokens per Turn**: Average token usage

## Data Models

### EventRecord
```python
{
    "event_id": str,
    "title": str,  # ≤80 chars
    "time_range": [datetime_start, datetime_end],
    "summary": str,  # 300-500 chars
    "entities": [str],  # Names, objects, topics
    "emotions": {emotion: intensity},
    "open_loops": [{"desc": str, "status": "open|closed"}],
    "pet_commitments": [{"desc": str, "due": datetime, "status": str}],
    "user_facts": [{"triple": [subj, rel, obj], "confidence": float}],
    "salience": float,  # 0-1
    "embeddings": [float]
}
```

### Commitment
```python
{
    "commitment_id": str,
    "desc": str,
    "made_at": datetime,
    "due": datetime | None,
    "status": "active|done|expired",
    "evidence_event_id": str,
    "reactivation_schedule": [datetime]
}
```

### SemanticFact
```python
{
    "fact_id": str,
    "triple": [subject, relation, object],
    "confidence": float,  # 0-1
    "importance": float,  # 0-1
    "last_reinforced": datetime,
    "source_event_ids": [str],
    "embeddings": [float]
}
```

### RelationshipState
```python
{
    "stage": "stranger|acquaintance|friend|close_friend",
    "pet_name": str | None,
    "topics_history": [str],
    "tone": str
}
```

### DailyDigest
```python
{
    "date": str,  # YYYY-MM-DD
    "daily_card": str,  # ≤700 tokens
    "new_facts": [str],
    "active_commitments": [str],
    "open_topics": [str],
    "next_step": str
}
```

## Firestore Collections

```
users/{user_id}/memories/
├── events/{event_id}
├── commitments/{commitment_id}
├── semantic/{fact_id}
├── digests/{date}
└── relationship_state (single document)
```

## Usage Examples

### Basic Usage with Enhanced Pet

```python
from tamagotchi.enhanced_virtual_pet import create_enhanced_pet

# Create pet with advanced memory
pet = create_enhanced_pet(user_id="user123")

# Process conversation
pet.user_message("Meu nome é Maria")
response = pet.pet_response()
print(response)

# Check active commitments
commitments = pet.get_active_commitments()
print(f"Active commitments: {commitments}")

# End session (triggers consolidation)
summary = pet.end_session()
print(f"Session summary: {summary}")

# Get daily digest
digest = pet.get_daily_digest()
print(f"Daily card: {digest.daily_card}")
print(f"New facts: {digest.new_facts}")
```

### Using HybridMemoryStore Directly

```python
from tamagotchi.memory_integration import create_hybrid_memory_store
from tamagotchi.firestore_store import get_firestore_client

# Create hybrid memory store
firestore = get_firestore_client()
memory = create_hybrid_memory_store(user_id="user123", firestore_client=firestore)

# Process conversation turn
result = memory.process_conversation_turn(
    user_message="Você pode me ajudar?",
    pet_response="Vou te ajudar amanhã!"
)
print(f"Commitment detected: {result['commitment_detected']}")

# Retrieve context for response
context = memory.get_context_for_response(
    query="ajudar",
    max_tokens=1200
)
print(f"Commitments: {context['commitments']}")
print(f"Facts: {context['semantic_facts']}")

# Get metrics
metrics = memory.get_metrics()
print(f"Metrics: {metrics}")
```

### Commitment Management

```python
# Get active commitments
commitments = pet.get_active_commitments()

# Mark commitment as done
pet.mark_commitment_done(commitment_id="abc-123")

# Check metrics
metrics = pet.get_memory_metrics()
print(f"Resolution rate: {metrics['commitment_resolution_rate']}")
```

## Configuration

### Salience Scorer Weights
```python
from tamagotchi.advanced_memory import SalienceScorer

scorer = SalienceScorer(
    alpha=0.25,   # recency
    beta=0.15,    # repetition
    gamma=0.20,   # novelty
    delta=0.15,   # emotion
    epsilon=0.25  # explicit
)
```

### Event Segmentation Thresholds
```python
from tamagotchi.advanced_memory import EventSegmenter

segmenter = EventSegmenter(
    topic_threshold=0.3,      # Cosine distance threshold
    time_gap_minutes=10.0     # Time gap for segmentation
)
```

### Context Retrieval Budget
```python
# Adjust token budget for context retrieval
context = memory.get_context_for_response(
    query="...",
    max_tokens=1500  # Increase from default 1200
)
```

## Migration from Legacy Memory

The `HybridMemoryStore` is backward compatible with the existing `MemoryStore`:

```python
# Old code (still works)
memory = MemoryStore()
memory.add_episode("Test episode", salience=0.7)
memory.consolidate()

# New code (enhanced features)
memory = HybridMemoryStore(user_id="user123")
memory.add_episode("Test episode", salience=0.7)  # Still works
memory.process_conversation_turn(...)  # New feature
memory.consolidate_session()  # Enhanced consolidation
```

## Performance Considerations

### Token Budget Management
- Default: 1200 tokens
- Priority order: C&C (always included) > Facts (10 max) > Events (2 max)
- Estimated tokens: ~4 characters per token

### Cache Size Limits
- Events: Last 30 days kept in cache
- Commitments: Active only
- Semantic facts: No limit (managed by importance decay)

### Firestore Queries
- Events: Query by time_range for recent events
- Commitments: Filter by status="active"
- Semantic facts: Load all (typically <1000)

## Testing

Run tests:
```bash
pytest test_advanced_memory.py -v
```

Test coverage:
- ✅ Data model serialization/deserialization
- ✅ Commitment detection (7 patterns)
- ✅ Correction detection (5 patterns)
- ✅ Open loop detection
- ✅ Salience scoring (all 5 factors)
- ✅ Event segmentation (time, topic, max turns)
- ✅ Metrics tracking (5 metrics)
- ✅ Hybrid retrieval (priority ranking)
- ✅ Integration with VirtualPet
- ✅ Backward compatibility

## Metrics Dashboard

Example metrics output:
```json
{
  "commitment_resolution_rate": 0.85,
  "thread_closure_latency_hours": 4.2,
  "self_consistency_per_100_turns": 0.5,
  "recall_utility": 0.92,
  "avg_tokens_per_turn": 987,
  "commitments_made": 20,
  "commitments_fulfilled": 17,
  "open_loops_active": 2,
  "turns_processed": 150
}
```

## Future Enhancements

Planned improvements:
- [ ] AI-powered event summarization (currently using simple concatenation)
- [ ] Embedding generation for semantic search
- [ ] Weekly digest generation
- [ ] Contradiction detection
- [ ] Entity extraction refinement
- [ ] Emotion intensity calculation
- [ ] Multi-modal memory (images, audio)

## References

This implementation is inspired by:
- Hierarchical Memory Systems in cognitive science
- Spaced Repetition algorithms (SM-2)
- BM25 information retrieval
- Reiss's 16 Basic Desires framework
- Production RAG systems

## License

Part of the Organic Virtual Pet project.
