# Enhanced Features Documentation

## Overview

This document describes the enhanced features implemented in the Tamagotchi Virtual Pet, including the expanded drive system, AI-driven memory with reinforcement learning, and advanced image memory capabilities.

## Expanded Drive System (18 Drives)

### Neuroscience-Based Drives

The pet now has **18 drives** inspired by neuroscience research, including Reiss's 16 Basic Desires, Drive Theory, and Panksepp's Affective Neuroscience systems.

#### Positive Drives (12)
These drives motivate positive behaviors and experiences:

1. **curiosity** - Desire to learn and explore new things
2. **affection** - Need for love and emotional connection
3. **order** - Need for organization and structure
4. **sociability** - Desire for social interaction
5. **autonomy** - Need for independence and self-direction
6. **humor** - Playfulness and desire for fun
7. **achievement** - Drive to accomplish goals and succeed
8. **power** - Desire for influence and control
9. **acceptance** - Need for approval and belonging
10. **idealism** - Desire for justice and fairness
11. **tranquility** - Need for peace and safety
12. **creativity** - Artistic and imaginative expression

#### Neutral Drives (2)
Basic needs that require balance:

13. **hunger** - Physical/metaphorical needs
14. **rest** - Need for downtime and recovery

#### Negative Drives (4)
**Important:** These drives start low and have safeguards to prevent extreme values.

15. **anxiety** - Worry and apprehension (lower is better)
16. **frustration** - Obstacles and setbacks (lower is better)
17. **loneliness** - Feeling isolated (lower is better)
18. **boredom** - Lack of stimulation (lower is better)

### Drive Dynamics

#### Initialization
- **Positive drives**: Initialize randomly between 0.3 and 0.7
- **Negative drives**: Initialize between 0.1 and 0.3 (kept low for safety)

#### Time-Based Changes
- **Positive drives** decay toward equilibrium (0.5) without interaction
- **Negative drives** slowly increase over time without interaction (but capped at 0.6)
- Personality traits modulate decay rates

#### Interaction Effects

**Reduces Negative Drives:**
- Any interaction: reduces loneliness (-0.15) and boredom (-0.10)
- Fast response: reduces anxiety (-0.05)
- Achievement words ("consegui", "venci"): reduces frustration (-0.10)
- Calm words ("calma", "paz"): reduces anxiety (-0.08)
- Social words ("amigos", "companhia"): reduces loneliness (-0.12)

**Increases Positive Drives:**
- Gratitude ("obrigado"): increases affection (+0.08) and acceptance (+0.05)
- Success ("consegui", "venci"): increases achievement (+0.10)
- Creative words ("criar", "arte"): increases creativity (+0.08)
- Calm words: increases tranquility (+0.10)
- Social words: increases sociability (+0.08)

### Example Drive Interactions

```python
from tamagotchi.pet_state import PetState

pet = PetState()

# Check initial drives
print(f"Anxiety: {pet.drives['anxiety']:.2f}")
print(f"Achievement: {pet.drives['achievement']:.2f}")

# User reports success
pet.update_from_interaction("Consegui terminar o projeto!", response_delay=5.0)

# Anxiety decreases, achievement increases
print(f"Anxiety after: {pet.drives['anxiety']:.2f}")
print(f"Achievement after: {pet.drives['achievement']:.2f}")
```

## Enhanced Memory System

### AI-Driven Importance Detection

The memory system now uses AI (Gemini) to analyze conversations and determine what information is important to remember.

#### Importance Scoring (0.0 - 1.0)

- **0.9-1.0**: Critical personal information (name, age, family, health)
- **0.7-0.9**: Important information (work, hobbies, preferences)
- **0.5-0.7**: Moderate information (opinions, experiences)
- **0.3-0.5**: Casual conversation
- **0.0-0.3**: Trivial messages

#### Automatic Fact Extraction

The AI automatically extracts structured facts from conversations:

```python
# User says: "Olá, meu nome é João e trabalho como engenheiro"
# AI extracts:
# - "nome: João" (importance: 0.95)
# - "profissão: engenheiro" (importance: 0.85)
```

### Memory Reinforcement Learning

The pet learns better through repetition, just like humans!

#### How It Works

1. **First mention**: Fact stored with initial importance
2. **Repetition**: Weight increases, access count increments
3. **More repetitions**: Stronger memory, resists decay better

```python
from tamagotchi.memory_store import MemoryStore

mem = MemoryStore()

# First time learning a fact
mem.semantic["nome: João"] = (0.9, datetime.now(), 1)

# User mentions name again - reinforcement!
mem.reinforce_memory("nome: João", boost=0.2)

# Weight increases: 0.9 → 1.0 (capped)
# Access count: 1 → 2
```

