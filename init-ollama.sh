#!/bin/bash
# Script to initialize Ollama with the llama3.2:3b model

set -e

OLLAMA_HOST="${OLLAMA_BASE_URL:-http://ollama:11434}"
MAX_RETRIES=30
RETRY_DELAY=2

echo "🚀 Waiting for Ollama service to be ready..."

# Wait for Ollama to be available
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama service is ready!"
        break
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ Ollama service did not become ready in time"
        exit 1
    fi
    
    echo "⏳ Waiting for Ollama... (attempt $i/$MAX_RETRIES)"
    sleep $RETRY_DELAY
done

# Check if model is already pulled
echo "🔍 Checking if llama3.2:3b model is already available..."
if curl -sf "$OLLAMA_HOST/api/tags" | grep -q "llama3.2:3b"; then
    echo "✅ Model llama3.2:3b is already available"
else
    echo "📥 Pulling llama3.2:3b model (this may take several minutes)..."
    
    # Pull the model using Ollama API
    curl -X POST "$OLLAMA_HOST/api/pull" \
        -H "Content-Type: application/json" \
        -d '{"name": "llama3.2:3b"}' \
        --no-buffer
    
    echo ""
    echo "✅ Model llama3.2:3b pulled successfully!"
fi

# Verify the model with a simple generation test
echo "🧪 Testing model with a simple prompt..."
RESPONSE=$(curl -sf -X POST "$OLLAMA_HOST/api/generate" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "llama3.2:3b",
        "prompt": "Say hello in one word.",
        "stream": false
    }')

if echo "$RESPONSE" | grep -q "response"; then
    echo "✅ Model test successful!"
    echo "📊 Response preview: $(echo "$RESPONSE" | head -c 100)..."
else
    echo "⚠️ Model test returned unexpected response"
    echo "$RESPONSE"
fi

echo "🎉 Ollama initialization complete!"
