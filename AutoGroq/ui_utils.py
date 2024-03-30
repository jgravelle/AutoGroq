import streamlit as st
from api_utils import rephrase_prompt, get_agents_from_text, extract_code_from_response

def display_discussion_and_whiteboard():
    col1, col2 = st.columns(2)
    with col1:
        st.text_area("Discussion", value=st.session_state.discussion, height=400, key="discussion")
    with col2:
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard")

def display_user_input():
    user_input = st.text_area("Additional Input:", key="user_input", height=100)
    return user_input

def display_rephrased_request():
    st.text_area("Rephrased Request:", value=st.session_state.get('rephrased_request', ''), height=100, key="rephrased_request_area")

def display_reset_button():
    if st.button("Reset", key="reset_button"):
        # Reset specific elements without clearing entire session state
        for key in ["rephrased_request", "discussion", "whiteboard", "user_request", "user_input", "agents"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.show_begin_button = True
        st.experimental_rerun()

def display_user_request_input():
    user_request = st.text_input("Enter your request:", key="user_request", on_change=handle_begin, args=(st.session_state,))
    return user_request

def handle_begin(session_state):
    user_request = session_state.user_request
    try:
        rephrased_text = rephrase_prompt(user_request)
        if rephrased_text:
            session_state.rephrased_request = rephrased_text
            agents = get_agents_from_text(rephrased_text)
            session_state.agents = agents
        else:
            raise ValueError("Failed to extract a valid rephrased request.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def update_discussion_and_whiteboard(expert_name, response, user_input):
    if user_input:
        user_input_text = f"\n\nAdditional Input:\n\n{user_input}\n\n"
        st.session_state.discussion += user_input_text
    response_with_expert = f"\n\n{expert_name}:\n\n{response}\n\n===\n\n"
    st.session_state.discussion += response_with_expert
    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard = code_blocks       