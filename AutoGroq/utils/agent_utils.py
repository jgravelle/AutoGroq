
import datetime
import streamlit as st

from configs.config import LLM_PROVIDER
from models.tool_base_model import ToolBaseModel
from utils.text_utils import sanitize_text


def create_agent_data(agent):
    expert_name = agent['name']
    description = agent.get('description', '')
    current_timestamp = datetime.datetime.now().isoformat()
    provider = agent.get('config', {}).get('provider', st.session_state.get('provider', LLM_PROVIDER))

    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    sanitized_description = sanitize_text(description)

    autogen_agent_data = {
        "type": "assistant",
        "config": {
            "name": formatted_expert_name,
            "provider": provider,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": current_timestamp,
                        "model": agent.get('config', {}).get('llm_config', {}).get('config_list', [{}])[0].get('model', 'default'),
                        "provider": provider,
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": f"{provider.capitalize()} model configuration"
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
        "tools": agent.get('tools', []),
        "role": agent.get('role', expert_name),
        "goal": agent.get('goal', f"Assist with tasks related to {sanitized_description}"),
        "backstory": agent.get('backstory', f"As an AI assistant, I specialize in {sanitized_description}")
    }

    crewai_agent_data = {
        "name": expert_name,
        "description": description,
        "verbose": True,
        "allow_delegation": True
    }

    return autogen_agent_data, crewai_agent_data
