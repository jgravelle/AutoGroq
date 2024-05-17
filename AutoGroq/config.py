# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # in seconds
RETRY_TOKEN_LIMIT = 5000
LLM_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model configurations
MODEL_TOKEN_LIMITS = {
    'llama3-70b-8192': 8192,
    'llama3-8b-8192': 8192,
    'mixtral-8x7b-32768': 32768,
    'gemma-7b-it': 8192
}