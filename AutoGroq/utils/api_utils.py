# utils/api_utils.py

import importlib
import os
import requests
import streamlit as st
import time

from configs.config import FALLBACK_MODEL_TOKEN_LIMITS, LLM_PROVIDER, RETRY_DELAY, RETRY_TOKEN_LIMIT


def display_api_key_input(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key_env_var = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    
    if api_key is None:
        st.session_state.warning_placeholder.warning(f"{provider.upper()} API Key not found. Please enter your API key, or select a different provider.")
    api_key = st.text_input(f"Enter your {provider.upper()} API Key:", type="password", key=f"api_key_input_{provider}")
    if api_key:
        st.session_state[api_key_env_var] = api_key
        os.environ[api_key_env_var] = api_key
        # st.success(f"{provider.upper()} API Key entered successfully.")
        st.session_state.warning_placeholder.empty()
    return api_key


def fetch_available_models(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key = get_api_key(provider)
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)
    try:
        models = llm_provider.get_available_models()
        st.session_state.available_models = models
        return models
    except Exception as e:
        st.error(f"Failed to fetch available models for {provider}: {str(e)}")
        return FALLBACK_MODEL_TOKEN_LIMITS.get(provider, {})
    

def get_api_key(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key_env_var = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    if api_key is None:
        api_key = st.session_state.get(api_key_env_var)
    return api_key


def get_llm_provider(api_key=None, api_url=None, provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    provider_module = importlib.import_module(f"llm_providers.{provider}_provider")
    provider_class = getattr(provider_module, f"{provider.capitalize()}Provider")
    if api_url is None:
        api_url = st.session_state.get(f'{provider.upper()}_API_URL')
    return provider_class(api_url=api_url, api_key=api_key)


def make_api_request(url, data, headers, api_key):
    time.sleep(RETRY_DELAY)  # Throttle the request to ensure at least 2 seconds between calls
    try:
        if not api_key:
            llm = LLM_PROVIDER.upper()
            raise ValueError(f"{llm}_API_KEY not found. Please enter your API key.")
        headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            error_message = response.json().get("error", {}).get("message", "")
            st.error(f"Rate limit reached for the current model. If you click 'Update' again, we'll retry with a reduced token count.  Or you can try selecting a different model.")
            st.error(f"Error details: {error_message}")
            return None
        else:
            print(f"Error: API request failed with status {response.status_code}, response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error: Request failed {e}")
        return None
    

def send_request_with_retry(url, data, headers, api_key):
    response = make_api_request(url, data, headers, api_key)
    if response is None:
        # Add a retry button
        if st.button("Retry with decreased token limit"):
            # Update the token limit in the request data
            data["max_tokens"] = RETRY_TOKEN_LIMIT
            # Retry the request with the decreased token limit
            print(f"Retrying the request with decreased token limit.")
            print(f"URL: {url}")
            print(f"Retry token limit: {RETRY_TOKEN_LIMIT}")
            response = make_api_request(url, data, headers, api_key)
            if response is not None:
                print(f"Retry successful. Response: {response}")
            else:
                print("Retry failed.")
    return response    


def set_llm_provider_title():
    # "What's life without whimsy?" ~Sheldon Cooper
    if LLM_PROVIDER == "groq":
        st.title("AutoGroq™")
    elif LLM_PROVIDER == "ollama":
        st.title("Auto̶G̶r̶o̶qOllama")
    elif LLM_PROVIDER == "lmstudio":
        st.title("Auto̶G̶r̶o̶qLM_Studio")
    elif LLM_PROVIDER == "openai":
        st.title("Auto̶G̶r̶o̶qChatGPT")
    elif LLM_PROVIDER == "anthropic":
        st.title("Auto̶G̶r̶o̶qClaude")

