# Organic Virtual Pet Project

Welcome to the Organic Virtual Pet project! This repository provides a fully
modular and well-structured implementation of an "organic" virtual pet
inspired by neuroscience and personality theory. The code serves as a
foundation for building a production-quality system that can power a
Tamagotchi-like experience via messaging platforms.

## 🎯 Quick Start

### Using Docker (Recommended)

```bash
# Start with Docker Compose
docker compose up -d

# Test the API
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "message": "Olá!"}'
```

See **[Docker Setup Guide](DOCKER.md)** for detailed instructions.

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the simulation
python -m tamagotchi.virtual_pet

# Start the API server
uvicorn tamagotchi.server:app --port 8080

# Test the API
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "message": "Olá!"}'
```

## 📚 Documentation

- **[Docker Setup Guide](DOCKER.md)** - Run the project with Docker and Docker Compose
- **[Ollama Integration Guide](OLLAMA_INTEGRATION.md)** - Local LLM with Llama 3.2-3B via Ollama
- **[Personality Engine Guide](PERSONALITY_ENGINE.md)** - Complete guide to the personality system
- **[Testing Guide](TESTING.md)** - Comprehensive testing instructions
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment to GCP
- **[Examples](EXAMPLES.md)** - Code examples and use cases

## ✨ Key Features

- **Unique Personalities**: Research-based personality engine using Big Five model
  - 8 predefined personality archetypes
  - Random unique personalities for each pet
  - Subtle personality evolution through interactions
- **Local LLM**: Llama 3.2-3B Instruct via Ollama for privacy-focused AI
  - Memory-guided prompts with PET-CANON/ABM/C&C context
  - Self-Consistency Guard for response validation
  - Comprehensive telemetry and metrics
- **Multimodal Chat**: Text and image processing
- **Evolving Personality**: Traits and drives that change with interactions
- **Hybrid Memory**: Episodic, semantic, and photographic memory
- **Natural Language**: Integration with Ollama (primary) and Google Gemini (fallback)
- **Image Recognition**: Google Cloud Vision for understanding images
- **Persistent Storage**: Firestore integration with in-memory fallback
- **MCP Integration**: AskIt-inspired client and Nerve-style configuration
- **Production Ready**: Dockerized with Cloud Run support

## Project Structure

This repository is organized into modular Python files that together
implement the core logic of the organic virtual pet, optional persistence
layers, and a production-ready HTTP server.

- **memory_store.py**: Defines the `MemoryStore` and `MemoryItem` classes for
  handling episodic and semantic memories.
- **personality_engine.py**: Implements the research-based personality system
  using the Big Five (OCEAN) model and temperament dimensions. Provides
  personality archetypes, behavior modulation, and personality evolution.
- **pet_state.py**: Implements the `PetState` class, which manages drives,
  traits, habits, personality, and memory interactions.
- **virtual_pet.py**: Provides the `VirtualPet` class that wraps a `PetState`
  instance and exposes methods for processing user messages and generating
  responses. When run directly, this module simulates a simple conversation
  for testing.
- **pet_server.py**: Contains simple stubs illustrating how the pet logic could
  be exposed as a server to handle incoming messages. It is kept for
  completeness but superseded by `server.py` for production use.
- **firestore_store.py**: Implements optional persistence using Google Cloud
  Firestore. When Firestore credentials are configured, pet states and
  memories (including personality) are stored per user; otherwise the module
  falls back to an in-memory dictionary.
- **server.py**: Implements a FastAPI server with a `/webhook` endpoint that
  processes incoming messages and returns the pet's response. The server
  integrates with `firestore_store.py` for persistence.
  The endpoint also accepts images (base64-encoded) to build photographic memory.
- **mcp_manifest.json**: Sample manifest describing the structure of MCP
  servers and their methods.
- **requirements.txt**: Lists project dependencies (`fastapi`, `uvicorn`,
  `google-cloud-firestore`, `pydantic`, and additional libraries for
  language generation and image recognition.

## Running a Simulation

To test the core logic, you can run the simulation provided in
`virtual_pet.py`. From the parent directory of the repository:

```bash
cd /path/to/parent/directory
python -m tamagotchi.virtual_pet
```

This will simulate a simple conversation between a user and the pet, showing
how drives, traits, and memory evolve over time.

**Note:** The project uses relative imports and must be run as a package.
If you cloned the repository, navigate to the parent directory and use the
`-m` flag with Python to execute modules.

## Running the API Server

To run the HTTP API locally, first install the dependencies:

```bash
pip install -r requirements.txt
```

If you want to enable Firestore persistence, set the environment variables
`GOOGLE_APPLICATION_CREDENTIALS` (pointing to your service account JSON) and
`USE_FIRESTORE=true`. Otherwise the server will store pet state in memory.

Start the server with Uvicorn from the parent directory:

```bash
cd /path/to/parent/directory
uvicorn tamagotchi.server:app --reload --port 8080
```

Then send a POST request to `http://localhost:8080/webhook` with a JSON body
containing `user_id` and `message`. The server returns a JSON response with
the pet's reply.

