"""
Firestore-based storage for pet states and memories.

This module provides helper functions to persist and retrieve `PetState` and
`MemoryStore` instances from Google Cloud Firestore. It abstracts away the
serialization logic and hides the Firestore client details from the rest of
the application. When Firestore is not configured (no credentials or the
`USE_FIRESTORE` environment variable is set to false), the module falls back
to an in-memory dictionary to store state. This makes the code easy to run
locally while providing a clear path to persistent storage in production.

To enable Firestore persistence, ensure that:

1. A Google Cloud project is created with Firestore enabled.
2. A service account with Firestore access is created and its JSON key
   downloaded.
3. The `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to this
   JSON key file.
4. The `USE_FIRESTORE` environment variable is set to `true` (default).

If any of these conditions are not met, the code will operate in memory
without persistence.
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime

# Logger for persistence layer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Attempt to import Firestore client. If unavailable, we'll use in-memory fallback.
try:
    from google.cloud import firestore  # type: ignore
    from google.cloud.firestore import Client  # type: ignore
except Exception:
    firestore = None  # type: ignore
    Client = None  # type: ignore

from .pet_state import PetState
from .memory_store import MemoryStore

# In-memory fallback store keyed by user ID
_IN_MEMORY_STORE: Dict[str, Dict] = {}


def _init_firestore_client() -> Optional[object]:
    """Create a Firestore client if credentials are available and enabled."""
    # If the Firestore library isn't available, always return None
    if firestore is None:
        logger.info("🔴 Firestore SDK not installed; falling back to in-memory storage")
        return None
    
    use_firestore = os.getenv("USE_FIRESTORE", "true").lower() in ("true", "1", "yes")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Debug logging for environment variables
    logger.info("🔍 Environment check: USE_FIRESTORE=%s, GOOGLE_APPLICATION_CREDENTIALS=%s", 
                os.getenv("USE_FIRESTORE", "not set"), 
                credentials_path or "not set")
    
    if not use_firestore:
        logger.info("🔴 USE_FIRESTORE is disabled; falling back to in-memory storage")
        return None
        
    if not credentials_path:
        logger.info("🔴 GOOGLE_APPLICATION_CREDENTIALS not set; falling back to in-memory storage")
        return None
        
    if not os.path.exists(credentials_path):
        logger.info("🔴 Credentials file not found at %s; falling back to in-memory storage", credentials_path)
        return None
    
    try:
        client = firestore.Client()
        logger.info("✅ Firestore client initialized using credentials: %s", credentials_path)
        return client
    except Exception as e:
        # Fall back to None if client init fails (e.g., invalid credentials)
        logger.exception("🔴 Failed to initialize Firestore client: %s; falling back to in-memory storage", str(e))
        return None


_FIRESTORE_CLIENT: Optional[object] = _init_firestore_client()


def pet_state_to_dict(state: PetState) -> Dict:
    """Serialize a PetState into a dictionary suitable for storage."""
    # Save personality state before serialization
    personality_data = state.save_personality_state()
    
    # Serialize semantic memory properly - format: Dict[str, Tuple[float, datetime, int]]
    semantic_serialized = {}
    for key, value in state.memory.semantic.items():
        if isinstance(value, tuple) and len(value) >= 3:
            # Proper format: (weight, timestamp, access_count)
            semantic_serialized[key] = [
                float(value[0]),  # weight
                value[1].isoformat() if hasattr(value[1], 'isoformat') else datetime.utcnow().isoformat(),  # timestamp
                int(value[2])  # access_count
            ]
        elif isinstance(value, (int, float)):
            # Legacy format: just a number, convert to proper tuple
            from datetime import datetime
            semantic_serialized[key] = [float(value), datetime.utcnow().isoformat(), 1]
        else:
            logger.warning(f"⚠️ Unknown semantic format for '{key}': {value}")
    
    return {
        "drives": state.drives,
        "traits": state.traits,
        "habits": state.habits,
        "stage": state.stage,
        "last_user_message": state.last_user_message.isoformat(),
        "personality_data": personality_data,  # Store personality profile
        "episodic": [
            {
                "kind": item.kind,
                "text": item.text,
                "salience": item.salience,
                "timestamp": item.timestamp.isoformat(),
            }
            for item in state.memory.episodic
        ],
        "semantic": semantic_serialized,
    }


def dict_to_pet_state(data: Dict) -> PetState:
    """Deserialize a dictionary back into a PetState instance."""
    from datetime import datetime
    
    memory = MemoryStore()
    
    # Populate episodic memories
    for ep in data.get("episodic", []):
        memory.add_episode(ep.get("text", ""), salience=float(ep.get("salience", 0.5)))
    
    # Set semantic memories - format: Dict[str, Tuple[float, datetime, int]]
    semantic_data = data.get("semantic", {})
    if semantic_data:
        for key, value in semantic_data.items():
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                # Correct format: [weight, timestamp_str, access_count]
                try:
                    weight = float(value[0])
                    timestamp = datetime.fromisoformat(value[1]) if isinstance(value[1], str) else datetime.utcnow()
                    access_count = int(value[2])
                    memory.semantic[str(key)] = (weight, timestamp, access_count)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse semantic memory '{key}': {e}")
                    # Fallback: create default tuple
                    memory.semantic[str(key)] = (0.8, datetime.utcnow(), 1)
            elif isinstance(value, (int, float)):
                # Legacy format: just a float weight
                memory.semantic[str(key)] = (float(value), datetime.utcnow(), 1)
            else:
                logger.warning(f"⚠️ Unknown semantic memory format for '{key}': {value}")
    
    # Create PetState
    state = PetState()
    state.drives = {k: float(v) for k, v in data.get("drives", {}).items()}
    state.traits = {k: float(v) for k, v in data.get("traits", {}).items()}
    state.habits = {k: float(v) for k, v in data.get("habits", {}).items()}
    state.stage = data.get("stage", "infante")
    if "last_user_message" in data:
        try:
            state.last_user_message = datetime.fromisoformat(data["last_user_message"])
        except Exception:
            pass
    state.memory = memory
    
    # Restore personality if available
    personality_data = data.get("personality_data")
    if personality_data:
        state.initialize_personality(profile_data=personality_data)
    else:
        # Initialize new random personality for existing pets without personality
        state.initialize_personality()
    
    return state


def get_pet_data(user_id: str) -> PetState:
    """Retrieve a PetState for the given user ID from Firestore or memory."""
    global _IN_MEMORY_STORE
    if _FIRESTORE_CLIENT is not None:
        doc_ref = _FIRESTORE_CLIENT.collection("pets").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            logger.info("Loaded pet state for user '%s' from Firestore", user_id)
            return dict_to_pet_state(data)
    # Fallback to in-memory
    if user_id in _IN_MEMORY_STORE:
        logger.info("Loaded pet state for user '%s' from in-memory store", user_id)
        return dict_to_pet_state(_IN_MEMORY_STORE[user_id])
    # Create a new state
    logger.info("Creating new PetState for user '%s' (no existing state found)", user_id)
    return PetState()


def save_pet_data(user_id: str, state: PetState) -> None:
    """Persist the given PetState under the user ID."""
    global _IN_MEMORY_STORE
    data = pet_state_to_dict(state)
    if _FIRESTORE_CLIENT is not None:
        _FIRESTORE_CLIENT.collection("pets").document(user_id).set(data)
        logger.info("Saved pet state for user '%s' to Firestore", user_id)
    else:
        _IN_MEMORY_STORE[user_id] = data
        logger.info("Saved pet state for user '%s' to in-memory store", user_id)