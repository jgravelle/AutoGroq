import datetime
import importlib.resources as resources
import re 
import streamlit as st

def create_agent_data(agent):
    expert_name = agent['config']['name']
    description = agent['description']  # Use the updated description from the session state
    skills = agent.get("skills", [])
    tools = agent.get("tools", [])
    current_timestamp = datetime.datetime.now().isoformat()

    # Format the expert_name
    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    # Sanitize the description
    sanitized_description = sanitize_text(description)

    # Sanitize the skills and tools
    sanitized_skills = [sanitize_text(skill) for skill in skills]
    sanitized_tools = [sanitize_text(tool) for tool in tools]

    # Create the Autogen agent data
    autogen_agent_data = {
        "type": "assistant",
        "config": {
            "name": formatted_expert_name,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": current_timestamp,
                        "model": "gpt-4",
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": "OpenAI model configuration"
                    }
                ],
                "temperature": st.session_state.get('temperature', 0.1),
                "cache_seed": None,
                "timeout": None,
                "max_tokens": None,
                "extra_body": None
            },
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 8,
            "system_message": f"You are a helpful assistant that can act as {expert_name} who {sanitized_description}.",
            "is_termination_msg": None,
            "code_execution_config": None,
            "default_auto_reply": "",
            "description": description
        },
        "timestamp": current_timestamp,
        "user_id": "default",
        "skills": []
    }

    if agent.get('fetch_web_content', False):
        fetch_web_content_data = resources.read_text('skills', 'fetch_web_content.py')
        skill_data = create_skill_data(fetch_web_content_data)
        autogen_agent_data["skills"].append(skill_data)

    if agent.get('generate_images', False):
        generate_images_data = resources.read_text('skills', 'generate_images.py')
        skill_data = create_skill_data(generate_images_data)
        autogen_agent_data["skills"].append(skill_data)

    # Create the CrewAI agent data
    crewai_agent_data = {
        "name": expert_name,
        "description": description,
        "skills": sanitized_skills,
        "tools": sanitized_tools,
        "verbose": True,
        "allow_delegation": True
    }

    return autogen_agent_data, crewai_agent_data
        

def create_skill_data(python_code):
    # Extract the function name from the Python code
    function_name_match = re.search(r"def\s+(\w+)\(", python_code)
    if function_name_match:
        function_name = function_name_match.group(1)    
    else:
        function_name = "unnamed_function"

    # Extract the skill description from the docstring
    docstring_match = re.search(r'"""(.*?)"""', python_code, re.DOTALL)
    if docstring_match:
        skill_description = docstring_match.group(1).strip()
    else:
        skill_description = "No description available"

    # Get the current timestamp
    current_timestamp = datetime.datetime.now().isoformat()

    # Create the skill data dictionary
    skill_data = {
        "title": function_name,
        "content": python_code,
        "file_name": f"{function_name}.json",
        "description": skill_description,
        "timestamp": current_timestamp,
        "user_id": "default"
    }

    return skill_data
        

def create_workflow_data(workflow):
    # Sanitize the workflow name
    sanitized_workflow_name = sanitize_text(workflow["name"])
    sanitized_workflow_name = sanitized_workflow_name.lower().replace(' ', '_')

    return workflow


def sanitize_text(text): 
    # Remove non-ASCII characters 
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    # Remove non-alphanumeric characters except for standard punctuation 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?:;\'"-]+', '', text) 
    return text 