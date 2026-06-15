import os
script_dir = os.path.dirname(os.path.abspath(__file__))
DEEPSEEK_MODEL_PATH = os.environ.get("DEEPSEEK_MODEL_PATH", os.path.join(script_dir, "model_resource", "DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf"))
