import datetime
import json
import os
import pandas as pd
import re
import requests
import streamlit as st
import time

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from configs.config import (DEBUG, LLM_PROVIDER, MAX_RETRIES, 
        FALLBACK_MODEL_TOKEN_LIMITS, RETRY_DELAY, SUPPORTED_PROVIDERS)

from anthropic.types import Message
from configs.current_project import Current_Project
from models.agent_base_model import AgentBaseModel
from models.workflow_base_model import WorkflowBaseModel
from prompts import create_project_manager_prompt, get_agents_prompt, get_rephrased_user_prompt, get_moderator_prompt  
from tools.fetch_web_content import fetch_web_content
from typing import Any, List, Dict, Tuple
from utils.agent_utils import create_agent_data
from utils.api_utils import fetch_available_models, get_api_key, get_llm_provider
from utils.auth_utils import display_api_key_input
from utils.db_utils import export_to_autogen
from utils.file_utils import zip_files_in_memory
from utils.workflow_utils import get_workflow_from_agents
    

def create_agents(json_data: List[Dict[str, Any]]) -> Tuple[List[AgentBaseModel], List[Dict[str, Any]]]:
    autogen_agents = []
    crewai_agents = []
    
    for agent_data in json_data:
        expert_name = agent_data.get('expert_name', '')
        description = agent_data.get('description', '')
        
        if not expert_name:
            print("Missing agent name. Skipping...")
            continue

        autogen_agent_data, crewai_agent_data = create_agent_data({
            "name": expert_name,
            "description": description,
            "role": agent_data.get('role', expert_name),
            "goal": agent_data.get('goal', f"Assist with tasks related to {description}"),
            "backstory": agent_data.get('backstory', f"As an AI assistant, I specialize in {description}")
        })
        
        try:
            agent_model = AgentBaseModel(
                name=autogen_agent_data['name'],
                description=autogen_agent_data['description'],
                tools=autogen_agent_data.get('tools', []),
                config=autogen_agent_data.get('config', {}),
                role=autogen_agent_data['role'],
                goal=autogen_agent_data['goal'],
                backstory=autogen_agent_data['backstory'],
                provider=autogen_agent_data.get('provider', ''),
                model=autogen_agent_data.get('model', '')
            )
            print(f"Created agent: {agent_model.name} with description: {agent_model.description}")
            autogen_agents.append(agent_model)
            crewai_agents.append(crewai_agent_data)
        except Exception as e:
            print(f"Error creating agent {expert_name}: {str(e)}")
            print(f"Agent data: {autogen_agent_data}")
            continue

    return autogen_agents, crewai_agents


def create_project_manager(rephrased_text):
    print(f"Creating Project Manager")
    temperature_value = st.session_state.get('temperature', 0.1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": create_project_manager_prompt(rephrased_text)    
            }
        ]
    }

    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    response = llm_provider.send_request(llm_request_data)
    
    if response is not None:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            return content.strip()
    
    return None


