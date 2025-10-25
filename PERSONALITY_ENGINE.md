# Personality Engine Documentation

## Overview

The personality engine is a research-based system that gives each virtual pet a unique and coherent personality. It combines modern personality psychology with affective computing to create pets that behave consistently according to their individual traits.

## Theoretical Foundation

### Big Five Personality Model (OCEAN)

The personality engine is built on the **Big Five** (also known as OCEAN or Five-Factor Model), the most scientifically validated framework in personality psychology:

1. **Openness to Experience** (0.0 - 1.0)
   - High: Curious, creative, imaginative, prefers novelty
   - Low: Practical, traditional, prefers routine

2. **Conscientiousness** (0.0 - 1.0)
   - High: Organized, responsible, goal-oriented
   - Low: Spontaneous, flexible, carefree

3. **Extraversion** (0.0 - 1.0)
   - High: Sociable, energetic, assertive
   - Low: Reserved, independent, calm

4. **Agreeableness** (0.0 - 1.0)
   - High: Compassionate, cooperative, trusting
   - Low: Direct, competitive, skeptical

5. **Neuroticism** (0.0 - 1.0)
   - High: Emotionally reactive, anxious, sensitive
   - Low: Emotionally stable, calm, resilient

### Temperament Dimensions

Additional dimensions based on temperament theory:

- **Emotionality**: Intensity of emotional responses (0.0 - 1.0)
- **Activity**: Energy level and preference for action (0.0 - 1.0)
- **Sociability**: Desire for social interaction (0.0 - 1.0)
- **Adaptability**: Ease of adjusting to changes (0.0 - 1.0)

## Personality Archetypes

For ease of use, the engine provides 8 predefined personality archetypes:

### 1. Curious Explorer
- High openness and activity
- Loves learning and asking questions
- Adaptable and sociable
- **Use case**: Educational companion, learning buddy

### 2. Playful Companion
- Very high extraversion and agreeableness
- Energetic and fun-loving
- Low neuroticism (stable emotions)
- **Use case**: Entertainment, stress relief

### 3. Gentle Caregiver
- High agreeableness and conscientiousness
- Compassionate and nurturing
- Moderate emotionality
- **Use case**: Emotional support, mindfulness

### 4. Wise Observer
- High openness, low extraversion
- Thoughtful and insightful
- Emotionally stable
- **Use case**: Reflection, deep conversations

### 5. Energetic Enthusiast
- Very high extraversion and activity
- Enthusiastic about everything
- Adaptable and social
- **Use case**: Motivation, fitness companion

### 6. Calm Philosopher
- Low neuroticism and activity
- Peaceful and reflective
- High openness and conscientiousness
- **Use case**: Meditation, philosophical discussions

### 7. Artistic Dreamer
- Very high openness and emotionality
- Creative and imaginative
- Sensitive and expressive
- **Use case**: Creative projects, artistic discussions

### 8. Balanced Friend
- All dimensions moderate (0.5-0.7)
- Well-rounded personality
- Adaptable to various situations
- **Use case**: General companionship

## Configuration

### In agent_config.yaml

```yaml
agent:
  system_prompt: "Your system prompt here..."
  
  # Set a specific archetype
  personality_archetype: "curious_explorer"
  
  # OR set to null for random unique personality
  personality_archetype: null
```

Available archetype names:
- `curious_explorer`
- `playful_companion`
- `gentle_caregiver`
- `wise_observer`
- `energetic_enthusiast`
- `calm_philosopher`
- `artistic_dreamer`
- `balanced_friend`

### Programmatic Configuration

```python
from tamagotchi.virtual_pet import VirtualPet

# Create pet with specific archetype
pet = VirtualPet(personality_archetype="playful_companion")

# Create pet with random personality
pet = VirtualPet()

# Access personality description
description = pet.state.get_personality_description()
print(description)  # e.g., "Você tem uma personalidade única: você é muito sociável..."
```

## How Personality Affects Behavior

### 1. Action Selection

The personality engine modulates the utility of different actions:

- **High Openness** → Boosts "ask_question", "explore", "learn"
- **High Extraversion** → Boosts "express_affection", "tell_joke", "request_game"
- **High Agreeableness** → Boosts "express_affection", "help", "comfort"
- **High Conscientiousness** → Boosts "share_fact", "teach", "organize"
- **High Neuroticism** → Adds more variability to action selection

### 2. Response Style

Personality influences how responses are generated:

```python
style_modifiers = personality.get_response_style_modifiers()
# Returns:
{
    'expressiveness': 0.3-1.0,  # Based on emotionality
    'formality': 0.0-0.5,        # Based on conscientiousness
    'verbosity': 0.5-0.8,        # Based on openness
    'humor_level': 0.2-0.8,      # Based on extraversion & stability
    'warmth': 0.4-1.0,           # Based on agreeableness
    'energy': 0.3-1.0,           # Based on activity
    'curiosity': 0.3-1.0,        # Based on openness
}
```

### 3. Drive Dynamics

Personality affects how quickly drives decay:

- **Emotional Stability** (low neuroticism) → More stable drives (slower decay)
- **High Conscientiousness** → Order drive decays slower
- **High Activity** → Curiosity and sociability drives more dynamic

### 4. Personality Evolution

Personality can evolve slowly based on interactions (neuroplasticity):

- **Positive interactions** → Slightly increase agreeableness, extraversion; decrease neuroticism
- **Negative interactions** → Slightly increase neuroticism; decrease extraversion
- **Frequent interactions** → Increase adaptability

Changes are very small (learning rate = 0.002) to maintain personality stability while allowing subtle growth.

