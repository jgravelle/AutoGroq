import streamlit as st
from api_utils import send_request_to_groq_api
from ui_utils import update_discussion_and_whiteboard

def add_or_update_agent(index, expert_name, description):
    agent = {"expert_name": expert_name, "description": description}
    if index is None:  # Add new agent
        if "agents" not in st.session_state:
            st.session_state.agents = []
        st.session_state.agents.append(agent)
    else:  # Update existing agent
        st.session_state.agents[index] = agent

def delete_agent(index):
    del st.session_state.agents[index]
    st.experimental_rerun()

def display_agents():
    if "agents" in st.session_state:
        st.sidebar.title("Agents")
        for index, agent in enumerate(st.session_state.agents):
            expert_name = agent["expert_name"]
            description = agent["description"]
            unique_key = f"agent_{expert_name}_{index}"
            if st.sidebar.button(expert_name, key=unique_key):
                process_agent_interaction(agent)

def process_agent_interaction(agent):
    st.session_state.selected_agent = agent
    expert_name = agent["expert_name"]
    description = agent["description"]
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')
    rephrased_request = st.session_state.get('rephrased_request', '')

    request = f"Act as the {expert_name} who {description}."
    if user_request:
        request += f" Original request was: {user_request}."
    if rephrased_request:
        request += f" You are helping a team work on satisfying {rephrased_request}."
    if user_input:
        request += f" Additional input: {user_input}."
    if st.session_state.discussion:
        request += f" The discussion so far has been {st.session_state.discussion[-50000:]}."

    response = send_request_to_groq_api(expert_name, request)
    if response:
        update_discussion_and_whiteboard(expert_name, response, user_input)