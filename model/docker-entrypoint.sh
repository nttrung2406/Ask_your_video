#!/bin/bash
# Docker entrypoint script for the video reasoning model service
# Builds whisper.cpp and llama.cpp from mounted sources, then starts the service

set -e

echo "======================================"
echo "  Video Reasoning Pipeline"
echo "======================================"

# ============================================
# Build whisper.cpp if not already built
# ============================================
echo "Checking whisper.cpp..."
WHISPER_DIR="/app/model_resource/whisper.cpp"

if [ -d "$WHISPER_DIR" ]; then
    # Check for the built binary (could be main or whisper-cli depending on version)
    if [ ! -f "$WHISPER_DIR/build/bin/whisper-cli" ] && [ ! -f "$WHISPER_DIR/build/main" ]; then
        echo "Building whisper.cpp with cmake..."
        cd "$WHISPER_DIR"
        mkdir -p build
        cd build
        /usr/bin/cmake .. -DGGML_NATIVE=OFF
        /usr/bin/cmake --build . --config Release -j$(nproc)
        echo "whisper.cpp: Built"
    else
        echo "whisper.cpp: Already built"
    fi
    
    # Download whisper model if not present
    WHISPER_MODEL=${WHISPER_MODEL:-base}
    WHISPER_MODEL_PATH="$WHISPER_DIR/models/ggml-${WHISPER_MODEL}.bin"
    
    if [ ! -f "$WHISPER_MODEL_PATH" ]; then
        echo "Downloading Whisper ${WHISPER_MODEL} model..."
        cd "$WHISPER_DIR/models"
        bash ./download-ggml-model.sh ${WHISPER_MODEL}
    fi
    echo "Whisper model: OK"
else
    echo "Warning: whisper.cpp not found at $WHISPER_DIR"
fi

# ============================================
# Build llama.cpp if not already built
# ============================================
echo "Checking llama.cpp..."
LLAMA_DIR="/app/model_resource/llama.cpp"
LLAMA_SERVER="$LLAMA_DIR/build/bin/llama-server"

if [ -d "$LLAMA_DIR" ]; then
    if [ ! -f "$LLAMA_SERVER" ]; then
        echo "Building llama.cpp with cmake..."
        cd "$LLAMA_DIR"
        mkdir -p build
        cd build
        /usr/bin/cmake .. -DGGML_NATIVE=OFF
        /usr/bin/cmake --build . --config Release -j$(nproc)
        echo "llama.cpp: Built"
    else
        echo "llama.cpp: Already built"
    fi
else
    echo "Warning: llama.cpp not found at $LLAMA_DIR"
fi

# ============================================
# Check DeepSeek model
# ============================================
echo "Checking DeepSeek model..."
MODEL_PATH=${LLAMA_MODEL_PATH:-/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf}

if [ ! -f "$MODEL_PATH" ]; then
    echo "Warning: DeepSeek model not found at $MODEL_PATH"
    echo "Please run start.sh on the host first to download the model."
else
    echo "DeepSeek model: OK"
fi

cd /app

# ============================================
# Start service based on MODE
# ============================================
MODE=${MODE:-api}

echo ""
echo "Starting in $MODE mode..."
echo ""

case $MODE in
    api)
        echo "Starting API server on port 8081..."
        
        # Start llama-server in background if available
        LLAMA_SERVER="/app/model_resource/llama.cpp/build/bin/llama-server"
        MODEL_PATH=${LLAMA_MODEL_PATH:-/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf}
        
        if [ -f "$LLAMA_SERVER" ] && [ -f "$MODEL_PATH" ]; then
            echo "Starting llama-server with KV cache optimizations..."
            
            # KV Cache configuration from environment
            LLM_PORT=${LLM_SERVER_PORT:-8080}
            CTX_SIZE=${LLM_CONTEXT_SIZE:-8192}
            N_SLOTS=${LLM_N_SLOTS:-4}
            CACHE_K=${LLM_CACHE_TYPE_K:-q8_0}
            CACHE_V=${LLM_CACHE_TYPE_V:-q8_0}
            N_GPU=${LLM_N_GPU_LAYERS:-0}
            
            # Build llama-server command
            LLAMA_CMD="$LLAMA_SERVER"
            LLAMA_CMD="$LLAMA_CMD --model $MODEL_PATH"
            LLAMA_CMD="$LLAMA_CMD --port $LLM_PORT"
            LLAMA_CMD="$LLAMA_CMD --ctx-size $CTX_SIZE"
            LLAMA_CMD="$LLAMA_CMD --parallel $N_SLOTS"
            LLAMA_CMD="$LLAMA_CMD --cache-type-k $CACHE_K"
            LLAMA_CMD="$LLAMA_CMD --cache-type-v $CACHE_V"
            LLAMA_CMD="$LLAMA_CMD --defrag-thold 0.1"
            LLAMA_CMD="$LLAMA_CMD --cont-batching"
            
            if [ "$N_GPU" != "0" ]; then
                LLAMA_CMD="$LLAMA_CMD --n-gpu-layers $N_GPU"
            fi
            
            echo "  Port: $LLM_PORT, Context: $CTX_SIZE, Slots: $N_SLOTS"
            echo "  KV Cache: K=$CACHE_K, V=$CACHE_V"
            
            # Start in background and log to file
            $LLAMA_CMD > /app/llama-server.log 2>&1 &
            LLAMA_PID=$!
            echo "llama-server started (PID: $LLAMA_PID)"
            
            # Wait a moment for server to initialize
            sleep 3
            
            # Check if server is running
            if kill -0 $LLAMA_PID 2>/dev/null; then
                echo "llama-server is running"
            else
                echo "Warning: llama-server may have failed to start, check /app/llama-server.log"
            fi
        else
            echo "Warning: llama-server or model not found, skipping KV cache server"
            echo "  Server: $LLAMA_SERVER (exists: $([ -f "$LLAMA_SERVER" ] && echo yes || echo no))"
            echo "  Model: $MODEL_PATH (exists: $([ -f "$MODEL_PATH" ] && echo yes || echo no))"
        fi
        
        # Start the Python API server
        exec python -m pipeline.api_server
        ;;
    cli)
        echo "Running CLI mode..."
        exec python -m pipeline.main "$@"
        ;;
    shell)
        echo "Starting shell..."
        exec /bin/bash
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Available modes: api, cli, shell"
        exit 1
        ;;
esac
