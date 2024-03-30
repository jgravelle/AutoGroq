import streamlit as st
from agent_management import add_or_update_agent, delete_agent, display_agents, process_agent_interaction
from ui_utils import display_discussion_and_whiteboard, display_user_input, display_rephrased_request, display_reset_button, display_user_request_input, handle_begin

def main():
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

    # Default values for session state
    if "discussion" not in st.session_state:
        st.session_state.discussion = ""
    if "whiteboard" not in st.session_state:
        st.session_state.whiteboard = ""

    user_request = display_user_request_input()
    display_agents()
    display_rephrased_request()
    display_discussion_and_whiteboard()
    user_input = display_user_input()
    display_reset_button()

if __name__ == "__main__":
    main()