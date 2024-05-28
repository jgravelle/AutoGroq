
import datetime
import importlib
import io
import json
import os
import pandas as pd
import re
import streamlit as st
import time
import zipfile

from config import API_URL, LLM_PROVIDER, MAX_RETRIES, MODEL_TOKEN_LIMITS, RETRY_DELAY

from current_project import Current_Project
from skills.fetch_web_content import fetch_web_content
from utils.api_utils import get_llm_provider
from utils.db_utils import export_skill_to_autogen
from utils.file_utils import create_agent_data, create_skill_data, sanitize_text
from utils.workflow_utils import get_workflow_from_agents
    
    
def create_project_manager(rephrased_text, api_url):
    temperature_value = st.session_state.get('temperature', 0.1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": temperature_value,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": f"""
                You are a Project Manager tasked with creating a comprehensive project outline and describing the perfect team of experts that should be created to work on the following project:

                {rephrased_text}

                Please provide a detailed project outline, including the objectives, key deliverables, and timeline. Also, describe the ideal team of experts required for this project, including their roles, skills, and responsibilities.  Your analysis shall consider the complexity, domain, and specific needs of the request to assemble a multidisciplinary team of experts. The team should be as small as possible while still providing a complete and comprehensive talent pool able to properly address the user's request. Each recommended agent shall come with a defined role, a brief but thorough description of their expertise, their specific skills, and the specific tools they would utilize to achieve the user's goal.

                Return your response in the following format:

                Project Outline:
                [Detailed project outline]

                Team of Experts:
                [Description of the ideal team of experts]
                """
            }
        ]
    }

    llm_provider = get_llm_provider(api_url)
    response = llm_provider.send_request(llm_request_data)
    
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            return content.strip()
    
    return None


def create_zip_file(zip_buffer, file_data):
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_content in file_data.items():
            zip_file.writestr(file_name, file_content)


def display_api_key_input():
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''
    llm = LLM_PROVIDER.upper()
    api_key = st.text_input(f"Enter your {llm}_API_KEY:", type="password", value=st.session_state.api_key, key="api_key_input")
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("API key entered successfully.")
        print(f"API Key: {api_key}")
    
    return api_key


def display_discussion_and_whiteboard():
    discussion_history = get_discussion_history()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Most Recent Comment", "Whiteboard", "Discussion History", "Objectives", "Deliverables", "Goal"])

    with tab1:
        if "last_comment" not in st.session_state:
            st.session_state.last_comment = ""
        st.text_area("Most Recent Comment", value=st.session_state.last_comment, height=400, key="discussion")

    with tab2:
        if "whiteboard" not in st.session_state:
            st.session_state.whiteboard = ""
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard")

    with tab3:
        st.write(discussion_history)

    with tab4:
        if "current_project" in st.session_state:
            current_project = st.session_state.current_project
            for index, objective in enumerate(current_project.objectives):
                if objective["text"].strip():  # Check if the objective text is not empty
                    checkbox_key = f"objective_{index}"
                    done = st.checkbox(objective["text"], value=objective["done"], key=checkbox_key)
                    if done != objective["done"]:
                        if done:
                            current_project.mark_objective_done(index)
                        else:
                            current_project.mark_objective_undone(index)
        else:
            st.warning("No objectives found. Please enter a user request.")

    with tab5:
        if "current_project" in st.session_state:
            current_project = st.session_state.current_project
            for index, deliverable in enumerate(current_project.deliverables):
                if deliverable["text"].strip():  # Check if the deliverable text is not empty
                    checkbox_key = f"deliverable_{index}"
                    done = st.checkbox(deliverable["text"], value=deliverable["done"], key=checkbox_key)
                    if done != deliverable["done"]:
                        if done:
                            current_project.mark_deliverable_done(index)
                        else:
                            current_project.mark_deliverable_undone(index)
    
    with tab6:
        rephrased_request = st.text_area("Re-engineered Prompt:", value=st.session_state.get('rephrased_request', ''), height=100, key="rephrased_request_area")


