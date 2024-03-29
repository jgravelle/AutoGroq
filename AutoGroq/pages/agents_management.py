import streamlit as st
import requests
import json
import re

def rephrase_prompt(user_request):
    url = "https://j.gravelle.us/APIs/Groq/groqApiRephrasePrompt.php"
    data = {"user_request": user_request}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=data, headers=headers)  # Use json=data for correct JSON formatting
        print(f"Debug: API request sent: {json.dumps(data)}")
        print(f"Debug: API response received: {response.text}")

        if response.status_code == 200:
            try:
                # First, attempt to parse the response as JSON
                json_response = response.json()
                # If parsing is successful and 'rephrased' key exists, return its value
                if 'rephrased' in json_response:
                    return json_response['rephrased']
                else:
                    # If JSON is valid but doesn't have 'rephrased' key, log and handle the case
                    st.error("Error: 'rephrased' key not found in the API response.")
                    return ""
            except ValueError:
                # If response is not JSON, assume it's plain text and return directly
                return response.text
        else:
            st.error(f"Error: API request failed with status code {response.status_code}")
            return ""
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")
        return ""

def get_agents_from_text(text):
    url = "https://j.gravelle.us/APIs/Groq/groqApiGetAgentsFromPrompt.php"
    data = {"user_request": text}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(f"Debug: API request sent: {json.dumps(data)}")
        print(f"Debug: API response received: {response.text}")

        if response.status_code == 200:
            try:
                agents = response.json()
                return agents
            except json.JSONDecodeError:
                st.error("Error: Unable to parse the API response as JSON.")
        else:
            st.error(f"Error: API request failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")

    return []

def send_request_to_groq_api(expert_name, request):
    url = "https://j.gravelle.us/APIs/Groq/groqAPI.php"
    data = {
        "model": "mixtral-8x7b-32768",
        "temperature": 0.5,
        "max_tokens": 32768,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "system",
                "content": "You are a chatbot capable of anything and everything."
            },
            {
                "role": "user",
                "content": request
            }
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(f"Debug: API request sent: {json.dumps(data)}")
        print(f"Debug: API response received: {response.text}")

        if response.status_code == 200:
            try:
                result = response.json()
                message_content = result["choices"][0]["message"]["content"]
                return message_content
            except (KeyError, IndexError, json.JSONDecodeError):
                st.error("Error: Unable to parse the API response.")
        else:
            st.error(f"Error: API request failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")

    return ""

def extract_code_from_response(response):
    code_pattern = r"```(.*?)```"
    code_blocks = re.findall(code_pattern, response, re.DOTALL)

    html_pattern = r"<html.*?>.*?</html>"
    html_blocks = re.findall(html_pattern, response, re.DOTALL | re.IGNORECASE)

    js_pattern = r"<script.*?>.*?</script>"
    js_blocks = re.findall(js_pattern, response, re.DOTALL | re.IGNORECASE)

    css_pattern = r"<style.*?>.*?</style>"
    css_blocks = re.findall(css_pattern, response, re.DOTALL | re.IGNORECASE)

    code_blocks.extend(html_blocks)
    code_blocks.extend(js_blocks)
    code_blocks.extend(css_blocks)

    code_blocks = [block.strip() for block in code_blocks]
    return "\n\n".join(code_blocks)

...

agents_management.py=

import sys
import os

project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
print(f"Adding to sys.path: {project_dir}")
sys.path.append(project_dir)
import streamlit as st

def add_agent():
    """Display form to add a new agent."""
    st.title("Add New Agent")
    with st.form("agent_form", clear_on_submit=True):
        expert_name = st.text_input("Expert Name", key="new_expert")
        description = st.text_area("Description", key="new_description")
        submit = st.form_submit_button("Submit")
        
        if submit and expert_name and description:
            add_or_update_agent(None, expert_name, description)
            st.success("Agent added successfully!")

def display_agents():
    """Display current agents with options to edit or delete."""
    if "agents" in st.session_state:
        for index, agent in enumerate(st.session_state["agents"]):
            st.write(f"{agent['expert_name']}: {agent['description']}")
            if st.button(f"Edit {agent['expert_name']}", key=f"edit_{index}"):
                st.session_state["editing_index"] = index
                st.experimental_rerun()
            if st.button(f"Delete {agent['expert_name']}", key=f"delete_{index}"):
                delete_agent(index)
                
def edit_agent_form():
    """Display a form to edit an agent's details if an agent is selected for editing."""
    index = st.session_state.get("editing_index")
    if index is not None:
        agent = st.session_state["agents"][index]
        with st.form("edit_agent_form"):
            expert_name = st.text_input("Expert Name", value=agent["expert_name"], key="edit_expert")
            description = st.text_area("Description", value=agent["description"], key="edit_description")
            submit_edit = st.form_submit_button("Update Agent")
            
            if submit_edit:
                add_or_update_agent(index, expert_name, description)
                del st.session_state["editing_index"]
                st.success("Agent updated successfully!")

def add_or_update_agent(index, expert_name, description):
    """Add a new agent or update an existing one in the session state."""
    agent = {"expert_name": expert_name, "description": description}
    if index is None:  # Add new agent
        if "agents" not in st.session_state:
            st.session_state.agents = []
        st.session_state.agents.append(agent)
    else:  # Update existing agent
        st.session_state.agents[index] = agent

def delete_agent(index):
    """Delete an agent from the session state."""
    del st.session_state.agents[index]
    st.experimental_rerun()

def manage_agents():
    add_agent()
    edit_agent_form()
    display_agents()