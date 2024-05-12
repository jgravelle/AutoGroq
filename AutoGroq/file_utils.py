import re 


def create_agent_data(agent):
    expert_name = agent['config']['name']
    description = agent['description']  # Use the updated description from the session state
    skills = agent.get("skills", [])
    tools = agent.get("tools", [])

    # Format the expert_name
    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    # Sanitize the description
    sanitized_description = sanitize_text(description)

    # Sanitize the skills and tools
    sanitized_skills = [sanitize_text(skill) for skill in skills]
    sanitized_tools = [sanitize_text(tool) for tool in tools]

    # Create the agent data
    agent_data = {
        "type": "assistant",
        "config": {
            "name": expert_name,
            "llm_config": {
                "config_list": [
                    {
                        "model": "gpt-4"
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
        "description": description,
        "skills": sanitized_skills,
        "tools": sanitized_tools
    }

    crewai_agent_data = {
        "name": expert_name,
        "description": description,
        "skills": sanitized_skills,
        "tools": sanitized_tools,
        "verbose": True,
        "allow_delegation": True
    }

    return agent_data, crewai_agent_data
        
        
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