def display_discussion_and_whiteboard():
    tabs = st.tabs(["Discussion", "Whiteboard", "History", "Deliverables", "Download", "Debug"])
    discussion_history = get_discussion_history()

    with tabs[0]:
        # Display only the most recent agent response
        if 'most_recent_response' in st.session_state and st.session_state.most_recent_response:
            st.text_area("Most Recent Response", value=st.session_state.most_recent_response, height=400, key="discussion")
        else:
            st.text_area("Discussion", value="No responses yet.", height=400, key="discussion")

    with tabs[1]:
        # Extract code snippets from the full discussion history
        code_snippets = extract_code_from_response(discussion_history)
        
        # Display code snippets in the whiteboard, allowing editing
        new_whiteboard_content = st.text_area("Whiteboard (Code Snippets)", value=code_snippets, height=400, key="whiteboard")
        
        # Update the whiteboard content in the session state if it has changed
        if new_whiteboard_content != st.session_state.get('whiteboard_content', ''):
            st.session_state.whiteboard_content = new_whiteboard_content

    with tabs[2]:
        st.write(discussion_history)


    with tabs[3]:
        if "current_project" in st.session_state:
            current_project = st.session_state.current_project
            for index, deliverable in enumerate(current_project.deliverables):
                if deliverable["text"].strip():  # Check if the deliverable text is not empty
                    checkbox_key = f"deliverable_{index}"
                    done = st.checkbox(
                        deliverable["text"], 
                        value=current_project.is_deliverable_complete(index),
                        key=checkbox_key,
                        on_change=update_deliverable_status,
                        args=(index,)
                    )
                    if done != deliverable["done"]:
                        if done:
                            current_project.mark_deliverable_phase_done(index, current_project.current_phase)
                        else:
                            current_project.deliverables[index]["done"] = False
                            for phase in current_project.implementation_phases:
                                current_project.deliverables[index]["phase"][phase] = False


    with tabs[4]:
        display_download_button() 
        if st.button("Export to Autogen"):
            export_to_autogen()

    with tabs[5]:
        if DEBUG:
            if "project_model" in st.session_state:
                project_model = st.session_state.project_model
                with st.expander("Project Details"):
                    st.write("ID:", project_model.id)
                    st.write("Re-engineered Prompt:", project_model.re_engineered_prompt)
                    st.write("Deliverables:", project_model.deliverables)
                    st.write("Created At:", project_model.created_at)
                    st.write("Updated At:", project_model.updated_at)
                    st.write("User ID:", project_model.user_id)
                    st.write("Name:", project_model.name)
                    st.write("Description:", project_model.description)
                    st.write("Status:", project_model.status)
                    st.write("Due Date:", project_model.due_date)
                    st.write("Priority:", project_model.priority)
                    st.write("Tags:", project_model.tags)
                    st.write("Attachments:", project_model.attachments)
                    st.write("Notes:", project_model.notes)
                    st.write("Collaborators:", project_model.collaborators)
                    st.write("Workflows:", project_model.workflows)
                    if project_model.tools:
                        st.write("Tools:")
                        for tool in project_model.tools:
                            substring = "init"
                            if not substring in tool.name:
                                st.write(f"- {tool.name}")
                                st.code(tool.content, language="python")
                    else:
                        st.write("Tools: []")
                    

            if "project_model" in st.session_state and st.session_state.project_model.workflows:
                workflow_data = st.session_state.project_model.workflows[0]
                workflow = WorkflowBaseModel.from_dict({**workflow_data, 'settings': workflow_data.get('settings', {})})
                with st.expander("Workflow Details"):
                    st.write("ID:", workflow.id)
                    st.write("Name:", workflow.name)
                    st.write("Description:", workflow.description)
                    
                    # Display the agents in the workflow
                    st.write("Agents:")
                    for agent in workflow.receiver.groupchat_config["agents"]:
                        st.write(f"- {agent['config']['name']}")
                    
                    st.write("Settings:", workflow.settings)    
                    st.write("Created At:", workflow.created_at)
                    st.write("Updated At:", workflow.updated_at)
                    st.write("User ID:", workflow.user_id)
                    st.write("Type:", workflow.type)
                    st.write("Summary Method:", workflow.summary_method)
                    
                    # Display sender details
                    st.write("Sender:")
                    st.write("- Type:", workflow.sender.type)
                    st.write("- Config:", workflow.sender.config)
                    st.write("- Timestamp:", workflow.sender.timestamp)
                    st.write("- User ID:", workflow.sender.user_id)
                    st.write("- Tools:", workflow.sender.tools)
                    
                    # Display receiver details
                    st.write("Receiver:")
                    st.write("- Type:", workflow.receiver.type)
                    st.write("- Config:", workflow.receiver.config)
                    st.write("- Groupchat Config:", workflow.receiver.groupchat_config)
                    st.write("- Timestamp:", workflow.receiver.timestamp)
                    st.write("- User ID:", workflow.receiver.user_id)
                    st.write("- Tools:", workflow.receiver.tools)
                    st.write("- Agents:", [agent.to_dict() for agent in workflow.receiver.agents])
                    
                    st.write("Timestamp:", workflow.timestamp)
            else:
                st.warning("No workflow data available.")
            

            if "agents" in st.session_state:
                with st.expander("Agent Details"):
                    agent_names = ["Select one..."] + [agent.get('name', f"Agent {index + 1}") for index, agent in enumerate(st.session_state.agents)]
                    selected_agent = st.selectbox("Select an agent:", agent_names)

                    if selected_agent != "Select one...":
                        agent_index = agent_names.index(selected_agent) - 1
                        agent = st.session_state.agents[agent_index]

                        st.subheader(selected_agent)
                        st.write("ID:", agent.get('id'))
                        st.write("Name:", agent.get('name'))
                        st.write("Description:", agent.get('description'))
                        
                        # Display the selected tools for the agent
                        st.write("Tools:", ", ".join(agent.get('tools', [])))
                        
                        st.write("Config:", agent.get('config'))
                        st.write("Created At:", agent.get('created_at'))
                        st.write("Updated At:", agent.get('updated_at'))
                        st.write("User ID:", agent.get('user_id'))
                        st.write("Workflows:", agent.get('workflows'))
                        st.write("Type:", agent.get('type'))
                        st.write("Models:", agent.get('models'))
                        st.write("Verbose:", agent.get('verbose'))
                        st.write("Allow Delegation:", agent.get('allow_delegation'))
                        st.write("New Description:", agent.get('new_description'))
                        st.write("Timestamp:", agent.get('timestamp'))
            else:
                st.warning("No agent data available.")

            if len(st.session_state.tool_models) > 0:
                with st.expander("Tool Details"):
                    tool_names = ["Select one..."] + [tool.name for tool in st.session_state.tool_models]
                    selected_tool = st.selectbox("Select a tool:", tool_names)

                    if selected_tool != "Select one...":
                        tool_index = tool_names.index(selected_tool) - 1
                        tool = st.session_state.tool_models[tool_index]
                        
                        st.subheader(selected_tool)
                        
                        # Display tool details in a more visually appealing way
                        col1, col2 = st.columns(RETRY_DELAY)
                        
                        with col1:
                            st.markdown(f"**ID:** {tool.id}")
                            st.markdown(f"**Name:** {tool.name}")
                            st.markdown(f"**Created At:** {tool.created_at}")
                            st.markdown(f"**Updated At:** {tool.updated_at}")
                            st.markdown(f"**User ID:** {tool.user_id}")
                        
                        with col2:
                            st.markdown(f"**Secrets:** {tool.secrets}")
                            st.markdown(f"**Libraries:** {tool.libraries}")
                            st.markdown(f"**File Name:** {tool.file_name}")
                            st.markdown(f"**Timestamp:** {tool.timestamp}")
                            st.markdown(f"**Title:** {tool.title}")

                        st.markdown(f"**Description:** {tool.description}")
                        
                        # Display the tool's content in a code block
                        st.markdown("**Content:**")
                        st.code(tool.content, language="python")
            else:
                st.warning("No tool data available.")

        else:
            st.warning("Debugging disabled.")   
                                    

