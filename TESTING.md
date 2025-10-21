# Testing Guide

This document provides comprehensive instructions for testing the Organic Virtual Pet project.

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Navigate to the parent directory of the cloned repository.

## Unit Testing

### Testing Core Components

Run individual component tests:

```bash
# Test memory store
python -c "from tamagotchi.memory_store import MemoryStore; m = MemoryStore(); m.add_episode('test', 0.5); print('MemoryStore OK')"

# Test pet state
python -c "from tamagotchi.pet_state import PetState; p = PetState(); print('PetState OK')"

# Test virtual pet
python -c "from tamagotchi.virtual_pet import VirtualPet; v = VirtualPet(); print('VirtualPet OK')"
```

### Running the Simulation

Test the full conversation simulation:

```bash
python -m tamagotchi.virtual_pet
```

Expected output: A simulated conversation showing the pet responding to various user inputs, followed by a JSON summary of the final state (drives, traits, habits, memories).

## Integration Testing

### Testing the HTTP API

1. Start the server:
```bash
uvicorn tamagotchi.server:app --port 8080
```

2. In another terminal, test the endpoints:

#### Health Check
```bash
curl http://localhost:8080/health
```
Expected: `{"status":"ok"}`

#### Text Message
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "message": "Olá, pet!"}'
```
Expected: JSON response with a `response` field containing the pet's reply.

#### Multiple Messages (Same User)
```bash
# First message
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "message": "Vamos ouvir música?"}'

# Second message - should remember context
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "message": "Gosto de rock!"}'
```

#### Image Upload (Base64)
```bash
# Create a test image (requires imagemagick or similar)
convert -size 100x100 xc:blue test.jpg
base64 test.jpg > test.b64

# Send image
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"user1\", \"message\": \"\", \"image\": \"data:image/jpeg;base64,$(cat test.b64)\"}"
```

## Testing with Environment Variables

### With Google Generative AI (Gemini)

Set your API key:
```bash
export GOOGLE_API_KEY="your-api-key-here"
uvicorn tamagotchi.server:app --port 8080
```

Test that responses use the Gemini API instead of fallback:
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "Conte uma piada"}'
```

### With Google Cloud Vision (Image Labels)

Set credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
uvicorn tamagotchi.server:app --port 8080
```

Send an image and verify it gets labeled:
```bash
# The response should reference image content if Vision API is working
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"test\", \"message\": \"\", \"image\": \"data:image/jpeg;base64,$(cat test.b64)\"}"
```

### With Firestore Persistence

Set credentials and enable Firestore:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export USE_FIRESTORE=true
uvicorn tamagotchi.server:app --port 8080
```

Test persistence:
1. Send a message
2. Stop the server
3. Restart the server
4. Send another message with the same user_id
5. The pet should remember the previous conversation

## Load Testing

For production readiness, test with multiple concurrent requests:

```bash
# Install apache bench if needed
sudo apt-get install apache2-utils

# Test with 100 requests, 10 concurrent
ab -n 100 -c 10 -p request.json -T application/json http://localhost:8080/webhook
```

Create `request.json`:
```json
{"user_id": "load_test_user", "message": "Teste de carga"}
```

## Docker Testing

Build and test the Docker container:

```bash
# Build image
docker build -t organic-pet:test .

# Run container
docker run -p 8080:8080 organic-pet:test

# Test from another terminal
curl http://localhost:8080/health
```

## Troubleshooting

### Import Errors

If you see `ImportError: attempted relative import with no known parent package`:
- Make sure you're running from the parent directory
- Use `python -m tamagotchi.module_name` instead of `python module_name.py`

### Port Already in Use

If port 8080 is busy:
```bash
# Kill existing process
pkill -f uvicorn

# Or use a different port
uvicorn tamagotchi.server:app --port 8081
```

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

## Expected Behavior

### Memory Evolution
- Episodic memories accumulate with each interaction
- Highly salient memories (salience >= 0.6) consolidate into semantic memory
- The pet should reference past interactions in responses

### Trait Changes
- Mentioning "música" or "music" increases the `musical` trait
- Mentioning "jogo" or "game" increases the `ludico` trait
- Fast responses increase `affection` and `sociability` drives

### Action Selection
- Actions are selected based on drives and traits
- Different times of day may prefer different actions (based on active hours)
- Responses should vary based on the selected action

## Automated Test Suite

For automated testing, you can create a test script. Example:

```python
#!/usr/bin/env python
import requests
import json

def test_health():
    r = requests.get("http://localhost:8080/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("✓ Health check passed")

def test_webhook():
    r = requests.post("http://localhost:8080/webhook",
                     json={"user_id": "test", "message": "Olá"})
    assert r.status_code == 200
    assert "response" in r.json()
    print("✓ Webhook test passed")

if __name__ == "__main__":
    test_health()
    test_webhook()
    print("\n✓ All tests passed!")
```

Run with:
```bash
python test_api.py
```
