#APIs
LLM_PROVIDER = "groq" # Supported values: "groq", "openai", "ollama", "lmstudio"


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

OPENAI_API_KEY = None
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

if LLM_PROVIDER == "groq":
    API_KEY_NAME = "GROQ_API_KEY"
    API_URL = GROQ_API_URL
elif LLM_PROVIDER == "lmstudio":
    API_KEY_NAME = None
    API_URL = LMSTUDIO_API_URL
elif LLM_PROVIDER == "openai":
    API_KEY_NAME = "OPENAI_API_KEY"
    API_URL = OPENAI_API_URL
elif LLM_PROVIDER == "ollama":
    API_KEY_NAME = None
    API_URL = OLLAMA_API_URL
else:
    raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

API_KEY_NAMES = {
    "groq": "GROQ_API_KEY",
    "lmstudio": None,
    "ollama": None,
    "openai": "OPENAI_API_KEY",
    # Add other LLM providers and their respective API key names here
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # in seconds
RETRY_TOKEN_LIMIT = 5000
LLM_URL = GROQ_API_URL

# Model configurations
if LLM_PROVIDER == "groq":
    MODEL_TOKEN_LIMITS = {
        'mixtral-8x7b-32768': 32768,
        'llama3-70b-8192': 8192,
        'llama3-8b-8192': 8192,
        'gemma-7b-it': 8192,
    }
elif LLM_PROVIDER == "lmstudio":
    MODEL_TOKEN_LIMITS = {
        'instructlab/granite-7b-lab-GGUF': 2048,
    } 
elif LLM_PROVIDER == "openai":
    MODEL_TOKEN_LIMITS = {
        'gpt-4o': 4096,
    }
elif LLM_PROVIDER == "ollama":
    MODEL_TOKEN_LIMITS = {
        'llama3': 8192,
    }   
else:
    MODEL_TOKEN_LIMITS = {}