def display_download_button():
    col1, col2 = st.columns(RETRY_DELAY)
    
    with col1:
        if st.session_state.get('autogen_zip_buffer') is not None:
            st.download_button(
                label="Download Autogen Files",
                data=st.session_state.autogen_zip_buffer,
                file_name="autogen_files.zip",
                mime="application/zip",
                key=f"autogen_download_button_{int(time.time())}"
            )
        else:
            st.warning("Autogen files are not available for download.")
    
    with col2:
        if st.session_state.get('crewai_zip_buffer') is not None:
            st.download_button(
                label="Download CrewAI Files",
                data=st.session_state.crewai_zip_buffer,
                file_name="crewai_files.zip",
                mime="application/zip",
                key=f"crewai_download_button_{int(time.time())}"
            )
        else:
            st.warning("CrewAI files are not available for download.")


def display_download_and_export_buttons():
    display_download_button() 
    if st.button("Export to Autogen"):
            export_to_autogen() 


def display_goal():
    if "current_project" in st.session_state:
        current_project = st.session_state.current_project
        if current_project.re_engineered_prompt:
            st.expander("Goal").markdown(f"**OUR CURRENT GOAL:**\n\r {current_project.re_engineered_prompt}")


def display_user_input():
    user_input = st.text_area("Additional Input:", value=st.session_state.get("user_input", ""), key="user_input_widget", height=100, on_change=update_user_input)
    reference_url = st.text_input("URL:", key="reference_url_widget")

    if user_input:
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        url_match = url_pattern.search(user_input)
        if url_match:
            url = url_match.group()
            if "reference_html" not in st.session_state or url not in st.session_state.reference_html:
                html_content = fetch_web_content(url)
                if html_content:
                    st.session_state.reference_html[url] = html_content
                else:
                    st.warning("Failed to fetch HTML content.")
            else:
                st.session_state.reference_html = {}
        else:
            st.session_state.reference_html = {}
    else:
        st.session_state.reference_html = {}

    return user_input, reference_url


