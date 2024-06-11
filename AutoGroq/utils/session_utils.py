
import streamlit as st

from datetime import datetime
from models.project_base_model import ProjectBaseModel
from models.tool_base_model import ToolBaseModel
from models.workflow_base_model import WorkflowBaseModel
from current_project import Current_Project


def initialize_session_variables():
    if "agents" not in st.session_state:
        st.session_state.agents = []

    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

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

    if "project_model" not in st.session_state:
        st.session_state.project_model = ProjectBaseModel()

    if "previous_user_request" not in st.session_state:
        st.session_state.previous_user_request = ""

#    if "project_manager_output" not in st.session_state:
#        st.session_state.project_manager_output = ""


    if "reference_html" not in st.session_state:
        st.session_state.reference_html = {}

    if "reference_url" not in st.session_state:
        st.session_state.reference_url = ""

    if "rephrased_request" not in st.session_state:
        st.session_state.rephrased_request = ""

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

    if "top_p" not in st.session_state:
          st.session_state.top_p = 1

    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = None

    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    if "user_input_widget_auto_moderate" not in st.session_state:
            st.session_state.user_input_widget_auto_moderate = ""

    if "user_request" not in st.session_state:
        st.session_state.user_request = ""

    if "whiteboard" not in st.session_state:
        st.session_state.whiteboard = ""

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