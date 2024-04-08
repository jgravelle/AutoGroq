import streamlit as st 
from agent_management import add_or_update_agent, delete_agent, display_agents, display_file_management_sidebar, process_agent_interaction 
from ui_utils import display_discussion_and_whiteboard, display_user_input, display_rephrased_request, display_reset_button, display_user_request_input, handle_begin 

def main(): 
    host = st.experimental_get_query_params().get("host", [""])[0]
    if "streamlit.app" in host:
        st.error("This software writes files to the hard drive and cannot be run on streamlit.app. Please run it on a local development machine.")
        return
    
    with open("styles.css") as f: 
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True) 
    
    model_token_limits = { 
        'mixtral-8x7b-32768': 32768, 
        'llama2-70b-4096': 4096, 
        'gemma-7b-it': 8192 
    } 
    
    col1, col2, col3 = st.columns([2, 5, 3]) 
    with col3: 
        selected_model = st.selectbox( 
            'Select Model', 
            options=list(model_token_limits.keys()), 
            index=0, 
            key='model_selection' 
        ) 
        st.session_state.model = selected_model 
        st.session_state.max_tokens = model_token_limits[selected_model] 
        
    st.title("AutoGroq") 
        
    # Ensure default values for session state are set     
    if "discussion" not in st.session_state: 
        st.session_state.discussion = "" 
    if "whiteboard" not in st.session_state: 
        st.session_state.whiteboard = "" # Apply CSS classes to elements 
    
    with st.sidebar: 
        st.markdown('<div class="sidebar">', unsafe_allow_html=True) 
        display_agents() 
        display_file_management_sidebar() 
        st.markdown('</div>', unsafe_allow_html=True) 
    
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
        display_reset_button() 
        st.markdown('</div>', unsafe_allow_html=True) 
    
if __name__ == "__main__": 
    main()