def display_reset_and_upload_buttons():
    col1, col2 = st.columns(RETRY_DELAY)  
    with col1:
        if st.button("Reset", key="reset_button"):
            # Define the keys of session state variables to clear
            keys_to_reset = [
                "rephrased_request", "discussion", "whiteboard", "user_request",
                "user_input", "agents", "zip_buffer", "crewai_zip_buffer",
                "autogen_zip_buffer", "uploaded_file_content", "discussion_history",
                "last_comment", "user_api_key", "reference_url"
            ]
            # Reset each specified key
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            # Additionally, explicitly reset user_input to an empty string
            st.session_state.user_input = ""
            st.session_state.show_begin_button = True
            st.experimental_rerun()
    
    with col2:
        uploaded_file = st.file_uploader("Upload a sample .csv of your data (optional)", type="csv")
        
        if uploaded_file is not None:
            try:
                # Attempt to read the uploaded file as a DataFrame
                df = pd.read_csv(uploaded_file).head(5)
                
                # Display the DataFrame in the app
                st.write("Data successfully uploaded and read as DataFrame:")
                st.dataframe(df)
                
                # Store the DataFrame in the session state
                st.session_state.uploaded_data = df
            except Exception as e:
                st.error(f"Error reading the file: {e}")                


def display_user_request_input():
    if st.session_state.show_request_input:
        if st.session_state.get("previous_user_request") != st.session_state.get("user_request", ""):
            st.session_state.previous_user_request = st.session_state.get("user_request", "")
            if st.session_state.get("user_request", ""):
                handle_user_request(st.session_state)
            else:
                st.session_state.agents = []
                st.session_state.show_request_input = False
            st.experimental_rerun()


def extract_code_from_response(response):
    code_pattern = r"```(.*?)```"
    code_blocks = re.findall(code_pattern, response, re.DOTALL)

    html_pattern = r"<html.*?>.*?</html>"
    html_blocks = re.findall(html_pattern, response, re.DOTALL | re.IGNORECASE)

    js_pattern = r"<script.*?>.*?</script>"
    js_blocks = re.findall(js_pattern, response, re.DOTALL | re.IGNORECASE)

    css_pattern = r"<style.*?>.*?</style>"
    css_blocks = re.findall(css_pattern, response, re.DOTALL | re.IGNORECASE)

    all_code_blocks = code_blocks + html_blocks + js_blocks + css_blocks
    unique_code_blocks = list(set(all_code_blocks))

    return "\n\n".join(unique_code_blocks) 


def extract_content(response: Any) -> str:
    if hasattr(response, 'content') and isinstance(response.content, list):
        # Anthropic-specific handling
        return response.content[0].text
    elif isinstance(response, requests.models.Response):
        # Groq and potentially other providers using requests.Response
        try:
            json_response = response.json()
            if 'choices' in json_response and json_response['choices']:
                return json_response['choices'][0]['message']['content']
        except json.JSONDecodeError:
            print("Failed to decode JSON from response")
            return ""
    elif isinstance(response, dict):
        if 'choices' in response and response['choices']:
            return response['choices'][0]['message']['content']
        elif 'content' in response:
            return response['content']
    elif isinstance(response, str):
        return response
    print(f"Unexpected response format: {type(response)}")
    return ""
 

