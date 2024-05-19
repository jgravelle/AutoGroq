#APIs
LLM_PROVIDER = "groq" # Supported values: "groq", "openai"

if LLM_PROVIDER == "groq":
    API_KEY_NAME = "GROQ_API_KEY"
elif LLM_PROVIDER == "openai":
    API_KEY_NAME = "OPENAI_API_KEY"
else:
    raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

GROQ_API_KEY = None
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

OPENAI_API_KEY = None
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # in seconds
RETRY_TOKEN_LIMIT = 5000
LLM_URL = GROQ_API_URL

# Model configurations
if LLM_PROVIDER == "groq":
    MODEL_TOKEN_LIMITS = {
        'llama3-70b-8192': 8192,
        'llama3-8b-8192': 8192,
        'mixtral-8x7b-32768': 32768,
        'gemma-7b-it': 8192,
    }
elif LLM_PROVIDER == "openai":
    MODEL_TOKEN_LIMITS = {
        'gpt-4o': 4096,
    }
else:
    MODEL_TOKEN_LIMITS = {}