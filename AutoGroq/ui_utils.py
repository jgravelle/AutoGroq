import io
import json
import os
import streamlit as st
import zipfile
from api_utils import call_coordinating_agent_api, rephrase_prompt, get_agents_from_text, extract_code_from_response, get_workflow_from_agents
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

def display_download_button():
    if "zip_buffer" in st.session_state:
        st.download_button(
            label="Download Files",
            data=st.session_state.zip_buffer,
            file_name="autogroq_files.zip",
            mime="application/zip"
        )

def display_reset_button():
    if st.button("Reset", key="reset_button"):
        # Reset specific elements without clearing entire session state
        for key in ["rephrased_request", "discussion", "whiteboard", "user_request", "user_input", "agents", "zip_buffer"]:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.user_request = ""
        
        st.session_state.show_begin_button = True
        st.experimental_rerun()
                
def display_user_request_input(): 
    user_request = st.text_input("Enter your request:", key="user_request", on_change=handle_begin, args=(st.session_state,)) 


import time

def handle_begin(session_state):
    user_request = session_state.user_request
    max_retries = 3
    retry_delay = 1  # in seconds
    
    for retry in range(max_retries):
        try:
            rephrased_text = rephrase_prompt(user_request)
            print(f"Debug: Rephrased text: {rephrased_text}")
            if rephrased_text:
                session_state.rephrased_request = rephrased_text
                agents = get_agents_from_text(rephrased_text)
                print(f"Debug: Agents: {agents}")
                agents_data = {agent["expert_name"]: create_agent_data(agent["expert_name"], agent["description"], agent.get("skills"), agent.get("tools")) for agent in agents}
                print(f"Debug: Agents data: {agents_data}")
                workflow_data = get_workflow_from_agents(agents)
                print(f"Debug: Workflow data: {workflow_data}")

                zip_buffer = zip_files_in_memory(agents_data, workflow_data)
                session_state.zip_buffer = zip_buffer
                session_state.agents = agents
                display_download_button()
                break  # Exit the loop if successful
            else:
                print("Error: Failed to extract a valid rephrased prompt.")
                break  # Exit the loop if rephrasing fails
        except Exception as e:
            if "string indices must be integers" in str(e):
                if retry < max_retries - 1:
                    print(f"Error occurred in handle_begin: {str(e)}. Retrying in {retry_delay} second(s)...")
                    time.sleep(retry_delay)
                else:
                    print(f"Error occurred in handle_begin: {str(e)}. Max retries exceeded.")
                    break  # Exit the loop if max retries exceeded
            else:
                print(f"Error occurred in handle_begin: {str(e)}")
                break  # Exit the loop for other errors


    
def update_discussion_and_whiteboard(expert_name, response, user_input):
    print("Updating discussion and whiteboard...")
    print(f"Expert Name: {expert_name}")
    print(f"Response: {response}")
    print(f"User Input: {user_input}")

    if user_input:
        user_input_text = f"\n\nAdditional Input:\n\n{user_input}\n\n"
        st.session_state.discussion += user_input_text

    response_text = f"{response}\n\n===\n\n"
    st.session_state.discussion += response_text

    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard = code_blocks
    display_download_button()

    # Store the last agent and their comment in session variables
    st.session_state.last_agent = expert_name
    st.session_state.last_comment = response

    print(f"Last Agent: {st.session_state.last_agent}")
    print(f"Last Comment: {st.session_state.last_comment}")

    # Check if there are at least two agents in the discussion
    if len(st.session_state.agents) >= 2:
        print("Sufficient agents in the discussion. Calling coordinating agent API...")
        print(f"Agents: {st.session_state.agents}")
        print(f"Enhanced Prompt: {st.session_state.rephrased_request}")

        # Call the internal coordinating agent API
        coordinating_agent_response = call_coordinating_agent_api(
            st.session_state.last_agent,
            st.session_state.last_comment,
            st.session_state.agents,
            st.session_state.rephrased_request
        )
        print(coordinating_agent_response)

        print(f"Coordinating Agent Response: {coordinating_agent_response}")

        # Append the coordinating agent's response to the discussion
        st.session_state.discussion += f"\n\n{coordinating_agent_response}\n\n"
    else:
        print("Insufficient agents in the discussion. Skipping coordinating agent API call.")


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