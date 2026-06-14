# Multimodal Video Reasoning Pipeline
# Includes: whisper.cpp, llama.cpp, ffmpeg, OpenCV, Moondream2

FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    ffmpeg \
    libopencv-dev \
    libsndfile1 \
    libgomp1 \
    libvips42 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create working directories
WORKDIR /app
RUN mkdir -p /app/models /app/data /app/output /app/model_resource

# Add whisper.cpp and llama.cpp to PATH (they will be mounted from host)
ENV PATH="/app/model_resource/whisper.cpp:${PATH}"
ENV WHISPER_CPP_PATH="/app/model_resource/whisper.cpp"
ENV PATH="/app/model_resource/llama.cpp:${PATH}"
ENV LLAMA_CPP_PATH="/app/model_resource/llama.cpp"

# ============================================
# Install Python dependencies
# ============================================
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Set Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Expose API port
EXPOSE 8001

# Default command - use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
