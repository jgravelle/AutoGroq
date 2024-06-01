import streamlit as st 

from config import LLM_PROVIDER, MODEL_TOKEN_LIMITS

from agent_management import display_agents
from utils.api_utils import set_llm_provider_title
from utils.session_utils import initialize_session_variables
from utils.ui_utils import ( display_download_and_export_buttons,
    display_reset_and_upload_buttons, key_prompt, 
    load_skill_functions, select_model, set_css, 
    set_temperature, show_interfaces, show_skills
)


def main():
    set_css()
    initialize_session_variables()
    load_skill_functions()
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
            show_skills()
        else:
            st.empty()  

    with st.container():
        show_interfaces()
        

    display_reset_and_upload_buttons()
    display_download_and_export_buttons()
    

if __name__ == "__main__":
    main()