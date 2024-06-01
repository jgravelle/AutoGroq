
import importlib
import requests
import streamlit as st
import time

from config import API_URL, LLM_PROVIDER, RETRY_TOKEN_LIMIT


def get_llm_provider(api_key=None, api_url=None, provider=None):
    if provider is None:
        provider = LLM_PROVIDER
    provider_module = importlib.import_module(f"llm_providers.{provider}_provider")
    provider_class = getattr(provider_module, f"{provider.capitalize()}Provider")
    if api_url is None:
        api_url = API_URL
    return provider_class(api_url=api_url, api_key=api_key)


def make_api_request(url, data, headers, api_key):
    time.sleep(2)  # Throttle the request to ensure at least 2 seconds between calls
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