def extract_json_objects(text: str) -> List[Dict]:
    objects = []
    stack = []
    start_index = 0
    for i, char in enumerate(text):
        if char == "{":
            if not stack:
                start_index = i
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack:
                    objects.append(text[start_index:i+1])
    parsed_objects = []
    for obj_str in objects:
        try:
            parsed_obj = json.loads(obj_str)
            parsed_objects.append(parsed_obj)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON object: {e}")
            print(f"JSON string: {obj_str}")
    return parsed_objects


def get_agents_from_text(text: str) -> Tuple[List[AgentBaseModel], List[Dict[str, Any]]]:
    print("Getting agents from text...")
    
    instructions = get_agents_prompt()
    combined_content = f"{instructions}\n\nTeam of Experts:\n{text}"
    
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "messages": [
            {"role": "user", "content": combined_content}
        ]
    }
    
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    
    try:
        response = llm_provider.send_request(llm_request_data)
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")

        content = extract_content(response)
        
        if not content:
            print("No content extracted from response.")
            return [], []

        print(f"Extracted content: {content}")

        json_data = parse_json(content)
        
        if not json_data:
            print("Failed to parse JSON data.")
            return [], []

        return create_agents(json_data)
    
    except Exception as e:
        print(f"Error in get_agents_from_text: {e}")
        return [], []
    

def get_discussion_history():
    return st.session_state.discussion_history


