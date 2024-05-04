import io
import json
import pandas as pd
import os
import re 
import streamlit as st
import time
import zipfile
from api_utils import rephrase_prompt, get_agents_from_text, extract_code_from_response, get_workflow_from_agents
from file_utils import create_agent_data, sanitize_text

def display_api_key_input():
    if "GROQ_API_KEY" in os.environ:
        # print("Environment variable GROQ_API_KEY:", os.environ["GROQ_API_KEY"])
        api_key = os.environ["GROQ_API_KEY"]
        # st.success("GROQ_API_KEY found in environment variables.")
    else:
        api_key = st.text_input("Enter your GROQ_API_KEY:", type="password", key="user_api_key")
    return api_key

def display_discussion_and_whiteboard():
    col1, col2 = st.columns(2)

    with col1:
        if "discussion_history" not in st.session_state:
            st.session_state.discussion_history = ""

        st.text_area("Most Recent Comment", value=st.session_state.get("last_comment", ""), height=400, key="discussion")

    with col2:
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard")

    with st.expander("Discussion History"):
            st.write(st.session_state.discussion_history)        




def display_discussion_modal():
    with st.expander("Discussion History"):
        st.write(st.session_state.discussion_history)

        

def display_user_input():
    user_input = st.text_area("Additional Input:", key="user_input", height=100)

    if user_input:
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        url_match = url_pattern.search(user_input)
        if url_match:
            st.session_state.reference_url = url_match.group()
        else:
            st.session_state.reference_url = ''
    else:
        st.session_state.reference_url = ''

    return user_input



def display_rephrased_request(): 
    st.text_area("Re-engineered Prompt:", value=st.session_state.get('rephrased_request', ''), height=100, key="rephrased_request_area") 


def display_download_button():
    if "autogen_zip_buffer" in st.session_state and "crewai_zip_buffer" in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download Autogen Files",
                data=st.session_state.autogen_zip_buffer,
                file_name="autogen_files.zip",
                mime="application/zip",
                key=f"autogen_download_button_{int(time.time())}"  # Generate a unique key based on timestamp
            )
        with col2:
            st.download_button(
                label="Download CrewAI Files",
                data=st.session_state.crewai_zip_buffer,
                file_name="crewai_files.zip",
                mime="application/zip",
                key=f"crewai_download_button_{int(time.time())}"  # Generate a unique key based on timestamp
            )
    else:
        st.warning("No files available for download.")


