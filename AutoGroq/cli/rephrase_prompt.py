
import argparse
import os
import sys

# Add the root directory to the Python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.config import FALLBACK_MODEL_TOKEN_LIMITS, LLM_PROVIDER
from utils.api_utils import get_llm_provider
from utils.auth_utils import get_api_key
from utils.ui_utils import rephrase_prompt


def rephrase_prompt_cli(prompt, provider, model, temperature, max_tokens):
    # Get the API key
    api_key = get_api_key()

    # Use the provider specified in the CLI arguments
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)

    # Override the model and max_tokens if specified in the command-line arguments
    model_to_use = model if model else provider
    max_tokens_to_use = FALLBACK_MODEL_TOKEN_LIMITS.get(model_to_use, max_tokens)

    rephrased_prompt = rephrase_prompt(prompt, model_to_use, max_tokens_to_use, llm_provider=llm_provider, provider=provider)

    if rephrased_prompt:
        print(f"Rephrased Prompt: {rephrased_prompt}")
    else:
        print("Error: Failed to rephrase the prompt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rephrase a user prompt.")
    parser.add_argument("--prompt", required=True, help="The user prompt to rephrase.")
    parser.add_argument("--model", default=None, help="The model to use for rephrasing.")
    parser.add_argument("--temperature", type=float, default=0.5, help="The temperature value for rephrasing.")
    parser.add_argument("--max_tokens", type=int, default=32768, help="The maximum number of tokens for rephrasing.")
    parser.add_argument("--provider", default=None, help="The LLM provider to use (e.g., 'openai', 'anthropic').")
    
    args = parser.parse_args()
    rephrase_prompt_cli(args.prompt, args.provider, args.model, args.temperature, args.max_tokens)
