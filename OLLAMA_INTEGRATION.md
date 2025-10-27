# Ollama Integration Guide

This guide explains how the Tamagotchi Virtual Pet project integrates **Llama 3.2-3B Instruct** via **Ollama** for local, privacy-focused language generation.

## Overview

The integration replaces external API calls (Google Gemini) with a local LLM running in Docker via Ollama, providing:

- **Privacy**: All inference happens locally, no data sent to external services
- **Control**: Fine-tuned prompt engineering with memory-guided context
- **Consistency**: Self-Consistency Guard (SCG) ensures responses align with pet's identity
- **Observability**: Comprehensive telemetry for monitoring and optimization

## Architecture

### Components

1. **Ollama Service** (`docker-compose.yml`)
   - Runs `ollama/ollama:latest` container
   - Serves Llama 3.2-3B model on port 11434
   - Persists models in Docker volume

2. **OllamaClient** (`ollama_client.py`)
   - Python client for Ollama API
   - Handles generation requests with configurable parameters
   - Tracks latency, tokens, and errors

3. **MemoryRetriever** (`memory_retriever.py`)
   - Retrieves context from pet memory with priority order:
     1. PET-CANON (identity)
     2. C&C (commitments & claims)
     3. Semantic facts (user knowledge)
     4. Episodic events (recent interactions)
     5. Echo-Trace (successful speech patterns)
   - Token budget management (~1000 tokens)
   - Assembles prompts for generation

4. **Self-Consistency Guard** (`self_consistency_guard.py`)
   - Validates responses before sending
   - Detects contradictions with ABM/PET-CANON
   - Auto-corrects high-severity issues

5. **Telemetry** (`telemetry.py`)
   - Tracks key metrics:
     - Latency (p50/p95)
     - Token counts (input/output)
     - Self-consistency rate
     - Commitment resolution rate

## Setup

### 1. Docker Compose

The Ollama service is defined in `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: tamagotchi-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2. Initialize Ollama

After starting Docker Compose, initialize the model:

```bash
# Start services
docker compose up -d

# Wait for Ollama to be ready
docker compose logs -f ollama

# Run initialization script
./init-ollama.sh
```

Or manually:

```bash
docker exec tamagotchi-ollama ollama pull llama3.2:3b
```

### 3. Configure Backend

Set the Ollama base URL in `.env`:

```bash
OLLAMA_BASE_URL=http://ollama:11434
```

### 4. Start the Backend

```bash
docker compose up -d tamagotchi
```

## Usage

### Generate Response

The integration is transparent - existing code automatically uses Ollama:

```python
from tamagotchi.virtual_pet import VirtualPet

pet = VirtualPet()
pet.user_message("Olá, como você está?")
response = pet.pet_response()  # Uses Ollama with memory context
```

### Access Metrics

Metrics are exposed via HTTP endpoints:

```bash
# Get metrics summary
curl http://localhost:8080/metrics

# Get detailed report
curl http://localhost:8080/metrics/report

# Get recent N turns
curl http://localhost:8080/metrics/report?recent=10
```

### Manual Ollama Call

Use `OllamaClient` directly:

```python
from tamagotchi.ollama_client import get_ollama_client

ollama = get_ollama_client()
if ollama:
    text, metadata = ollama.generate(
        prompt="Tell me a joke",
        temperature=0.7,
        top_p=0.9,
        max_tokens=512
    )
    
    print(f"Response: {text}")
    print(f"Latency: {metadata['latency_ms']:.0f}ms")
    print(f"Tokens: {metadata['tokens_in']}→{metadata['tokens_out']}")
```

## Memory-Guided Prompts

The system builds prompts using a priority-based memory retrieval:

### Priority Order

1. **PET-CANON** (5-10 sentences)
   - Who the pet is
   - Capabilities and limits
   - Communication style
   - Core principles

2. **C&C** (Commitments & Claims)
   - Active promises
   - Persona commitments
   - Interaction commitments

3. **Semantic Facts** (3-5 facts)
   - Highest importance user facts
   - Learned preferences
   - User attributes

4. **Episodic Event** (1 event)
   - Most recent or relevant interaction
   - Contextual information

5. **Echo-Trace** (1 pattern)
   - Successful speech pattern
   - Tone/style guidance

### Token Budget

Total context limited to ~1000 tokens to ensure:
- Fast inference
- Focused context
- Cost efficiency
- Quality responses

### Example Prompt

```
INSTRUÇÃO: Você é um pet virtual orgânico com memória e personalidade únicas.

IDENTIDADE (PET-CANON):
Sou um pet virtual amigável. Eu posso conversar e aprender sobre você.
Eu não posso acessar internet ou fazer ligações.

COMPROMISSOS ATIVOS:
  1. Prometi lembrar o usuário de ligar para a mãe amanhã

FATOS IMPORTANTES SOBRE O USUÁRIO:
  - Nome: João
  - Gosta de música
  - Trabalha como desenvolvedor

CONTEXTO RECENTE:
  episode: usuário perguntou sobre agenda

MENSAGEM DO USUÁRIO:
O que eu preciso fazer hoje?