def display_reset_and_upload_buttons():
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Reset", key="reset_button"):
            # Reset specific elements without clearing entire session state
            for key in ["rephrased_request", "discussion", "whiteboard", "user_request", "user_input", "agents", "zip_buffer", "crewai_zip_buffer", "autogen_zip_buffer", "uploaded_file_content", "discussion_history", "last_comment","api_key", "user_api_key"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.user_request = ""
            st.session_state.show_begin_button = True
            st.experimental_rerun()
    
    with col2:
        uploaded_file = st.file_uploader("Upload a sample .csv of your data (optional)", type="csv")
        
        if uploaded_file is not None:
            try:
                # Attempt to read the uploaded file as a DataFrame
                df = pd.read_csv(uploaded_file).head(5)
                
                # Display the DataFrame in the app
                st.write("Data successfully uploaded and read as DataFrame:")
                st.dataframe(df)
                
                # Store the DataFrame in the session state
                st.session_state.uploaded_data = df
            except Exception as e:
                st.error(f"Error reading the file: {e}")
                


def display_user_request_input():
    user_request = st.text_input("Enter your request:", key="user_request")
    
    if st.session_state.get("previous_user_request") != user_request:
        st.session_state.previous_user_request = user_request
        
        if user_request:
            if not st.session_state.get('rephrased_request'):
                handle_begin(st.session_state)
            else:
                autogen_agents, crewai_agents = get_agents_from_text(st.session_state.rephrased_request)
                print(f"Debug: AutoGen Agents: {autogen_agents}")
                print(f"Debug: CrewAI Agents: {crewai_agents}")
                
                if not autogen_agents:
                    print("Error: No agents created.")
                    st.warning("Failed to create agents. Please try again.")
                    return
                
                agents_data = {}
                for agent in autogen_agents:
                    agent_name = agent['config']['name']
                    agents_data[agent_name] = agent
                
                print(f"Debug: Agents data: {agents_data}")
                
                workflow_data, _ = get_workflow_from_agents(autogen_agents)
                print(f"Debug: Workflow data: {workflow_data}")
                print(f"Debug: CrewAI agents: {crewai_agents}")
                
                autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(agents_data, workflow_data, crewai_agents)
                st.session_state.autogen_zip_buffer = autogen_zip_buffer
                st.session_state.crewai_zip_buffer = crewai_zip_buffer
                st.session_state.agents = autogen_agents
                
            st.experimental_rerun()



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
                break  # Exit the loop if successful
            else:
                print("Error: Failed to rephrase the user request.")
                st.warning("Failed to rephrase the user request. Please try again.")
                return  # Exit the function if rephrasing fails
        except Exception as e:
            print(f"Error occurred in handle_begin: {str(e)}")
            if retry < max_retries - 1:
                print(f"Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
            else:
                print("Max retries exceeded.")
                st.warning("An error occurred. Please try again.")
                return  # Exit the function if max retries are exceeded
    
    rephrased_text = session_state.rephrased_request
    
    autogen_agents, crewai_agents = get_agents_from_text(rephrased_text)
    print(f"Debug: AutoGen Agents: {autogen_agents}")
    print(f"Debug: CrewAI Agents: {crewai_agents}")
    
    if not autogen_agents:
        print("Error: No agents created.")
        st.warning("Failed to create agents. Please try again.")
        return
    
    agents_data = {}
    for agent in autogen_agents:
        agent_name = agent['config']['name']
        agents_data[agent_name] = agent
    
    print(f"Debug: Agents data: {agents_data}")
    
    workflow_data, _ = get_workflow_from_agents(autogen_agents)
    print(f"Debug: Workflow data: {workflow_data}")
    print(f"Debug: CrewAI agents: {crewai_agents}")
    
    autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(agents_data, workflow_data, crewai_agents)
    session_state.autogen_zip_buffer = autogen_zip_buffer 
    session_state.crewai_zip_buffer = crewai_zip_buffer
    session_state.agents = autogen_agents


    
def update_discussion_and_whiteboard(expert_name, response, user_input):
    print("Updating discussion and whiteboard...")
    print(f"Expert Name: {expert_name}")
    print(f"Response: {response}")
    print(f"User Input: {user_input}")

    if user_input:
        user_input_text = f"\n\nAdditional Input:\n\n{user_input}\n\n"
        st.session_state.discussion_history += user_input_text

    response_text = f"{expert_name}:\n\n    {response}\n\n===\n\n"
    st.session_state.discussion_history += response_text

    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard = code_blocks

    st.session_state.last_agent = expert_name
    st.session_state.last_comment = response_text
    print(f"Last Agent: {st.session_state.last_agent}")
    print(f"Last Comment: {st.session_state.last_comment}")
    


def zip_files_in_memory(agents_data, workflow_data, crewai_agents):
    # Create separate ZIP buffers for Autogen and CrewAI
    autogen_zip_buffer = io.BytesIO()
    crewai_zip_buffer = io.BytesIO()

    # Create a ZIP file in memory
    with zipfile.ZipFile(autogen_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Write agent files to the ZIP
        for agent_name, agent_data in agents_data.items():
            agent_file_name = f"{agent_name}.json"
            agent_file_data = json.dumps(agent_data, indent=2)
            zip_file.writestr(f"agents/{agent_file_name}", agent_file_data)

        # Write workflow file to the ZIP
        workflow_file_name = f"{sanitize_text(workflow_data['name'])}.json"
        workflow_file_data = json.dumps(workflow_data, indent=2)
        zip_file.writestr(f"workflows/{workflow_file_name}", workflow_file_data)

    with zipfile.ZipFile(crewai_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for index, agent_data in enumerate(crewai_agents):
            agent_file_name = f"agent_{index}.json"
            agent_file_data = json.dumps(agent_data, indent=2)
            zip_file.writestr(f"agents/{agent_file_name}", agent_file_data)

    # Move the ZIP file pointers to the beginning
    autogen_zip_buffer.seek(0)
    crewai_zip_buffer.seek(0)

    return autogen_zip_buffer, crewai_zip_buffer