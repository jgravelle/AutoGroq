# agents/code_tester.py

import datetime
import streamlit as st

from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.code_test import code_test_tool

class CodeTesterAgent(AgentBaseModel):
    @classmethod
    def create_default(cls):
        current_timestamp = datetime.datetime.now().isoformat()
        return cls(
            name="Code Tester",
            description="An agent specialized in testing code and providing feedback on its functionality.",
            tools=[code_test_tool.to_dict()],
            config={
                "name": "Code Tester",
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
                "system_message": "You are an AI agent designed to test code and provide feedback on its functionality. Your goal is to ensure the code meets the specified requirements and works correctly."
            },
            role="Code Tester",
            goal="Test code thoroughly and provide detailed feedback on its functionality",
            backstory="I am an AI agent with expertise in software testing and quality assurance. My purpose is to rigorously test code and provide comprehensive feedback to ensure its reliability and correctness.",
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
    