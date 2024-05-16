import datetime
import importlib
import os
import streamlit as st
import time

from config import MAX_RETRIES, RETRY_DELAY
from skills.fetch_web_content import fetch_web_content

def get_api_key():
    if 'api_key' in st.session_state and st.session_state.api_key:
        api_key = st.session_state.api_key
        print(f"API Key from session state: {api_key}")
        return api_key
    elif "GROQ_API_KEY" in os.environ:  
        api_key = os.environ["GROQ_API_KEY"]
        print(f"API Key from environment variable: {api_key}")
        return api_key
    else:
        return None
    
    
def display_api_key_input():
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''
    
    api_key = st.text_input("Enter your GROQ_API_KEY:", type="password", value=st.session_state.api_key, key="api_key_input")
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("API key entered successfully.")
        print(f"API Key: {api_key}")
    
    return api_key

import io
import json
import pandas as pd
import re
import time
import zipfile
from file_utils import create_agent_data, create_skill_data, sanitize_text

import datetime
import requests


def create_zip_file(zip_buffer, file_data):
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_content in file_data.items():
            zip_file.writestr(file_name, file_content)


def display_discussion_and_whiteboard():
    discussion_history = get_discussion_history()
    tab1, tab2, tab3 = st.tabs(["Most Recent Comment", "Whiteboard", "Discussion History"])
    with tab1:
        st.text_area("Most Recent Comment", value=st.session_state.get("last_comment", ""), height=400, key="discussion")
    with tab2:
        if "whiteboard" not in st.session_state:
            st.session_state.whiteboard = ""
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard")
    with tab3:
        st.write(discussion_history)


def display_discussion_modal():
    discussion_history = get_discussion_history()
    
    with st.expander("Discussion History"):
        st.write(discussion_history)


def display_download_button():
    if "autogen_zip_buffer" in st.session_state and "crewai_zip_buffer" in st.session_state:
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
    else:
        st.warning("No files available for download.")


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


def display_rephrased_request(): 
    if "rephrased_request" not in st.session_state:
        st.session_state.rephrased_request = "" 

    st.text_area("Re-engineered Prompt:", value=st.session_state.get('rephrased_request', ''), height=100, key="rephrased_request_area") 


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
    user_request = st.text_input("Enter your request:", key="user_request", value=st.session_state.get("user_request", ""))
    if st.session_state.get("previous_user_request") != user_request:
        st.session_state.previous_user_request = user_request
        if user_request:
            if not st.session_state.get('rephrased_request'):
                handle_user_request(st.session_state)
            else:
                autogen_agents, crewai_agents = get_agents_from_text(st.session_state.rephrased_request)
                print(f"Debug: AutoGen Agents: {autogen_agents}")
                print(f"Debug: CrewAI Agents: {crewai_agents}")
                
                if not autogen_agents:
                    print("Error: No agents created.")
                    st.warning("Failed to create agents. Please try again.")
                    return
                
                agents_data = {}
                for agent in autogen_agents:
                    agent_name = agent['config']['name']
                    agents_data[agent_name] = agent
                
                print(f"Debug: Agents data: {agents_data}")
                
                workflow_data, _ = get_workflow_from_agents(autogen_agents)
                print(f"Debug: Workflow data: {workflow_data}")
                print(f"Debug: CrewAI agents: {crewai_agents}")
                
                autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(agents_data, workflow_data, crewai_agents)
                st.session_state.autogen_zip_buffer = autogen_zip_buffer
                st.session_state.crewai_zip_buffer = crewai_zip_buffer
                st.session_state.agents = autogen_agents
                
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
    start_index = json_string.find("{")
    while start_index != -1:
        end_index = json_string.find("}", start_index)
        if end_index != -1:
            object_str = json_string[start_index:end_index+1]
            objects.append(object_str)
            start_index = json_string.find("{", end_index + 1)
        else:
            break
    return objects


