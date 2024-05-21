import os
import streamlit as st 

from config import LLM_PROVIDER, MODEL_TOKEN_LIMITS

from agent_management import display_agents
from auth_utils import get_api_key
from ui_utils import display_api_key_input, display_discussion_and_whiteboard, display_download_button, display_user_input, display_rephrased_request, display_reset_and_upload_buttons, display_user_request_input, load_skill_functions


def main(): 
    # Construct the relative path to the CSS file
    css_file = "AutoGroq/style.css"

    # Check if the CSS file exists
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found: {os.path.abspath(css_file)}")

    load_skill_functions()

    api_key = get_api_key()
    if api_key is None:
        api_key = display_api_key_input()
        if api_key is None:
            llm = LLM_PROVIDER.upper()
            st.warning(f"{llm}_API_KEY not found. Please enter your API key.")
            return

    
    col1, col2 = st.columns([1, 1])  # Adjust the column widths as needed
    with col1:
        selected_model = st.selectbox(
            'Select Model',
            options=list(MODEL_TOKEN_LIMITS.keys()),
            index=0,
            key='model_selection'
        )
        st.session_state.model = selected_model
        st.session_state.max_tokens = MODEL_TOKEN_LIMITS[selected_model]

    with col2:
        temperature = st.slider(
            "Set Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.get('temperature', 0.3),
            step=0.01,
            key='temperature'
        )

    # If the LLM Provider is "groq", the title is "AutoGroq"
    if LLM_PROVIDER == "groq":
        st.title("AutoGroq")
    elif LLM_PROVIDER == "ollama":
        st.title("Auto̶G̶r̶o̶qOllama")
    elif LLM_PROVIDER == "lmstudio":
        st.title("Auto̶G̶r̶o̶qLM_Studio")
    elif LLM_PROVIDER == "openai":
        st.title("Auto̶G̶r̶o̶qChatGPT") 
    
        
    # Ensure default values for session state are set     
    if "discussion" not in st.session_state: 
        st.session_state.discussion = ""
    if "whiteboard" not in st.session_state: 
        st.session_state.whiteboard = "" # Apply CSS classes to elements 
    
    with st.sidebar: 
        st.markdown('<div class="sidebar">', unsafe_allow_html=True) 
        st.markdown('</div>', unsafe_allow_html=True) 

    display_agents() 
    
    with st.container(): 
        st.markdown('<div class="main">', unsafe_allow_html=True) 
        display_user_request_input() 
        display_rephrased_request() 
        st.markdown('<div class="discussion-whiteboard">', unsafe_allow_html=True) 
        display_discussion_and_whiteboard() 
        st.markdown('</div>', unsafe_allow_html=True) 
        st.markdown('<div class="user-input">', unsafe_allow_html=True) 
        display_user_input() 
        st.markdown('</div>', unsafe_allow_html=True) 
        display_reset_and_upload_buttons() 
        st.markdown('</div>', unsafe_allow_html=True) 

    display_download_button()        
    
if __name__ == "__main__": 
    main()