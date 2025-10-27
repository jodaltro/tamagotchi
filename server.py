"""
FastAPI server for the organic virtual pet.

This module defines a simple HTTP API that wraps the virtual pet logic and
persists state using Firestore when available. It exposes a single endpoint
`/webhook` to handle incoming messages. Each request must include a `user_id`
to identify the pet and a `message` containing the text from the user. The
response body contains the pet's reply. The server is ready to be deployed
to Google Cloud Run or Cloud Functions (2nd gen) with minimal configuration.

Example usage locally:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
export USE_FIRESTORE=true
pip install -r requirements.txt
uvicorn server:app --reload --port 8080
```

You can then send a POST request to `http://localhost:8080/webhook` with a
JSON body like `{"user_id": "123", "message": "Olá, pet!"}`. The server
responds with a JSON containing the pet's response.
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import base64

from .virtual_pet import VirtualPet
from .firestore_store import get_pet_data, save_pet_data

# Configure basic logging for the server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log environment variables on startup for debugging
logger.info("🐾 Server starting up...")
logger.info("🔍 Environment variables:")
logger.info("   USE_FIRESTORE: %s", os.getenv("USE_FIRESTORE", "not set"))
logger.info("   GOOGLE_APPLICATION_CREDENTIALS: %s", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "not set"))
logger.info("   GOOGLE_API_KEY: %s", "***HIDDEN***" if os.getenv("GOOGLE_API_KEY") else "not set")

app = FastAPI(title="Organic Virtual Pet API")


class WebhookRequest(BaseModel):
    user_id: str
    message: str = Field("", description="Texto enviado pelo usuário. Se vazio e uma imagem for fornecida, a imagem será processada.")
    image: Optional[str] = Field(None, description="Imagem codificada em base64 enviada pelo usuário.")


class WebhookResponse(BaseModel):
    response: str


@app.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(req: WebhookRequest) -> WebhookResponse:
    """Handle an incoming message and return the pet's response."""
    user_id = req.user_id.strip()
    message = (req.message or "").strip()
    image_b64 = req.image
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    # Load or create the pet state
    logger.info("Incoming webhook: user=%s, has_image=%s, message_len=%d", user_id, bool(image_b64), len(message))
    pet_state = get_pet_data(user_id)
    pet = VirtualPet(user_id=user_id)
    pet.state = pet_state
    # Process the message and/or image
    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64.split(',')[-1])
        except Exception:
            raise HTTPException(status_code=400, detail="invalid base64 image")
        pet.user_image(image_bytes)
        # If there's also a text message with the image, process it too
        if message:
            pet.user_message(message)
    elif message:
        pet.user_message(message)
    else:
        raise HTTPException(status_code=400, detail="either message or image must be provided")
    
    # Advance time to allow drives to evolve
    pet.state.tick(minutes=15.0)  # Simulate 15 minutes between interactions
    
    # Generate a reply
    reply = pet.pet_response()
    
    # Consolidate memories occasionally to build semantic knowledge
    import random
    if random.random() < 0.3:  # 30% chance to consolidate
        pet.state.memory.consolidate(threshold=0.4)
        logger.info("🧠 Consolidated memories into semantic knowledge")
    
    # Run reflection pass occasionally to update ABM and canon
    if random.random() < 0.2:  # 20% chance for reflection pass
        pet.reflection_pass()
        logger.info("🔄 Completed reflection pass")
    
    # Log memory summary and quick state info
    try:
        mem_summary = str(pet.state.memory)
    except Exception:
        mem_summary = "(unavailable)"
    logger.info("Reply generated for user=%s; memory=%s", user_id, mem_summary)
    # Persist the updated state
    save_pet_data(user_id, pet.state)
    return WebhookResponse(response=reply)


@app.get("/health")
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics() -> dict:
    """Get telemetry metrics for monitoring."""
    from .telemetry import get_telemetry
    
    telemetry = get_telemetry()
    summary = telemetry.get_summary()
    
    return {
        "status": "ok",
        "metrics": summary
    }


@app.get("/metrics/report")
async def get_metrics_report(recent: Optional[int] = None) -> dict:
    """Get detailed telemetry report."""
    from .telemetry import get_telemetry
    
    telemetry = get_telemetry()
    report = telemetry.get_detailed_report(recent_n=recent)
    
    return {
        "status": "ok",
        "report": report
    }