def display_download_button():
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download Autogen Files",
            data=st.session_state.autogen_zip_buffer,
            file_name="autogen_files.zip",
            mime="application/zip",
            key=f"autogen_download_button_{int(time.time())}"  # Generate a unique key based on timestamp
        )
    with col2:
        st.download_button(
            label="Download CrewAI Files",
            data=st.session_state.crewai_zip_buffer,
            file_name="crewai_files.zip",
            mime="application/zip",
            key=f"crewai_download_button_{int(time.time())}"  # Generate a unique key based on timestamp
        )


def display_user_input():
    user_input = st.text_area("Additional Input:", key="user_input", height=100)
    reference_url = st.text_input("URL:", key="reference_url")

    if user_input:
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        url_match = url_pattern.search(user_input)
        if url_match:
            url = url_match.group()
            if "reference_html" not in st.session_state or url not in st.session_state.reference_html:
                html_content = fetch_web_content(url)
                if html_content:
                    if "reference_html" not in st.session_state:
                        st.session_state.reference_html = {}
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
    col1, col2 = st.columns(2)  
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
    if "show_request_input" not in st.session_state:
        st.session_state.show_request_input = True
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

 
def extract_json_objects(json_string):
    objects = []
    stack = []
    start_index = 0
    for i, char in enumerate(json_string):
        if char == "{":
            if not stack:
                start_index = i
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack:
                    objects.append(json_string[start_index:i+1])
    parsed_objects = []
    for obj_str in objects:
        try:
            parsed_obj = json.loads(obj_str)
            parsed_objects.append(parsed_obj)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON object: {e}")
            print(f"JSON string: {obj_str}")
    return parsed_objects
                

def generate_skill(rephrased_skill_request):
    temperature_value = st.session_state.get('temperature', 0.1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": temperature_value,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": f"""
                Based on the rephrased skill request below, please do the following:

                1. Do step-by-step reasoning and think to understand the request better.
                2. Code the best Autogen skill in Python as per the request as a [skill_name].py file.
                3. Follow the provided examples.
                4. Return ONLY THE CODE for the skill.  Any non-code content (e.g., comments, docstrings) is not required.  If there ARE any non-code lines, please pre-pend them with a '#' symbol to comment them out.

                Rephrased skill request: "{rephrased_skill_request}"
                """
            }
        ]
    }
    llm_provider = get_llm_provider(API_URL)
    response = llm_provider.send_request(llm_request_data)
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            proposed_skill = response_data["choices"][0]["message"]["content"].strip()
            return proposed_skill
    return None


