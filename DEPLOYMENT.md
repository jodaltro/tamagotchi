# Deployment Guide

This guide covers deploying the Organic Virtual Pet to production environments, with a focus on Google Cloud Platform.

## Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Docker installed (for containerized deployments)
- A WhatsApp Business API account (for WhatsApp integration)

## Deployment Options

### Option 1: Google Cloud Run (Recommended)

Cloud Run is ideal for this project because:
- Automatic scaling (including to zero)
- Pay only for what you use
- Generous free tier
- Easy integration with other GCP services

#### Steps

1. **Set up your GCP project:**

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable generativelanguage.googleapis.com
```

2. **Create a Firestore database:**

```bash
# Create in native mode
gcloud firestore databases create --region=us-central1
```

3. **Build and push the container:**

```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/organic-pet:latest .

# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/organic-pet:latest
```

Or use Cloud Build:

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/organic-pet:latest
```

4. **Deploy to Cloud Run:**

```bash
gcloud run deploy organic-pet \
  --image gcr.io/$PROJECT_ID/organic-pet:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars USE_FIRESTORE=true \
  --set-env-vars GOOGLE_API_KEY="your-gemini-api-key" \
  --memory 512Mi \
  --max-instances 10
```

5. **Get your service URL:**

```bash
gcloud run services describe organic-pet \
  --region us-central1 \
  --format 'value(status.url)'
```

Your webhook URL will be: `https://your-service-url/webhook`

### Option 2: Google Cloud Functions

For even more serverless simplicity:

1. **Create a function entry point** (`main.py`):

```python
from tamagotchi.server import app

def handle_webhook(request):
    """Cloud Function entry point."""
    return app(request)
```

2. **Deploy:**

```bash
gcloud functions deploy organic-pet \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point handle_webhook \
  --set-env-vars USE_FIRESTORE=true
```

### Option 3: Traditional VM (Compute Engine)

For more control or custom requirements:

1. **Create a VM:**

```bash
gcloud compute instances create organic-pet-vm \
  --machine-type e2-small \
  --zone us-central1-a \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud
```

2. **SSH and set up:**

```bash
gcloud compute ssh organic-pet-vm --zone us-central1-a

# Install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip git

# Clone repo and install
git clone https://github.com/your-repo/tamagotchi.git
cd tamagotchi
pip3 install -r requirements.txt

# Set up as a service (systemd)
sudo nano /etc/systemd/system/organic-pet.service
```

Example service file:
```ini
[Unit]
Description=Organic Virtual Pet API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/tamagotchi
Environment="USE_FIRESTORE=true"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json"
ExecStart=/usr/bin/python3 -m uvicorn tamagotchi.server:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable organic-pet
sudo systemctl start organic-pet
```

## WhatsApp Integration

### Using WhatsApp Business Platform

1. **Set up a WhatsApp Business Account** at https://business.facebook.com

2. **Configure webhook:**
   - Go to your WhatsApp Business App settings
   - Set Webhook URL to your Cloud Run URL + `/webhook`
   - Set Verify Token (save this for later)
   - Subscribe to message events

3. **Add webhook verification** to your code:

```python
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Verify webhook for WhatsApp."""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "your-verify-token")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Forbidden")
```

4. **Transform WhatsApp messages** to your format:

```python
@app.post("/webhook")
async def handle_whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages."""
    body = await request.json()
    
    # Extract message from WhatsApp format
    if "messages" in body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}):
        message_data = body["entry"][0]["changes"][0]["value"]["messages"][0]
        user_id = message_data["from"]
        message_text = message_data.get("text", {}).get("body", "")
        
        # Process with your existing logic
        # ... (call VirtualPet)
        
        # Send response back to WhatsApp
        # ... (use WhatsApp API)
```

## Environment Variables

Set these in your deployment:

| Variable | Required | Description |
|----------|----------|-------------|
| `USE_FIRESTORE` | No | Set to `true` to enable Firestore (default: true) |
| `GOOGLE_API_KEY` | No | Gemini API key for language generation |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to service account JSON (auto-set in Cloud Run) |
| `WHATSAPP_VERIFY_TOKEN` | For WhatsApp | Token for webhook verification |
| `WHATSAPP_ACCESS_TOKEN` | For WhatsApp | Access token for sending messages |

## Security & Compliance

### LGPD/GDPR Compliance

1. **Add consent tracking:**

```python
@app.post("/webhook")
async def handle_webhook(req: WebhookRequest):
    # Check if user has consented
    if not has_user_consent(req.user_id):
        return {"response": "Para continuar, você precisa aceitar nossos termos. Digite 'aceito' para concordar."}
    # ... rest of logic
```

2. **Implement data export:**

```python
@app.get("/export/{user_id}")
async def export_user_data(user_id: str):
    """Export all data for a user (LGPD compliance)."""
    data = get_pet_data(user_id)
    return pet_state_to_dict(data)
```

3. **Implement data deletion:**

```python
@app.delete("/user/{user_id}")
async def delete_user_data(user_id: str):
    """Delete all data for a user (right to be forgotten)."""
    if _FIRESTORE_CLIENT:
        _FIRESTORE_CLIENT.collection("pets").document(user_id).delete()
    return {"status": "deleted"}
```

### Rate Limiting

Add rate limiting to prevent abuse:

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/webhook", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def handle_webhook(req: WebhookRequest):
    # ... your logic
```

### Content Moderation

Consider adding content filtering:

```python
def is_safe_content(text: str) -> bool:
    """Check if content is appropriate."""
    # Use Google Cloud Natural Language API or similar
    # to detect toxic content
    pass
```

## Monitoring & Logging

### Cloud Run Logging

Logs are automatically sent to Cloud Logging:

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=organic-pet" --limit 50
```

### Add Custom Metrics

```python
import logging
from google.cloud import monitoring_v3

logger = logging.getLogger(__name__)

@app.post("/webhook")
async def handle_webhook(req: WebhookRequest):
    logger.info(f"Processing message from user {req.user_id}")
    # ... your logic
```

### Set Up Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  # ... additional config
```

## Cost Optimization

### Free Tier Limits (GCP)
- Cloud Run: 2 million requests/month
- Firestore: 50k reads, 20k writes, 20k deletes per day
- Cloud Vision: 1,000 units/month
- Gemini API: Check current pricing

### Cost Reduction Tips

1. **Use Cloud Run scaling:**
```bash
--min-instances 0  # Scale to zero when not in use
--max-instances 10  # Prevent runaway costs
```

2. **Optimize Firestore:**
- Use batched writes
- Cache frequently accessed data
- Set TTL on old memories

3. **Rate limit generative AI calls:**
```python
# Cache responses for common queries
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_response(prompt: str) -> str:
    return generate_text(prompt)
```

## Continuous Deployment

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      
      - name: Deploy to Cloud Run
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.PROJECT_ID }}/organic-pet
          gcloud run deploy organic-pet \
            --image gcr.io/${{ secrets.PROJECT_ID }}/organic-pet \
            --region us-central1
```

## Troubleshooting

### Container won't start
Check logs:
```bash
gcloud run services logs read organic-pet --region us-central1
```

### Firestore connection issues
Verify service account permissions:
```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"
```

### High latency
Consider:
- Moving to a region closer to users
- Increasing memory allocation
- Caching frequent queries

## Rollback

If a deployment fails:
```bash
# List revisions
gcloud run revisions list --service organic-pet --region us-central1

# Rollback to previous revision
gcloud run services update-traffic organic-pet \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```
