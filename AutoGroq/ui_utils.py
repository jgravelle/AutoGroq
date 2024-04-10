import io
import json
import os
import streamlit as st
import zipfile
from api_utils import rephrase_prompt, get_agents_from_text, extract_code_from_response, get_workflow_from_agents
from file_utils import create_agent_data, sanitize_text


def display_discussion_and_whiteboard(): 
    col1, col2 = st.columns(2) 
    with col1: 
        st.text_area("Discussion", value=st.session_state.discussion, height=400, key="discussion") 
    with col2: 
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard") 
        
def display_user_input(): 
    user_input = st.text_area("Additional Input:", key="user_input", height=100) 
    return user_input 

def display_rephrased_request(): 
    st.text_area("Re-engineered Prompt:", value=st.session_state.get('rephrased_request', ''), height=100, key="rephrased_request_area") 
    
def display_reset_button():
    if st.button("Reset", key="reset_button"):
        # Reset specific elements without clearing entire session state
        for key in ["rephrased_request", "discussion", "whiteboard", "user_request", "user_input", "agents"]:
            if key in st.session_state:
                del st.session_state[key]

        st.session_state.show_begin_button = True
        st.experimental_rerun()
                
def display_user_request_input(): 
    user_request = st.text_input("Enter your request:", key="user_request", on_change=handle_begin, args=(st.session_state,)) 


def handle_begin(session_state):
    user_request = session_state.user_request
    try:
        rephrased_text = rephrase_prompt(user_request)
        if rephrased_text:
            session_state.rephrased_request = rephrased_text
            agents = get_agents_from_text(rephrased_text)
            agents_data = {agent["expert_name"]: create_agent_data(agent["expert_name"], agent["description"], agent.get("skills"), agent.get("tools")) for agent in agents}
            workflow_data = get_workflow_from_agents(agents)

            zip_buffer = zip_files_in_memory(agents_data, workflow_data)

            st.download_button(
                label="Download Files",
                data=zip_buffer,
                file_name="autogroq_files.zip",
                mime="application/zip"
            )

            session_state.agents = agents
        else:
            raise ValueError("Failed to extract a valid rephrased prompt.")
    except Exception as e:
        st.error(f"Error: {str(e)}")


    
def update_discussion_and_whiteboard(expert_name, response, user_input): 
    if user_input: 
        user_input_text = f"\n\nAdditional Input:\n\n{user_input}\n\n" 
        st.session_state.discussion += user_input_text 

    response_text = f"{response}\n\n===\n\n" 
    st.session_state.discussion += response_text 

    code_blocks = extract_code_from_response(response) 
    st.session_state.whiteboard = code_blocks


def zip_files_in_memory(agents_data, workflow_data):
    # Create a BytesIO object to hold the ZIP data
    zip_buffer = io.BytesIO()

    # Create a ZIP file in memory
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Write agent files to the ZIP
        for agent_name, agent_data in agents_data.items():
            agent_file_name = f"{agent_name}.json"
            agent_file_data = json.dumps(agent_data, indent=2)
            zip_file.writestr(f"agents/{agent_file_name}", agent_file_data)

        # Write workflow file to the ZIP
        workflow_file_name = f"{sanitize_text(workflow_data['name'])}.json"
        workflow_file_data = json.dumps(workflow_data, indent=2)
        zip_file.writestr(f"workflows/{workflow_file_name}", workflow_file_data)

    # Move the ZIP file pointer to the beginning
    zip_buffer.seek(0)

    return zip_buffer