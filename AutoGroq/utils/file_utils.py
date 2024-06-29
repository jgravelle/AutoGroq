
import datetime 
import io
import json
import streamlit as st
import zipfile

from utils.db_utils import normalize_config
from utils.text_utils import sanitize_text
from utils.workflow_utils import get_workflow_from_agents

   

def create_workflow_data(workflow):
    # Sanitize the workflow name
    sanitized_workflow_name = sanitize_text(workflow["name"])
    sanitized_workflow_name = sanitized_workflow_name.lower().replace(' ', '_')

    return workflow


def create_zip_file(zip_buffer, file_data):
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_content in file_data.items():
            zip_file.writestr(file_name, file_content)


def regenerate_json_files_and_zip():
    # Get the updated workflow data
    workflow_data, _ = get_workflow_from_agents(st.session_state.agents)
    workflow_data["updated_at"] = datetime.datetime.now().isoformat()
    
    # Regenerate the zip files
    autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
    
    # Update the zip buffers in the session state
    st.session_state.autogen_zip_buffer = autogen_zip_buffer
    st.session_state.crewai_zip_buffer = crewai_zip_buffer


def regenerate_zip_files():
    if "agents" in st.session_state:
        workflow_data, _ = get_workflow_from_agents(st.session_state.agents)

        workflow_data["updated_at"] = datetime.datetime.now().isoformat()
        autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
        st.session_state.autogen_zip_buffer = autogen_zip_buffer
        st.session_state.crewai_zip_buffer = crewai_zip_buffer
        print("Zip files regenerated.")
    else:
        print("No agents found. Skipping zip file regeneration.")


def zip_files_in_memory(workflow_data):
    autogen_zip_buffer = io.BytesIO()
    crewai_zip_buffer = io.BytesIO()

    with zipfile.ZipFile(autogen_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as autogen_zip:
        for agent in st.session_state.agents:
            agent_data = agent.to_dict()
            agent_name = agent_data['name']
            agent_file_name = f"{agent_name}.json"
            autogen_zip.writestr(f"agents/{agent_file_name}", json.dumps(agent_data, indent=2))

        # Add tools to the zip file
        for tool in st.session_state.tool_models:
            tool_data = tool.to_dict()
            tool_name = tool_data['name']
            tool_file_name = f"{tool_name}.json"
            autogen_zip.writestr(f"tools/{tool_file_name}", json.dumps(tool_data, indent=2))

        # Add workflow data
        autogen_zip.writestr("workflow.json", json.dumps(workflow_data, indent=2))

    with zipfile.ZipFile(crewai_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as crewai_zip:
        for agent in st.session_state.agents:
            agent_data = normalize_config(agent.to_dict(), agent.name)
            agent_name = agent_data['name']
            crewai_agent_data = {
                "name": agent_name,
                "description": agent_data.get('description', ''),
                "verbose": True,
                "allow_delegation": True
            }
            crewai_zip.writestr(f"agents/{agent_name}.json", json.dumps(crewai_agent_data, indent=2))

    autogen_zip_buffer.seek(0)
    crewai_zip_buffer.seek(0)

    return autogen_zip_buffer, crewai_zip_buffer
