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
from .enhanced_virtual_pet import EnhancedVirtualPet
from .firestore_store import get_pet_data, save_pet_data, get_firestore_client

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
    """Handle an incoming message and return the pet's response with advanced memory."""
    user_id = req.user_id.strip()
    message = (req.message or "").strip()
    image_b64 = req.image
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Determine if we should use enhanced memory (enabled by default)
    use_enhanced_memory = os.getenv("USE_ENHANCED_MEMORY", "true").lower() in ("true", "1", "yes")
    
    logger.info("Incoming webhook: user=%s, has_image=%s, message_len=%d, enhanced_memory=%s", 
                user_id, bool(image_b64), len(message), use_enhanced_memory)
    
    if use_enhanced_memory:
        # Use EnhancedVirtualPet with advanced memory features
        pet_state = get_pet_data(user_id)
        pet = EnhancedVirtualPet(user_id=user_id)
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
        pet.state.tick(minutes=15.0)
        
        # Generate a reply (this will process the turn with advanced memory)
        reply = pet.pet_response()
        
        # Session consolidation (every 5-7 interactions on average)
        import random
        if random.random() < 0.15:  # 15% chance to consolidate session
            consolidation = pet.end_session()
            logger.info("🧠 Advanced consolidation: %s", consolidation)
        
        # Log memory summary with metrics
        try:
            metrics = pet.get_memory_metrics()
            active_commitments = pet.get_active_commitments()
            logger.info("Reply for user=%s; commitments=%d, resolution_rate=%.2f, tokens/turn=%.1f", 
                       user_id, len(active_commitments), 
                       metrics.get('commitment_resolution_rate', 0),
                       metrics.get('avg_tokens_per_turn', 0))
        except Exception as e:
            logger.warning("Could not get memory metrics: %s", e)
        
    else:
        # Fallback to standard VirtualPet (for backward compatibility)
        pet_state = get_pet_data(user_id)
        pet = VirtualPet()
        pet.state = pet_state
        
        # Process the message and/or image
        if image_b64:
            try:
                image_bytes = base64.b64decode(image_b64.split(',')[-1])
            except Exception:
                raise HTTPException(status_code=400, detail="invalid base64 image")
            pet.user_image(image_bytes)
            if message:
                pet.user_message(message)
        elif message:
            pet.user_message(message)
        else:
            raise HTTPException(status_code=400, detail="either message or image must be provided")
        
        # Advance time
        pet.state.tick(minutes=15.0)
        
        # Generate reply
        reply = pet.pet_response()
        
        # Consolidate memories occasionally
        import random
        if random.random() < 0.3:
            pet.state.memory.consolidate(threshold=0.4)
            logger.info("🧠 Consolidated memories into semantic knowledge")
        
        logger.info("Reply generated for user=%s; memory=%s", user_id, str(pet.state.memory))
    
    # Persist the updated state
    save_pet_data(user_id, pet.state)
    return WebhookResponse(response=reply)


@app.get("/health")
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.get("/memory/{user_id}")
async def get_memory_info(user_id: str) -> dict:
    """Get advanced memory information for a user (commitments, metrics, digest)."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    use_enhanced_memory = os.getenv("USE_ENHANCED_MEMORY", "true").lower() in ("true", "1", "yes")
    
    if not use_enhanced_memory:
        return {"error": "Enhanced memory is disabled. Set USE_ENHANCED_MEMORY=true to enable."}
    
    try:
        # Load pet state
        pet_state = get_pet_data(user_id)
        pet = EnhancedVirtualPet(user_id=user_id)
        pet.state = pet_state
        
        # Get advanced memory info
        metrics = pet.get_memory_metrics()
        commitments = pet.get_active_commitments()
        relationship_stage = pet.get_relationship_stage()
        
        # Try to get daily digest
        try:
            digest = pet.get_daily_digest()
            digest_info = {
                "daily_card": digest.daily_card,
                "new_facts": digest.new_facts,
                "active_commitments": digest.active_commitments,
                "open_topics": digest.open_topics,
                "next_step": digest.next_step
            }
        except Exception as e:
            logger.warning("Could not get daily digest: %s", e)
            digest_info = None
        
        return {
            "user_id": user_id,
            "metrics": metrics,
            "active_commitments": commitments,
            "relationship_stage": relationship_stage,
            "daily_digest": digest_info,
            "enhanced_memory_enabled": True
        }
    except Exception as e:
        logger.error("Error getting memory info for user %s: %s", user_id, str(e))
        raise HTTPException(status_code=500, detail=f"Error retrieving memory info: {str(e)}")
