# Autobiographical Memory (ABM) System

## Overview

The Autobiographical Memory (ABM) system enables the virtual pet to maintain a consistent persona by tracking what it has said about itself, its capabilities, communication style, principles, and commitments. This prevents contradictions and "persona drift" across conversations.

## Key Components

### 1. Autobiographical Memory (`autobiographical_memory.py`)

The core repository of the pet's self-knowledge, storing:

- **C-PET Claims**: Factual statements about itself ("posso te lembrar diariamente", "não tenho visão em tempo real")
- **VOICE**: Style and tone preferences ("responder curto", "usar emojis com moderação")
- **POLICY**: Principles and limits ("não dou conselho médico", "evito julgar")
- **TOOLS**: Declared capabilities and tools
- **C&C-PERSONA**: Interaction commitments ("sempre confirmo mudanças", "vou perguntar antes de agir")

**Key Features**:
- Automatic claim extraction from responses using pattern matching
- Claim reinforcement (repeated statements increase importance)
- Claim revision tracking (when the pet changes its mind)
- Concise storage (≤140 chars per item)

### 2. PET-CANON (`pet_canon.py`)

A consolidated, concise (5-10 sentences, ≤400 tokens) view of who the pet is. The canon is:

- **Derived from ABM**: Automatically generated from active ABM items
- **Prompt-First**: Always included at the top of the context for consistency
- **Updated Intelligently**: Only refreshed when significant changes occur
- **Versioned**: Tracks changes over time

The PET-CANON covers:
- Role and purpose
- Capabilities (what it can do)
- Limits (what it cannot/will not do)
- Communication style
- Core principles
- Interaction commitments

### 3. Echo-Trace (`echo_trace.py`)

Tracks successful speech patterns for maintaining natural, consistent communication:

- **Pattern Categories**: greeting, empathy, enthusiasm, question, confirmation, etc.
- **Success Tracking**: Patterns scored by effectiveness
- **Context-Aware**: Different patterns for different situations
- **Paraphrasing Material**: Stored for inspiration, not literal repetition

### 4. Self-Consistency Guard (`self_consistency_guard.py`)

Pre-response validation to prevent contradictions:

- **Contradiction Detection**: Checks claims against ABM
- **Policy Enforcement**: Validates against established principles
- **Commitment Tracking**: Ensures promises are kept
- **Auto-Correction**: High-severity issues trigger automatic fixes

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Message                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│               Virtual Pet Processing                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  1. Process Message (update drives, memory)      │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  2. Generate Response Context                    │  │
│  │     - Include PET-CANON first                    │  │
│  │     - Add C&C-PERSONA commitments                │  │
│  │     - Add user facts and recent memories         │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  3. Generate Draft Response (AI)                 │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  4. Self-Consistency Check (Optional)            │  │
│  │     - Detect contradictions                      │  │
│  │     - Auto-correct if needed                     │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  5. Process Response for ABM                     │  │
│  │     - Extract new claims                         │  │
│  │     - Extract echo patterns                      │  │
│  │     - Update canon if needed                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                  Response to User                        │
└─────────────────────────────────────────────────────────┘
```

## Integration with Existing System

### Memory Store

The ABM components are automatically initialized in `MemoryStore`:

```python
class MemoryStore:
    abm: Optional[AutobiographicalMemory] = None
    canon: Optional[PetCanon] = None
    echo: Optional[EchoTrace] = None
    
    def __post_init__(self):
        if self.abm is None:
            self.abm = AutobiographicalMemory()
        if self.canon is None:
            self.canon = PetCanon()
        if self.echo is None:
            self.echo = EchoTrace()
```

### Persistence

ABM components are automatically serialized to/from Firestore:

```python
# Serialization (in pet_state_to_dict)
data = {
    ...
    "abm": state.memory.abm.to_dict() if state.memory.abm else None,
    "canon": state.memory.canon.to_dict() if state.memory.canon else None,
    "echo": state.memory.echo.to_dict() if state.memory.echo else None,
}

