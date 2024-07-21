import os
from typing import Dict

# Get user home directory
home_dir = os.path.expanduser("~")
default_db_path = f'{home_dir}/.autogenstudio/database.sqlite'

# Debug
DEFAULT_DEBUG = False

# Default configurations
DEFAULT_LLM_PROVIDER = "anthropic"
DEFAULT_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
DEFAULT_OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Try to import user-specific configurations from config_local.py
try:
    from config_local import *
except ImportError:
    pass

# Set the configurations using the user-specific values if available, otherwise use the defaults
DEBUG = locals().get('DEBUG', DEFAULT_DEBUG)
LLM_PROVIDER = locals().get('LLM_PROVIDER', DEFAULT_LLM_PROVIDER)

# API URLs for different providers
API_URLS = {
    "groq": locals().get('GROQ_API_URL', DEFAULT_GROQ_API_URL),
    "lmstudio": locals().get('LMSTUDIO_API_URL', DEFAULT_LMSTUDIO_API_URL),
    "ollama": locals().get('OLLAMA_API_URL', DEFAULT_OLLAMA_API_URL),
    "openai": locals().get('OPENAI_API_URL', DEFAULT_OPENAI_API_URL),
    "anthropic": locals().get('ANTHROPIC_API_URL', DEFAULT_ANTHROPIC_API_URL),
}

API_KEY_NAMES = {
    "groq": "GROQ_API_KEY",
    "lmstudio": None,
    "ollama": None,
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # in seconds
RETRY_TOKEN_LIMIT = 5000

# Fallback model configurations (used when API fails)
FALLBACK_MODEL_TOKEN_LIMITS = {
    "anthropic": {
        "claude-3-5-sonnet-20240620": 4096,
        "claude-3-opus-20240229": 4096,
        "claude-3-sonnet-20240229": 4096,
        "claude-3-haiku-20240307": 4096,
        "claude-2.1": 100000,
        "claude-2.0": 100000,
        "claude-instant-1.2": 100000,
    },
    "groq": {
        "mixtral-8x7b-32768": 32768,
        "llama3-70b-8192": 8192,
        "llama3-8b-8192": 8192,
        "gemma-7b-it": 8192,
    },
    "openai": {
        "gpt-4": 8192,
        "gpt-3.5-turbo": 4096,
    },
    "ollama": {
        "llama3": 8192,
    },
    "lmstudio": {
        "instructlab/granite-7b-lab-GGUF": 2048,
        "MaziyarPanahi/Codestral-22B-v0.1-GGUF": 32768,
    },
}

# Database path
FRAMEWORK_DB_PATH = os.environ.get('FRAMEWORK_DB_PATH', default_db_path)

SUPPORTED_PROVIDERS = ["anthropic", "groq", "lmstudio", "ollama", "openai"]

BUILT_IN_AGENTS = ["Web Content Retriever", "Code Developer", "Code Tester"]

AVAILABLE_MODELS: Dict[str, Dict[str, int]] = {}

def update_available_models(provider: str, models: Dict[str, int]):
    """
    Update the available models for a given provider.
    
    :param provider: The name of the provider (e.g., 'groq', 'openai')
    :param models: A dictionary of model names and their token limits
    """
    global AVAILABLE_MODELS
    AVAILABLE_MODELS[provider] = models