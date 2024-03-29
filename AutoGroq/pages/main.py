import sys
import os
import json

project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
print(f"Adding to sys.path: {project_dir}")
sys.path.append(project_dir)
import streamlit as st
from auto_groq_utils import rephrase_prompt, get_agents_from_text, send_request_to_groq_api, extract_code_from_response

def process_agent_interaction(agent):
    # Handles logic when an agent button is clicked, using 'user_request' and 'user_input'.
    st.session_state.selected_agent = agent
    expert_name = agent["expert_name"]
    description = agent["description"]
    # Use the original user request if available.
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')  # Get additional user input.
    rephrased_request = st.session_state.get('rephrased_request', '')

    request = f"Act as the {expert_name} who {description}."
    if user_request:
        request += f" Original request was: {user_request}."
    if rephrased_request:
        request += f" You are helping a team work on satisfying {rephrased_request}."
    if user_input:  # Include user_input in the request if available.
        request += f" Additional input: {user_input}."
    if st.session_state.discussion:
        request += f" The discussion so far has been {st.session_state.discussion[-50000:]}."

    response = send_request_to_groq_api(expert_name, request)
    if response:
        update_discussion_and_whiteboard(expert_name, response, user_input)  # Pass user_input to the update function.

def update_discussion_and_whiteboard(expert_name, response, user_input):
    if user_input:  # Append user_input to the discussion if available.
        user_input_text = f"\n\nAdditional Input:\n\n{user_input}\n\n"
        st.session_state.discussion += user_input_text
    response_with_expert = f"\n\n{expert_name}:\n\n{response}\n\n===\n\n"
    st.session_state.discussion += response_with_expert
    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard += "\n\n" + code_blocks

def display_agents():
    if "agents" in st.session_state:
        st.sidebar.title("Agents")
        for index, agent in enumerate(st.session_state.agents):
            expert_name = agent["expert_name"]
            description = agent["description"]
            unique_key = f"agent_{expert_name}_{index}"
            if st.sidebar.button(expert_name, key=unique_key):
                process_agent_interaction(agent)

def main():
    st.title("AutoGroq")

    # Default values for session state
    if "show_begin_button" not in st.session_state:
        st.session_state.show_begin_button = True
    if "discussion" not in st.session_state:
        st.session_state.discussion = ""
    if "whiteboard" not in st.session_state:
        st.session_state.whiteboard = ""

    user_request = st.text_input("Enter your request:", key="user_request")

    if st.session_state.show_begin_button:
        if st.button("Begin", key="begin_button") and user_request:
            handle_begin(user_request)

    display_agents()

    st.text_area("Rephrased Request:", value=st.session_state.get('rephrased_request', ''), height=100, key="rephrased_request_area")

    col1, col2 = st.columns(2)
    with col1:
        st.text_area("Discussion", value=st.session_state.discussion, height=400, key="discussion")
    with col2:
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard")

    user_input = st.text_area("Additional Input:", key="user_input", height=100)

    if st.button("Reset", key="reset_button"):
        # Reset specific elements without clearing entire session state
        for key in ["rephrased_request", "discussion", "whiteboard", "user_request", "user_input", "agents"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.show_begin_button = True
        st.experimental_rerun()

def handle_begin(user_request):
    try:
        # Directly use the response from rephrase_prompt without trying to parse it as JSON again
        rephrased_text = rephrase_prompt(user_request)
        
        # No need to parse rephrased_text as JSON again, it's already the final text
        if rephrased_text:
            # Directly use rephrased_text
            st.session_state.rephrased_request = rephrased_text
            
            # Extract content before the first HTML tag ("<") if necessary
            # If your application logic requires removing HTML tags or further processing, do it here
            
            agents = get_agents_from_text(rephrased_text)  # Assuming this function expects the rephrased text
            st.session_state.agents = agents
            st.session_state.show_begin_button = False
        else:
            raise ValueError("Failed to extract a valid rephrased request.")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.session_state.show_begin_button = True  # Show 'Begin' button again upon encountering an error


if __name__ == "__main__":
    main()