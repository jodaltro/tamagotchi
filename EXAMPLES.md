# Usage Examples

This document provides practical examples of using the Organic Virtual Pet in different scenarios.

## Basic Conversation Flow

### Example 1: Getting to Know the Pet

```bash
# First message
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "maria", "message": "Oi! Como você está?"}'

# Response might be: "Claro! Isso soa divertido."

# Second message
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "maria", "message": "Vamos ouvir música?"}'

# The pet's musical trait increases, and it might respond enthusiastically
```

### Example 2: Playing with the Pet

```bash
# Suggest a game
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "joao", "message": "Vamos jogar?"}'

# The pet's ludico (playful) trait increases
# Response might suggest a game or ask what to play

# Follow up
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "joao", "message": "Vamos jogar adivinhação!"}'
```

## Programmatic Usage

### Python Client Example

```python
import requests

class PetClient:
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url
        self.user_id = user_id
    
    def send_message(self, message: str) -> str:
        """Send a text message to the pet."""
        response = requests.post(
            f"{self.base_url}/webhook",
            json={"user_id": self.user_id, "message": message}
        )
        response.raise_for_status()
        return response.json()["response"]
    
    def send_image(self, image_path: str) -> str:
        """Send an image to the pet."""
        import base64
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
        response = requests.post(
            f"{self.base_url}/webhook",
            json={
                "user_id": self.user_id,
                "message": "",
                "image": f"data:image/jpeg;base64,{image_b64}"
            }
        )
        response.raise_for_status()
        return response.json()["response"]


# Usage
client = PetClient("http://localhost:8080", "user123")

# Have a conversation
print(client.send_message("Oi!"))
print(client.send_message("Vamos ouvir música?"))
print(client.send_message("Gosto de rock!"))

# Send an image
print(client.send_image("photo.jpg"))
```

### JavaScript/Node.js Client Example

```javascript
const axios = require('axios');
const fs = require('fs');

class PetClient {
  constructor(baseUrl, userId) {
    this.baseUrl = baseUrl;
    this.userId = userId;
  }

  async sendMessage(message) {
    const response = await axios.post(`${this.baseUrl}/webhook`, {
      user_id: this.userId,
      message: message
    });
    return response.data.response;
  }

  async sendImage(imagePath) {
    const imageBuffer = fs.readFileSync(imagePath);
    const imageB64 = imageBuffer.toString('base64');
    
    const response = await axios.post(`${this.baseUrl}/webhook`, {
      user_id: this.userId,
      message: '',
      image: `data:image/jpeg;base64,${imageB64}`
    });
    return response.data.response;
  }
}

// Usage
(async () => {
  const client = new PetClient('http://localhost:8080', 'user123');
  
  console.log(await client.sendMessage('Oi!'));
  console.log(await client.sendMessage('Conta uma piada'));
  console.log(await client.sendImage('photo.jpg'));
})();
```

## Advanced Use Cases

### Example 3: Building a Chatbot with Memory

```python
from tamagotchi.virtual_pet import VirtualPet
from tamagotchi.firestore_store import get_pet_data, save_pet_data

class ChatBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.pet = VirtualPet()
        # Load existing state
        self.pet.state = get_pet_data(user_id)
    
    def chat(self, message: str) -> str:
        """Process a message and return response."""
        # Update state with message
        self.pet.user_message(message)
        
        # Generate response
        response = self.pet.pet_response()
        
        # Save state
        save_pet_data(self.user_id, self.pet.state)
        
        return response
    
    def get_stats(self) -> dict:
        """Get current pet statistics."""
        return {
            "drives": self.pet.state.drives,
            "traits": self.pet.state.traits,
            "stage": self.pet.state.stage,
            "memories": len(self.pet.state.memory.episodic),
            "facts": len(self.pet.state.memory.semantic)
        }

# Usage
bot = ChatBot("user456")
print(bot.chat("Olá!"))
print(bot.chat("Gosto de filmes de ficção científica"))
print(bot.chat("Vamos ver um filme?"))
print("Stats:", bot.get_stats())
```

### Example 4: Multi-User Chat Room

```python
from fastapi import FastAPI, WebSocket
from tamagotchi.virtual_pet import VirtualPet
from tamagotchi.firestore_store import get_pet_data, save_pet_data

app = FastAPI()

# Store active pets per user
active_pets = {}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    
    # Create or load pet
    if user_id not in active_pets:
        pet = VirtualPet()
        pet.state = get_pet_data(user_id)
        active_pets[user_id] = pet
    else:
        pet = active_pets[user_id]
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            # Process
            pet.user_message(data)
            response = pet.pet_response()
            
            # Send response
            await websocket.send_text(response)
            
            # Save state
            save_pet_data(user_id, pet.state)
    except:
        # Clean up on disconnect
        save_pet_data(user_id, pet.state)
        del active_pets[user_id]
```

### Example 5: Scheduled Interactions

