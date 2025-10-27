# Quick Start: Advanced Memory System

## What is it?

The Advanced Memory System is a hierarchical, intelligent memory architecture that makes your pet:
- **More consistent**: Tracks promises and remembers what it said
- **More efficient**: Uses ≤1200 tokens instead of dumping all history
- **More contextual**: Retrieves only relevant memories for each conversation
- **More reliable**: Validates itself with 5 key metrics

## Key Features in 30 seconds

```python
from tamagotchi.enhanced_virtual_pet import create_enhanced_pet

# 1. Create enhanced pet (drop-in replacement for VirtualPet)
pet = create_enhanced_pet(user_id="user123")

# 2. Commitments are automatically tracked
pet.user_message("Can you remind me to buy milk?")
pet.pet_response()  # "I'll remind you!"
print(pet.get_active_commitments())  # ["remind you"]

# 3. User corrections get highest priority
pet.user_message("Actually, my name is Maria")
pet.pet_response()  # Stores with 95% importance

# 4. Context is intelligently retrieved (not dumped)
context = pet.get_enhanced_context("remind")
# Returns: commitments + relevant facts + recent events (≤1200 tokens)

# 5. End session to consolidate
summary = pet.end_session()
print(summary)  # {"events_created": 3, "facts_promoted": 5, ...}

# 6. Check metrics
metrics = pet.get_memory_metrics()
print(f"Commitment rate: {metrics['commitment_resolution_rate']:.0%}")
```

## Run the Demo

```bash
python tamagotchi/demo_advanced_memory.py
```

This demo shows:
1. ✅ Commitment tracking (promises + spaced repetition)
2. ✅ User correction detection (name, preferences)
3. ✅ Event segmentation (3-10 turns → structured summary)
4. ✅ Hybrid retrieval (dense + sparse search)
5. ✅ Salience scoring (5 factors)
6. ✅ Metrics tracking (5 metrics)
7. ✅ Daily digest generation

## Architecture Overview

```
User Message + Pet Response
           ↓
    AdvancedMemoryManager
           ↓
    ┌──────────────────────┐
    │ Pattern Detection    │
    │ - Commitments        │
    │ - Corrections        │
    │ - Open Loops         │
    └──────────────────────┘
           ↓
    ┌──────────────────────┐
    │ Event Segmentation   │
    │ (3-10 turns)         │
    └──────────────────────┘
           ↓
    ┌──────────────────────┐
    │ Salience Scoring     │
    │ (α·recency + β·rep   │
    │  + γ·novelty + ...)  │
    └──────────────────────┘
           ↓
    ┌──────────────────────┐
    │ Firestore Storage    │
    │ - events/            │
    │ - commitments/       │
    │ - semantic/          │
    │ - digests/           │
    └──────────────────────┘
           ↓
    When generating response:
    ┌──────────────────────┐
    │ Hybrid Retrieval     │
    │ C&C > Facts > Events │
    │ (≤1200 tokens)       │
    └──────────────────────┘
```

## Commitment Tracking

The system automatically detects when your pet makes a promise:

**Detected Patterns:**
- "vou..." → "I'll..."
- "posso te..." → "I can..."
- "prometo..." → "I promise..."
- "sempre que X, farei Y" → "whenever X, I'll do Y"

**Lifecycle:**
```
Promise made → active → [reactivation: 1d, 3d, 7d, 30d] → done/expired
```

**Example:**
```python
pet.user_message("Remind me tomorrow")
response = pet.pet_response()  # "I'll remind you tomorrow!"
# Automatically creates commitment with reactivation schedule

# Next day, commitment appears in context
commitments = pet.get_active_commitments()
# ["remind you tomorrow"]

# Mark as done
pet.mark_commitment_done(commitment_id)
```

## User Corrections

Corrections get **highest priority** (importance = 0.95):

**Detected Patterns:**
- "na verdade..." → "actually..."
- "meu nome é..." → "my name is..."
- "prefiro X" → "I prefer X"
- "não gosto de Y" → "I don't like Y"

**Example:**
```python
pet.user_message("My name is João")
# Stored as: ("user", "name", "joão") with confidence=1.0

pet.user_message("I prefer coffee")
# Stored as: ("user", "preference", "coffee") with importance=0.95
```