### Memory Decay (Forgetting)

Memories naturally decay over time, especially if not accessed:

#### Decay Factors

1. **Time**: Older memories decay faster
2. **Access frequency**: Rarely accessed memories decay faster
3. **Importance**: More important memories decay slower

```python
# Memory decay formula
decay_amount = decay_factor * access_factor * time_factor * 0.1

# Where:
# - access_factor = 1.0 / (1.0 + access_count * 0.2)
# - time_factor = min(1.0, hours_since_access / (24 * 30))
```

#### Forgetting Threshold

- Memories with weight < 0.1 are completely forgotten
- Decay is applied automatically every 24 hours during interactions

### Memory Structure

#### Episodic Memory
Short-term memories of recent events:
```python
class MemoryItem:
    kind: str                    # "episode"
    text: str                    # The memory content
    salience: float              # How notable (0.0-1.0)
    timestamp: datetime          # When it happened
    access_count: int            # How many times recalled
    last_accessed: datetime      # Last time accessed
    importance_score: float      # AI-determined importance
```

#### Semantic Memory
Long-term consolidated facts:
```python
semantic: Dict[str, Tuple[float, datetime, int]]
# Key: fact text
# Value: (weight, last_accessed, access_count)
```

## Advanced Image Memory

### AI-Powered Image Analysis

When you send an image, the pet uses Gemini Vision to:

1. **Generate detailed description** (2-3 sentences)
2. **Detect entities** with characteristics:
   - **People**: appearance, style, age, who they are
   - **Animals**: species, characteristics, owner, name
   - **Objects/Places**: what they are, relevance
3. **Determine importance** (0.0-1.0)
4. **Extract simple labels** (3-5 keywords)

### Image Memory Structure

```python
class ImageMemory:
    features: List[float]              # Visual features for similarity
    labels: List[str]                  # Simple labels
    timestamp: datetime                # When sent
    ai_description: str                # Detailed AI description
    detected_entities: Dict[str, str]  # Detected entities
    context: str                       # Conversation context
    importance_score: float            # How important
```

### Example Image Analysis

```python
# User sends cat photo with message: "Este é meu gato Miau"

# AI analyzes and stores:
{
    "description": "Um gato laranja de pelo curto, aparentemente filhote, olhando para a câmera",
    "entities": {
        "animal": "gato, laranja, pelo curto, jovem",
        "owner": "usuário",
        "name": "Miau"
    },
    "importance": 0.9,  # Pet photo = high importance
    "labels": ["cat", "orange", "pet", "young", "indoor"],
    "context": "Este é meu gato Miau"
}

# Also stores semantic fact:
# "tem pet: gato laranja chamado Miau"
```

### Image Memory Recall

The pet can recall and reference previous images:

```python
# Get recent image memories
image_memories = pet.state.memory.get_image_memories_with_context(top_k=5)

# Returns list of dicts with description, entities, context, etc.
for img in image_memories:
    print(f"Image: {img['description']}")
    print(f"Entities: {img['entities']}")
    print(f"When: {img['timestamp']}")
```

## Usage Examples

### Basic Interaction with Enhanced Features

```python
from tamagotchi.virtual_pet import VirtualPet

# Create pet
pet = VirtualPet()

# User introduces themselves
pet.user_message("Olá! Meu nome é Ana e trabalho como designer")

# AI analyzes importance and extracts facts:
# - "nome: Ana" (importance: 0.95)
# - "profissão: designer" (importance: 0.85)

# Get response
response = pet.pet_response()
print(response)  # Pet acknowledges and remembers

# Later conversation
pet.user_message("Consegui terminar meu projeto de design!")

# Pet remembers Ana is a designer and celebrates achievement
# Drives updated: achievement ↑, frustration ↓
```

### Image Interaction

```python
# User sends pet photo
with open("my_cat.jpg", "rb") as f:
    image_bytes = f.read()

pet.user_message("Este é meu gato, o Miau")
pet.user_image(image_bytes)

response = pet.pet_response()
# AI analyzes image and responds with:
# "Que fofo! O Miau é um gato laranja adorável. Ele parece bem jovem ainda!"

# Facts stored:
# - "imagem animal: gato, laranja, jovem, dono: usuário, nome: Miau"
# - Detailed description in image memory

# Later, if user sends another cat photo:
pet.user_image(another_cat_photo)
response = pet.pet_response()
# "Ah, é o Miau de novo? Ele cresceu um pouco desde a última foto!"
```

### Memory Reinforcement

