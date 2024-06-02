
import streamlit as st

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

    if "previous_user_request" not in st.session_state:
        st.session_state.previous_user_request = ""

#    if "project_manager_output" not in st.session_state:
#        st.session_state.project_manager_output = ""

#    if "proposed_skill" not in st.session_state:
#        st.session_state.proposed_skill = None

    if "reference_html" not in st.session_state:
        st.session_state.reference_html = {}

    if "reference_url" not in st.session_state:
        st.session_state.reference_url = ""

    if "rephrased_request" not in st.session_state:
        st.session_state.rephrased_request = ""

    if "selected_skills" not in st.session_state:
        st.session_state.selected_skills = []

    if "show_request_input" not in st.session_state:
        st.session_state.show_request_input = True

    if "skill_functions" not in st.session_state:
        st.session_state.skill_functions = {}

    if "skill_name" not in st.session_state:
        st.session_state.skill_name = None

    if "skill_request" not in st.session_state:
        st.session_state.skill_request = ""

#    if "temperature" not in st.session_state:
#           st.session_state.temperature = 0.3

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
