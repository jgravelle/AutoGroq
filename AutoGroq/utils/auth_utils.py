
import os
import streamlit as st

from configs.config import LLM_PROVIDER
from utils.api_utils import display_api_key_input

        
def check_api_key(provider=None):
    # Ensure we have a warning placeholder
    if 'warning_placeholder' not in st.session_state:
        st.session_state.warning_placeholder = st.empty()

    # Check for API key of the default provider on initial load
    if 'initial_api_check' not in st.session_state:
        st.session_state.initial_api_check = True
        default_provider = st.session_state.get('provider', LLM_PROVIDER)
        if not check_api_key(default_provider):
            display_api_key_input(default_provider)
    return True


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