# Deserialization (in dict_to_pet_state)
if "abm" in data:
    memory.abm = AutobiographicalMemory.from_dict(data["abm"])
if "canon" in data:
    memory.canon = PetCanon.from_dict(data["canon"])
if "echo" in data:
    memory.echo = EchoTrace.from_dict(data["echo"])
```

### Webhook Flow

The webhook automatically processes ABM after each interaction:

```python
@app.post("/webhook")
async def handle_webhook(req: WebhookRequest):
    # ... process message ...
    
    # Generate response (ABM extraction happens automatically)
    reply = pet.pet_response()
    
    # Periodic reflection pass (20% chance)
    if random.random() < 0.2:
        pet.reflection_pass()
    
    # Save state (ABM is persisted)
    save_pet_data(user_id, pet.state)
    
    return WebhookResponse(response=reply)
```

## Usage Examples

### Automatic Claim Extraction

When the pet says something about itself, claims are automatically extracted:

```python
# Pet's response
response = "Eu sou um pet virtual que pode te ajudar com lembretes. " \
           "Eu não posso acessar a internet em tempo real."

# After processing
pet._process_response_for_abm(response)

# ABM now contains:
# - [C-PET] "Eu sou um pet virtual que pode te ajudar com lembretes"
# - [C-PET] "Eu não posso acessar a internet em tempo real"
```

### Canon Generation

The canon is automatically updated from ABM:

```python
# Add claims to ABM
abm.add_claim("Sou um pet virtual amigável", ABMType.C_PET, event_id, 0.9)
abm.add_claim("Eu posso te ajudar com tarefas", ABMType.TOOLS, event_id, 0.8)
abm.add_claim("Eu não posso acessar a internet", ABMType.C_PET, event_id, 0.9)

# Update canon
canon.update_from_abm(abm)

# Canon text for prompt
canon_text = canon.to_prompt_text()
# Output: "Sou um pet virtual amigável Eu posso te ajudar com tarefas. 
#          Eu não posso acessar a internet."
```

### Consistency Checking

Before sending a response, check for contradictions:

```python
# Pet has claimed: "Eu posso te ajudar com lembretes"

# Draft response contradicts this
draft = "Eu não posso te ajudar com lembretes"

# Check consistency
corrected = pet.run_consistency_check(draft)

# Result: "Corrigindo: na verdade, Eu posso te ajudar com lembretes. 
#          Eu não posso te ajudar com lembretes"
```

### Manual ABM Management

You can also manually manage ABM items:

```python
# Add a specific claim
pet.state.memory.abm.add_claim(
    "Vou sempre confirmar antes de fazer mudanças",
    ABMType.C_AND_C_PERSONA,
    event_id="manual_commitment",
    importance=0.95,
    stability=0.95
)

# Revise a claim
pet.state.memory.abm.revise_claim(
    old_text="Respondo sempre de forma curta",
    new_text="Respondo de forma detalhada quando necessário",
    reason="Feedback do usuário",
    source_event_id="revision_event"
)