def get_agents_from_text(text, api_url, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):     
    print("Getting agents from text...")
    temperature_value = st.session_state.get('temperature', 0.5)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": temperature_value,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "system",
                "content": f"""
                You are an expert system designed to format the JSON describing each member of the team of AI agents specifically listed in this provided text: $text.
                Fulfill the following guidelines without ever explicitly stating them in your response.
                Guidelines:
                1. **Agent Roles**: Clearly transcribe the titles of each agent listed in the provided text by iterating through the 'Team of Experts:' section of the provided text. Transcribe the info for those specific agents. Do not create new agents.
                2. **Expertise Description**: Provide a brief but thorough description of each agent's expertise based upon the provided text. Do not create new agents.
                3. **Specific Skills**: List the specific skills of each agent based upon the provided text. Skills must be single-purpose methods, very specific, and not ambiguous (e.g., 'calculate_area' is good, but 'do_math' is bad).
                4. **Specific Tools**: List the specific tools each agent would utilize. Tools must be single-purpose methods, very specific, and not ambiguous.
                5. **Format**: Return the results in JSON format with values labeled as expert_name, description, skills, and tools. 'expert_name' should be the agent's title, not their given name. Skills and tools should be arrays (one agent can have multiple specific skills and use multiple specific tools).
                6. **Naming Conventions**: Skills and tools should be in lowercase with underscores instead of spaces, named per their functionality (e.g., calculate_surface_area, or search_web).

                ALWAYS and ONLY return the results in the following JSON format, with no other narrative, commentary, synopsis, or superfluous text of any kind:
                [
                    {{
                        "expert_name": "agent_title",
                        "description": "agent_description",
                        "skills": ["skill1", "skill2"],
                        "tools": ["tool1", "tool2"]
                    }},
                    {{
                        "expert_name": "agent_title",
                        "description": "agent_description",
                        "skills": ["skill1", "skill2"],
                        "tools": ["tool1", "tool2"]
                    }}
                ]
                You will only have been successful if you have returned the results in the above format and followed these guidelines precisely by transcribing the provided text and returning the results in JSON format without any other narrative, commentary, synopsis, or superfluous text of any kind, and taking care to only transcribe the agents from the provided text without creating new agents.
                """
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }
    llm_provider = get_llm_provider(api_url)
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = llm_provider.send_request(llm_request_data)
            print(f"Response received. Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Request successful. Parsing response...")
                response_data = llm_provider.process_response(response)
                print(f"Response Data: {json.dumps(response_data, indent=2)}")
                if "choices" in response_data and response_data["choices"]:
                    content = response_data["choices"][0]["message"]["content"]
                    print(f"Content: {content}")
                    try:
                        json_data = json.loads(content)
                        if isinstance(json_data, list):
                            autogen_agents = []
                            crewai_agents = []
                            for agent_data in json_data:
                                expert_name = agent_data.get('expert_name', '')
                                if not expert_name:
                                    print("Missing agent name. Retrying...")
                                    retry_count += 1
                                    time.sleep(retry_delay)
                                    continue
                                description = agent_data.get('description', '')
                                skills = agent_data.get('skills', [])
                                tools = agent_data.get('tools', [])
                                agent_skills = st.session_state.selected_skills
                                autogen_agent_data = {
                                    "type": "assistant",
                                    "config": {
                                        "name": expert_name,
                                        "llm_config": {
                                            "config_list": [
                                                {
                                                    "user_id": "default",
                                                    "timestamp": datetime.datetime.now().isoformat(),
                                                    "model": st.session_state.model,
                                                    "base_url": None,
                                                    "api_type": None,
                                                    "api_version": None,
                                                    "description": "OpenAI model configuration"
                                                }
                                            ],
                                            "temperature": temperature_value,
                                            "timeout": 600,
                                            "cache_seed": 42
                                        },
                                        "human_input_mode": "NEVER",
                                        "max_consecutive_auto_reply": 8,
                                        "system_message": f"You are a helpful assistant that can act as {expert_name} who {description}."
                                    },
                                    "description": description,
                                    "skills": agent_skills,
                                    "tools": tools
                                }
                                crewai_agent_data = {
                                    "name": expert_name,
                                    "description": description,
                                    "skills": agent_skills,
                                    "tools": tools,
                                    "verbose": True,
                                    "allow_delegation": True
                                }
                                autogen_agents.append(autogen_agent_data)
                                crewai_agents.append(crewai_agent_data)
                            print(f"AutoGen Agents: {autogen_agents}")
                            print(f"CrewAI Agents: {crewai_agents}")
                            return autogen_agents, crewai_agents
                        else:
                            print("Invalid JSON format. Expected a list of agents.")
                            return [], []
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")
                        print(f"Content: {content}")
                        json_data = extract_json_objects(content)
                        if json_data:
                            autogen_agents = []
                            crewai_agents = []
                            for agent_data in json_data:
                                expert_name = agent_data.get('expert_name', '')
                                if not expert_name:
                                    print("Missing agent name. Retrying...")
                                    retry_count += 1
                                    time.sleep(retry_delay)
                                    continue
                                description = agent_data.get('description', '')
                                skills = agent_data.get('skills', [])
                                tools = agent_data.get('tools', [])
                                agent_skills = st.session_state.selected_skills
                                autogen_agent_data = {
                                    "type": "assistant",
                                    "config": {
                                        "name": expert_name,
                                        "llm_config": {
                                            "config_list": [
                                                {
                                                    "user_id": "default",
                                                    "timestamp": datetime.datetime.now().isoformat(),
                                                    "model": st.session_state.model,
                                                    "base_url": None,
                                                    "api_type": None,
                                                    "api_version": None,
                                                    "description": "OpenAI model configuration"
                                                }
                                            ],
                                            "temperature": temperature_value,
                                            "timeout": 600,
                                            "cache_seed": 42
                                        },
                                        "human_input_mode": "NEVER",
                                        "max_consecutive_auto_reply": 8,
                                        "system_message": f"You are a helpful assistant that can act as {expert_name} who {description}."
                                    },
                                    "description": description,
                                    "skills": agent_skills,
                                    "tools": tools
                                }
                                crewai_agent_data = {
                                    "name": expert_name,
                                    "description": description,
                                    "skills": agent_skills,
                                    "tools": tools,
                                    "verbose": True,
                                    "allow_delegation": True
                                }
                                autogen_agents.append(autogen_agent_data)
                                crewai_agents.append(crewai_agent_data)
                            print(f"AutoGen Agents: {autogen_agents}")
                            print(f"CrewAI Agents: {crewai_agents}")
                            return autogen_agents, crewai_agents
                        else:
                            print("Failed to extract JSON objects from content.")
                            return [], []
                else:
                    print("No agents data found in response")
            else:
                print(f"API request failed with status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error making API request: {e}")
            retry_count += 1
            time.sleep(retry_delay)
    print(f"Maximum retries ({max_retries}) exceeded. Failed to retrieve valid agent names.")
    return [], []


