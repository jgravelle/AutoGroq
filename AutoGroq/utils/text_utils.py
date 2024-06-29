import re


def normalize_config(config, agent_name):
    """Normalize the config dictionary to match the format of default entries."""
    normalized = {
        "name": normalize_name(config.get('name', agent_name)),
        "human_input_mode": "NEVER",
        "max_consecutive_auto_reply": 25,
        "system_message": config.get('system_message', f"You are a helpful AI assistant that can act as {agent_name}."),
        "is_termination_msg": None,
        "code_execution_config": "none",
        "default_auto_reply": "",
        "description": "Assistant Agent",
        "llm_config": {
            "config_list": [],
            "temperature": 0,
            "cache_seed": None,
            "timeout": None,
            "max_tokens": 2048,
            "extra_body": None
        },
        "admin_name": "Admin",
        "messages": [],
        "max_round": 100,
        "speaker_selection_method": "auto",
        "allow_repeat_speaker": True
    }
    
    return normalized


def normalize_name(name):
    """Convert name to lowercase and replace spaces with underscores."""
    return sanitize_text(name).lower().replace(' ', '_')


def sanitize_text(text): 
    # Remove non-ASCII characters 
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    # Remove non-alphanumeric characters except for standard punctuation 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?:;\'"-]+', '', text) 
    return text 