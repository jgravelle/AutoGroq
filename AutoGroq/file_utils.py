# file_utils.py 
import os 
import json 
import re 


def sanitize_text(text): 
    # Remove non-ASCII characters 
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    # Remove non-alphanumeric characters except for standard punctuation 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?:;\'"-]+', '', text) 
    return text 


def create_agent_data(expert_name, description, skills=None, tools=None):
    # Format the expert_name
    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    # Sanitize the description
    sanitized_description = sanitize_text(description)

    # Sanitize the skills and tools
    sanitized_skills = [sanitize_text(skill) for skill in skills] if skills else []
    sanitized_tools = [sanitize_text(tool) for tool in tools] if tools else []

    # Create the agent data
    agent_data = {
        "type": "assistant",
        "config": {
            "name": formatted_expert_name,
            "llm_config": {
                "config_list": [
                    {
                        "model": "gpt-4-1106-preview"
                    }
                ],
                "temperature": 0.1,
                "timeout": 600,
                "cache_seed": 42
            },
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 8,
            "system_message": f"You are a helpful assistant that can act as {expert_name} who {sanitized_description}."
        },
        "description": sanitized_description,
        "skills": [],
        "tools": sanitized_tools
    }

    return agent_data

        
def create_workflow_data(workflow):
    # Sanitize the workflow name
    sanitized_workflow_name = sanitize_text(workflow["name"])
    sanitized_workflow_name = sanitized_workflow_name.lower().replace(' ', '_')

    return workflow