def get_discussion_history():
    if "discussion_history" not in st.session_state:
        st.session_state.discussion_history = ""
    return st.session_state.discussion_history


def handle_user_request(session_state):
    print("Debug: Handling user request for session state: ", session_state)
    user_request = session_state.user_request
    max_retries = MAX_RETRIES
    retry_delay = RETRY_DELAY

    for retry in range(max_retries):
        try:
            print("Debug: Sending request to rephrase_prompt")
            rephrased_text = rephrase_prompt(user_request, API_URL)  # Pass the API_URL to rephrase_prompt
            print(f"Debug: Rephrased text: {rephrased_text}")
            if rephrased_text:
                session_state.rephrased_request = rephrased_text
                break  # Exit the loop if successful
            else:
                print("Error: Failed to rephrase the user request.")
                st.warning("Failed to rephrase the user request. Please try again.")
                return  # Exit the function if rephrasing fails
        except Exception as e:
            print(f"Error occurred in handle_user_request: {str(e)}")
            if retry < max_retries - 1:
                print(f"Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
            else:
                print("Max retries exceeded.")
                st.warning("An error occurred. Please try again.")
                return  # Exit the function if max retries are exceeded

    if "rephrased_request" not in session_state:
        st.warning("Failed to rephrase the user request. Please try again.")
        return

    rephrased_text = session_state.rephrased_request

    if "project_manager_output" not in session_state:
        # Create the Project Manager agent only if it hasn't been created before
        project_manager_output = create_project_manager(rephrased_text, API_URL)

        if not project_manager_output:
            print("Error: Failed to create Project Manager.")
            st.warning("Failed to create Project Manager. Please try again.")
            return

        session_state.project_manager_output = project_manager_output

        # Create an instance of the Current_Project class
        current_project = Current_Project()
        current_project.set_re_engineered_prompt(rephrased_text)

        # Extract objectives and deliverables from the project manager's output
        objectives_pattern = r"Objectives:\n(.*?)(?=Deliverables|$)"
        deliverables_pattern = r"Deliverables:\n(.*?)(?=Timeline|Team of Experts|$)"

        objectives_match = re.search(objectives_pattern, project_manager_output, re.DOTALL)
        if objectives_match:
            objectives = objectives_match.group(1).strip().split("\n")
            for objective in objectives:
                current_project.add_objective(objective.strip())

        deliverables_match = re.search(deliverables_pattern, project_manager_output, re.DOTALL)
        if deliverables_match:
            deliverables = deliverables_match.group(1).strip().split("\n")
            for deliverable in deliverables:
                current_project.add_deliverable(deliverable.strip())

        session_state.current_project = current_project

        # Update the discussion and whiteboard with the Project Manager's initial response
        update_discussion_and_whiteboard("Project Manager", project_manager_output, "")
    else:
        # Retrieve the previously created Project Manager's output from the session state
        project_manager_output = session_state.project_manager_output

    team_of_experts_pattern = r"Team of Experts:\n(.*)"
    match = re.search(team_of_experts_pattern, project_manager_output, re.DOTALL)
    if match:
        team_of_experts_text = match.group(1).strip()
    else:
        print("Error: 'Team of Experts' section not found in Project Manager's output.")
        st.warning("Failed to extract the team of experts from the Project Manager's output. Please try again.")
        return

    autogen_agents, crewai_agents = get_agents_from_text(team_of_experts_text, API_URL)

    print(f"Debug: AutoGen Agents: {autogen_agents}")
    print(f"Debug: CrewAI Agents: {crewai_agents}")

    if not autogen_agents:
        print("Error: No agents created.")
        st.warning("Failed to create agents. Please try again.")
        return

    # Set the agents attribute in the session state
    session_state.agents = autogen_agents

    workflow_data, _ = get_workflow_from_agents(autogen_agents)
    print(f"Debug: Workflow data: {workflow_data}")
    print(f"Debug: CrewAI agents: {crewai_agents}")

    autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
    session_state.autogen_zip_buffer = autogen_zip_buffer
    session_state.crewai_zip_buffer = crewai_zip_buffer


def load_skill_functions():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_folder = os.path.join(project_root, "skills")
    skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]
    skill_functions = {}
    for skill_file in skill_files:
        skill_name = os.path.splitext(skill_file)[0]
        skill_module = importlib.import_module(f"skills.{skill_name}")
        if hasattr(skill_module, skill_name):
            skill_functions[skill_name] = getattr(skill_module, skill_name)
    st.session_state.skill_functions = skill_functions


