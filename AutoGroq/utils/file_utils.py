
import datetime 
import io
import json
import streamlit as st
import zipfile

from configs.config import MODEL_TOKEN_LIMITS

from utils.agent_utils import create_agent_data
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
    try:
        autogen_file_data = {}
        for agent in st.session_state.agents:
            agent_name = agent.name
            formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
            agent_file_name = f"{formatted_agent_name}.json"

            # Use the agent-specific model configuration
            autogen_agent_data, _ = create_agent_data(agent.to_dict())
            autogen_agent_data['config']['name'] = formatted_agent_name
            autogen_agent_data['config']['llm_config']['config_list'][0]['model'] = agent.config['llm_config']['config_list'][0]['model']
            autogen_agent_data['config']['llm_config']['max_tokens'] = agent.config['llm_config'].get('max_tokens', MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096))
            autogen_agent_data['tools'] = []

            for tool_model in st.session_state.tool_models:
                if tool_model.name in st.session_state.selected_tools:
                    tool_json = {
                        "name": tool_model.name,
                        "description": tool_model.description,
                        "title": tool_model.title,
                        "file_name": tool_model.file_name,
                        "content": tool_model.content,
                        "timestamp": tool_model.timestamp,
                        "user_id": tool_model.user_id
                    }
                    autogen_agent_data['tools'].append(tool_json)

            agent_file_data = json.dumps(autogen_agent_data, indent=2)
            agent_file_data = agent_file_data.encode('utf-8')
            autogen_file_data[f"agents/{agent_file_name}"] = agent_file_data

        for tool_model in st.session_state.tool_models:
            if tool_model.name in st.session_state.selected_tools:
                tool_json = json.dumps({
                    "name": tool_model.name,
                    "description": tool_model.description,
                    "title": tool_model.title,
                    "file_name": tool_model.file_name,
                    "content": tool_model.content,
                    "timestamp": tool_model.timestamp,
                    "user_id": tool_model.user_id
                }, indent=2)
                tool_json = tool_json.encode('utf-8')
                autogen_file_data[f"tools/{tool_model.name}.json"] = tool_json

        workflow_file_name = "workflow.json"
        workflow_file_data = json.dumps(workflow_data, indent=2)
        workflow_file_data = workflow_file_data.encode('utf-8')
        autogen_file_data[workflow_file_name] = workflow_file_data

        crewai_file_data = {}
        for index, agent in enumerate(st.session_state.agents):
            agent_name = agent.name
            formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
            crewai_agent_data = create_agent_data(agent.to_dict())[1]
            crewai_agent_data['name'] = formatted_agent_name
            agent_file_name = f"{formatted_agent_name}.json"
            agent_file_data = json.dumps(crewai_agent_data, indent=2)
            agent_file_data = agent_file_data.encode('utf-8')
            crewai_file_data[f"agents/{agent_file_name}"] = agent_file_data

        create_zip_file(autogen_zip_buffer, autogen_file_data)
        create_zip_file(crewai_zip_buffer, crewai_file_data)
        autogen_zip_buffer.seek(0)
        crewai_zip_buffer.seek(0)
        return autogen_zip_buffer, crewai_zip_buffer
    except Exception as e:
        print(f"Error creating zip files: {str(e)}")
        return None, None   