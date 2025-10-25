# Docker Setup Guide

This guide explains how to run the Tamagotchi Virtual Pet project using Docker and Docker Compose.

## Prerequisites

- Docker installed on your system ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose (usually included with Docker Desktop)

## Quick Start

1. **Clone the repository** (if not already done):
   ```bash
   git clone https://github.com/jodaltro/tamagotchi.git
   cd tamagotchi
   ```

2. **Configure environment variables** (optional):
   ```bash
   cp .env.example .env
   # Edit .env file with your preferred settings
   ```

3. **Start the application**:
   ```bash
   docker compose up -d
   ```

4. **Verify the application is running**:
   ```bash
   curl http://localhost:8080/health
   ```

   Expected response: `{"status":"ok"}`

5. **Test the pet interaction**:
   ```bash
   curl -X POST http://localhost:8080/webhook \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test_user", "message": "Olá, pet!"}'
   ```

## Environment Variables

The following environment variables can be configured in your `.env` file:

### Required Variables
- `USE_FIRESTORE`: Set to `true` to enable Google Firestore persistence, `false` for in-memory storage (default: `false`)

### Optional Variables
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud service account JSON key file (required if `USE_FIRESTORE=true` or using Vision API)
- `GOOGLE_API_KEY` or `GENAI_API_KEY`: Google Generative AI API key for enhanced language generation
- `PORT`: Application port (default: `8080`)

## Using Google Cloud Services

### Firestore Persistence

To enable Firestore persistence:

1. Create a Google Cloud project and enable Firestore
2. Download a service account key JSON file
3. Create a `credentials` directory in the project root:
   ```bash
   mkdir credentials
   cp /path/to/your-service-account.json credentials/
   ```

4. Update your `.env` file:
   ```env
   USE_FIRESTORE=true
   GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/your-service-account.json
   ```

5. Uncomment the volume mount in `docker-compose.yml`:
   ```yaml
   volumes:
     - ./credentials:/app/credentials:ro
   ```

6. Restart the container:
   ```bash
   docker compose down
   docker compose up -d
   ```

### Google Generative AI (Gemini)

To enable enhanced language generation:

1. Get an API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add it to your `.env` file:
   ```env
   GOOGLE_API_KEY=your-api-key-here
   ```

3. Restart the container:
   ```bash
   docker compose restart
   ```

## Docker Commands

### Start the application
```bash
docker compose up -d
```

### Stop the application
```bash
docker compose down
```

### View logs
```bash
docker compose logs -f tamagotchi
```

### Rebuild after code changes
```bash
docker compose up -d --build
```

### Check container status
```bash
docker compose ps
```

### Execute commands inside the container
```bash
docker compose exec tamagotchi /bin/bash
```

### Restart the application
```bash
docker compose restart
```

## Building the Docker Image Manually

If you prefer to build the Docker image manually:

```bash
# Build the image
DOCKER_BUILDKIT=0 docker build -t tamagotchi-pet .

# Run the container
docker run -d \
  --name tamagotchi \
  -p 8080:8080 \
  -e USE_FIRESTORE=false \
  tamagotchi-pet

# Check logs
docker logs -f tamagotchi

# Stop and remove
docker stop tamagotchi
docker rm tamagotchi
```

## Troubleshooting

### SSL Certificate Errors During Build

If you encounter SSL certificate errors during the Docker build process, use the following command:

```bash
DOCKER_BUILDKIT=0 docker compose up -d --build
```

### Port Already in Use

If port 8080 is already in use on your system, you can change it in `docker-compose.yml`:

```yaml
ports:
  - "8081:8080"  # Use port 8081 on host instead
```

### Container Health Check Failing

Check the container logs:
```bash
docker compose logs tamagotchi
```

Ensure curl is available in the container (it's included in the Dockerfile).

### Memory Issues

If the container crashes due to memory issues, you can limit its resources in `docker-compose.yml`:

```yaml
services:
  tamagotchi:
    # ... other settings ...
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## Development Workflow

For active development:

1. **Make code changes** on your host machine
2. **Rebuild and restart**:
   ```bash
   docker compose up -d --build
   ```

3. **View logs in real-time**:
   ```bash
   docker compose logs -f tamagotchi
   ```

## Production Deployment

For production deployment, consider:

1. **Use a specific tag** instead of `latest`
2. **Set up proper logging** with a logging driver
3. **Configure resource limits**
4. **Use secrets management** for sensitive environment variables
5. **Deploy to a container orchestration platform** (Kubernetes, Google Cloud Run, etc.)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions.

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/health
```

### Webhook (Text Message)
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Como você está?"
  }'
```

### Webhook (Image)
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "",
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }'
```

## Additional Resources

- [Project README](README.md) - Main project documentation
- [Personality Engine](PERSONALITY_ENGINE.md) - Details about the personality system
- [Testing Guide](TESTING.md) - How to run tests
- [Deployment Guide](DEPLOYMENT.md) - Production deployment to GCP
