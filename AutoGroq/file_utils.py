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

def write_agent_file(expert_name, description, skills=None, tools=None):
    # Get the full path to the "agents" directory
    agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))

    # Create the "agents" directory if it doesn't exist
    if not os.path.exists(agents_dir):
        os.makedirs(agents_dir)
        print(f"Created directory: {agents_dir}")
    else:
        print(f"Directory already exists: {agents_dir}")

    # Format the expert_name
    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    # Sanitize the description
    sanitized_description = sanitize_text(description)

    # Sanitize the skills and tools
    # sanitized_skills = [sanitize_text(skill) for skill in skills] if skills else []
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
        "skills": [], # sanitized_skills,
        "tools": sanitized_tools
    }

    # Write the JSON file
    json_file = os.path.join(agents_dir, f"{formatted_expert_name}.json")
    with open(json_file, "w") as f:
        json.dump(agent_data, f, indent=2)
        print(f"JSON file written: {json_file}")


def write_workflow_file(workflow):
    # Get the full path to the "workflows" directory
    workflows_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "workflows"))

    # Create the "workflows" directory if it doesn't exist
    if not os.path.exists(workflows_dir):
        os.makedirs(workflows_dir)
        print(f"Created directory: {workflows_dir}")
    else:
        print(f"Directory already exists: {workflows_dir}")

    # Sanitize the workflow name
    sanitized_workflow_name = sanitize_text(workflow["name"])
    sanitized_workflow_name = sanitized_workflow_name.lower().replace(' ', '_')

    # Write the JSON file
    json_file = os.path.join(workflows_dir, f"{sanitized_workflow_name}.json")
    with open(json_file, "w") as f:
        json.dump(workflow, f, indent=2)
    print(f"JSON file written: {json_file}")