```python
import schedule
import time
from datetime import datetime

def check_and_greet_users():
    """Send a greeting to users at specific times."""
    users = ["user1", "user2", "user3"]
    
    for user_id in users:
        pet = VirtualPet()
        pet.state = get_pet_data(user_id)
        
        # Check if it's morning
        if datetime.now().hour == 8:
            # Send morning greeting
            greeting = "Bom dia! Como você dormiu?"
            # Send via WhatsApp or notification system
            send_notification(user_id, greeting)
        
        # Tick the pet's state
        pet.state.tick(minutes=60)
        save_pet_data(user_id, pet.state)

# Schedule daily greetings
schedule.every().day.at("08:00").do(check_and_greet_users)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Example 6: Image-Based Interactions

```python
import base64
from tamagotchi.virtual_pet import VirtualPet

def analyze_user_photos(user_id: str, photo_paths: list):
    """Analyze multiple photos and build photographic memory."""
    pet = VirtualPet()
    pet.state = get_pet_data(user_id)
    
    for photo_path in photo_paths:
        with open(photo_path, "rb") as f:
            image_bytes = f.read()
        
        # Process image
        pet.user_image(image_bytes)
    
    # Generate a response about the photos
    response = pet.pet_response()
    
    save_pet_data(user_id, pet.state)
    return response

# Usage
response = analyze_user_photos(
    "user789",
    ["vacation1.jpg", "vacation2.jpg", "vacation3.jpg"]
)
print(f"Pet's response to vacation photos: {response}")
```

## WhatsApp Integration Example

### Using Twilio API for WhatsApp

```python
from twilio.rest import Client
from fastapi import FastAPI, Request

app = FastAPI()

# Twilio credentials
account_sid = "your_account_sid"
auth_token = "your_auth_token"
twilio_whatsapp_number = "whatsapp:+14155238886"

client = Client(account_sid, auth_token)

@app.post("/whatsapp")
async def handle_whatsapp(request: Request):
    """Handle incoming WhatsApp messages via Twilio."""
    form = await request.form()
    
    user_number = form.get("From")
    message_text = form.get("Body")
    
    # Extract user_id from phone number
    user_id = user_number.replace("whatsapp:", "")
    
    # Process with pet
    pet = VirtualPet()
    pet.state = get_pet_data(user_id)
    pet.user_message(message_text)
    response = pet.pet_response()
    save_pet_data(user_id, pet.state)
    
    # Send response back via Twilio
    message = client.messages.create(
        from_=twilio_whatsapp_number,
        body=response,
        to=user_number
    )
    
    return {"status": "sent"}
```

## Testing Different Personalities

### Example 7: A/B Testing Personalities

```python
# Create two different agent configs
config_a = {
    "agent": {
        "system_prompt": "Você é um pet divertido e brincalhão. Use emojis e seja bem energético! 😄"
    }
}

config_b = {
    "agent": {
        "system_prompt": "Você é um pet calmo e reflexivo. Fale de forma poética e filosófica."
    }
}

def test_personality(config: dict, message: str):
    """Test a personality configuration."""
    pet = VirtualPet()
    # Override system prompt
    pet.system_prompt = config["agent"]["system_prompt"]
    
    pet.user_message(message)
    return pet.pet_response()

# Compare responses
message = "Como foi seu dia?"
print("Personality A:", test_personality(config_a, message))
print("Personality B:", test_personality(config_b, message))
```

## Data Export Example

### Example 8: Export User Data (LGPD Compliance)

```python
from tamagotchi.firestore_store import get_pet_data, pet_state_to_dict
import json

def export_user_data(user_id: str, output_file: str):
    """Export all user data to JSON file."""
    state = get_pet_data(user_id)
    data = pet_state_to_dict(state)
    
    # Add metadata
    export_data = {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "pet_data": data
    }
    
    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"Data exported to {output_file}")

# Usage
export_user_data("user123", "user123_data.json")
```

## Performance Monitoring Example

### Example 9: Track Response Times

```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f}s")
        return result
    return wrapper

@measure_time
def process_message(user_id: str, message: str):
    pet = VirtualPet()
    pet.state = get_pet_data(user_id)
    pet.user_message(message)
    response = pet.pet_response()
    save_pet_data(user_id, pet.state)
    return response

# Usage
response = process_message("user123", "Olá!")
# Output: process_message took 0.15s
```

## Tips for Different Scenarios

### For Educational Apps
- Use the pet to teach subjects through conversation
- Track learning progress in semantic memory
- Adjust personality to be encouraging and patient

### For Mental Health Support
- Configure calm, empathetic system prompts
- Track mood patterns in memory
- Never claim to replace professional help

### For Gaming
- High ludico and humor traits
- Use jokes and game requests frequently
- Track high scores in semantic memory

### For Customer Service
- Professional but friendly tone
- Track user preferences and issues
- Integration with ticketing systems
