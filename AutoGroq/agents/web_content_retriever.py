# agents/web_content_retriever.py

import datetime
import streamlit as st
from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.fetch_web_content import fetch_web_content_tool

class WebContentRetrieverAgent(AgentBaseModel):
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
            name="Web Content Retriever",
            description="An agent specialized in retrieving and processing web content.",
            tools=[fetch_web_content_tool],
            config={
                "llm_config": {
                    "config_list": [{"model": st.session_state.get('model', 'default'), "api_key": None}],
                    "temperature": st.session_state.get('temperature', 0.7)
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10
            },
            role="Web Content Specialist",
            goal="To retrieve and analyze web content efficiently and accurately.",
            backstory="I am an AI agent designed to fetch and analyze web content, providing valuable insights and information from various online sources.",
            provider=st.session_state.get('provider', LLM_PROVIDER),
            model=st.session_state.get('model', 'default')
        )

    def to_dict(self):
        data = self.__dict__
        for key, value in data.items():
            if isinstance(value, ToolBaseModel):
                data[key] = value.to_dict()
        return data