## Event Segmentation

Conversations are segmented into events based on:
1. **Topic change** (embedding distance > 0.3)
2. **Time gap** (> 10 minutes)
3. **Max turns** (10 turns)

Each event contains:
- Title (≤80 chars)
- Summary (300-500 chars)
- Entities, emotions, open loops
- Salience score

**Example:**
```
Turn 1-3: Discussing music
Turn 4-7: Discussing movies
          ↓
Event 1: "Conversa sobre música" (salience: 0.7)
Event 2: "Conversa sobre filmes" (salience: 0.6)
```

## Salience Scoring

Formula: `score = α·recency + β·repetition + γ·novelty + δ·emotion + ε·explicit`

**Weights:**
- α = 0.25 (recency: exponential decay)
- β = 0.15 (repetition: log scale)
- γ = 0.20 (novelty: binary)
- δ = 0.15 (emotion: intensity)
- ε = 0.25 (explicit: corrections/promises)

**Examples:**
- Recent casual: 0.37
- User correction: 0.55 (highest!)
- Novel info: 0.54
- Repeated emotional: 0.49

## Hybrid Retrieval

When generating a response, the system retrieves:

**Priority:**
1. **Commitments** (always included if active)
2. **Semantic Facts** (top 10 by importance + relevance)
3. **Events** (top 2 by salience + relevance)

**Search Methods:**
- **Dense**: Embedding cosine similarity
- **Sparse**: BM25-like keyword matching
- **Combined**: Weighted by type priority

**Token Budget:**
- Default: 1200 tokens
- Configurable per request
- Prevents context overflow

## Metrics

Track 5 key metrics:

```python
metrics = pet.get_memory_metrics()
```

**Output:**
```json
{
  "commitment_resolution_rate": 0.85,    // 85% of promises kept
  "thread_closure_latency_hours": 4.2,   // Avg time to answer questions
  "self_consistency_per_100_turns": 0.5, // Very few contradictions
  "recall_utility": 0.92,                // 92% of recalls were useful
  "avg_tokens_per_turn": 987             // Well under 1200 budget
}
```

## Daily Digest

End-of-day summary:

```python
digest = pet.get_daily_digest()
```

**Contains:**
- Daily card (≤700 tokens)
- New facts learned
- Active commitments
- Open topics
- Suggested next step

## Firestore Collections

```
users/{user_id}/memories/
├── events/{event_id}          # EventRecord
├── commitments/{commitment_id} # Commitment
├── semantic/{fact_id}         # SemanticFact
├── digests/{date}             # DailyDigest
└── relationship_state         # RelationshipState
```

**Each collection auto-saves** when using Firestore. Falls back to in-memory if Firestore not configured.

## Migration Path

**Option 1: Drop-in replacement**
```python
# Old
from tamagotchi.virtual_pet import VirtualPet
pet = VirtualPet()

# New
from tamagotchi.enhanced_virtual_pet import create_enhanced_pet
pet = create_enhanced_pet(user_id="user123")
# All existing methods still work!
```

**Option 2: Gradual adoption**
```python
from tamagotchi.memory_integration import HybridMemoryStore

# Use hybrid memory with existing PetState
state.memory = HybridMemoryStore(user_id, firestore_client)
# Legacy methods + new features
```

## Testing

```bash
# Run all tests
pytest test_advanced_memory.py -v

# Run specific test
pytest test_advanced_memory.py::TestCommitmentDetector -v

# Run with coverage
pytest test_advanced_memory.py --cov=tamagotchi --cov-report=html
```

**29 tests, all passing** ✅

## Complete Documentation

See **[ADVANCED_MEMORY.md](ADVANCED_MEMORY.md)** for:
- Complete API reference
- All data models
- Configuration options
- Performance tuning
- Advanced examples

## Support

For questions or issues:
1. Check [ADVANCED_MEMORY.md](ADVANCED_MEMORY.md)
2. Run the demo: `python tamagotchi/demo_advanced_memory.py`
3. Look at tests: `test_advanced_memory.py`
4. Open an issue on GitHub

---

**Happy memory building! 🧠✨**
