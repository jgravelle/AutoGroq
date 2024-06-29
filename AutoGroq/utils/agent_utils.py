# utils/agent_utils.py

import datetime
import streamlit as st

from configs.config import LLM_PROVIDER

from utils.text_utils import normalize_config


def create_agent_data(agent):
    expert_name = agent['name']
    description = agent.get('description', '')
    current_timestamp = datetime.datetime.now().isoformat()
    provider = agent.get('config', {}).get('provider', st.session_state.get('provider', LLM_PROVIDER))

    # Use normalize_config to get the standardized config
    normalized_config = normalize_config(agent, expert_name)

    autogen_agent_data = {
        "name": normalized_config['name'],
        "description": description,
        "config": normalized_config,
        "tools": agent.get('tools', []),
        "role": agent.get('role', normalized_config['name']),
        "goal": agent.get('goal', f"Assist with tasks related to {description}"),
        "backstory": agent.get('backstory', f"As an AI assistant, I specialize in {description}"),
        "provider": provider,
        "model": st.session_state.get('model', 'default')
    }

    crewai_agent_data = {
        "name": normalized_config['name'],
        "description": description,
        "verbose": True,
        "allow_delegation": True
    }

    return autogen_agent_data, crewai_agent_data
