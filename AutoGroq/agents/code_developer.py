# agents/code_developer.py

import datetime
import streamlit as st

from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.code_generator import code_generator_tool


class CodeDeveloperAgent(AgentBaseModel):
    @classmethod
    def create_default(cls):
        current_timestamp = datetime.datetime.now().isoformat()
        return cls(
            name="Code Developer",
            description="An agent specialized in generating code based on feature descriptions.",
            tools=[code_generator_tool],  # Use the tool object directly, not its dict representation
            config={
                "name": "Code Developer",
                "llm_config": {
                    "config_list": [
                        {
                            "model": st.session_state.get('model', 'default'),
                            "api_key": None,
                        }
                    ],
                    "temperature": st.session_state.get('temperature', 0.7),
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10,
                "system_message": "You are an AI agent designed to generate code based on feature descriptions. Your goal is to produce efficient, clean, and well-documented code."
            },
            role="Code Developer",
            goal="Generate high-quality code based on feature descriptions",
            backstory="I am an AI agent with extensive knowledge of various programming languages and software development best practices. My purpose is to assist in creating code that meets the specified requirements.",
            provider=st.session_state.get('provider', LLM_PROVIDER),
            model=st.session_state.get('model', 'default'),
            created_at=current_timestamp,
            updated_at=current_timestamp,
            user_id="default",
            timestamp=current_timestamp
        )

    def to_dict(self):
        data = super().to_dict()
        data['tools'] = [tool.to_dict() if isinstance(tool, ToolBaseModel) else tool for tool in self.tools]
        return data