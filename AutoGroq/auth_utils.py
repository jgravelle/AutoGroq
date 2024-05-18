import os
import streamlit as st
from config import GROQ_API_KEY_NAME, LLM_PROVIDER, OPENAI_API_KEY_NAME

def get_api_key():
    if LLM_PROVIDER == "groq":
        api_key_name = GROQ_API_KEY_NAME
    elif LLM_PROVIDER == "openai":
        api_key_name = OPENAI_API_KEY_NAME
    # Add other LLM providers here...
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

    if 'api_key' in st.session_state and st.session_state.api_key:
        api_key = st.session_state.api_key
        print(f"API Key from session state: {api_key}")
        return api_key

    api_key = os.environ.get(api_key_name)
    if api_key:
        print(f"API Key from environment variable: {api_key}")
        return api_key

    api_key = st.secrets.get(api_key_name)
    if api_key:
        print(f"API Key from Streamlit secrets: {api_key}")
        return api_key

    api_key = st.text_input(f"Enter the {api_key_name}:", type="password")
    if api_key:
        st.session_state.api_key = api_key
        st.success("API key entered successfully.")
        return api_key
    else:
        st.warning(f"Please enter the {api_key_name} to use the app.")
        return None