
import streamlit as st

from agents.code_developer import CodeDeveloperAgent
from agents.code_tester import CodeTesterAgent
from agents.web_content_retriever import WebContentRetrieverAgent
from configs.config import LLM_PROVIDER, SUPPORTED_PROVIDERS
from configs.config_sessions import DEFAULT_AGENT_CONFIG
from configs.current_project import Current_Project
from datetime import datetime
from models.agent_base_model import AgentBaseModel
from models.project_base_model import ProjectBaseModel
from models.tool_base_model import ToolBaseModel
from models.workflow_base_model import WorkflowBaseModel
from utils.ui_utils import handle_user_request


def create_default_agent():
    return AgentBaseModel(**DEFAULT_AGENT_CONFIG)


def initialize_session_variables():

    if "agent_model" not in st.session_state:
        st.session_state.agent_model = create_default_agent()

    if "agent_models" not in st.session_state:
        st.session_state.agent_models = []

    if "agents" not in st.session_state:
        st.session_state.agents = []

    # Ensure built-in agents are always present
    built_in_agents = [
        WebContentRetrieverAgent.create_default(),
        CodeDeveloperAgent.create_default(),
        CodeTesterAgent.create_default()
    ]

    # Add built-in agents if they're not already in the list
    for built_in_agent in built_in_agents:
        if not any(agent.name == built_in_agent.name for agent in st.session_state.agents):
            st.session_state.agents.append(built_in_agent)

    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

    if "api_url" not in st.session_state:
        st.session_state.api_url = None

    if "autogen_zip_buffer" not in st.session_state:
        st.session_state.autogen_zip_buffer = None

    if "crewai_zip_buffer" not in st.session_state:
        st.session_state.crewai_zip_buffer = None

    if "current_project" not in st.session_state:
        st.session_state.current_project = Current_Project()

    if "discussion_history" not in st.session_state:
        st.session_state.discussion_history = ""

    if "last_agent" not in st.session_state:
        st.session_state.last_agent = ""

    if "last_comment" not in st.session_state:
        st.session_state.last_comment = ""

    if "max_tokens" not in st.session_state:
        st.session_state.max_tokens = 4096

    if "model" not in st.session_state:
        st.session_state.model = "default"

    if "most_recent_response" not in st.session_state:
        st.session_state.most_recent_response = ""

    if "previous_user_request" not in st.session_state:
        st.session_state.previous_user_request = ""        

    if "project_model" not in st.session_state:
        st.session_state.project_model = ProjectBaseModel()

    if "provider" not in st.session_state:
        st.session_state.provider = LLM_PROVIDER

    if "reference_html" not in st.session_state:
        st.session_state.reference_html = {}

    if "reference_url" not in st.session_state:
        st.session_state.reference_url = ""

    if "rephrased_request" not in st.session_state:
        st.session_state.rephrased_request = ""

    if "response_text" not in st.session_state:       
        st.session_state.response_text = ""

    if "show_edit" not in st.session_state:
        st.session_state.show_edit = False        

    if "selected_tools" not in st.session_state:
        st.session_state.selected_tools = []

    if "show_request_input" not in st.session_state:
        st.session_state.show_request_input = True

    if "temperature_slider" not in st.session_state:
        st.session_state.temperature_slider = 0.3

    if "tool_model" not in st.session_state:
        st.session_state.tool_model = ToolBaseModel(
            name="",
            description="",
            title="",
            file_name="",
            content="",
            id=None,
            created_at=None,
            updated_at=None,
            user_id=None,
            secrets=None,
            libraries=None,
            timestamp=None
        )    

    if "tool_models" not in st.session_state:
        st.session_state.tool_models = []


    # if "tools" not in st.session_state:
    #     st.session_state.tools = [] 

    if "tool_functions" not in st.session_state:
        st.session_state.tool_functions = {}

    if "tool_name" not in st.session_state:
        st.session_state.tool_name = None

    if "tool_request" not in st.session_state:
        st.session_state.tool_request = ""

    if "tool_result_string" not in st.session_state:
        st.session_state.tool_result_string = ""

    if "top_p" not in st.session_state:
          st.session_state.top_p = 1

    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = None

    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    if "user_input_widget_auto_moderate" not in st.session_state:
            st.session_state.user_input_widget_auto_moderate = ""

    if st.session_state.get("user_request"):
        handle_user_request(st.session_state)

    if "whiteboard_content" not in st.session_state:
        st.session_state.whiteboard_content = ""

    if "workflow" not in st.session_state:
        st.session_state.workflow = WorkflowBaseModel(
            name="",
            created_at=datetime.now(),
            description="",
            agents=[],
            sender=None,
            receiver=None,
            type="",
            user_id="default",
            timestamp=datetime.now(),
            summary_method=""
        )

    for provider in SUPPORTED_PROVIDERS:
        if f"{provider.upper()}_API_URL" not in st.session_state:
            st.session_state[f"{provider.upper()}_API_URL"] = None