@st.cache_data(ttl=3600)  # Cache the result for 1 hour
def get_provider_models(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    return st.session_state.get('available_models') or FALLBACK_MODEL_TOKEN_LIMITS.get(provider, {})


def handle_user_request(session_state):
    print("Debug: Handling user request for session state: ", session_state)
    user_request = session_state.user_request
    max_retries = MAX_RETRIES
    retry_delay = RETRY_DELAY

    for retry in range(max_retries):
        try:
            print("Debug: Sending request to rephrase_prompt")
            model = session_state.model
            print(f"Debug: Model: {model}")
            rephrased_text = rephrase_prompt(user_request, model)
            print(f"Debug: Rephrased text: {rephrased_text}")
            if rephrased_text:
                session_state.rephrased_request = rephrased_text
                break
            else:
                print("Error: Failed to rephrase the user request.")
                st.warning("Failed to rephrase the user request. Please try again.")
                return
        except Exception as e:
            print(f"Error occurred in handle_user_request: {str(e)}")
            if retry < max_retries - 1:
                print(f"Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
            else:
                print("Max retries exceeded.")
                st.warning("An error occurred. Please try again.")
                return

    if "rephrased_request" not in session_state:
        st.warning("Failed to rephrase the user request. Please try again.")
        return

    session_state.project_model.description = session_state.user_request
    rephrased_text = session_state.rephrased_request
    session_state.project_model.set_re_engineered_prompt(rephrased_text)

    if "project_manager_output" not in session_state:
        project_manager_output = create_project_manager(rephrased_text)

        if not project_manager_output:
            print("Error: Failed to create Project Manager.")
            st.warning("Failed to create Project Manager. Please try again.")
            return

        session_state.project_manager_output = project_manager_output

        current_project = Current_Project()
        current_project.set_re_engineered_prompt(rephrased_text)

        deliverables_patterns = [
            r"(?:Deliverables|Key Deliverables):\n(.*?)(?=Timeline|Team of Experts|$)",
            r"\*\*(?:Deliverables|Key Deliverables):\*\*\n(.*?)(?=\*\*Timeline|\*\*Team of Experts|$)"
        ]

        deliverables_text = None
        for pattern in deliverables_patterns:
            match = re.search(pattern, project_manager_output, re.DOTALL)
            if match:
                deliverables_text = match.group(1).strip()
                break

        if deliverables_text:
            deliverables = re.findall(r'\d+\.\s*(.*)', deliverables_text)
            for deliverable in deliverables:
                current_project.add_deliverable(deliverable.strip())
                session_state.project_model.add_deliverable(deliverable.strip())
        else:
            print("Warning: 'Deliverables' or 'Key Deliverables' section not found in Project Manager's output.")

        session_state.current_project = current_project

        update_discussion_and_whiteboard("Project Manager", project_manager_output, "")
    else:
        project_manager_output = session_state.project_manager_output

    team_of_experts_patterns = [
        r"\*\*Team of Experts:\*\*\n(.*)",
        r"Team of Experts:\n(.*)"
    ]

    team_of_experts_text = None
    for pattern in team_of_experts_patterns:
        match = re.search(pattern, project_manager_output, re.DOTALL)
        if match:
            team_of_experts_text = match.group(1).strip()
            break

    if team_of_experts_text:
        autogen_agents, crewai_agents = get_agents_from_text(team_of_experts_text)

        if not autogen_agents:
            print("Error: No agents created.")
            st.warning("Failed to create agents. Please try again.")
            return

        session_state.agents = autogen_agents
        session_state.workflow.agents = session_state.agents

        # Generate the workflow data
        workflow_data, _ = get_workflow_from_agents(autogen_agents)
        workflow_data["created_at"] = datetime.datetime.now().isoformat()
        print(f"Debug: Workflow data: {workflow_data}")
        print(f"Debug: CrewAI agents: {crewai_agents}")

        if workflow_data:
            autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
            session_state.autogen_zip_buffer = autogen_zip_buffer
            session_state.crewai_zip_buffer = crewai_zip_buffer
        else:
            session_state.autogen_zip_buffer = None
            session_state.crewai_zip_buffer = None

        # Update the project session state with the workflow data
        session_state.project_model.workflows = [workflow_data]

        print("Debug: Agents in session state project workflow:")
        for agent in workflow_data["receiver"]["groupchat_config"]["agents"]:
            print(agent)

        # Indicate that a rerun is needed
        session_state.need_rerun = True
    else:
        print("Error: 'Team of Experts' section not found in Project Manager's output.")
        st.warning("Failed to extract the team of experts from the Project Manager's output. Please try again.")
        return
    

def key_prompt():
    api_key = get_api_key()
    api_key = display_api_key_input()
    if api_key is None:
        llm = LLM_PROVIDER.upper()
        st.warning(f"{llm}_API_KEY not found, or select a different provider.")
        return


def parse_json(content: str) -> List[Dict[str, Any]]:
    try:
        json_data = json.loads(content)
        if isinstance(json_data, list):
            return json_data
        else:
            print("JSON data is not a list as expected.")
            return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Content: {content}")
        return []


def rephrase_prompt(user_request, model, max_tokens=None, llm_provider=None, provider=None):
    print("Executing rephrase_prompt()")

    refactoring_prompt = get_rephrased_user_prompt(user_request)

    if llm_provider is None:
        api_key = get_api_key()
        try:
            llm_provider = get_llm_provider(api_key=api_key, provider=provider)
        except Exception as e:
            print(f"Error initializing LLM provider: {str(e)}")
            return None

    if max_tokens is None:
        max_tokens = llm_provider.get_available_models().get(model, 4096)

    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": refactoring_prompt,
            },
        ],
    }

    try:
        print("Sending request to LLM API...")
        print(f"Request Details:")
        print(f"Provider: {provider}")
        print(f"llm_provider: {llm_provider}")
        print(f" Model: {model}")
        print(f" Max Tokens: {max_tokens}")
        print(f" Messages: {llm_request_data['messages']}")

        response = llm_provider.send_request(llm_request_data)
        
        if response is None:
            print("Error: No response received from the LLM provider.")
            return None

        print(f"Response received. Processing response...")
        response_data = llm_provider.process_response(response)
        print(f"Response Data: {json.dumps(response_data, indent=2)}")

        if "choices" in response_data and len(response_data["choices"]) > 0:
            rephrased = response_data["choices"][0]["message"]["content"]
            return rephrased.strip()
        else:
            print("Error: Unexpected response format. 'choices' field missing or empty.")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def select_model():
    provider = st.session_state.get('provider', LLM_PROVIDER)
    provider_models = get_provider_models(provider)
    
    if not provider_models:
        st.warning(f"No models available for {provider}. Please check your API key and connection.")
        return None

    if 'model' not in st.session_state or st.session_state.model not in provider_models:
        default_model = next(iter(provider_models))
    else:
        default_model = st.session_state.model
    
    selected_model = st.selectbox(
        'Select Model',
        options=list(provider_models.keys()),
        index=list(provider_models.keys()).index(default_model),
        key='model_selection'
    )
    
    st.session_state.model = selected_model
    st.session_state.max_tokens = provider_models[selected_model]
    
    return selected_model


