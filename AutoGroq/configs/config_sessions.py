# config_sessions.py

from datetime import datetime
from typing import Dict

DEFAULT_AGENT_CONFIG: Dict = {
    "name": "Default Agent",
    "description": "A default agent for initialization purposes in AutoGroq",
    "tools": [],  # Empty list as default
    "config": {
        "llm_config": {
            "config_list": [
                {
                    "model": "default",
                    "api_key": None,
                    "base_url": None,
                    "api_type": None,
                    "api_version": None,
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
        "human_input_mode": "NEVER",
        "max_consecutive_auto_reply": 10,
    },
    "role": "Default Assistant",
    "goal": "Assist users with general tasks in AutoGroq",
    "backstory": "I am a default AI assistant created to help initialize the AutoGroq system.",
    "id": None,  # Will be set dynamically when needed
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "user_id": "default_user",
    "workflows": None,
    "type": "assistant",
    "models": [],  # Empty list as default
    "verbose": False,
    "allow_delegation": True,
    "new_description": None,
    "timestamp": datetime.now().isoformat(),
    "is_termination_msg": None,
    "code_execution_config": {
        "work_dir": "./agent_workspace",
        "use_docker": False,
    },
    "llm": None,
    "function_calling_llm": None,
    "max_iter": 25,
    "max_rpm": None,
    "max_execution_time": 600,  # 10 minutes default
    "step_callback": None,
    "cache": True
}