def get_agents_from_text(text, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    api_key = get_api_key()
    temperature_value = st.session_state.get('temperature', 0.5)
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    groq_request = {
        "model": st.session_state.model,
        "temperature": temperature_value,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "system",
                "content": f"""
                You are an expert system designed to identify and recommend the optimal team of experts
                required to fulfill this specific user's request: $userRequest Your analysis shall
                consider the complexity, domain, and specific needs of the request to assemble
                a multidisciplinary team of experts. The team should be as small as possible while still
                providing a complete and comprehensive talent pool able to properly address the users' requests.
                Each recommended expert shall come with a defined role,
                a brief but thorough description of their expertise, their specific skills, and the specific tools they would utilize
                to achieve the user's goal. The first agent must be qualified to manage the entire project,
                aggregate the work done by all the other agents, and produce a robust, complete,
                and reliable solution. Return the results in JSON values labeled as expert_name, description,
                skills, and tools. Their 'expert_name' is their title, not their given name.
                Skills and tools are arrays (one expert can have multiple specific skills and use multiple specific tools).
                Return ONLY this JSON response, with no other narrative, commentary, synopsis,
                or superfluous remarks/text of any kind. Tools shall be single-purpose methods,
                very specific and narrow in their scope, and not at all ambiguous (e.g.: 'add_numbers'
                would be good, but simply 'do_math' would be bad) Skills and tools shall be all lower case
                with underscores instead of spaces, and they shall be named per their functionality,
                e.g.: calculate_surface_area, or search_web

                IMPORTANT: The agents should focus on executing the tasks and providing actionable steps rather than just planning.
                They should break down the tasks into specific, executable actions and delegate subtasks to other agents or utilize their skills when appropriate.
                The agents should move from the planning phase to the execution phase as quickly as possible and provide step-by-step solutions to the user's request.
                """
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }

    retry_count = 0
    while retry_count < max_retries:
        try:
            response = requests.post(url, json=groq_request, headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                if "choices" in response_data and response_data["choices"]:
                    content = response_data["choices"][0]["message"]["content"]
                    print(f"Content: {content}")
                    json_objects = extract_json_objects(content)
                    if json_objects:
                        autogen_agents = []
                        crewai_agents = []
                        missing_names = False
                        for json_str in json_objects:
                            try:
                                agent_data = json.loads(json_str)
                                expert_name = agent_data.get('expert_name', '')
                                if not expert_name:
                                    missing_names = True
                                    break
                                description = agent_data.get('description', '')
                                skills = agent_data.get('skills', [])
                                tools = agent_data.get('tools', [])
                                # Associate skills with the agent based on their capabilities
                                agent_skills = []
                                for skill_name in skills:
                                    if skill_name in st.session_state.skill_functions:
                                        agent_skills.append(skill_name)
                                # Create the agent data using the new signature
                                autogen_agent_data = {
                                    "type": "assistant",
                                    "config": {
                                        "name": expert_name,
                                        "llm_config": {
                                            "config_list": [
                                                {
                                                    "user_id": "default",
                                                    "timestamp": datetime.datetime.now().isoformat(),
                                                    "model": "gpt-4",
                                                    "base_url": None,
                                                    "api_type": None,
                                                    "api_version": None,
                                                    "description": "OpenAI model configuration"
                                                }
                                            ],
                                            "temperature": st.session_state.get('temperature', 0.1),
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
                            except json.JSONDecodeError as e:
                                print(f"Error parsing JSON object: {e}")
                                print(f"JSON string: {json_str}")

                        if missing_names:
                            print("Missing agent names. Retrying...")
                            retry_count += 1
                            time.sleep(retry_delay)
                            continue
                        print(f"AutoGen Agents: {autogen_agents}")
                        print(f"CrewAI Agents: {crewai_agents}")
                        return autogen_agents, crewai_agents
                    else:
                        print("No valid JSON objects found in the response")
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


def get_workflow_from_agents(agents):
    current_timestamp = datetime.datetime.now().isoformat()
    temperature_value = st.session_state.get('temperature', 0.3)

    workflow = {
        "name": "AutoGroq Workflow",
        "description": "Workflow auto-generated by AutoGroq.",
        "sender": {
            "type": "userproxy",
            "config": {
                "name": "userproxy",
                "llm_config": False,
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 5,
                "system_message": "You are a helpful assistant.",
                "is_termination_msg": None,
                "code_execution_config": {
                    "work_dir": None,
                    "use_docker": False
                },
                "default_auto_reply": "",
                "description": None
            },
            "timestamp": current_timestamp,
            "user_id": "default",
            "skills": []
        },
        "receiver": {
            "type": "groupchat",
            "config": {
                "name": "group_chat_manager",
                "llm_config": {
                    "config_list": [
                        {
                            "user_id": "default",
                            "timestamp": datetime.datetime.now().isoformat(),
                            "model": "gpt-4",
                            "base_url": None,
                            "api_type": None,
                            "api_version": None,
                            "description": "OpenAI model configuration"
                        }
                    ],
                    "temperature": temperature_value,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": None,
                    "extra_body": None
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10,
                "system_message": "Group chat manager",
                "is_termination_msg": None,
                "code_execution_config": None,
                "default_auto_reply": "",
                "description": None
            },
            "groupchat_config": {
                "agents": [],
                "admin_name": "Admin",
                "messages": [],
                "max_round": 10,
                "speaker_selection_method": "auto",
                "allow_repeat_speaker": True
            },
            "timestamp": current_timestamp,
            "user_id": "default",
            "skills": []
        },
        "type": "groupchat",
        "user_id": "default",
        "timestamp": current_timestamp,
        "summary_method": "last"
    }

    for index, agent in enumerate(agents):
        agent_name = agent["config"]["name"]
        description = agent["description"]
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        sanitized_description = sanitize_text(description)
        
        system_message = f"You are a helpful assistant that can act as {agent_name} who {sanitized_description}."
        if index == 0:
            other_agent_names = [sanitize_text(a['config']['name']).lower().replace(' ', '_') for a in agents[1:] if a in st.session_state.agents]  # Filter out deleted agents
            system_message += f" You are the primary coordinator who will receive suggestions or advice from all the other agents ({', '.join(other_agent_names)}). You must ensure that the final response integrates the suggestions from other agents or team members. YOUR FINAL RESPONSE MUST OFFER THE COMPLETE RESOLUTION TO THE USER'S REQUEST. When the user's request has been satisfied and all perspectives are integrated, you can respond with TERMINATE."

            other_agent_names = [sanitize_text(a['config']['name']).lower().replace(' ', '_') for a in agents[1:]]
            system_message += f" You are the primary coordinator who will receive suggestions or advice from all the other agents ({', '.join(other_agent_names)}). You must ensure that the final response integrates the suggestions from other agents or team members. YOUR FINAL RESPONSE MUST OFFER THE COMPLETE RESOLUTION TO THE USER'S REQUEST. When the user's request has been satisfied and all perspectives are integrated, you can respond with TERMINATE."

        agent_config = {
            "type": "assistant",
            "config": {
                "name": formatted_agent_name,
                "llm_config": {
                    "config_list": [
                        {
                            "user_id": "default",
                            "timestamp": datetime.datetime.now().isoformat(),
                            "model": "gpt-4",
                            "base_url": None,
                            "api_type": None,
                            "api_version": None,
                            "description": "OpenAI model configuration"
                        }
                    ],
                    "temperature": temperature_value,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": None,
                    "extra_body": None
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 8,
                "system_message": system_message,
                "is_termination_msg": None,
                "code_execution_config": None,
                "default_auto_reply": "",
                "description": None
            },
            "timestamp": current_timestamp,
            "user_id": "default",
            "skills": []  # Set skills to null only in the workflow JSON
        }

        workflow["receiver"]["groupchat_config"]["agents"].append(agent_config)

    crewai_agents = []
    for agent in agents:
        if agent not in st.session_state.agents:  # Check if the agent exists in st.session_state.agents
            continue  # Skip the agent if it has been deleted
        
        _, crewai_agent_data = create_agent_data(agent)
        crewai_agents.append(crewai_agent_data)

    return workflow, crewai_agents


def handle_user_request(session_state):
    user_request = session_state.user_request
    max_retries = MAX_RETRIES
    retry_delay = RETRY_DELAY
    
    for retry in range(max_retries):
        try:
            rephrased_text = rephrase_prompt(user_request)
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

    rephrased_text = session_state.rephrased_request

    autogen_agents, crewai_agents = get_agents_from_text(rephrased_text)
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_folder = os.path.join(script_dir, "skills")
    skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]
    skill_functions = {}
    for skill_file in skill_files:
        skill_name = os.path.splitext(skill_file)[0]
        skill_module = importlib.import_module(f"skills.{skill_name}")
        if hasattr(skill_module, skill_name):
            skill_functions[skill_name] = getattr(skill_module, skill_name)
    st.session_state.skill_functions = skill_functions


def regenerate_json_files_and_zip():
    # Get the updated workflow data
    workflow_data, _ = get_workflow_from_agents(st.session_state.agents)
    
    # Regenerate the zip files
    autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
    
    # Update the zip buffers in the session state
    st.session_state.autogen_zip_buffer = autogen_zip_buffer
    st.session_state.crewai_zip_buffer = crewai_zip_buffer


def rephrase_prompt(user_request):
    temperature_value = st.session_state.get('temperature', 0.1)
    print("Executing rephrase_prompt()")
    api_key = get_api_key()
    if not api_key:
        st.error("API key not found. Please enter your API key.")
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    refactoring_prompt = f"""
    Refactor the following user request into an optimized prompt for an LLM,
    focusing on clarity, conciseness, and effectiveness. Provide specific details
    and examples where relevant. Do NOT reply with a direct response to the request;
    instead, rephrase the request as a well-structured prompt, and return ONLY that rephrased 
    prompt.  Do not preface the rephrased prompt with any other text or superfluous narrative.
    Do not enclose the rephrased prompt in quotes.
    \n\nUser request: \"{user_request}\"\n\nrephrased:
    """
    
    groq_request = {
        "model": st.session_state.model,
        "temperature": temperature_value,
        "max_tokens": 100,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": refactoring_prompt,
            },
        ],
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    print(f"Request URL: {url}")
    print(f"Request Headers: {headers}")
    print(f"Request Payload: {json.dumps(groq_request, indent=2)}")
    
    try:
        print("Sending request to Groq API...")
        response = requests.post(url, json=groq_request, headers=headers, timeout=10)
        print(f"Response received. Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Request successful. Parsing response...")
            response_data = response.json()
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
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while sending the request: {str(e)}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error occurred while parsing the response: {str(e)}")
        print(f"Response Content: {response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None
    
    
def update_discussion_and_whiteboard(agent_name, response, user_input):
    if user_input:
        user_input_text = f"\n\n\n\n{user_input}\n\n"
        st.session_state.discussion_history += user_input_text
    response_text = f"{agent_name}:\n\n {response}\n\n===\n\n"
    st.session_state.discussion_history += response_text
    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard = code_blocks
    st.session_state.last_agent = agent_name
    st.session_state.last_comment = response_text
    

def zip_files_in_memory(workflow_data):
    autogen_zip_buffer = io.BytesIO()
    crewai_zip_buffer = io.BytesIO()

    autogen_file_data = {}
    for agent in st.session_state.agents:
        agent_name = agent['config']['name']
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        agent_file_name = f"{formatted_agent_name}.json"
        autogen_agent_data, _ = create_agent_data(agent)
        autogen_agent_data['config']['name'] = formatted_agent_name
        agent_file_data = json.dumps(autogen_agent_data, indent=2).encode('utf-8')
        autogen_file_data[f"agents/{agent_file_name}"] = agent_file_data

        script_dir = os.path.dirname(os.path.abspath(__file__))
        skill_folder = os.path.join(script_dir, "skills")
        skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]

        for skill_file in skill_files:
            skill_name = os.path.splitext(skill_file)[0]
            if agent.get(skill_name, False):
                skill_file_path = os.path.join(skill_folder, skill_file)
                with open(skill_file_path, 'r') as file:
                    skill_data = file.read()
                skill_json = json.dumps(create_skill_data(skill_data), indent=2).encode('utf-8')
                autogen_file_data[f"skills/{skill_name}.json"] = skill_json

    workflow_file_name = "workflow.json"
    workflow_file_data = json.dumps(workflow_data, indent=2).encode('utf-8')
    autogen_file_data[workflow_file_name] = workflow_file_data

    crewai_file_data = {}
    for index, agent in enumerate(st.session_state.agents):
        agent_name = agent['config']['name']
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        crewai_agent_data = create_agent_data(agent)[1]
        crewai_agent_data['name'] = formatted_agent_name
        agent_file_name = f"{formatted_agent_name}.json"
        agent_file_data = json.dumps(crewai_agent_data, indent=2).encode('utf-8')
        crewai_file_data[f"agents/{agent_file_name}"] = agent_file_data

    create_zip_file(autogen_zip_buffer, autogen_file_data)
    create_zip_file(crewai_zip_buffer, crewai_file_data)

    autogen_zip_buffer.seek(0)
    crewai_zip_buffer.seek(0)

    return autogen_zip_buffer, crewai_zip_buffer