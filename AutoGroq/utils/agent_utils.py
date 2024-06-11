
import datetime
import streamlit as st

from config import MODEL_TOKEN_LIMITS
from utils.text_utils import sanitize_text




def create_agent_data(agent):
    expert_name = agent['config']['name']
    description = agent['config'].get('description', agent.get('description', ''))  # Get description from config, default to empty string if missing
    current_timestamp = datetime.datetime.now().isoformat()

    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    sanitized_description = sanitize_text(description)
    temperature_value = 0.1  # Default value for temperature

    autogen_agent_data = {
        "type": "assistant",
        "config": {
            "name": formatted_expert_name,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": current_timestamp,
                        "model": agent['config']['llm_config']['config_list'][0]['model'],
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": "OpenAI model configuration"
                    }
                ],
                "temperature": st.session_state.temperature,
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
        "tools": []
    }

    for tool_model in st.session_state.tool_models:
        tool_name = tool_model.name
        if agent.get(tool_name, False):
            tool_json = {
                "name": tool_model.name,
                "description": tool_model.description,
                "title": tool_model.title,
                "file_name": tool_model.file_name,
                "content": tool_model.content,
                "timestamp": tool_model.timestamp,
                "user_id": tool_model.user_id
            }
            autogen_agent_data["tools"].append(tool_json)

    crewai_agent_data = {
        "name": expert_name,
        "description": description,
        "verbose": True,
        "allow_delegation": True
    }

    return autogen_agent_data, crewai_agent_data