**Example using curl:**

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "message": "Olá, pet!"}'
```

To send an image instead of a text message, include an `image` field with a
base64-encoded string. The `message` field can be empty in this case. The
pet will analyze the image, store a compact representation, and generate
a reply based on the detected content. Example payload:

```json
{
  "user_id": "123",
  "message": "",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQE..."
}
```
The server decodes the image, extracts visual features, attempts to label
the image using the Vision API (if configured), and updates the pet's
photographic memory. The reply reflects this visual stimulus.

## Extending to Production

The provided code is designed to be deployable in a production environment.
Follow these steps to adapt it for your needs:

1. **Use the FastAPI server:** Deploy `server.py` instead of the simple
   stubs in `pet_server.py`. The FastAPI server exposes a `/webhook` endpoint
   that is compatible with messaging platform webhooks (e.g., WhatsApp
   Business Platform). The request body must include a `user_id` (string)
   and a `message` (string).

2. **Enable persistent storage:** Configure Google Cloud Firestore to persist
   pet states between requests. Create a Firestore database in your GCP
   project, download a service account key with Firestore access, and set
   environment variables:

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account.json
   export USE_FIRESTORE=true
   ```

   If these variables are not set, the server falls back to an in-memory
   dictionary. While fine for local testing, in-memory storage does not
   persist across sessions or scale horizontally.

3. **Deploy to Google Cloud Run:** Build a container using the provided
   `Dockerfile` (create one if not present) and deploy to Cloud Run. This
   managed service automatically scales with traffic and offers a generous
   free tier. Example commands:

   ```bash
   # Build and push the container image
   gcloud builds submit --tag gcr.io/your-project-id/organic-pet

   # Deploy to Cloud Run
   gcloud run deploy organic-pet \
     --image gcr.io/your-project-id/organic-pet \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars USE_FIRESTORE=true
   ```

4. **Integrate with your messaging platform:** Configure your platform (e.g.,
   WhatsApp Business API) to send incoming messages to your Cloud Run URL
   ending in `/webhook`. The server will handle the requests and return
   responses accordingly.

5. **Extend the MCP manifest:** If you wish to expose additional tools or

## Language Generation and Image Recognition

The latest version of this project introduces two major features:

1. **Natural Language Generation:** The pet can produce more varied and
   natural responses by leveraging generative AI models. The module
   `language_generation.py` wraps Google’s Generative AI (Gemini) API. If
   you set the environment variable `GOOGLE_API_KEY` (or `GENAI_API_KEY`)
   with a valid API key and install the `google-generativeai` package, the
   pet will call the API to generate replies. Otherwise it falls back to
   simple deterministic responses. You can customize the prompts in
   `virtual_pet.py` to fine-tune the tone and behavior.

2. **Photographic Memory:** When a user sends a base64-encoded image, the
   pet extracts a compact feature vector using OpenCV, optionally classifies
   it via the Google Cloud Vision API, and stores both the features and
   labels in its memory. This allows the pet to reference past images and
   recognize similarities. To enable label detection, set
   `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON key and
   install `google-cloud-vision`. Without these, the feature extraction
   still works but no labels are generated.

These capabilities mirror aspects of human cognition: generative models
approximate language production, while visual features and labels provide a
rudimentary “photographic” memory. Feel free to extend these modules with
more sophisticated embeddings or classifiers as your project evolves.

## MCP, AskIt and Nerve Integration

This repository now includes stubs and helpers inspired by the
[AskIt](https://github.com/johnrobinsn/askit) MCP client and the
[Nerve Agent Development Kit](https://github.com/evilsocket/nerve). While
the full third‑party packages cannot be installed in the current execution
environment, you can experiment with their concepts as follows:

### AskIt‐like MCP client

The new module `mcp_client.py` implements a minimal MCP client stub. It
loads an `mcp_config.json` file describing available servers and exposes
an asynchronous `call` method. In this stub, calls are dispatched to
methods on the in‑process `VirtualPet` instance rather than over the
network. This sets the stage for migrating to a real MCP client when
external dependencies are available. See the `mcp_config.json` file for
a sample configuration.

### Nerve‐style agent configuration

The file `agent_config.yaml` allows you to declare high‑level agent
attributes in YAML, similar to how Nerve defines agents. The
`VirtualPet` class now loads this configuration on startup. The
`system_prompt` field from the YAML is prepended to the conversational
context whenever the pet generates a reply, influencing its tone and
personality. Future extensions could interpret the `tasks` weights or
include additional fields to tweak behavior without touching code.
   integrate with other systems (e.g., analytics, compliance services),
   extend `mcp_manifest.json` and implement the corresponding endpoints in
   `server.py` or separate modules following the same pattern.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
│              (WhatsApp / Web / API Client)               │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Server                         │
│                   (server.py)                            │
└─────────┬───────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                  Virtual Pet Engine                      │
│                  (virtual_pet.py)                        │
│  ┌────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Pet State  │  │   Memory    │  │ Language Gen    │  │
│  │ (drives,   │  │  (episodic, │  │ (Gemini API/    │  │
│  │  traits)   │  │  semantic)  │  │  Fallback)      │  │
│  └────────────┘  └─────────────┘  └─────────────────┘  │
└─────────┬───────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│              Persistence & External APIs                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Firestore   │  │ Vision API   │  │  Gemini API  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Suggested Improvements

Based on the project analysis, here are recommended improvements:

### High Priority
1. **Add proper test suite** - Unit tests for all modules
2. **Enhance error handling** - Better error messages and recovery
3. **Add rate limiting** - Prevent API abuse
4. **Implement logging** - Structured logging for debugging

### Medium Priority
5. **Add authentication** - Secure the webhook endpoint
6. **Implement metrics** - Track usage and performance
7. **Add caching** - Reduce API calls and improve speed
8. **WhatsApp templates** - Pre-approved message templates

### Long Term
9. **Vector database** - Scalable semantic search (Qdrant, pgvector)
10. **A/B testing** - Test different personalities
11. **Multi-language** - Support languages beyond Portuguese
12. **Advanced NLP** - Sentiment analysis, intent detection

## Contributing

Contributions are welcome! Please read the documentation and ensure all tests pass before submitting a PR.

## License

This project is provided as-is for educational and commercial use.
