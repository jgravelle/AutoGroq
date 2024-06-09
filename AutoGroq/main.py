import streamlit as st 

from config import LLM_PROVIDER, MODEL_TOKEN_LIMITS

from agent_management import display_agents
from utils.api_utils import set_llm_provider_title
from utils.session_utils import initialize_session_variables
from utils.ui_utils import (
    display_goal, display_reset_and_upload_buttons, 
    display_user_request_input, handle_user_request, key_prompt, 
    load_tool_functions, select_model, set_css, 
    set_temperature, show_interfaces, show_tools
)


def main():
    set_css()
    initialize_session_variables()
    load_tool_functions()
    key_prompt()
    set_llm_provider_title()



    col1, col2 = st.columns([1, 1])  # Adjust the column widths as needed
    with col1:
        select_model()

    with col2:
        set_temperature()


    with st.sidebar:
        display_agents()
        if "agents" in st.session_state and st.session_state.agents:
            display_goal()
            show_tools()
        else:
            st.empty()  

    with st.container():
        if st.session_state.get("rephrased_request", "") == "":
            user_request = st.text_input("Enter your request:", key="user_request", value=st.session_state.get("user_request", ""), on_change=handle_user_request, args=(st.session_state,))
            display_user_request_input()
        if "agents" in st.session_state and st.session_state.agents:
            show_interfaces()
            display_reset_and_upload_buttons()
        

if __name__ == "__main__":
    main()