# Current problematic code
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    local_files_only=True,  # Force local files
    trust_remote_code=False  # For security
)