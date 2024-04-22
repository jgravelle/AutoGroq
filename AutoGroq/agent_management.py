import base64
import streamlit as st
import json
import os
import re

from api_utils import send_request_to_groq_api      
from file_utils import create_agent_data                
from ui_utils import update_discussion_and_whiteboard


def agent_button_callback(agent_index):
    # Callback function to handle state update and logic execution
    def callback():
        st.session_state['selected_agent_index'] = agent_index
        agent = st.session_state.agents[agent_index]
        agent_name = agent['config']['name'] if 'config' in agent and 'name' in agent['config'] else ''
        st.session_state['form_agent_name'] = agent_name
        st.session_state['form_agent_description'] = agent['description'] if 'description' in agent else ''
        # Directly call process_agent_interaction here if appropriate
        process_agent_interaction(agent_index)
    return callback


def delete_agent(index):
    if 0 <= index < len(st.session_state.agents):
        expert_name = st.session_state.agents[index]["expert_name"]
        del st.session_state.agents[index]
        
        # Get the full path to the JSON file
        agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))
        json_file = os.path.join(agents_dir, f"{expert_name}.json")
        
        # Delete the corresponding JSON file
        if os.path.exists(json_file):
            os.remove(json_file)
            print(f"JSON file deleted: {json_file}")
        else:
            print(f"JSON file not found: {json_file}")
        
        st.experimental_rerun()


def display_agents():
    if "agents" in st.session_state and st.session_state.agents:
        st.sidebar.title("Your Agents")
        st.sidebar.subheader("click to interact")
        for index, agent in enumerate(st.session_state.agents):
            agent_name = agent["config"]["name"]
            if "next_agent" in st.session_state and st.session_state.next_agent == agent_name:
                button_style = """
                <style>
                div[data-testid*="stButton"] > button[kind="secondary"] {
                    background-color: green !important;
                    color: white !important;
                }
                </style>
                """
                st.sidebar.markdown(button_style, unsafe_allow_html=True)
            st.sidebar.button(agent_name, key=f"agent_{index}", on_click=agent_button_callback(index))
    else:
        st.sidebar.warning("AutoGroq creates your entire team of Autogen and CrewAI agents from a simple task request, including an Autogen workflow file.<br><br/>You can test your agents with this interface.<br><br/>No agents have yet been created. Please enter a new request.")


def download_agent_file(expert_name):
    # Format the expert_name
    formatted_expert_name = re.sub(r'[^a-zA-Z0-9\s]', '', expert_name)  # Remove non-alphanumeric characters
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')  # Convert to lowercase and replace spaces with underscores

    # Get the full path to the agent JSON file
    agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))
    json_file = os.path.join(agents_dir, f"{formatted_expert_name}.json")

    # Check if the file exists
    if os.path.exists(json_file):
        # Read the file content
        with open(json_file, "r") as f:
            file_content = f.read()

        # Encode the file content as base64
        b64_content = base64.b64encode(file_content.encode()).decode()

        # Create a download link
        href = f'<a href="data:application/json;base64,{b64_content}" download="{formatted_expert_name}.json">Download {formatted_expert_name}.json</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error(f"File not found: {json_file}")


def process_agent_interaction(agent_index):
    # Retrieve agent information using the provided index
    agent = st.session_state.agents[agent_index]

    # Preserve the original "Act as" functionality
    agent_name = agent["config"]["name"]
    description = agent["description"]
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')
    rephrased_request = st.session_state.get('rephrased_request', '')

    request = f"Act as the {agent_name} who {description}."
    if user_request:
        request += f" Original request was: {user_request}."
    if rephrased_request:
        request += f" You are helping a team work on satisfying {rephrased_request}."
    if user_input:
        request += f" Additional input: {user_input}."
    if st.session_state.discussion:
        request += f" The discussion so far has been {st.session_state.discussion[-50000:]}."

    response = send_request_to_groq_api(agent_name, request)
    if response:
        update_discussion_and_whiteboard(agent_name, response, user_input)

    # Additionally, populate the sidebar form with the agent's information
    st.session_state['form_agent_name'] = agent_name
    st.session_state['form_agent_description'] = description
    st.session_state['selected_agent_index'] = agent_index  # Keep track of the selected agent for potential updates/deletes