def process_skill_request():
    skill_request = st.session_state.skill_request_input
    if skill_request:
        print(f"Skill Request: {skill_request}")
        rephrased_skill_request = rephrase_skill(skill_request)
        if rephrased_skill_request:
            print(f"Generating proposed skill...")
            proposed_skill = generate_skill(rephrased_skill_request)
            print(f"Proposed Skill: {proposed_skill}")
            if proposed_skill:
                skill_name = re.search(r"def\s+(\w+)\(", proposed_skill).group(1)
                st.write(f"Proposed Skill: {skill_name}")
                st.code(proposed_skill)
                if st.button("Export to Autogen", key=f"export_button_{skill_name}"):
                    print(f"Exporting skill {skill_name} to Autogen")
                    export_skill_to_autogen(skill_name, proposed_skill)
                    st.success(f"Skill {skill_name} exported to Autogen successfully!")
                    st.experimental_rerun()
                if st.button("Discard", key=f"discard_button_{skill_name}"):
                    st.warning("Skill discarded.")
                    st.experimental_rerun()


def regenerate_json_files_and_zip():
    # Get the updated workflow data
    workflow_data, _ = get_workflow_from_agents(st.session_state.agents)
    
    # Regenerate the zip files
    autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
    
    # Update the zip buffers in the session state
    st.session_state.autogen_zip_buffer = autogen_zip_buffer
    st.session_state.crewai_zip_buffer = crewai_zip_buffer


