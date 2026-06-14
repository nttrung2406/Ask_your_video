#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_RESOURCE_DIR="${SCRIPT_DIR}/model_resource"

echo "======================================"
echo "  Video Reasoning Pipeline Setup"
echo "======================================"

# Create model_resource directory if it doesn't exist
mkdir -p "${MODEL_RESOURCE_DIR}"

# ============================================
# Check and download whisper.cpp
# ============================================
echo "Checking whisper.cpp..."
if [ ! -d "${MODEL_RESOURCE_DIR}/whisper.cpp" ]; then
    echo "whisper.cpp not found. Cloning..."
    git clone https://github.com/ggerganov/whisper.cpp.git "${MODEL_RESOURCE_DIR}/whisper.cpp"
    echo "whisper.cpp: Downloaded"
else
    echo "whisper.cpp: OK"
fi

# ============================================
# Check and download llama.cpp
# ============================================
echo "Checking llama.cpp..."
if [ ! -d "${MODEL_RESOURCE_DIR}/llama.cpp" ]; then
    echo "llama.cpp not found. Cloning..."
    git clone https://github.com/ggerganov/llama.cpp.git "${MODEL_RESOURCE_DIR}/llama.cpp"
    echo "llama.cpp: Downloaded"
else
    echo "llama.cpp: OK"
fi

# ============================================
# Check and download DeepSeek model
# ============================================
MODEL_FILE="DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf"
MODEL_PATH="${MODEL_RESOURCE_DIR}/${MODEL_FILE}"
MODEL_URL="https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/${MODEL_FILE}"

echo "Checking DeepSeek model..."
if [ ! -f "${MODEL_PATH}" ]; then
    echo "DeepSeek model not found. Downloading from HuggingFace..."
    echo "This may take a while depending on your connection speed..."
    wget -O "${MODEL_PATH}" "${MODEL_URL}" || curl -L -o "${MODEL_PATH}" "${MODEL_URL}"
    echo "DeepSeek model: Downloaded"
else
    echo "DeepSeek model: OK"
fi

echo ""
echo "======================================"
echo "  All model resources ready!"
echo "======================================"

# ============================================
# Build and start Docker container
# ============================================
echo ""
echo "Building and starting model service..."
cd "${SCRIPT_DIR}"
docker compose up --build -d

echo ""
echo "Waiting for model service to be ready..."
echo "(This may take several minutes while llama.cpp and whisper.cpp compile)"

MAX_WAIT=600  # 10 minutes max wait
WAIT_INTERVAL=5
elapsed=0

while [ $elapsed -lt $MAX_WAIT ]; do
    # Check if API is responding
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/health 2>/dev/null | grep -q "200"; then
        echo ""
        echo "Model service is ready!"
        break
    fi
    
    # Show progress from container logs (last line)
    STATUS=$(docker compose logs --tail=1 2>/dev/null | grep -v "^$" | tail -1 || echo "Starting...")
    printf "\r  [%3ds] %s" "$elapsed" "${STATUS:0:60}"
    
    sleep $WAIT_INTERVAL
    elapsed=$((elapsed + WAIT_INTERVAL))
done

if [ $elapsed -ge $MAX_WAIT ]; then
    echo ""
    echo "WARNING: Timed out waiting for model service. Check logs with: docker compose logs -f"
fi

echo ""
echo "Model service started!"
echo "  API: http://localhost:8081"
echo "  Logs: docker compose logs -f"
