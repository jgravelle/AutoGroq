# agents/web_content_retriever.py

import datetime
import streamlit as st

from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.fetch_web_content import fetch_web_content_tool


class WebContentRetrieverAgent(AgentBaseModel):
    @classmethod
    def create_default(cls):
        current_timestamp = datetime.datetime.now().isoformat()
        return cls(
            name="Web Content Retriever",
            description="An agent specialized in retrieving and processing web content.",
            tools=[fetch_web_content_tool.to_dict()],  # Convert ToolBaseModel to dictionary
            config={
                "name": "Web Content Retriever",
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
                "system_message": "You are an AI agent designed to fetch and analyze web content, providing valuable insights and information from various online sources."
            },
            role="Web Content Specialist",
            goal="Retrieve and process web content efficiently",
            backstory="I am an AI agent designed to fetch and analyze web content, providing valuable insights and information from various online sources.",
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