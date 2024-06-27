# agents/code_tester.py

import datetime
import streamlit as st
from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.code_test import code_test_tool

class CodeTesterAgent(AgentBaseModel):
    def __init__(self, name, description, tools, config, role, goal, backstory, provider, model):
        current_timestamp = datetime.datetime.now().isoformat()
        super().__init__(name=name, description=description, tools=tools, config=config,
                         role=role, goal=goal, backstory=backstory)
        self.provider = provider
        self.model = model
        self.created_at = current_timestamp
        self.updated_at = current_timestamp
        self.user_id = "default"
        self.timestamp = current_timestamp

    @classmethod
    def create_default(cls):
        return cls(
            name="Code Tester",
            description="An agent specialized in testing code and providing feedback on its functionality.",
            tools=[code_test_tool],
            config={
                "llm_config": {
                    "config_list": [{"model": st.session_state.get('model', 'default'), "api_key": None}],
                    "temperature": st.session_state.get('temperature', 0.7)
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10
            },
            role="Code Tester",
            goal="To thoroughly test code and provide comprehensive feedback to ensure its reliability and correctness.",
            backstory="I am an AI agent with expertise in software testing and quality assurance. My purpose is to rigorously test code and provide comprehensive feedback to ensure its reliability and correctness.",
            provider=st.session_state.get('provider', LLM_PROVIDER),
            model=st.session_state.get('model', 'default')
        )

    def to_dict(self):
        data = self.__dict__
        for key, value in data.items():
            if isinstance(value, ToolBaseModel):
                data[key] = value.to_dict()
        return data