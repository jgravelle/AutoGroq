
import argparse
import datetime
import json
import os
import streamlit as st
import sys

# Add the root directory to the Python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.config import FALLBACK_MODEL_TOKEN_LIMITS
from prompts import get_agent_prompt
from utils.api_utils import get_llm_provider
from utils.agent_utils import create_agent_data
from utils.auth_utils import get_api_key
from utils.file_utils import sanitize_text

def create_agent(request, provider, model, temperature, max_tokens, output_file):
    # Get the API key and provider
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)

    # Generate the prompt using get_agent_prompt
    prompt = get_agent_prompt(request)

    # Adjust the token limit based on the selected model
    max_tokens = FALLBACK_MODEL_TOKEN_LIMITS.get(provider, {}).get(model, 4096)

    # Make the request to the LLM API
    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = llm_provider.send_request(llm_request_data)

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(response.text)
        return

    response_data = response.json()

    if 'choices' not in response_data or len(response_data['choices']) == 0:
        print("Error: 'choices' not found in the response data or it's empty")
        print(json.dumps(response_data, indent=2))
        return

    agent_description = response_data['choices'][0]['message']['content'].strip()

    agent_data = {
        "type": "assistant",
        "config": {
            "name": request,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "model": model,
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": "OpenAI model configuration"
                    }
                ],
                "temperature": temperature,
                "cache_seed": None,
                "timeout": None,
                "max_tokens": max_tokens,
                "extra_body": None
            },
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 8,
            "system_message": f"You are a helpful assistant that can act as {sanitize_text(agent_description)} who {request}.",
            "is_termination_msg": None,
            "code_execution_config": None,
            "default_auto_reply": "",
            "description": agent_description  # Ensure the description key is present
        },
        "timestamp": datetime.datetime.now().isoformat(),
        "user_id": "default",
        "tools": []
    }

    # Debug print to verify agent_data
    print("Agent Data:", json.dumps(agent_data, indent=2))

    # Create the appropriate agent data
    autogen_agent_data, crewai_agent_data = create_agent_data(agent_data)

    # Save the agent data to the output file
    with open(output_file, "w") as f:
        json.dump(autogen_agent_data, f, indent=2)

    print(f"Agent created successfully. Output saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an agent based on a user request.")
    parser.add_argument("--request", required=True, help="The user request for creating the agent.")
    parser.add_argument("--model", default="mixtral-8x7b-32768", help="The model to use for the agent.")
    parser.add_argument("--temperature", type=float, default=0.5, help="The temperature value for the agent.")
    parser.add_argument("--max_tokens", type=int, default=32768, help="The maximum number of tokens for the agent.")
    parser.add_argument("--agent_type", default="autogen", choices=["autogen", "crewai"], help="The type of agent to create.")
    parser.add_argument("--output", default="agent.json", help="The output file path for the agent JSON.")
    parser.add_argument("--provider", default="groq", help="The LLM provider to use (e.g., 'openai', 'anthropic').")
    
    args = parser.parse_args()
    create_agent(args.request, args.provider, args.model, args.temperature, args.max_tokens, args.output)
    