# Get active items by type
commitments = pet.state.memory.abm.get_active_items(
    ABMType.C_AND_C_PERSONA,
    min_importance=0.5
)
```

## Configuration

### Extraction Patterns

Claims are extracted using pattern matching. Current patterns:

**C-PET (Self-claims)**:
- "eu posso"
- "eu não posso"
- "não tenho acesso"
- "meu papel é"
- "sou um"

**C&C-PERSONA (Commitments)**:
- "vou sempre"
- "vou te"
- "sempre confirmo"
- "nunca vou"

**POLICY**:
- "não dou conselho"
- "não faço"
- "evito"

### Reflection Pass Triggers

The reflection pass (which updates the canon) runs:

1. **Automatically**: 20% chance after each webhook request
2. **Manually**: Call `pet.reflection_pass()`
3. **Conditionally**: When `canon.needs_update(abm)` returns `True`

### Canon Update Criteria

The canon updates when:

- High-importance items (>0.7) are added
- More than 5 new items accumulated
- Any items are revised

## Best Practices

### 1. Keep Claims Concise

All ABM items should be ≤140 characters. The system will automatically truncate longer claims.

### 2. Use Appropriate Types

- **C-PET**: Factual capabilities ("Eu posso", "Eu não posso")
- **VOICE**: Style preferences ("Falo de forma casual", "Evito jargões")
- **POLICY**: Principles ("Não dou conselhos médicos")
- **TOOLS**: Specific capabilities ("Posso criar lembretes")
- **C&C-PERSONA**: Behavioral commitments ("Sempre confirmo mudanças")

### 3. Set Appropriate Importance

- **0.9-1.0**: Critical identity items (core capabilities, strict limits)
- **0.7-0.9**: Important but not critical
- **0.4-0.7**: Useful context
- **<0.4**: May be pruned during consolidation

### 4. Monitor Consistency

Check the consistency guard stats periodically:

```python
scg = SelfConsistencyGuard()
# ... use for checking ...
stats = scg.get_stats()
# Returns: {"total_checks": N, "total_issues": M, "issue_rate": M/N}
```

### 5. Periodic Reflection

Run reflection passes periodically to keep the canon updated:

```python
# After every N interactions
if interaction_count % 10 == 0:
    pet.reflection_pass()
```

## Metrics

The system tracks:

- **Active ABM items**: Number of active claims per type
- **Canon version**: How many times the canon has been updated
- **Echo patterns**: Number of stored successful patterns
- **Consistency checks**: Number of checks performed
- **Issues detected**: Number of contradictions found
- **Auto-corrections**: Number of automatic fixes applied

Access these via:

```python
# ABM stats
active_items = pet.state.memory.abm.get_active_items()
print(f"Active ABM items: {len(active_items)}")

# Canon stats
print(f"Canon version: {pet.state.memory.canon.version}")

# SCG stats
stats = scg.get_stats()
print(f"Issue rate: {stats['issue_rate']:.2%}")
```

## Testing

Run the comprehensive test suite:

```bash
cd /home/runner/work/tamagotchi/tamagotchi
python test_abm.py
```

Tests cover:
1. ABM basic functionality (creation, reinforcement)
2. PET-CANON generation and updates
3. Echo-Trace pattern extraction
4. Self-Consistency Guard detection and correction
5. Persistence (serialization/deserialization)
6. VirtualPet integration

## Troubleshooting

### ABM Not Initializing

If ABM components are `None`, ensure you're using `MemoryStore()` which auto-initializes them:

```python
memory = MemoryStore()  # ABM auto-initialized
assert memory.abm is not None
assert memory.canon is not None
assert memory.echo is not None
```

### Claims Not Being Extracted

Check if your response contains the extraction patterns:

```python
# These will be extracted:
"Eu posso te ajudar"  ✅
"Não tenho acesso a dados externos"  ✅
"Vou sempre confirmar antes"  ✅

# These will NOT be extracted:
"Posso ajudar" (missing "eu")  ❌
"Você pode me ajudar" (not self-referential)  ❌
```

### Consistency Check Not Working

Ensure ABM has relevant claims:

```python
# Add the claim first
pet.state.memory.abm.add_claim(
    "Eu não posso acessar a internet",
    ABMType.C_PET,
    "event_id",
    importance=0.9
)

# Then contradictory responses will be detected
draft = "Eu posso acessar a internet"
corrected = pet.run_consistency_check(draft)
# Will be corrected
```

## Future Enhancements

Potential improvements:

1. **Semantic Similarity**: Use embeddings to detect contradictions beyond exact text matching
2. **Confidence Scoring**: Track confidence in claims based on reinforcement
3. **Temporal Decay**: Reduce importance of very old claims
4. **User Feedback**: Explicitly mark claims as correct/incorrect based on user feedback
5. **Dashboard**: Visual interface to view and manage ABM items
6. **A/B Testing**: Compare pet behavior with/without ABM

## References

- Problem Statement: Original specification (in Portuguese)
- Test Suite: `test_abm.py`
- Implementation: `autobiographical_memory.py`, `pet_canon.py`, `echo_trace.py`, `self_consistency_guard.py`
