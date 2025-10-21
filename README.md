# Organic Virtual Pet Project

Welcome to the Organic Virtual Pet project! This repository provides a fully
modular and well-structured implementation of an "organic" virtual pet
inspired by neuroscience and personality theory. The code serves as a
foundation for building a production-quality system that can power a
Tamagotchi-like experience via messaging platforms.

## Project Structure

This repository is organized into modular Python files that together
implement the core logic of the organic virtual pet, optional persistence
layers, and a production-ready HTTP server.

- **memory_store.py**: Defines the `MemoryStore` and `MemoryItem` classes for
  handling episodic and semantic memories.
- **pet_state.py**: Implements the `PetState` class, which manages drives,
  traits, habits, and memory interactions.
- **virtual_pet.py**: Provides the `VirtualPet` class that wraps a `PetState`
  instance and exposes methods for processing user messages and generating
  responses. When run directly, this module simulates a simple conversation
  for testing.
- **pet_server.py**: Contains simple stubs illustrating how the pet logic could
  be exposed as a server to handle incoming messages. It is kept for
  completeness but superseded by `server.py` for production use.
- **firestore_store.py**: Implements optional persistence using Google Cloud
  Firestore. When Firestore credentials are configured, pet states and
  memories are stored per user; otherwise the module falls back to an
  in-memory dictionary.
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
`virtual_pet.py`:

```bash
python virtual_pet.py
```

This will simulate a simple conversation between a user and the pet, showing
how drives, traits, and memory evolve over time.

## Running the API Server

To run the HTTP API locally, first install the dependencies:

```bash
pip install -r requirements.txt
```

If you want to enable Firestore persistence, set the environment variables
`GOOGLE_APPLICATION_CREDENTIALS` (pointing to your service account JSON) and
`USE_FIRESTORE=true`. Otherwise the server will store pet state in memory.

Start the server with Uvicorn:

```bash
uvicorn server:app --reload --port 8080
```

Then send a POST request to `http://localhost:8080/webhook` with a JSON body
containing `user_id` and `message`. The server returns a JSON response with
the pet's reply.

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