```python
# First interaction
pet.user_message("Gosto de tocar piano")
# Fact stored: "gosta de: tocar piano" (weight: 0.8)

# User mentions again later
pet.user_message("Hoje pratiquei piano por duas horas")
# Fact reinforced: weight 0.8 → 0.95, access_count: 1 → 2

# Much later, fact not mentioned for weeks
# Automatic decay reduces weight slightly
# But because of high access count, decay is slower

# User mentions again after long time
pet.user_message("Voltei a tocar piano!")
# Fact reinforced again, shows pet remembers
```

### Drive-Based Responses

```python
# Pet with high curiosity asks questions
pet.state.drives['curiosity'] = 0.9
response = pet.pet_response()
# More likely to ask exploratory questions

# Pet with high anxiety after long silence
# (loneliness and anxiety increased over time)
pet.state.tick(minutes=1440)  # 24 hours
# anxiety: 0.2 → 0.4
# loneliness: 0.2 → 0.5

# Next interaction reduces negative drives
pet.user_message("Oi!")
# loneliness: 0.5 → 0.35
# anxiety: 0.4 → 0.35
```

## API Reference

### PetState

```python
class PetState:
    drives: Dict[str, float]          # 18 drives (0.0-1.0)
    memory: MemoryStore               # Enhanced memory
    personality: PersonalityEngine     # Personality system
    
    def tick(minutes: float) -> None:
        """Advance time, decay drives, negative drives increase"""
    
    def update_from_interaction(text: str, delay: float) -> None:
        """Process interaction, update drives and memory"""
```

### MemoryStore

```python
class MemoryStore:
    def add_episode(text: str, salience: float, importance_score: float):
        """Add memory with AI importance"""
    
    def consolidate(threshold: float):
        """Move important episodes to semantic memory"""
    
    def reinforce_memory(text: str, boost: float) -> bool:
        """Strengthen existing memory"""
    
    def apply_memory_decay(hours_elapsed: float):
        """Natural forgetting over time"""
    
    def get_semantic_facts(min_weight: float) -> List[str]:
        """Get facts above threshold"""
    
    def add_image_memory(features, labels, ai_description, 
                         entities, context, importance):
        """Store enhanced image memory"""
    
    def get_image_memories_with_context(top_k: int) -> List[Dict]:
        """Retrieve recent image memories with full context"""
```

### VirtualPet

```python
class VirtualPet:
    def user_message(text: str, delay: float = None):
        """Process text message with AI importance analysis"""
    
    def user_image(image_bytes: bytes, delay: float = None):
        """Process image with AI analysis and entity detection"""
    
    def pet_response() -> str:
        """Generate response considering drives, memory, personality"""
```

## Performance Considerations

### AI Analysis
- AI importance detection adds ~1-2 seconds per message
- Image analysis adds ~2-3 seconds per image
- Falls back gracefully if AI unavailable

### Memory
- Episodic memory capped at 100 items (automatic rollover)
- Semantic memory grows with facts but auto-decays
- Image memory stores only features + metadata (not full images)

### Optimization Tips
1. Set `GOOGLE_API_KEY` for AI features
2. Memory decay runs automatically every 24 hours
3. Consolidate memories periodically for best performance
4. Use `min_weight` parameter to filter semantic facts

## Configuration

### Environment Variables

```bash
# Required for AI features
export GOOGLE_API_KEY="your-gemini-api-key"

# Optional - For persistent storage across sessions
export USE_FIRESTORE="true"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

### Firestore Integration

The enhanced features work seamlessly with Firestore for persistent storage:

**What's Stored:**
- All 18 drives and their current values
- Enhanced semantic memory (with weight, timestamp, access_count)
- Image memories with AI descriptions and entities
- Personality profile and evolution

**Setup:**
1. Create a Firestore database in Google Cloud
2. Download service account credentials JSON
3. Set environment variables (see above)
4. Memory automatically persists after each interaction

**Note:** When Firestore is not configured, the system uses in-memory storage (data lost on restart).

### Customization

```python
# Adjust drive decay rates
pet.state.personality.calculate_drive_decay_rate("anxiety")

# Change consolidation threshold
pet.state.memory.consolidate(threshold=0.7)  # More selective

# Change decay cycle
pet.state.memory.apply_memory_decay(hours_elapsed=48)  # Twice a day
```

## Future Enhancements

Potential improvements:
- Vector embeddings for semantic similarity
- Emotion detection from text/images
- Multi-modal memory linking (text ↔ image)
- Proactive memory recall (pet initiates topics)
- Dream-like memory consolidation during "sleep"