def select_provider():
    selected_provider = st.selectbox(
        'Select Provider',
        options=SUPPORTED_PROVIDERS,
        index=SUPPORTED_PROVIDERS.index(st.session_state.get('provider', LLM_PROVIDER)),
        key='provider_selection'
    )
    
    if selected_provider != st.session_state.get('provider'):
        st.session_state.provider = selected_provider
        update_api_url(selected_provider)
        
        # Clear any existing warnings
        if 'warning_placeholder' in st.session_state:
            st.session_state.warning_placeholder.empty()
        
        # Check for API key and prompt if not found
        api_key = get_api_key(selected_provider)
        if api_key is None:
            display_api_key_input(selected_provider)
        else:
            # Fetch available models for the selected provider
            fetch_available_models(selected_provider)
        
        # Clear the model selection when changing providers
        if 'model' in st.session_state:
            del st.session_state.model
        
        # Trigger a rerun to update the UI
        st.experimental_rerun()
    
    return selected_provider


def set_css():
    parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css_file = os.path.join(parent_directory, "style.css")

    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found: {os.path.abspath(css_file)}")


def set_temperature():
    def update_temperature(value):
        st.session_state.temperature = value

    temperature_slider = st.slider(
        "Set Temperature",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        key='temperature_slider',
        on_change=update_temperature,
        args=(st.session_state.temperature_slider,)
    )

    if 'temperature' not in st.session_state:
        st.session_state.temperature = temperature_slider


def show_interfaces():
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            display_discussion_and_whiteboard()
        with col2:
            auto_moderate = st.checkbox("Auto-moderate (slow, eats tokens, but very cool)", key="auto_moderate", on_change=trigger_moderator_agent_if_checked)
            if auto_moderate:
                with st.spinner("Auto-moderating..."):
                    moderator_response = trigger_moderator_agent()
                if moderator_response:
                    if st.session_state.next_agent:
                        st.session_state.user_input = f"To {st.session_state.next_agent}: {moderator_response}"
                    else:
                        st.session_state.user_input = moderator_response
                    st.success("Auto-moderation complete. New input has been generated.")
                else:
                    st.warning("Auto-moderation failed due to rate limiting. Please wait a moment and try again, or proceed manually.")
            
            user_input = st.text_area("Additional Input:", value=st.session_state.user_input, height=200, key="user_input_widget")
            reference_url = st.text_input("URL:", key="reference_url_widget")

    return user_input, reference_url