def regenerate_zip_files():
    if "agents" in st.session_state:
        workflow_data, _ = get_workflow_from_agents(st.session_state.agents)
        autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
        st.session_state.autogen_zip_buffer = autogen_zip_buffer
        st.session_state.crewai_zip_buffer = crewai_zip_buffer
        print("Zip files regenerated.")
    else:
        print("No agents found. Skipping zip file regeneration.")


def rephrase_skill(skill_request):
    print("Debug: Rephrasing skill: ", skill_request)
    temperature_value = st.session_state.get('temperature', 0.1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": temperature_value,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": f"""
                Act as a professional skill creator and rephrase the following skill request into an optimized prompt:

                Skill request: "{skill_request}"

                Rephrased:
                """
            }
        ]
    }
    llm_provider = get_llm_provider(API_URL)
    response = llm_provider.send_request(llm_request_data)
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            rephrased = response_data["choices"][0]["message"]["content"].strip()
            print(f"Debug: Rephrased skill: {rephrased}")
            return rephrased
    return None


def rephrase_prompt(user_request, api_url):
    temperature_value = st.session_state.get('temperature', 0.1)
    print("Executing rephrase_prompt()")
    print(f"Debug: api_url: {api_url}")

    refactoring_prompt = f"""
    Act as a professional prompt engineer and efactor the following user request into an optimized prompt. Your goal is to rephrase the request with a focus on the satisfying all following the criteria without explicitly stating them:
    1. Clarity: Ensure the prompt is clear and unambiguous.
    2. Specific Instructions: Provide detailed steps or guidelines.
    3. Context: Include necessary background information.
    4. Structure: Organize the prompt logically.
    5. Language: Use concise and precise language.
    6. Examples: Offer examples to illustrate the desired output.
    7. Constraints: Define any limits or guidelines.
    8. Engagement: Make the prompt engaging and interesting.
    9. Feedback Mechanism: Suggest a way to improve or iterate on the response.
    Do NOT reply with a direct response to these instructions OR the original user request. Instead, rephrase the user's request as a well-structured prompt, and
    return ONLY that rephrased prompt. Do not preface the rephrased prompt with any other text or superfluous narrative.
    Do not enclose the rephrased prompt in quotes. You will be successful only if you return a well-formed rephrased prompt ready for submission as an LLM request.
    User request: "{user_request}"
    Rephrased:
    """

    model = st.session_state.model
    max_tokens = MODEL_TOKEN_LIMITS.get(model, 4096)  # Use the appropriate max_tokens value based on the selected model

    llm_request_data = {
        "model": model,
        "temperature": temperature_value,
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

    llm_provider = get_llm_provider(api_url)  # Pass the api_url to get_llm_provider

    try:
        print("Sending request to LLM API...")
        print(f"Request Details:")
        print(f" URL: {api_url}")  # Print the API URL
        print(f" Model: {model}")
        print(f" Max Tokens: {max_tokens}")
        print(f" Temperature: {temperature_value}")
        print(f" Messages: {llm_request_data['messages']}")

        response = llm_provider.send_request(llm_request_data)
        print(f"Response received. Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")

        if response.status_code == 200:
            print("Request successful. Parsing response...")
            response_data = llm_provider.process_response(response)
            print(f"Response Data: {json.dumps(response_data, indent=2)}")

            if "choices" in response_data and len(response_data["choices"]) > 0:
                rephrased = response_data["choices"][0]["message"]["content"]
                return rephrased.strip()
            else:
                print("Error: Unexpected response format. 'choices' field missing or empty.")
                return None
        else:
            print(f"Request failed. Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def save_skill(skill_name, edited_skill):
    with open(f"{skill_name}.py", "w") as f:
        f.write(edited_skill)
    st.success(f"Skill {skill_name} saved successfully!")

    
def update_discussion_and_whiteboard(agent_name, response, user_input):
    if user_input:
        user_input_text = f"\n\n\n\n{user_input}\n\n"
        st.session_state.discussion_history += user_input_text

    if "last_agent" not in st.session_state or st.session_state.last_agent != agent_name:
        response_text = f"{agent_name}:\n\n{response}\n\n===\n\n"
    else:
        response_text = f"{response}\n\n===\n\n"

    st.session_state.discussion_history += response_text
    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard = code_blocks
    st.session_state.last_agent = agent_name
    st.session_state.last_comment = response_text
    

def zip_files_in_memory(workflow_data):
    autogen_zip_buffer = io.BytesIO()
    crewai_zip_buffer = io.BytesIO()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_folder = os.path.join(project_root, "skills")
    autogen_file_data = {}
    for agent in st.session_state.agents:
        agent_name = agent['config']['name']
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        agent_file_name = f"{formatted_agent_name}.json"
        
        # Use the agent-specific model configuration
        autogen_agent_data, _ = create_agent_data(agent)
        autogen_agent_data['config']['name'] = formatted_agent_name
        autogen_agent_data['config']['llm_config']['config_list'][0]['model'] = agent['config']['llm_config']['config_list'][0]['model']
        autogen_agent_data['config']['llm_config']['max_tokens'] = agent['config']['llm_config'].get('max_tokens', MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096))
        autogen_agent_data['skills'] = []
        
        for skill_name in st.session_state.selected_skills:
            skill_file_path = os.path.join(skill_folder, f"{skill_name}.py")
            with open(skill_file_path, 'r') as file:
                skill_data = file.read()
                skill_json = create_skill_data(skill_data)
                autogen_agent_data['skills'].append(skill_json)
        agent_file_data = "# Created by AutoGroq™ [https://github.com/jgravelle/AutoGroq]\n# https://j.gravelle.us\n\n"
        agent_file_data += json.dumps(autogen_agent_data, indent=2)
        agent_file_data = agent_file_data.encode('utf-8')
        autogen_file_data[f"agents/{agent_file_name}"] = agent_file_data
    for skill_name in st.session_state.selected_skills:
        skill_file_path = os.path.join(skill_folder, f"{skill_name}.py")
        with open(skill_file_path, 'r') as file:
            skill_data = file.read()
            skill_json = "# Created by AutoGroq™ [https://github.com/jgravelle/AutoGroq]\n# https://j.gravelle.us\n\n"
            skill_json += json.dumps(create_skill_data(skill_data), indent=2)
            skill_json = skill_json.encode('utf-8')
            autogen_file_data[f"skills/{skill_name}.json"] = skill_json
    workflow_file_name = "workflow.json"
    workflow_file_data = "# Created by AutoGroq™ [https://github.com/jgravelle/AutoGroq]\n# https://j.gravelle.us\n\n"
    workflow_file_data += json.dumps(workflow_data, indent=2)
    workflow_file_data = workflow_file_data.encode('utf-8')
    autogen_file_data[workflow_file_name] = workflow_file_data
    crewai_file_data = {}
    for index, agent in enumerate(st.session_state.agents):
        agent_name = agent['config']['name']
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        crewai_agent_data = create_agent_data(agent)[1]
        crewai_agent_data['name'] = formatted_agent_name
        agent_file_name = f"{formatted_agent_name}.json"
        agent_file_data = "# Created by AutoGroq™ [https://github.com/jgravelle/AutoGroq]\n# https://j.gravelle.us\n\n"
        agent_file_data += json.dumps(crewai_agent_data, indent=2)
        agent_file_data = agent_file_data.encode('utf-8')
        crewai_file_data[f"agents/{agent_file_name}"] = agent_file_data
    create_zip_file(autogen_zip_buffer, autogen_file_data)
    create_zip_file(crewai_zip_buffer, crewai_file_data)
    autogen_zip_buffer.seek(0)
    crewai_zip_buffer.seek(0)
    return autogen_zip_buffer, crewai_zip_buffer
