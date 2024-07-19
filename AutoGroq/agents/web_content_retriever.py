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
        self.reference_url = None
        self.web_content = None

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

    def retrieve_web_content(self, reference_url):
        """
        Retrieve web content from the given reference URL and store it in the agent's memory.
        
        Args:
            reference_url (str): The URL to fetch content from.
        
        Returns:
            dict: A dictionary containing the status, URL, and content (or error message).
        """
        self.reference_url = reference_url
        fetch_tool = next((tool for tool in self.tools if tool.name == "fetch_web_content"), None)
        if fetch_tool is None:
            return {"status": "error", "message": "fetch_web_content tool not found"}
        
        result = fetch_tool.function(reference_url)
        if result["status"] == "success":
            self.web_content = result["content"]
        return result

    def get_web_content(self):
        """
        Get the stored web content.
        
        Returns:
            str: The stored web content or None if not available.
        """
        return self.web_content

    def get_reference_url(self):
        """
        Get the stored reference URL.
        
        Returns:
            str: The stored reference URL or None if not available.
        """
        return self.reference_url