## Persistence

Personality profiles are automatically saved and restored with pet state:

```python
# When saving pet state
data = pet_state_to_dict(state)
# data includes 'personality_data' with all dimensions

# When loading pet state
state = dict_to_pet_state(data)
# personality is automatically restored
```

## API Reference

### PersonalityProfile

```python
from tamagotchi.personality_engine import PersonalityProfile, PersonalityArchetype

# Create balanced profile
profile = PersonalityProfile()

# Create from archetype
profile = PersonalityProfile.from_archetype(PersonalityArchetype.CURIOUS_EXPLORER)

# Create random profile
profile = PersonalityProfile.random_profile(variation=0.3)

# Evolve personality
profile.evolve('openness', 0.01)  # Slight increase

# Get emotional stability
stability = profile.get_emotional_stability()

# Serialize
data = profile.to_dict()
```

### PersonalityEngine

```python
from tamagotchi.personality_engine import PersonalityEngine, create_personality

# Create engine
engine = create_personality(archetype="playful_companion")

# Modulate action utilities
intentions = [("ask_question", 0.5), ("tell_joke", 0.6)]
modulated = engine.modulate_action_utilities(intentions)

# Get response style
style = engine.get_response_style_modifiers()

# Generate personality description
description = engine.generate_personality_prompt()

# Process interaction feedback
engine.process_interaction_feedback("positive", quality=0.9)

# Calculate drive decay rate
decay_rate = engine.calculate_drive_decay_rate("curiosity")

# Check if should initiate interaction
should_initiate = engine.should_initiate_interaction(hours_since_last=12.0)
```

## Research References

The personality engine is based on established research in psychology and affective computing:

1. **McCrae, R. R., & Costa, P. T. (2008).** The Five-Factor Theory of Personality. In O. P. John, R. W. Robins, & L. A. Pervin (Eds.), Handbook of personality: Theory and research (3rd ed., pp. 159-181). Guilford Press.

2. **Rothbart, M. K., & Bates, J. E. (2006).** Temperament. In N. Eisenberg, W. Damon, & R. M. Lerner (Eds.), Handbook of child psychology: Vol. 3. Social, emotional, and personality development (6th ed., pp. 99-166). Wiley.

3. **Bates, J. E. (1989).** Applications of temperament concepts. In G. A. Kohnstamm, J. E. Bates, & M. K. Rothbart (Eds.), Temperament in childhood (pp. 321-355). Wiley.

4. **Picard, R. W. (1997).** Affective Computing. MIT Press.

5. **Goldberg, L. R. (1993).** The structure of phenotypic personality traits. American Psychologist, 48(1), 26-34.

## Examples

### Example 1: Creating Pets with Different Personalities

```python
from tamagotchi.virtual_pet import VirtualPet

# Create a curious pet
curious_pet = VirtualPet(personality_archetype="curious_explorer")
curious_pet.user_message("Hello!")
response = curious_pet.pet_response()
# Likely to ask questions

# Create a playful pet
playful_pet = VirtualPet(personality_archetype="playful_companion")
playful_pet.user_message("Hello!")
response = playful_pet.pet_response()
# Likely to be energetic and fun

# Create a calm pet
calm_pet = VirtualPet(personality_archetype="calm_philosopher")
calm_pet.user_message("Hello!")
response = calm_pet.pet_response()
# Likely to be thoughtful and peaceful
```

### Example 2: Observing Personality Evolution

```python
from tamagotchi.virtual_pet import VirtualPet

pet = VirtualPet(personality_archetype="balanced_friend")

# Check initial personality
initial_desc = pet.state.get_personality_description()
print("Initial:", initial_desc)

# Simulate many positive interactions
for i in range(100):
    pet.user_message(f"Message {i}", delay=5.0)
    pet.pet_response()

# Check evolved personality
evolved_desc = pet.state.get_personality_description()
print("After 100 interactions:", evolved_desc)
# Personality may have become slightly more agreeable and extraverted
```

### Example 3: Using Personality in Custom Actions

```python
from tamagotchi.personality_engine import create_personality

engine = create_personality(archetype="artistic_dreamer")

# Get style modifiers for custom response generation
style = engine.get_response_style_modifiers()

if style['expressiveness'] > 0.7:
    print("This pet is very expressive!")

if style['curiosity'] > 0.7:
    print("This pet is very curious!")
```

## Best Practices

1. **Archetype Selection**: Choose archetypes that match your use case
   - Education: Curious Explorer or Wise Observer
   - Entertainment: Playful Companion or Energetic Enthusiast
   - Support: Gentle Caregiver or Calm Philosopher
   - Creativity: Artistic Dreamer

2. **Random Personalities**: For maximum uniqueness, use random personalities (set archetype to null)

3. **Personality Evolution**: Let personalities evolve naturally through interactions for more realistic behavior

4. **Consistency**: The same pet should maintain personality consistency across sessions due to persistence

5. **Testing**: Test different personality types to see which works best for your application

## Troubleshooting

**Q: Pet behavior seems inconsistent**
A: Check that personality is being properly saved and restored. Use `pet.state.get_personality_description()` to verify.

**Q: All pets seem similar**
A: Make sure you're using `personality_archetype: null` in config to get random personalities, or specify different archetypes for different pets.

**Q: Personality doesn't seem to affect responses**
A: The personality influences action selection and provides context to the language model. Make sure the language generation is working (check API keys if using external LLM).

**Q: How fast should personality evolve?**
A: Personality evolution is intentionally slow (learning rate = 0.002 per interaction). Expect subtle changes over hundreds of interactions, which is psychologically realistic.
