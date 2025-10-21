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
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import base64

from .virtual_pet import VirtualPet
from .firestore_store import get_pet_data, save_pet_data

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
    pet_state = get_pet_data(user_id)
    pet = VirtualPet()
    pet.state = pet_state
    # If an image is provided, process it; otherwise process the text message
    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64.split(',')[-1])
        except Exception:
            raise HTTPException(status_code=400, detail="invalid base64 image")
        pet.user_image(image_bytes)
    elif message:
        pet.user_message(message)
    else:
        raise HTTPException(status_code=400, detail="either message or image must be provided")
    # Generate a reply
    reply = pet.pet_response()
    # Persist the updated state
    save_pet_data(user_id, pet.state)
    return WebhookResponse(response=reply)


@app.get("/health")
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}
