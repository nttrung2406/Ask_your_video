# Video Reasoning For Local Usage

A multimodal video reasoning system that processes videos to answer questions about video content. Uses **DeepSeek-R1-Distill-Qwen-7B** for reasoning.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VIDEO REASONING PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: PREPROCESSING          Phase 2: TRANSLATION                       │
│  ┌─────────────────────┐         ┌─────────────────────┐                    │
│  │  Video Input        │         │  Audio → Text       │                    │
│  │  ↓                  │         │  (Whisper.cpp)      │                    │
│  │  FFmpeg (Audio)     │    →    │  ↓                  │                    │
│  │  OpenCV (Frames)    │         │  Frames → Text      │                    │
│  │  @ 5 FPS            │         │  (Moondream2)       │                    │
│  └─────────────────────┘         └─────────────────────┘                    │
│            ↓                               ↓                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Phase 3: AGGREGATION                             │    │
│  │  Combine audio transcripts + frame captions into chronological      │    │
│  │  timeline format for LLM reasoning                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│            ↓                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Phase 4: REASONING (DeepSeek)                    │    │
│  │  DeepSeek-R1 via Llama.cpp analyzes timeline + question → Answer    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```
# Start all services
chmod +x ./start.sh
./start.sh start

# Stop all services
./start.sh stop

# Restart all services
./start.sh restart

# View logs
./start.sh logs backend    # Backend logs
./start.sh logs model      # Model service logs

# Check service status
./start.sh status

# Clean up (stop + remove volumes/network)
./start.sh clean
```

## Example API Usage

```python
import httpx

# Process video and ask question
response = httpx.post("http://localhost:8001/process", json={
    "video_path": "/app/data/video.mp4",
    "question": "What is happening in this video?"
})
result = response.json()
print(result["answer"])
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | Whisper model size |
| `MOONDREAM_PRECISION` | `4bit` | VLM quantization |
| `LLAMA_MODEL_PATH` | `/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf` | Path to GGUF model |
| `OUTPUT_DIR` | `/app/output` | Output directory |
| `LOG_LEVEL` | `INFO` | Logging level |

### Pipeline Configuration

```python
from pipeline import PipelineController, PipelineConfig

config = PipelineConfig(
    target_fps=5,
    whisper_model="base",
    vlm_precision="4bit",
    llm_temperature=0.7
)

pipeline = PipelineController(config)
```

## Timeline Format Example

```
[VIDEO TIMELINE]
00:01 - 00:02 | Visual: A person is sitting at a wooden desk opening a laptop.
00:02 - 00:04 | Visual: They type intensely on the keyboard, looking frustrated.
00:03 - 00:04 | Audio Track (Subtitles): "Why isn't this code compiling..."
00:05 - 00:07 | Visual: The person throws their hands in the air and smiles.

[USER QUESTION]
Why did the person's mood change from frustrated to happy?

[REASONING COMPONENT]
Thinking Process:
The timeline shows the person was frustrated while coding (00:02-00:04), 
as evidenced by the audio "Why isn't this code compiling..." 
Then at 00:05-00:07, they smile and throw their hands up in celebration.
This suggests they successfully fixed their code issue.

Answer: The person's mood changed from frustrated to happy because they 
solved their coding problem. The green checkmark appearing on screen 
indicates the code finally compiled successfully.
```

## Models Used

| Component | Model | Purpose |
|-----------|-------|---------|
| Audio Transcription | Whisper.cpp (base) | Convert speech to text with timestamps |
| Frame Captioning | Moondream2 (4-bit) | Describe visual content of frames |
| Reasoning | DeepSeek-R1-Distill-Qwen-7B (Q3_K_M) | Answer questions about video content |

## Performance Notes

- **Keyframe Extraction**: 20 FPS reduces redundant frames while capturing motion
- **Whisper Base**: Good balance of speed and accuracy for CPU inference
- **4-bit Quantization**: Enables VLM to run on limited GPU/CPU memory
- **DeepSeek-R1**: Strong reasoning capabilities for video understanding
- **CPU Support**: All components can run on CPU (slower but accessible)

## Integration with Backend

The API server provides endpoints for seamless integration with the backend service:

1. **Upload** video via `/upload`
2. **Preprocess** video via `/preprocess` (returns session_id)
3. **Ask questions** via `/ask` using session_id
4. Multiple questions can be asked about the same preprocessed video

