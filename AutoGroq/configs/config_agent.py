# /configs/config_agent.py

import datetime
import streamlit as st

from typing import Dict

AGENT_CONFIG: Dict = {
    "type": "assistant",
    "config": {
        "name": "",
        "llm_config": {
            "config_list": [
                {
                    "user_id": "default",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "model": st.session_state.model,
                    "base_url": st.session_state.api_url,
                    "api_type": None,
                    "api_version": None,
                    "description": "Model configuration"
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
        "system_message": "",
        "is_termination_msg": None,
        "code_execution_config": None,
        "default_auto_reply": "",
        "description": ""
    },
    "timestamp": datetime.datetime.now().isoformat(),
    "user_id": "default",
    "tools": []
}