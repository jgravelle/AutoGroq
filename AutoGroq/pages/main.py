import streamlit as st
from agent_management import add_or_update_agent, delete_agent, display_agents, process_agent_interaction
from api_utils import extract_code_from_response
from ui_utils import display_discussion_and_whiteboard, display_user_input, display_rephrased_request, display_reset_button, display_user_request_input, handle_begin

def main():
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