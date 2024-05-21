import os
import streamlit as st

from config import LLM_PROVIDER


def get_api_key():
    api_key_env_var = f"{LLM_PROVIDER.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    if api_key is None:
        api_key = globals().get(api_key_env_var)
        if api_key is None:
            if api_key_env_var not in st.session_state:
                api_key = st.text_input(f"Enter the {LLM_PROVIDER.upper()} API Key:", type="password", key=f"{LLM_PROVIDER}_api_key_input")
                if api_key:
                    st.session_state[api_key_env_var] = api_key
                    st.success("API Key entered successfully.")
                else:
                    st.warning(f"Please enter the {LLM_PROVIDER.upper()} API Key to use the app.")
            else:
                api_key = st.session_state.get(api_key_env_var)
    return api_key

def get_api_url():
    api_url_env_var = f"{LLM_PROVIDER.upper()}_API_URL"
    api_url = os.environ.get(api_url_env_var)
    if api_url is None:
        api_url = globals().get(api_url_env_var)
        if api_url is None:
            if api_url_env_var not in st.session_state:
                api_url = st.text_input(f"Enter the {LLM_PROVIDER.upper()} API URL:", type="password", key=f"{LLM_PROVIDER}_api_url_input")
                if api_url:
                    st.session_state[api_url_env_var] = api_url
                    st.success("API URL entered successfully.")
                else:
                    st.warning(f"Please enter the {LLM_PROVIDER.upper()} API URL to use the app.")
            else:
                api_url = st.session_state.get(api_url_env_var)
    return api_url