def trigger_moderator_agent():
    current_project = st.session_state.current_project
    goal = current_project.re_engineered_prompt
    last_speaker = st.session_state.last_agent
    last_comment = st.session_state.last_comment
    discussion_history = st.session_state.discussion_history

    deliverable_index, current_deliverable = current_project.get_next_unchecked_deliverable()
    
    if current_deliverable is None:
        if current_project.current_phase != "Deployment":
            current_project.move_to_next_phase()
            st.success(f"Moving to {current_project.current_phase} phase!")
            deliverable_index, current_deliverable = current_project.get_next_unchecked_deliverable()
        else:
            st.success("All deliverables have been completed and deployed!")
            return None

    current_phase = current_project.get_next_uncompleted_phase(deliverable_index)
    
    team_members = []
    for agent in st.session_state.agents:
        if isinstance(agent, AgentBaseModel):
            team_members.append(f"{agent.name}: {agent.description}")
        else:
            # Fallback for dictionary-like structure
            agent_name = agent.get('config', {}).get('name', agent.get('name', 'Unknown'))
            agent_description = agent.get('description', 'No description')
            team_members.append(f"{agent_name}: {agent_description}")
    team_members_str = "\n".join(team_members)

    moderator_prompt = get_moderator_prompt(discussion_history, goal, last_comment, last_speaker, team_members_str, current_deliverable, current_phase)

    for attempt in range(MAX_RETRIES):
        api_key = get_api_key()
        llm_provider = get_llm_provider(api_key=api_key)
        llm_request_data = {
            "model": st.session_state.model,
            "temperature": st.session_state.temperature,
            "max_tokens": st.session_state.max_tokens,
            "top_p": 1,
            "stop": "TERMINATE",
            "messages": [
                {
                    "role": "user",
                    "content": moderator_prompt
                }
            ]
        }
        retry_delay = RETRY_DELAY
        time.sleep(retry_delay)
        response = llm_provider.send_request(llm_request_data)

        if isinstance(response, dict) and 'choices' in response:
            # Handle response from providers like Groq
            content = response['choices'][0]['message']['content']
        elif hasattr(response, 'content') and isinstance(response.content, list):
            # Handle Anthropic-style response
            content = response.content[0].text
        else:
            print(f"Unexpected response format: {type(response)}")
            continue

        if content:
            # Extract the agent name from the content
            agent_name_match = re.match(r"To (\w+( \w+)*):", content)
            if agent_name_match:
                next_agent = agent_name_match.group(1)
                # Check if the extracted name is a valid agent and not a tool
                if any(agent.name.lower() == next_agent.lower() for agent in st.session_state.agents):
                    st.session_state.next_agent = next_agent
                    # Remove the "To [Agent Name]:" prefix from the content
                    content = re.sub(r"^To \w+( \w+)*:\s*", "", content).strip()
                else:
                    st.warning(f"'{next_agent}' is not a valid agent. Please select a valid agent.")
                    st.session_state.next_agent = None
            else:
                st.session_state.next_agent = None
            
            if "PHASE_COMPLETED" in content:
                current_project.mark_deliverable_phase_done(deliverable_index, current_phase)
                content = content.replace("PHASE_COMPLETED", "").strip()
                st.success(f"Phase {current_phase} completed for deliverable: {current_deliverable}")
            
            if "DELIVERABLE_COMPLETED" in content:
                current_project.mark_deliverable_done(deliverable_index)
                content = content.replace("DELIVERABLE_COMPLETED", "").strip()
                st.success(f"Deliverable completed: {current_deliverable}")
            
            return content.strip()

    logger.error("All retry attempts failed.")
    return None


def trigger_moderator_agent_if_checked():
    if st.session_state.get("auto_moderate", False):
        with st.spinner("Auto-moderating..."):
            moderator_response = trigger_moderator_agent()
        if moderator_response:
            st.session_state.user_input = moderator_response
            st.success("Auto-moderation complete. New input has been generated.")
        else:
            st.warning("Auto-moderation did not produce a response. Please try again or proceed manually.")
    st.experimental_rerun()


def update_api_url(provider):
    api_url_key = f"{provider.upper()}_API_URL"
    st.session_state.api_url = st.session_state.get(api_url_key)


def update_deliverable_status(index):
    current_project = st.session_state.current_project
    is_checked = st.session_state[f"deliverable_{index}"]
    if is_checked:
        for phase in current_project.implementation_phases:
            current_project.mark_deliverable_phase_done(index, phase)
    else:
        current_project.deliverables[index]["done"] = False
        for phase in current_project.implementation_phases:
            current_project.deliverables[index]["phase"][phase] = False
    st.experimental_rerun()


def update_discussion_and_whiteboard(agent_name, response, user_input):
    # Update the full discussion history
    if user_input:
        user_input_text = f"\n\nUser: {user_input}\n\n"
        st.session_state.discussion_history += user_input_text

    # Format the most recent response
    st.session_state.most_recent_response = f"{agent_name}:\n\n{response}\n\n"

    # Add the new response to the full discussion history
    st.session_state.discussion_history += st.session_state.most_recent_response

    st.session_state.last_agent = agent_name
    st.session_state.last_comment = response

    # Force a rerun to update the UI
    st.experimental_rerun()


def update_user_input():
    if st.session_state.get("auto_moderate"):
        st.session_state.user_input = st.session_state.user_input_widget_auto_moderate
    else:
        st.session_state.user_input = st.session_state.user_input_widget