RESPOSTA:
```

## Self-Consistency Guard

The SCG validates responses before sending:

### Checks Performed

1. **Capability Contradictions**
   - Ensures pet doesn't claim abilities it doesn't have
   - Validates against ABM C-PET items

2. **Policy Violations**
   - Checks against POLICY items
   - Ensures pet doesn't violate established boundaries

3. **Broken Commitments**
   - Validates C&C-PERSONA commitments
   - Ensures promises are acknowledged

4. **Tone Consistency**
   - Compares against VOICE items
   - Validates formality/informality

### Auto-Correction

High-severity issues (≥0.8) trigger auto-correction:

```
Corrigindo: na verdade, não posso ver em tempo real. [original response]
```

## Telemetry

### Collected Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Latency (p50) | Median response time | <2000ms |
| Latency (p95) | 95th percentile response time | <5000ms |
| Tokens/turn | Average tokens per interaction | Stable or decreasing |
| Consistency rate | % responses passing SCG | ≥95% |
| Commitment resolution | % commitments fulfilled | ≥80% |

### Viewing Metrics

```bash
# Summary JSON
curl http://localhost:8080/metrics

{
  "status": "ok",
  "metrics": {
    "total_turns": 42,
    "latency_p50_ms": 1834,
    "latency_p95_ms": 4221,
    "avg_tokens_in": 243.5,
    "avg_tokens_out": 87.3,
    "consistency_rate_pct": 97.6,
    "commitment_resolution_rate_pct": 85.0
  }
}
```

```bash
# Detailed report
curl http://localhost:8080/metrics/report

============================================================
TELEMETRY REPORT
============================================================
Total turns: 42

LATENCY METRICS:
  p50: 1834 ms
  p95: 4221 ms
  min: 891 ms
  max: 5103 ms
  avg: 1987 ms

TOKEN METRICS:
  Input tokens (avg):  243.5
  Output tokens (avg): 87.3
  Total tokens (avg):  330.8

CONSISTENCY METRICS:
  Consistency rate: 97.6%
  Passed: 41
  Failed: 1
============================================================
```

## Configuration

### Ollama Parameters

Edit `ollama_client.py` to adjust generation parameters:

```python
ollama.generate(
    prompt=prompt,
    temperature=0.7,  # Randomness (0.0-1.0)
    top_p=0.9,        # Nucleus sampling
    max_tokens=512    # Max output tokens
)
```

### Memory Budget

Edit `memory_retriever.py` to adjust token budget:

```python
retriever = MemoryRetriever(token_budget=1000)  # Adjust as needed
```

### SCG Thresholds

Edit `self_consistency_guard.py` for sensitivity:

```python
# Severity threshold for auto-correction
if top_issue.severity >= 0.8:  # Lower = more aggressive correction
    ...
```

## Troubleshooting

### Ollama Not Responding

```bash
# Check Ollama health
docker compose ps ollama
curl http://localhost:11434/api/tags

# View logs
docker compose logs ollama

# Restart
docker compose restart ollama
```

### Model Not Loaded

```bash
# Pull model manually
docker exec tamagotchi-ollama ollama pull llama3.2:3b

# Verify
docker exec tamagotchi-ollama ollama list
```

### Slow Responses

1. **Check system resources**: Ollama needs adequate CPU/RAM
2. **Reduce max_tokens**: Lower output length
3. **Simplify prompt**: Reduce context size
4. **Use GPU**: Enable GPU support in Docker (NVIDIA only)

### Fallback to Gemini

If Ollama fails, the system automatically falls back to Gemini API (if configured):

1. Ollama attempted first
2. If error, tries Gemini
3. If both fail, uses rule-based fallback

## Performance Tips

1. **Preload Model**: Run `init-ollama.sh` to load model at startup
2. **Optimize Context**: Keep token budget tight (800-1000 tokens)
3. **Cache Responses**: Consider caching for common queries
4. **Monitor Metrics**: Watch telemetry for degradation
5. **Batch Requests**: If possible, batch similar requests

## Testing

Run acceptance tests:

```bash
# Minimal tests (no dependencies)
python test_minimal_acceptance.py

# Full tests (requires all dependencies)
python test_acceptance.py
```

Expected: All tests pass (6/6 for minimal tests)

## Security Considerations

1. **No External Data**: All inference is local
2. **Input Validation**: Prompts are assembled safely
3. **Output Filtering**: SCG validates responses
4. **Rate Limiting**: Consider adding if exposed publicly
5. **Resource Limits**: Set Docker memory/CPU limits

## Next Steps

1. **Tune Parameters**: Adjust temperature/top_p for personality
2. **Optimize Prompts**: Refine memory retrieval order
3. **Add Caching**: Cache frequent queries
4. **Monitor Production**: Set up alerts on key metrics
5. **A/B Testing**: Compare Ollama vs Gemini responses

## References

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Llama 3.2 Model Card](https://ai.meta.com/llama/)
- [PET-CANON Specification](ABM_DOCUMENTATION.md)
- [Memory Architecture](IMPLEMENTATION_SUMMARY.md)
