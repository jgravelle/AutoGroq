# AutoGroq\agent_management.py

```python
# agent_management.py

import base64
import json
import logging
import os
import re
import requests
import streamlit as st

from configs.config import BUILT_IN_AGENTS, LLM_PROVIDER, MODEL_CHOICES, MODEL_TOKEN_LIMITS

from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from utils.api_utils import get_api_key
from utils.error_handling import log_error
from utils.tool_utils import populate_tool_models, show_tools
from utils.ui_utils import display_goal, get_llm_provider, get_provider_models, update_discussion_and_whiteboard

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def agent_button_callback(agent_index):
    def callback():
        logger.debug(f"Agent button clicked for index: {agent_index}")
        st.session_state['selected_agent_index'] = agent_index
        agent = st.session_state.agents[agent_index]
        
        logger.debug(f"Agent: {agent}")
        
        # Check if the agent is an instance of AgentBaseModel
        if isinstance(agent, AgentBaseModel):
            agent_name = agent.name if hasattr(agent, 'name') else ''
            agent_description = agent.description if hasattr(agent, 'description') else ''
        else:
            # Fallback for dictionary-like structure
            agent_name = agent.get('config', {}).get('name', '')
            agent_description = agent.get('description', '')
        
        logger.debug(f"Agent name: {agent_name}, description: {agent_description}")
        
        st.session_state['form_agent_name'] = agent_name
        st.session_state['form_agent_description'] = agent_description
        # Directly call process_agent_interaction here if appropriate
        process_agent_interaction(agent_index)
    return callback


def construct_request(agent, agent_name, description, user_request, user_input, rephrased_request, reference_url, tool_results):
    request = f"Act as the {agent_name} who {description}."
    if user_request:
        request += f" Original request was: {user_request}."
    if rephrased_request:
        request += f" You are helping a team work on satisfying {rephrased_request}."
    if user_input:
        request += f" Additional input: {user_input}."
    if reference_url and reference_url in st.session_state.reference_html:
        html_content = st.session_state.reference_html[reference_url]
        request += f" Reference URL content: {html_content}."
    if st.session_state.discussion:
        request += f" The discussion so far has been {st.session_state.discussion[-50000:]}."
    if tool_results:
        request += f" tool results: {tool_results}."
    
    # Check if agent is an AgentBaseModel instance
    if isinstance(agent, AgentBaseModel):
        agent_tools = agent.tools
    else:
        agent_tools = agent.get('tools', [])
    
    if agent_tools:
        request += "\n\nYou have access to the following tools:\n"
        for tool in agent_tools:
            if isinstance(tool, ToolBaseModel):
                request += f"{str(tool)}\n"
            elif isinstance(tool, dict):
                request += f"{tool.get('name', 'Unknown Tool')}: {tool.get('description', 'No description available')}\n"
        request += "\nTo use a tool, include its name and arguments in your response, e.g., 'I will use calculate_compound_interest(1000, 0.05, 10) to determine the future value.'"
    
    return request


def display_agents():
    if "agents" in st.session_state and st.session_state.agents and len(st.session_state.agents) == 3:
        st.sidebar.warning(f"No agents have yet been created. Please enter a new request.")
        st.sidebar.warning(f"ALSO: If no agents are created, do a hard reset (CTL-F5) and try switching models. LLM results can be unpredictable.")
        st.sidebar.warning(f"SOURCE:  https://github.com/jgravelle/AutoGroq\n\r\n\r https://j.gravelle.us\n\r\n\r DISCORD: https://discord.gg/DXjFPX84gs \n\r\n\r YouTube: https://www.youtube.com/playlist?list=PLPu97iZ5SLTsGX3WWJjQ5GNHy7ZX66ryP")

    else:
        st.sidebar.title("Your Agents")
        st.sidebar.subheader("Click to interact")
        
        dynamic_agents_exist = False
        built_in_agents = []

        # First pass: Identify if there are any dynamic agents and collect built-in agents
        for index, agent in enumerate(st.session_state.agents):
            if agent.name not in BUILT_IN_AGENTS:
                dynamic_agents_exist = True
            else:
                built_in_agents.append((agent, index))

        # Display dynamically created agents
        for index, agent in enumerate(st.session_state.agents):
            if agent.name not in BUILT_IN_AGENTS:
                display_agent_button(agent, index)

        # Display built-in agents only if dynamic agents exist
        if dynamic_agents_exist and built_in_agents:
            st.sidebar.markdown("---")
            st.sidebar.markdown("Built-in Agents:")
            for agent, index in built_in_agents:
                display_agent_button(agent, index)
            display_goal()
            populate_tool_models()
            show_tools()
        else:
            st.empty()


def display_agent_button(agent, index):
    col1, col2 = st.sidebar.columns([1, 4])
    with col1:
        gear_icon = "⚙️"
        if st.button(gear_icon, key=f"gear_{index}", help="Edit Agent"):
            st.session_state['edit_agent_index'] = index
            st.session_state[f'show_edit_{index}'] = not st.session_state.get(f'show_edit_{index}', False)
    with col2:
        if "next_agent" in st.session_state and st.session_state.next_agent == agent.name:
            button_style = """
            <style>
            div[data-testid*="stButton"] > button[kind="secondary"] {
                background-color: green !important;
                color: white !important;
            }
            </style>
            """
            st.markdown(button_style, unsafe_allow_html=True)
        st.button(agent.name, key=f"agent_{index}", on_click=agent_button_callback(index))
    
    if st.session_state.get(f'show_edit_{index}', False):
        display_agent_edit_form(agent, index)


def display_agent_buttons(agents):
    for index, agent in enumerate(agents):
        agent_name = agent.name if agent.name else f"Unnamed Agent {index + 1}"
        agent_id = getattr(agent, 'id', index)  # Use agent's id if available, otherwise use index
        col1, col2 = st.sidebar.columns([1, 4])
        with col1:
            gear_icon = "⚙️" # Unicode character for gear icon
            if st.button(
                gear_icon,
                key=f"gear_{agent_id}_{agent_name}",  # Use both id and name for uniqueness
                help="Edit Agent" # Add the tooltip text
            ):
                st.session_state['edit_agent_index'] = index
                st.session_state['show_edit'] = True
        with col2:
            if "next_agent" in st.session_state and st.session_state.next_agent == agent_name:
                button_style = """
                <style>
                div[data-testid*="stButton"] > button[kind="secondary"] {
                    background-color: green !important;
                    color: white !important;
                }
                </style>
                """
                st.markdown(button_style, unsafe_allow_html=True)
            st.button(agent_name, key=f"agent_{agent_id}_{agent_name}", on_click=agent_button_callback(index))


def display_agent_edit_form(agent, edit_index):
    with st.expander(f"Edit Properties of {agent.name}", expanded=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            unique_key = f"name_{edit_index}_{agent.name}"
            new_name = st.text_input("Name", value=agent.name, key=unique_key)
            if st.session_state.get(f"delete_confirmed_{edit_index}_{agent.name}", False):
                if st.button("Confirm Deletion", key=f"confirm_delete_{edit_index}_{agent.name}"):
                    st.session_state.agents.pop(edit_index)
                    st.session_state[f'show_edit_{edit_index}'] = False
                    del st.session_state[f"delete_confirmed_{edit_index}_{agent.name}"]
                    st.experimental_rerun()
                if st.button("Cancel", key=f"cancel_delete_{edit_index}_{agent.name}"):
                    del st.session_state[f"delete_confirmed_{edit_index}_{agent.name}"]
                    st.experimental_rerun()
        with col2:
            container = st.container()
            if container.button("X", key=f"delete_{edit_index}_{agent.name}"):
                if st.session_state.get(f"delete_confirmed_{edit_index}_{agent.name}", False):
                    st.session_state.agents.pop(edit_index)
                    st.session_state[f'show_edit_{edit_index}'] = False
                    st.experimental_rerun()
                else:
                    st.session_state[f"delete_confirmed_{edit_index}_{agent.name}"] = True
                    st.experimental_rerun()
        
        description_value = agent.description
        
        col1, col2 = st.columns([3, 1])
        with col1:
            current_provider = agent.provider or st.session_state.get('provider')
            selected_provider = st.selectbox(
                "Provider",
                options=MODEL_CHOICES.keys(),
                index=list(MODEL_CHOICES.keys()).index(current_provider),
                key=f"provider_select_{edit_index}_{agent.name}"
            )

            provider_models = get_provider_models(selected_provider)
            current_model = agent.model or st.session_state.get('model')
            
            if current_model not in provider_models:
                st.warning(f"Current model '{current_model}' is not available for the selected provider. Please select a new model.")
                current_model = next(iter(provider_models))  # Set to first available model
            
            selected_model = st.selectbox(
                "Model", 
                options=list(provider_models.keys()),
                index=list(provider_models.keys()).index(current_model),
                key=f"model_select_{edit_index}_{agent.name}"
            )
        with col2:
            if st.button("Set for ALL agents", key=f"set_all_agents_{edit_index}_{agent.name}"):
                for agent in st.session_state.agents:
                    agent.config['provider'] = selected_provider
                    if 'llm_config' not in agent.config:
                        agent.config['llm_config'] = {'config_list': [{}]}
                    if not agent.config['llm_config']['config_list']:
                        agent.config['llm_config']['config_list'] = [{}]
                    agent.config['llm_config']['config_list'][0]['model'] = selected_model
                    agent.config['llm_config']['max_tokens'] = provider_models[selected_model]
                st.experimental_rerun()
        
        # Display the description in a text area
        new_description = st.text_area("Description", value=description_value, key=f"desc_{edit_index}_{agent.name}")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Update User Description", key=f"regenerate_{edit_index}_{agent.name}"):
                print(f"Regenerate button clicked for agent {edit_index}")
                new_description = regenerate_agent_description(agent)
                if new_description:
                    agent.description = new_description
                    print(f"Description regenerated for {agent.name}: {new_description}")
                    st.session_state[f"regenerate_description_{edit_index}_{agent.name}"] = True
                    description_value = new_description
                    st.experimental_rerun()
                else:
                    print(f"Failed to regenerate description for {agent.name}")
        with col2:
            if st.button("Save", key=f"save_{edit_index}_{agent.name}"):
                agent.name = new_name
                agent.description = new_description
                agent.provider = selected_provider
                agent.model = selected_model
                
                # Update the config as well
                agent.config['provider'] = selected_provider
                if 'llm_config' not in agent.config:
                    agent.config['llm_config'] = {'config_list': [{}]}
                if not agent.config['llm_config']['config_list']:
                    agent.config['llm_config']['config_list'] = [{}]
                agent.config['llm_config']['config_list'][0]['model'] = selected_model
                agent.config['llm_config']['max_tokens'] = provider_models[selected_model]
                
                st.session_state[f'show_edit_{edit_index}'] = False
           
                if 'edit_agent_index' in st.session_state:
                    del st.session_state['edit_agent_index']
                st.session_state.agents[edit_index] = agent
                st.experimental_rerun()

    # Add a debug print to check the agent's description
    print(f"Agent {agent.name} description: {agent.description}")


def download_agent_file(expert_name):
    # Format the expert_name
    formatted_expert_name = re.sub(r'[^a-zA-Z0-9\s]', '', expert_name) # Remove non-alphanumeric characters
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_') # Convert to lowercase and replace spaces with underscores
    # Get the full path to the agent JSON file
    agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))
    json_file = os.path.join(agents_dir, f"{formatted_expert_name}.json")
    # Check if the file exists
    if os.path.exists(json_file):
        # Read the file content
        with open(json_file, "r") as f:
            file_content = f.read()
        # Encode the file content as base64
        b64_content = base64.b64encode(file_content.encode()).decode()
        # Create a download link
        href = f'<a href="data:application/json;base64,{b64_content}" download="{formatted_expert_name}.json">Download {formatted_expert_name}.json</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error(f"File not found: {json_file}")


def extract_content(response):
    if isinstance(response, dict) and 'choices' in response:
        # Handle response from providers like Groq
        return response['choices'][0]['message']['content']
    elif hasattr(response, 'content') and isinstance(response.content, list):
        # Handle Anthropic-style response
        return response.content[0].text
    elif isinstance(response, requests.models.Response):
        # Handle response from providers using requests.Response
        try:
            json_response = response.json()
            if 'choices' in json_response and json_response['choices']:
                return json_response['choices'][0]['message']['content']
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from response")
    logger.error(f"Unexpected response format: {type(response)}")
    return None


def process_agent_interaction(agent_index):
    agent = st.session_state.agents[agent_index]
    logger.debug(f"Processing interaction for agent: {agent.name}")
    logger.debug(f"Agent tools: {agent.tools}")
    
    if isinstance(agent, AgentBaseModel):
        agent_name = agent.name
        description = agent.description
        agent_tools = agent.tools
    else:
        # Fallback for dictionary-like structure
        agent_name = agent.get('config', {}).get('name', '')
        description = agent.get('description', '')
        agent_tools = agent.get("tools", [])
    
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')
    rephrased_request = st.session_state.get('rephrased_request', '')
    reference_url = st.session_state.get('reference_url', '')
    
    # Execute associated tools for the agent
    tool_results = {}
    for tool in agent_tools:
        try:
            logger.debug(f"Executing tool: {tool.name}")
            if tool.name in st.session_state.tool_functions:
                tool_function = st.session_state.tool_functions[tool.name]
                if tool.name == 'fetch_web_content' and reference_url:
                    tool_result = tool_function(reference_url)
                elif tool.name == 'generate_code':
                    tool_result = tool_function(user_input or user_request or rephrased_request)
                else:
                    tool_result = tool_function(user_input or user_request or rephrased_request)
                logger.debug(f"Tool result: {tool_result[:500]}...")  # Log first 500 characters of result
            else:
                logger.error(f"Tool function not found for {tool.name}")
                tool_result = f"Error: Tool function not found for {tool.name}"
            
            tool_results[tool.name] = tool_result
            
            logger.debug(f"Tool result for {tool.name}: {tool_result[:500]}...")
            
            # Update the tool_result_string in the session state
            st.session_state.tool_result_string = tool_result[:1000] + "..."  # Limit to first 1000 characters
            
            # Update the discussion and whiteboard immediately
            update_discussion_and_whiteboard(tool.name, st.session_state.tool_result_string, "")
            
        except Exception as e:
            error_message = f"Error executing tool {tool.name}: {str(e)}"
            logger.error(error_message, exc_info=True)
            tool_results[tool.name] = error_message
            st.session_state.tool_result_string = error_message
            update_discussion_and_whiteboard(tool.name, error_message, "")
    
    request = construct_request(agent, agent_name, description, user_request, user_input, rephrased_request, reference_url, tool_results)
    
    # Use the agent-specific provider and model
    if isinstance(agent, AgentBaseModel):
        provider = agent.provider or st.session_state.get('provider', LLM_PROVIDER)
        model = agent.model or st.session_state.get('model', 'default')
    else:
        # Fallback for dictionary-like structure
        provider = agent.get('provider') or st.session_state.get('provider', LLM_PROVIDER)
        model = agent.get('model') or st.session_state.get('model', 'default')

    logger.debug(f"Using provider: {provider}, model: {model}")

    api_key = get_api_key(provider)
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)
    
    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": MODEL_TOKEN_LIMITS.get(model, 4096),
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": request
            }
        ]
    }
    logger.debug(f"Sending request to {provider} using model {model}")
    response = llm_provider.send_request(llm_request_data)
    
    content = extract_content(response)
    if content:
        update_discussion_and_whiteboard(agent_name, content, user_input)
        st.session_state['form_agent_name'] = agent_name
        st.session_state['form_agent_description'] = description
        st.session_state['selected_agent_index'] = agent_index
    else:
        error_message = f"Error: Failed to extract content from response"
        log_error(error_message)
        logger.error(error_message)

    # Force a rerun to update the UI and trigger the moderator if necessary
    st.experimental_rerun()


def regenerate_agent_description(agent):
    agent_name = agent.name if hasattr(agent, 'name') else "Unknown Agent"
    agent_description = agent.description if hasattr(agent, 'description') else ""
    print(f"agent_name: {agent_name}")
    print(f"agent_description: {agent_description}")
    user_request = st.session_state.get('user_request', '')
    print(f"user_request: {user_request}")
    discussion_history = st.session_state.get('discussion_history', '')
    prompt = f"""
    You are an AI assistant helping to improve an agent's description. The agent's current details are:
    Name: {agent_name}
    Description: {agent_description}
    The current user request is: {user_request}
    The discussion history so far is: {discussion_history}
    Please generate a revised description for this agent that defines it in the best manner possible to address the current user request, taking into account the discussion thus far. Return only the revised description, written in the third-person, without any additional commentary or narrative. It is imperative that you return ONLY the text of the new description written in the third-person. No preamble, no narrative, no superfluous commentary whatsoever. Just the description, written in the third-person, unlabeled, please.  You will have been successful if your reply is thorough, comprehensive, concise, written in the third-person, and adherent to all of these instructions.
    """
    print(f"regenerate_agent_description called with agent_name: {agent_name}")
    print(f"regenerate_agent_description called with prompt: {prompt}")
    
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    response = llm_provider.send_request(llm_request_data)

    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            return content.strip()

    return None


def retrieve_agent_information(agent_index):
    agent = st.session_state.agents[agent_index]
    agent_name = agent["config"]["name"]
    description = agent["description"]
    return agent_name, description


def send_request(agent_name, request):
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    response = llm_provider.send_request(request)
    return response

```

# AutoGroq\main.py

```python
# main.py

import streamlit as st 

from agent_management import display_agents
from utils.api_utils import fetch_available_models, get_api_key
from utils.auth_utils import display_api_key_input
from utils.error_handling import setup_logging
from utils.session_utils import initialize_session_variables
from utils.tool_utils import load_tool_functions
from utils.ui_utils import (
    display_reset_and_upload_buttons, 
    display_user_request_input, handle_user_request, 
    select_model, select_provider, set_css, 
    set_temperature, show_interfaces
)


def main():
    setup_logging()
    if 'warning_placeholder' not in st.session_state:
        st.session_state.warning_placeholder = st.empty()
    st.title("AutoGroq™")

    set_css()
    initialize_session_variables()
    fetch_available_models()
    load_tool_functions()

    if st.session_state.get("need_rerun", False):
        st.session_state.need_rerun = False
        st.rerun()    

    display_api_key_input()
    get_api_key() 
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        select_provider()
    
    with col2:
        select_model()

    with col3:
        set_temperature()

    if st.session_state.show_request_input:
        with st.container():
            if st.session_state.get("rephrased_request", "") == "":
                user_request = st.text_input("Enter your request:", key="user_request", value=st.session_state.get("user_request", ""), on_change=handle_user_request, args=(st.session_state,))
                display_user_request_input()
            if "agents" in st.session_state and st.session_state.agents:
                show_interfaces()
                display_reset_and_upload_buttons()
        
    with st.sidebar:
        display_agents()
         

if __name__ == "__main__":
    main()
```

# AutoGroq\prompts.py

```python
# prompts.py

def create_project_manager_prompt(rephrased_text):
    return f"""
                As a Project Manager, create a project plan for:
                {rephrased_text}
                Include:

                Project Outline:

                Comprehensive overview
                Logical structure
                Key Deliverables: List in order of completion


                Expert Team:

                Roles based on project needs
                Minimum necessary team size
                For each expert:
                a) Role title
                b) Key responsibilities
                c) Essential expertise



                Format:
                Project Outline:
                [Your detailed outline]
                Key Deliverables:
                [Numbered list]
                Team of Experts:
                [Description of the ideal team of experts]
            """


def get_agent_prompt(rephrased_request):
    return f"""
        Based on the following user request, please create a detailed and comprehensive description 
        of an AI agent that can effectively assist with the request:

        User Request: "{rephrased_request}"

        Provide a clear and concise description of the agent's role, capabilities, and expertise.
        The description should be efficiently written in a concise, professional and engaging manner, 
        highlighting the agent's ability to understand and respond to the request efficiently.

        Agent Description:
        """


def get_agents_prompt():
    return """
    You are an expert system designed to format the JSON describing each member of the team 
    of AI agents listed in the 'Team of Experts' section below. Follow these guidelines:
    1. Agent Roles: Clearly transcribe the titles of each agent listed.
    2. Expertise Description: Provide a brief but thorough description of each agent's expertise 
       based on the provided information.
    3. Format: Return the results in JSON format with values labeled as expert_name, description, role, goal, and backstory.
       'expert_name' should be the agent's title, not their given or proper name.

    Return ONLY the JSON array, with no other text:
    [
        {
            "expert_name": "agent_title",
            "description": "agent_description",
            "role": "agent_role",
            "goal": "agent_goal",
            "backstory": "agent_backstory"
        }
    ]
    """
        
# Contributed by ScruffyNerf
def get_generate_tool_prompt(rephrased_tool_request):
    return f'''
                Based on the rephrased tool request below, please do the following:

                1. Do step-by-step reasoning and think to better understand the request.
                2. Code the best Autogen Studio Python tool as per the request as a [tool_name].py file.
                3. Return only the tool file, no commentary, intro, or other extra text. If there ARE any non-code lines, 
                    please pre-pend them with a '#' symbol to comment them out.
                4. A proper tool will have these parts:
                   a. Imports (import libraries needed for the tool)
                   b. Function definition AND docstrings (this helps the LLM understand what the function does and how to use it)
                   c. Function body (the actual code that implements the function)
                   d. (optional) Example usage - ALWAYS commented out
                   Here is an example of a well formatted tool:

                   # Tool filename: save_file_to_disk.py
                   # Import necessary module(s)
                   import os

                   def save_file_to_disk(contents, file_name):
                   # docstrings
                   """
                   Saves the given contents to a file with the given file name.

                   Parameters:
                   contents (str): The string contents to save to the file.
                   file_name (str): The name of the file, including its extension.

                   Returns:
                   str: A message indicating the success of the operation.
                   """

                   # Body of tool

                   # Ensure the directory exists; create it if it doesn't
                   directory = os.path.dirname(file_name)
                   if directory and not os.path.exists(directory):
                      os.makedirs(directory)

                   # Write the contents to the file
                   with open(file_name, 'w') as file:
                      file.write(contents)
    
                   return f"File file_name has been saved successfully."

                   # Example usage:
                   # contents_to_save = "Hello, world!"
                   # file_name = "example.txt"
                   # print(save_file_to_disk(contents_to_save, file_name))

                Rephrased tool request: "{rephrased_tool_request}"
                '''


def get_moderator_prompt(discussion_history, goal, last_comment, last_speaker, team_members_str, current_deliverable, current_phase):
    return f"""
        This agent is our Moderator Bot. Its goal is to mediate the conversation between a team of AI agents 
        in a manner that persuades them to act in the most expeditious and thorough manner to accomplish their goal. 
        This will entail considering the user's stated goal, the conversation thus far, the descriptions 
        of all the available agent/experts in the current team, the last speaker, and their remark. 
        Based upon a holistic analysis of all the facts at hand, use logic and reasoning to decide which team member should speak next. 
        Then draft a prompt directed at that agent that persuades them to act in the most expeditious and thorough manner toward helping this team of agents 
        accomplish their goal.

        Their overall goal is: {goal}.
        The current deliverable they're working on is: {current_deliverable}
        The current implementation phase is: {current_phase}
        The last speaker was {last_speaker}, who said: {last_comment}

        Here is the current conversational discussion history: {discussion_history}

        And here are the team members and their descriptions:
        {team_members_str}

        IMPORTANT: Your response must start with "To [Agent Name]:", where [Agent Name] is one of the valid team members listed above. Do not address tools or non-existent team members.

        This agent's response should be JUST the requested prompt addressed to the next agent, and should not contain 
        any introduction, narrative, or any other superfluous text whatsoever.

        If you believe the current phase of the deliverable has been satisfactorily completed, include the exact phrase 
        "PHASE_COMPLETED" at the beginning of your response, followed by your usual prompt to the next agent focusing on 
        the next phase or deliverable.

        Remember, we are now in the {current_phase} phase. The agents should focus on actually implementing, coding, 
        testing, or deploying the solutions as appropriate for the current phase, not just planning.
    """


def get_rephrased_user_prompt(user_request):
    return f"""Act as a professional prompt engineer and refactor the following 
                user request into an optimized prompt. This agent's goal is to rephrase the request 
                with a focus on the satisfying all following the criteria without explicitly stating them:
        1. Clarity: Ensure the prompt is clear and unambiguous.
        2. Specific Instructions: Provide detailed steps or guidelines.
        3. Context: Include necessary background information.
        4. Structure: Organize the prompt logically.
        5. Language: Use concise and precise language.
        6. Examples: Offer examples to illustrate the desired output.
        7. Constraints: Define any limits or guidelines.
        8. Engagement: Make the prompt engaging and interesting.
        9. Feedback Mechanism: Suggest a way to improve or iterate on the response.

        Apply introspection and reasoning to reconsider your own prompt[s] to:
        Clarify ambiguities
        Break down complex tasks
        Provide essential context
        Structure logically
        Use precise, concise language
        Include relevant examples
        Specify constraints

        Do NOT reply with a direct response to these instructions OR the original user request. Instead, rephrase the user's request as a well-structured prompt, and
        return ONLY that rephrased prompt. Do not preface the rephrased prompt with any other text or superfluous narrative.
        Do not enclose the rephrased prompt in quotes. This agent will be successful only if it returns a well-formed rephrased prompt ready for submission as an LLM request.
        User request: "{user_request}"
        Rephrased:
    """

        
```

# AutoGroq\agents\code_developer.py

```python
# agents/code_developer.py

import datetime
import streamlit as st
from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.code_generator import code_generator_tool

class CodeDeveloperAgent(AgentBaseModel):
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

    @classmethod
    def create_default(cls):
        return cls(
            name="Code Developer",
            description="An agent specialized in generating code based on feature descriptions.",
            tools=[code_generator_tool],
            config={
                "llm_config": {
                    "config_list": [{"model": st.session_state.get('model', 'default'), "api_key": None}],
                    "temperature": st.session_state.get('temperature', 0.7)
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10
            },
            role="Code Developer",
            goal="To create efficient and effective code solutions based on given requirements.",
            backstory="I am an AI agent with extensive knowledge of various programming languages and software development best practices. My purpose is to assist in creating code that meets the specified requirements.",
            provider=st.session_state.get('provider', LLM_PROVIDER),
            model=st.session_state.get('model', 'default')
        )
    

    def to_dict(self):
        data = self.__dict__
        for key, value in data.items():
            if isinstance(value, ToolBaseModel):
                data[key] = value.to_dict()
        return data
```

# AutoGroq\agents\code_tester.py

```python
# agents/code_tester.py

import datetime
import streamlit as st
from configs.config import LLM_PROVIDER
from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from tools.code_test import code_test_tool

class CodeTesterAgent(AgentBaseModel):
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

    @classmethod
    def create_default(cls):
        return cls(
            name="Code Tester",
            description="An agent specialized in testing code and providing feedback on its functionality.",
            tools=[code_test_tool],
            config={
                "llm_config": {
                    "config_list": [{"model": st.session_state.get('model', 'default'), "api_key": None}],
                    "temperature": st.session_state.get('temperature', 0.7)
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10
            },
            role="Code Tester",
            goal="To thoroughly test code and provide comprehensive feedback to ensure its reliability and correctness.",
            backstory="I am an AI agent with expertise in software testing and quality assurance. My purpose is to rigorously test code and provide comprehensive feedback to ensure its reliability and correctness.",
            provider=st.session_state.get('provider', LLM_PROVIDER),
            model=st.session_state.get('model', 'default')
        )

    def to_dict(self):
        data = self.__dict__
        for key, value in data.items():
            if isinstance(value, ToolBaseModel):
                data[key] = value.to_dict()
        return data
```

# AutoGroq\agents\web_content_retriever.py

```python
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

```

# AutoGroq\cli\create_agent.py

```python

import argparse
import datetime
import json
import os
import streamlit as st
import sys

# Add the root directory to the Python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.config import MODEL_TOKEN_LIMITS
from prompts import get_agent_prompt
from utils.api_utils import get_llm_provider
from utils.agent_utils import create_agent_data
from utils.auth_utils import get_api_key
from utils.file_utils import sanitize_text

def create_agent(request, provider, model, temperature, max_tokens, output_file):
    # Get the API key and provider
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)

    # Generate the prompt using get_agent_prompt
    prompt = get_agent_prompt(request)

    # Adjust the token limit based on the selected model
    max_tokens = MODEL_TOKEN_LIMITS.get(provider, {}).get(model, 4096)

    # Make the request to the LLM API
    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = llm_provider.send_request(llm_request_data)

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(response.text)
        return

    response_data = response.json()

    if 'choices' not in response_data or len(response_data['choices']) == 0:
        print("Error: 'choices' not found in the response data or it's empty")
        print(json.dumps(response_data, indent=2))
        return

    agent_description = response_data['choices'][0]['message']['content'].strip()

    agent_data = {
        "type": "assistant",
        "config": {
            "name": request,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "model": model,
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": "OpenAI model configuration"
                    }
                ],
                "temperature": temperature,
                "cache_seed": None,
                "timeout": None,
                "max_tokens": max_tokens,
                "extra_body": None
            },
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 8,
            "system_message": f"You are a helpful assistant that can act as {sanitize_text(agent_description)} who {request}.",
            "is_termination_msg": None,
            "code_execution_config": None,
            "default_auto_reply": "",
            "description": agent_description  # Ensure the description key is present
        },
        "timestamp": datetime.datetime.now().isoformat(),
        "user_id": "default",
        "tools": []
    }

    # Debug print to verify agent_data
    print("Agent Data:", json.dumps(agent_data, indent=2))

    # Create the appropriate agent data
    autogen_agent_data, crewai_agent_data = create_agent_data(agent_data)

    # Save the agent data to the output file
    with open(output_file, "w") as f:
        json.dump(autogen_agent_data, f, indent=2)

    print(f"Agent created successfully. Output saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an agent based on a user request.")
    parser.add_argument("--request", required=True, help="The user request for creating the agent.")
    parser.add_argument("--model", default="mixtral-8x7b-32768", help="The model to use for the agent.")
    parser.add_argument("--temperature", type=float, default=0.5, help="The temperature value for the agent.")
    parser.add_argument("--max_tokens", type=int, default=32768, help="The maximum number of tokens for the agent.")
    parser.add_argument("--agent_type", default="autogen", choices=["autogen", "crewai"], help="The type of agent to create.")
    parser.add_argument("--output", default="agent.json", help="The output file path for the agent JSON.")
    parser.add_argument("--provider", default="groq", help="The LLM provider to use (e.g., 'openai', 'anthropic').")
    
    args = parser.parse_args()
    create_agent(args.request, args.provider, args.model, args.temperature, args.max_tokens, args.output)
    
```

# AutoGroq\cli\rephrase_prompt.py

```python

import argparse
import os
import sys

# Add the root directory to the Python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.config import MODEL_TOKEN_LIMITS, LLM_PROVIDER
from utils.api_utils import get_llm_provider
from utils.auth_utils import get_api_key
from utils.ui_utils import rephrase_prompt


def rephrase_prompt_cli(prompt, provider, model, temperature, max_tokens):
    # Get the API key
    api_key = get_api_key()

    # Use the provider specified in the CLI arguments
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)

    # Override the model and max_tokens if specified in the command-line arguments
    model_to_use = model if model else provider
    max_tokens_to_use = MODEL_TOKEN_LIMITS.get(model_to_use, max_tokens)

    rephrased_prompt = rephrase_prompt(prompt, model_to_use, max_tokens_to_use, llm_provider=llm_provider, provider=provider)

    if rephrased_prompt:
        print(f"Rephrased Prompt: {rephrased_prompt}")
    else:
        print("Error: Failed to rephrase the prompt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rephrase a user prompt.")
    parser.add_argument("--prompt", required=True, help="The user prompt to rephrase.")
    parser.add_argument("--model", default=None, help="The model to use for rephrasing.")
    parser.add_argument("--temperature", type=float, default=0.5, help="The temperature value for rephrasing.")
    parser.add_argument("--max_tokens", type=int, default=32768, help="The maximum number of tokens for rephrasing.")
    parser.add_argument("--provider", default=None, help="The LLM provider to use (e.g., 'openai', 'anthropic').")
    
    args = parser.parse_args()
    rephrase_prompt_cli(args.prompt, args.provider, args.model, args.temperature, args.max_tokens)

```

# AutoGroq\configs\config.py

```python
# configs/config.py:

import os

from typing import Dict


# Get user home directory
home_dir = os.path.expanduser("~")
default_db_path = f'{home_dir}/.autogenstudio/database.sqlite'

# Debug
DEFAULT_DEBUG = False

# Default configurations
DEFAULT_LLM_PROVIDER = "anthropic" # Supported values: "anthropic", "groq", "openai", "ollama", "lmstudio", "fireworks"
DEFAULT_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
DEFAULT_OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Try to import user-specific configurations from config_local.py
try:
    from config_local import *
except ImportError:
    pass

# Set the configurations using the user-specific values if available, otherwise use the defaults
DEBUG = locals().get('DEBUG', DEFAULT_DEBUG)

LLM_PROVIDER = locals().get('LLM_PROVIDER', DEFAULT_LLM_PROVIDER)

GROQ_API_URL = locals().get('GROQ_API_URL', DEFAULT_GROQ_API_URL)
LMSTUDIO_API_URL = locals().get('LMSTUDIO_API_URL', DEFAULT_LMSTUDIO_API_URL)
OLLAMA_API_URL = locals().get('OLLAMA_API_URL', DEFAULT_OLLAMA_API_URL)
OPENAI_API_URL = locals().get('OPENAI_API_URL', DEFAULT_OPENAI_API_URL)
ANTHROPIC_API_URL = locals().get('ANTHROPIC_API_URL', DEFAULT_ANTHROPIC_API_URL)

API_KEY_NAMES = {
    "groq": "GROQ_API_KEY",
    "lmstudio": None,
    "ollama": None,
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # in seconds
RETRY_TOKEN_LIMIT = 5000

# Model configurations
if LLM_PROVIDER == "groq":
    API_URL = GROQ_API_URL
    MODEL_TOKEN_LIMITS = {
        'mixtral-8x7b-32768': 32768,
        'llama3-70b-8192': 8192,
        'llama3-8b-8192': 8192,
        'gemma-7b-it': 8192,
    }
elif LLM_PROVIDER == "lmstudio":
    API_URL = LMSTUDIO_API_URL
    MODEL_TOKEN_LIMITS = {
        'instructlab/granite-7b-lab-GGUF': 2048,
        'MaziyarPanahi/Codestral-22B-v0.1-GGUF': 32768,
    } 
elif LLM_PROVIDER == "openai":
    API_URL = OPENAI_API_URL
    MODEL_TOKEN_LIMITS = {
        'gpt-4o': 4096,
    }
elif LLM_PROVIDER == "ollama":
    API_URL = OLLAMA_API_URL
    MODEL_TOKEN_LIMITS = {
        'llama3': 8192,
    }
elif LLM_PROVIDER == "anthropic":
    API_URL = ANTHROPIC_API_URL
    MODEL_TOKEN_LIMITS = {
        "claude-3-5-sonnet-20240620": 4096,
        "claude-3-opus-20240229": 4096,
        "claude-3-sonnet-20240229": 4096,
        "claude-3-haiku-20240307": 4096,
        "claude-2.1": 100000,
        "claude-2.0": 100000,
        "claude-instant-1.2": 100000,
    }
else:
    API_URL = None
    MODEL_TOKEN_LIMITS = {}

# Database path
FRAMEWORK_DB_PATH = os.environ.get('FRAMEWORK_DB_PATH', default_db_path)

MODEL_CHOICES = {
    "anthropic": {
    "claude-3-5-sonnet-20240620": 4096,
    "claude-3-opus-20240229": 4096,
    "claude-3-sonnet-20240229": 4096,
    "claude-3-haiku-20240307": 4096,
    "claude-2.1": 100000,
    "claude-2.0": 100000,
    "claude-instant-1.2": 100000,
    },
    "groq": {
        "mixtral-8x7b-32768": 32768,
        "llama3-70b-8192": 8192,
        "llama3-8b-8192": 8192,
        "gemma-7b-it": 8192,
    },
    "openai": {
        "gpt-4o": 4096,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 4096,
        "dall-e-3": 4096,
    },
    "fireworks": {
        "fireworks": 4096,
    },
    "ollama": {
        "llama3": 8192,
    },
    "lmstudio": {
        "instructlab/granite-7b-lab-GGUF": 2048,
        "MaziyarPanahi/Codestral-22B-v0.1-GGUF": 32768,
    },
}

SUPPORTED_PROVIDERS = ["anthropic", "fireworks", "groq", "lmstudio", "ollama", "openai"]    

BUILT_IN_AGENTS = ["Web Content Retriever", "Code Developer", "Code Tester"]

AVAILABLE_MODELS: Dict[str, Dict[str, int]] = {}

def update_available_models(provider: str, models: Dict[str, int]):
    """
    Update the available models for a given provider.
    
    :param provider: The name of the provider (e.g., 'groq', 'openai')
    :param models: A dictionary of model names and their token limits
    """
    global AVAILABLE_MODELS
    AVAILABLE_MODELS[provider] = models
```

# AutoGroq\configs\config_agent.py

```python
# /configs/config_agent.py

import datetime
import streamlit as st

from typing import Dict

AGENT_CONFIG: Dict = {
    "type": "assistant",
    "config": {
        "name": "",
        "llm_config": {
            "config_list": [
                {
                    "user_id": "default",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "model": st.session_state.model,
                    "base_url": st.session_state.api_url,
                    "api_type": None,
                    "api_version": None,
                    "description": "Model configuration"
                }
            ],
            "temperature": st.session_state.temperature,
            "cache_seed": None,
            "timeout": None,
            "max_tokens": None,
            "extra_body": None
        },
        "human_input_mode": "NEVER",
        "max_consecutive_auto_reply": 8,
        "system_message": "",
        "is_termination_msg": None,
        "code_execution_config": None,
        "default_auto_reply": "",
        "description": ""
    },
    "timestamp": datetime.datetime.now().isoformat(),
    "user_id": "default",
    "tools": []
}
```

# AutoGroq\configs\config_local.py

```python
# User-specific configurations

LLM_PROVIDER = "anthropic"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
# OPENAI_API_KEY = "your_openai_api_key"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

DEBUG = True

RETRY_DELAY = 2
```

# AutoGroq\configs\config_sessions.py

```python
# config_sessions.py

from datetime import datetime
from typing import Dict

DEFAULT_AGENT_CONFIG: Dict = {
    "name": "Default Agent",
    "description": "A default agent for initialization purposes in AutoGroq",
    "tools": [],  # Empty list as default
    "config": {
        "llm_config": {
            "config_list": [
                {
                    "model": "default",
                    "api_key": None,
                    "base_url": None,
                    "api_type": None,
                    "api_version": None,
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
        "human_input_mode": "NEVER",
        "max_consecutive_auto_reply": 10,
    },
    "role": "Default Assistant",
    "goal": "Assist users with general tasks in AutoGroq",
    "backstory": "I am a default AI assistant created to help initialize the AutoGroq system.",
    "id": None,  # Will be set dynamically when needed
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "user_id": "default_user",
    "workflows": None,
    "type": "assistant",
    "models": [],  # Empty list as default
    "verbose": False,
    "allow_delegation": True,
    "new_description": None,
    "timestamp": datetime.now().isoformat(),
    "is_termination_msg": None,
    "code_execution_config": {
        "work_dir": "./agent_workspace",
        "use_docker": False,
    },
    "llm": None,
    "function_calling_llm": None,
    "max_iter": 25,
    "max_rpm": None,
    "max_execution_time": 600,  # 10 minutes default
    "step_callback": None,
    "cache": True
}
```

# AutoGroq\configs\current_project.py

```python

class Current_Project:
    def __init__(self):
        self.deliverables = []
        self.re_engineered_prompt = ""
        self.implementation_phases = ["Planning", "Development", "Testing", "Deployment"]
        self.current_phase = "Planning"


    def add_deliverable(self, deliverable):
        self.deliverables.append({
            "text": deliverable, 
            "done": False,
            "phase": {phase: False for phase in self.implementation_phases}
        })


    def get_next_unchecked_deliverable(self):
        for index, deliverable in enumerate(self.deliverables):
            if not deliverable["done"]:
                return index, deliverable["text"]
        return None, None
    

    def get_next_uncompleted_phase(self, index):
        if 0 <= index < len(self.deliverables):
            for phase in self.implementation_phases:
                if not self.deliverables[index]["phase"][phase]:
                    return phase
        return None    


    def is_deliverable_complete(self, index):
        if 0 <= index < len(self.deliverables):
            return all(self.deliverables[index]["phase"].values())
        return False


    def mark_deliverable_phase_done(self, index, phase):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["phase"][phase] = True
            if self.is_deliverable_complete(index):
                self.deliverables[index]["done"] = True
                

    def mark_deliverable_undone(self, index):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False


    def move_to_next_phase(self):
        current_index = self.implementation_phases.index(self.current_phase)
        if current_index < len(self.implementation_phases) - 1:
            self.current_phase = self.implementation_phases[current_index + 1]            


    def set_re_engineered_prompt(self, prompt):
        self.re_engineered_prompt = prompt

```

# AutoGroq\llm_providers\anthropic_provider.py

```python
# llm_providers/anthropic_provider.py

import anthropic
import streamlit as st

from llm_providers.base_provider import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_url, api_key):
        self.api_key = api_key
        self.api_url = api_url or "https://api.anthropic.com/v1/messages"
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def get_available_models(self):
        return {
            "claude-3-5-sonnet-20240620": 4096,
            "claude-3-opus-20240229": 4096,
            "claude-3-sonnet-20240229": 4096,
            "claude-3-haiku-20240307": 4096,
            "claude-2.1": 100000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000,
        }
                
    def process_response(self, response):
        if response is not None:
            return {
                "choices": [
                    {
                        "message": {
                            "content": response.content[0].text
                        }
                    }
                ]
            }
        return None
    
    def send_request(self, data):
        try:
            model = data['model']
            max_tokens = min(data.get('max_tokens', 1000), self.get_available_models()[model])
            
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=data.get('temperature', st.session_state.temperature),
                messages=[
                    {"role": "user", "content": message["content"]}
                    for message in data['messages']
                ]
            )
            return response
        except anthropic.APIError as e:
            print(f"Anthropic API error: {e}")
            return None
```

# AutoGroq\llm_providers\base_provider.py

```python
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    def __init__(self, api_key, api_url=None):
        pass

    @abstractmethod
    def send_request(self, data):
        pass

    @abstractmethod
    def process_response(self, response):
        pass

    @abstractmethod
    def get_available_models(self):
        pass
```

# AutoGroq\llm_providers\fireworks_provider.py

```python

import json
import requests

from llm_providers.base_provider import BaseLLMProvider


class FireworksProvider(BaseLLMProvider):
    def __init__(self, api_url, api_key):
        self.api_url = api_url


    def get_available_models(self):
        return None


    def process_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed with status code {response.status_code}")


    def send_request(self, data):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Ensure data is a JSON string
        if isinstance(data, dict):
            json_data = json.dumps(data)
        else:
            json_data = data
        response = requests.post(self.api_url, data=json_data, headers=headers)
        return response
    
```

# AutoGroq\llm_providers\groq_provider.py

```python

import json
import requests

from llm_providers.base_provider import BaseLLMProvider


class GroqProvider:
    def __init__(self, api_url, api_key):
        self.api_key = api_key
        self.api_url = api_url or "https://api.groq.com/openai/v1/chat/completions"


    def process_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed with status code {response.status_code}")


    def send_request(self, data):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Ensure data is a JSON string
        if isinstance(data, dict):
            json_data = json.dumps(data)
        else:
            json_data = data
        response = requests.post(self.api_url, data=json_data, headers=headers)
        return response
    

    def get_available_models(self):
        response = requests.get("https://api.groq.com/openai/v1/models", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        if response.status_code == 200:
            models_data = response.json().get("data", [])
            return {model["id"]: model.get("max_tokens", 4096) for model in models_data}
        else:
            raise Exception(f"Failed to retrieve models: {response.status_code}")
```

# AutoGroq\llm_providers\lmstudio_provider.py

```python
# llm_providers/lmstudio_provider.py

import json
import requests
import streamlit as st

from llm_providers.base_provider import BaseLLMProvider


class LmstudioProvider:
    def __init__(self, api_url, api_key):
        self.api_url = api_url or "http://localhost:1234/v1/chat/completions"


    def get_available_models(self):
        return {
            "instructlab/granite-7b-lab-GGUF": 2048,
            "MaziyarPanahi/Codestral-22B-v0.1-GGUF": 32768,
            # Add other LMStudio models here
        }


    def process_response(self, response):
        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data:
                content = response_data["choices"][0]["message"]["content"]
                return {
                    "choices": [
                        {
                            "message": {
                                "content": content.strip()
                            }
                        }
                    ]
                }
            else:
                raise Exception("Unexpected response format. 'choices' field missing.")
        else:
            raise Exception(f"Request failed with status code {response.status_code}")


    def send_request(self, data):
        headers = {
            "Content-Type": "application/json",
        }

        # Construct the request data in the format expected by the LM Studio API
        lm_studio_request_data = {
            "model": data["model"],
            "messages": data["messages"],
            "temperature": st.session_state.temperature,
            "max_tokens": data.get("max_tokens", 2048),
            "stop": data.get("stop", "TERMINATE"),
        }

        # Ensure data is a JSON string
        if isinstance(lm_studio_request_data, dict):
            json_data = json.dumps(lm_studio_request_data)
        else:
            json_data = lm_studio_request_data

        response = requests.post(self.api_url, data=json_data, headers=headers)
        return response
    
```

# AutoGroq\llm_providers\ollama_provider.py

```python
# llm_providers/ollama_provider.py

import json
import requests
import streamlit as st

from llm_providers.base_provider import BaseLLMProvider


class OllamaProvider:
    def __init__(self, api_url, api_key):
        self.api_url = api_url or "http://127.0.0.1:11434/api/generate"


    def get_available_models(self):
        return {
            "llama3": 8192,
            # Add other Ollama models here
        }
    

    def process_response(self, response):
        if response.status_code == 200:
            response_data = response.json()
            if "response" in response_data:
                content = response_data["response"].strip()
                if content:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": content
                                }
                            }
                        ]
                    }
                else:
                    raise Exception("Empty response received from the Ollama API.")
            else:
                raise Exception("Unexpected response format. 'response' field missing.")
        else:
            raise Exception(f"Request failed with status code {response.status_code}")


    def send_request(self, data):
        headers = {
            "Content-Type": "application/json",
        }
        # Construct the request data in the format expected by the Ollama API
        ollama_request_data = {
            "model": data["model"],
            "prompt": data["messages"][0]["content"],
            "temperature": st.session_state.temperature,
            "max_tokens": data.get("max_tokens", 2048),
            "stop": data.get("stop", "TERMINATE"),
            "stream": False,
        }
        # Ensure data is a JSON string
        if isinstance(ollama_request_data, dict):
            json_data = json.dumps(ollama_request_data)
        else:
            json_data = ollama_request_data
        response = requests.post(self.api_url, data=json_data, headers=headers)
        return response
```

# AutoGroq\llm_providers\openai_provider.py

```python

import json
import os
import requests

from llm_providers.base_provider import BaseLLMProvider

class OpenaiProvider:
    def __init__(self, api_url, api_key):
        self.api_key = api_key
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"


    def get_available_models(self):
        response = requests.get("https://api.openai.com/v1/models", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        if response.status_code == 200:
            models_data = response.json().get("data", [])
            return {model["id"]: model.get("max_tokens", 4096) for model in models_data}
        else:
            raise Exception(f"Failed to retrieve models: {response.status_code}")
    

    def process_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed with status code {response.status_code}")


    def send_request(self, data):
        print("self.api_url: ", self.api_url)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Ensure data is a JSON string
        if isinstance(data, dict):
            json_data = json.dumps(data)
        else:
            json_data = data
        
        response = requests.post(self.api_url, data=json_data, headers=headers)
        print("response.status_code: ", response.status_code)
        print("response.text: ", response.text)
        return response
    
```

# AutoGroq\models\agent_base_model.py

```python
# models/agent_base_model.py

import inspect

from models.tool_base_model import ToolBaseModel
from typing import List, Dict, Callable, Optional, Union


class AgentBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        tools: List[Union[Dict, ToolBaseModel]],
        config: Dict,
        role: str,
        goal: str,
        backstory: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        workflows: Optional[str] = None,
        type: Optional[str] = None,
        models: Optional[List[Dict]] = None,
        verbose: Optional[bool] = False,
        allow_delegation: Optional[bool] = True,
        new_description: Optional[str] = None,
        timestamp: Optional[str] = None,
        is_termination_msg: Optional[bool] = None,
        code_execution_config: Optional[Dict] = None,
        llm: Optional[str] = None,
        function_calling_llm: Optional[str] = None,
        max_iter: Optional[int] = 25,
        max_rpm: Optional[int] = None,
        max_execution_time: Optional[int] = None,
        step_callback: Optional[Callable] = None,
        cache: Optional[bool] = True
    ):
        self.id = id
        self.name = name
        self.description = description
        self.tools = [tool if isinstance(tool, ToolBaseModel) else ToolBaseModel(**tool) for tool in tools]
        self.config = config
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.provider = provider
        self.model = model
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.workflows = workflows
        self.type = type
        self.models = models
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.new_description = new_description
        self.timestamp = timestamp
        self.is_termination_msg = is_termination_msg
        self.code_execution_config = code_execution_config
        self.llm = llm
        self.function_calling_llm = function_calling_llm
        self.max_iter = max_iter
        self.max_rpm = max_rpm
        self.max_execution_time = max_execution_time
        self.step_callback = step_callback
        self.cache = cache


    def __str__(self):
        return f"Agent(name={self.name}, description={self.description})"

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            'tools': [tool.to_dict() if hasattr(tool, 'to_dict') else tool for tool in self.tools],
            "provider": self.provider,
            "model": self.model,
            "config": self.config,
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "workflows": self.workflows,
            "type": self.type,
            "models": self.models,
            "verbose": self.verbose,
            "allow_delegation": self.allow_delegation,
            "new_description": self.new_description,
            "timestamp": self.timestamp,
            "is_termination_msg": self.is_termination_msg,
            "code_execution_config": self.code_execution_config,
            "llm": self.llm,
            "function_calling_llm": self.function_calling_llm,
            "max_iter": self.max_iter,
            "max_rpm": self.max_rpm,
            "max_execution_time": self.max_execution_time,
            "step_callback": self.step_callback,
            "cache": self.cache
        }

    @classmethod
    def from_dict(cls, data: Dict):
        tools = [ToolBaseModel.from_dict(tool) if isinstance(tool, dict) else tool for tool in data.get('tools', [])]
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            tools=tools,
            config=data["config"],
            role=data.get("role", ""),
            goal=data.get("goal", ""),
            backstory=data.get("backstory", ""),
            provider=data.get("provider"),
            model=data.get("model"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            workflows=data.get("workflows"),
            type=data.get("type"),
            models=data.get("models"),
            verbose=data.get("verbose", False),
            allow_delegation=data.get("allow_delegation", True),
            new_description=data.get("new_description"),
            timestamp=data.get("timestamp"),
            is_termination_msg=data.get("is_termination_msg"),
            code_execution_config=data.get("code_execution_config"),
            llm=data.get("llm"),
            function_calling_llm=data.get("function_calling_llm"),
            max_iter=data.get("max_iter", 25),
            max_rpm=data.get("max_rpm"),
            max_execution_time=data.get("max_execution_time"),
            step_callback=data.get("step_callback"),
            cache=data.get("cache", True)
        )
    
    @classmethod
    def debug_init(cls):
        signature = inspect.signature(cls.__init__)
        params = signature.parameters
        required_params = [name for name, param in params.items() 
                           if param.default == inspect.Parameter.empty 
                           and param.kind != inspect.Parameter.VAR_KEYWORD]
        optional_params = [name for name, param in params.items() 
                           if param.default != inspect.Parameter.empty]
        
        print(f"Required parameters for {cls.__name__}:")
        for param in required_params:
            print(f"  - {param}")
        
        print(f"\nOptional parameters for {cls.__name__}:")
        for param in optional_params:
            print(f"  - {param}")

        return required_params, optional_params

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

```

# AutoGroq\models\project_base_model.py

```python
from typing import List, Dict, Optional
from datetime import datetime

class ProjectBaseModel:
    def __init__(
        self,
        re_engineered_prompt: str = "",
        deliverables: List[Dict] = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        notes: Optional[str] = None,
        collaborators: Optional[List[str]] = None,
        tools: Optional[List[Dict]] = None,
        workflows: Optional[List[Dict]] = None
    ):
        self.id = id or 1
        self.re_engineered_prompt = re_engineered_prompt
        self.deliverables = deliverables or []
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at
        self.user_id = user_id or "user"
        self.name = name or "project"
        self.description = description
        self.status = status or "not started"
        self.due_date = due_date
        self.priority = priority
        self.tags = tags or []
        self.attachments = attachments or []
        self.notes = notes
        self.collaborators = collaborators or []
        self.tools = tools or []
        self.workflows = workflows or []


    def add_deliverable(self, deliverable: str):
        self.deliverables.append({"text": deliverable, "done": False})


    def mark_deliverable_done(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = True


    def mark_deliverable_undone(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False


    def set_re_engineered_prompt(self, prompt: str):
        self.re_engineered_prompt = prompt

    def to_dict(self):
        return {
            "id": self.id,
            "re_engineered_prompt": self.re_engineered_prompt,
            "deliverables": self.deliverables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "due_date": self.due_date,
            "priority": self.priority,
            "tags": self.tags,
            "attachments": self.attachments,
            "notes": self.notes,
            "collaborators": self.collaborators,
            "tools": self.tools,
            "workflows": self.workflows
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            id=data.get("id"),
            re_engineered_prompt=data.get("re_engineered_prompt", ""),
            deliverables=data.get("deliverables", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            name=data.get("name"),
            description=data.get("description"),
            status=data.get("status"),
            due_date=data.get("due_date"),
            priority=data.get("priority"),
            tags=data.get("tags"),
            attachments=data.get("attachments"),
            notes=data.get("notes"),
            collaborators=data.get("collaborators")
        )
    
```

# AutoGroq\models\tool_base_model.py

```python
# tool_base_model.py

from typing import List, Dict, Optional, Callable

class ToolBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        title: str,
        file_name: str,
        content: str,
        function: Optional[Callable] = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        secrets: Optional[Dict] = None,
        libraries: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.title = title
        self.file_name = file_name
        self.content = content
        self.function = function
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.secrets = secrets if secrets is not None else []
        self.libraries = libraries if libraries is not None else []
        self.timestamp = timestamp

    def execute(self, *args, **kwargs):
        if self.function:
            return self.function(*args, **kwargs)
        else:
            raise ValueError(f"No function defined for tool {self.name}")

    def __str__(self):
        return f"{self.name}: {self.description}"

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "title": self.title,
            "file_name": self.file_name,
            "content": self.content,
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "secrets": self.secrets,
            "libraries": self.libraries,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict):     
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),  # Default to empty string if 'name' is missing
            description=data.get("description", ""),  # Default to empty string if 'description' is missing
            title=data["title"],
            file_name=data["file_name"],
            content=data["content"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            secrets=data.get("secrets"),
            libraries=data.get("libraries"),
            timestamp=data.get("timestamp")
        )
    
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)
    
```

# AutoGroq\models\workflow_base_model.py

```python
from typing import List, Dict, Optional
from models.agent_base_model import AgentBaseModel

class Sender:
    def __init__(
        self,
        type: str,
        config: Dict,
        timestamp: str,
        user_id: str,
        tools: List[Dict],
    ):
        self.type = type
        self.config = config
        self.timestamp = timestamp
        self.user_id = user_id
        self.tools = tools

    def to_dict(self):
        return {
            "type": self.type,
            "config": self.config,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            type=data["type"],
            config=data["config"],
            timestamp=data["timestamp"],
            user_id=data["user_id"],
            tools=data["tools"],
        )

class Receiver:
    def __init__(
        self,
        type: str,
        config: Dict,
        groupchat_config: Dict,
        timestamp: str,
        user_id: str,
        tools: List[Dict],
        agents: List[AgentBaseModel],
    ):
        self.type = type
        self.config = config
        self.groupchat_config = groupchat_config
        self.timestamp = timestamp
        self.user_id = user_id
        self.tools = tools
        self.agents = agents

    def to_dict(self):
        return {
            "type": self.type,
            "config": self.config,
            "groupchat_config": self.groupchat_config,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "tools": self.tools,
            "agents": [agent.to_dict() for agent in self.agents],
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            type=data["type"],
            config=data["config"],
            groupchat_config=data["groupchat_config"],
            timestamp=data["timestamp"],
            user_id=data["user_id"],
            tools=data["tools"],
            agents=[AgentBaseModel.from_dict(agent) for agent in data.get("agents", [])],
        )

class WorkflowBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        agents: List[AgentBaseModel],
        sender: Sender,
        receiver: Receiver,
        type: str,
        user_id: str,
        timestamp: str,
        summary_method: str,
        settings: Dict = None,
        groupchat_config: Dict = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.agents = agents
        self.sender = sender
        self.receiver = receiver
        self.type = type
        self.user_id = user_id
        self.timestamp = timestamp
        self.summary_method = summary_method
        self.settings = settings or {}
        self.groupchat_config = groupchat_config or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents": [agent.to_dict() for agent in self.agents],
            "sender": self.sender.to_dict(),
            "receiver": self.receiver.to_dict(),
            "type": self.type,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "summary_method": self.summary_method,
            "settings": self.settings,
            "groupchat_config": self.groupchat_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        sender = Sender.from_dict(data["sender"])
        receiver = Receiver.from_dict(data["receiver"])
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            agents=[AgentBaseModel.from_dict(agent) for agent in data.get("agents", [])],
            sender=sender,
            receiver=receiver,
            type=data["type"],
            user_id=data["user_id"],
            timestamp=data["timestamp"],
            summary_method=data["summary_method"],
            settings=data.get("settings", {}),
            groupchat_config=data.get("groupchat_config", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
```

# AutoGroq\tools\code_generator.py

```python
# tools/code_generator.py

import inspect
import json
import logging
from models.tool_base_model import ToolBaseModel
from utils.api_utils import get_api_key, get_llm_provider
import streamlit as st

logger = logging.getLogger(__name__)

def generate_code(request: str, language: str = "Python") -> str:
    logger.debug(f"Generating code for request: {request}")
    logger.debug(f"Language: {language}")
    
    if not request.strip():
        return "Error: No specific code generation request provided."

    prompt = f"""
    You are an advanced AI language model with expertise in software development. Your task is to generate the best possible software solution for the following request:
    **Request:**
    {request}
    **Language:**
    {language}
    Please ensure that the code follows best practices for {language}, is optimized for performance and maintainability, and includes comprehensive comments explaining each part of the code. Additionally, provide any necessary context or explanations to help understand the implementation. The solution should be robust, scalable, and adhere to industry standards.
    If there are multiple ways to solve the problem, choose the most efficient and elegant approach. If any libraries or frameworks are beneficial, include their usage with appropriate explanations.
    Begin your response with a brief overview of the approach you are taking, and then provide the complete code.
    Example overview: "To solve the problem of {request}, we will implement a {{specific algorithm/pattern}} using {{specific features/libraries of the language}}. This approach ensures {{benefits of the approach}}."
    Here is the code:
    """

    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    
    llm_request_data = {
        "model": st.session_state.get('model', 'default'),
        "temperature": st.session_state.get('temperature', 0.7),
        "max_tokens": st.session_state.get('max_tokens', 2000),
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert code generator."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = llm_provider.send_request(llm_request_data)
        logger.debug(f"LLM response status code: {response.status_code}")
        logger.debug(f"LLM response content: {response.text[:500]}...")  # Log first 500 characters of response
        
        if response.status_code == 200:
            response_data = llm_provider.process_response(response)
            if "choices" in response_data and response_data["choices"]:
                generated_code = response_data["choices"][0]["message"]["content"]
                return generated_code.strip()
            else:
                return "Error: Unexpected response format from the language model."
        else:
            return f"Error: Received status code {response.status_code} from the language model API."
    except Exception as e:
        logger.error(f"Error generating code: {str(e)}", exc_info=True)
        return f"Error generating code: {str(e)}"

code_generator_tool = ToolBaseModel(
    name="generate_code",
    description="Generates code for a specified feature in a given programming language.",
    title="Code Generator",
    file_name="code_generator.py",
    content=inspect.getsource(generate_code),
    function=generate_code,
)

def get_tool():
    return code_generator_tool
```

# AutoGroq\tools\code_test.py

```python
# tools/code_test.py

import inspect
import subprocess
import tempfile
from models.tool_base_model import ToolBaseModel

def test_code(language: str, code: str, test_cases: str) -> str:
    """
    Tests the given code with provided test cases.

    Args:
        language (str): The programming language of the code (e.g., "Python", "JavaScript").
        code (str): The code to be tested.
        test_cases (str): A string containing test cases, each on a new line.

    Returns:
        str: The test results as a string.
    """
    if language.lower() != "python":
        return f"Testing for {language} is not supported yet."

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file.write("\n\n# Test cases\n")
        temp_file.write(test_cases)
        temp_file_name = temp_file.name

    try:
        result = subprocess.run(['python', temp_file_name], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"Tests passed successfully.\nOutput:\n{result.stdout}"
        else:
            return f"Tests failed.\nError:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Test execution timed out."
    except Exception as e:
        return f"An error occurred during testing: {str(e)}"

code_test_tool = ToolBaseModel(
    name="test_code",
    description="Tests the given code with provided test cases.",
    title="Code Tester",
    file_name="code_test.py",
    content=inspect.getsource(test_code),
    function=test_code,
)

def get_tool():
    return code_test_tool

```

# AutoGroq\tools\fetch_web_content.py

```python
# tools/fetch_web_content.py

import inspect
import json
import logging
import requests

from bs4 import BeautifulSoup
from models.tool_base_model import ToolBaseModel
from urllib.parse import urlparse, urlunparse


def fetch_web_content(url: str) -> dict:
    """
    Fetches the text content from a website.

    Args:
        url (str): The URL of the website.

    Returns:
        dict: A dictionary containing the status, URL, and content (or error message).
    """
    try:
        cleaned_url = clean_url(url)
        logging.info(f"Fetching content from cleaned URL: {cleaned_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(cleaned_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        logging.info(f"Response status code: {response.status_code}")
        logging.info(f"Response headers: {response.headers}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        logging.info(f"Parsed HTML structure: {soup.prettify()[:500]}...")  # Log first 500 characters of prettified HTML
        
        # Try to get content from article tags first
        article_content = soup.find('article')
        if article_content:
            content = article_content.get_text(strip=True)
        else:
            # If no article tag, fall back to body content
            body_content = soup.body
            if body_content:
                content = body_content.get_text(strip=True)
            else:
                raise ValueError("No content found in the webpage")

        logging.info(f"Extracted text content (first 500 chars): {content[:500]}...")
        result = {
            "status": "success",
            "url": cleaned_url,
            "content": content  
        }
        print(f"DEBUG: fetch_web_content result: {str(result)[:500]}...")  # Debug print
        return result

    except requests.RequestException as e:
        error_message = f"Error fetching content from {cleaned_url}: {str(e)}"
        logging.error(error_message)
        return {
            "status": "error",
            "url": cleaned_url,
            "message": error_message
        }
    except Exception as e:
        error_message = f"Unexpected error while fetching content from {cleaned_url}: {str(e)}"
        logging.error(error_message)
        return {
            "status": "error",
            "url": cleaned_url,
            "message": error_message
        }

# Create the ToolBaseModel instance
fetch_web_content_tool = ToolBaseModel(
    name="fetch_web_content",
    description="Fetches the text content from a website.",
    title="Fetch Web Content",
    file_name="fetch_web_content.py",
    content=inspect.getsource(fetch_web_content),
    function=fetch_web_content,
)

# Function to get the tool
def get_tool():
    return fetch_web_content_tool


def clean_url(url: str) -> str:
    """
    Clean and validate the URL.
    
    Args:
        url (str): The URL to clean.
    
    Returns:
        str: The cleaned URL.
    """
    url = url.strip().strip("'\"")
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    return urlunparse(parsed)

```

# AutoGroq\utils\agent_utils.py

```python
# utils/agent_utils.py

import datetime
import streamlit as st

from configs.config import LLM_PROVIDER

from utils.text_utils import normalize_config


def create_agent_data(agent):
    expert_name = agent['name']
    description = agent.get('description', '')
    current_timestamp = datetime.datetime.now().isoformat()
    provider = agent.get('config', {}).get('provider', st.session_state.get('provider', LLM_PROVIDER))

    # Use normalize_config to get the standardized config
    normalized_config = normalize_config(agent, expert_name)

    autogen_agent_data = {
        "name": normalized_config['name'],
        "description": description,
        "config": normalized_config,
        "tools": agent.get('tools', []),
        "role": agent.get('role', normalized_config['name']),
        "goal": agent.get('goal', f"Assist with tasks related to {description}"),
        "backstory": agent.get('backstory', f"As an AI assistant, I specialize in {description}"),
        "provider": provider,
        "model": st.session_state.get('model', 'default')
    }

    crewai_agent_data = {
        "name": normalized_config['name'],
        "description": description,
        "verbose": True,
        "allow_delegation": True
    }

    return autogen_agent_data, crewai_agent_data

```

# AutoGroq\utils\api_utils.py

```python
# utils/api_utils.py

import importlib
import os
import requests
import streamlit as st
import time

from configs.config import LLM_PROVIDER, RETRY_DELAY, RETRY_TOKEN_LIMIT


def display_api_key_input(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key_env_var = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    
    if api_key is None:
        st.session_state.warning_placeholder.warning(f"{provider.upper()} API Key not found. Please enter your API key, or select a different provider.")
    api_key = st.text_input(f"Enter your {provider.upper()} API Key:", type="password", key=f"api_key_input_{provider}")
    if api_key:
        st.session_state[api_key_env_var] = api_key
        os.environ[api_key_env_var] = api_key
        # st.success(f"{provider.upper()} API Key entered successfully.")
        st.session_state.warning_placeholder.empty()
    return api_key


def fetch_available_models(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key = get_api_key(provider)
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)
    try:
        models = llm_provider.get_available_models()
        st.session_state.available_models = models
        return models
    except Exception as e:
        st.error(f"Failed to fetch available models: {str(e)}")
        return {}
    

def fetch_available_models(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key = get_api_key(provider)
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)
    try:
        models = llm_provider.get_available_models()
        st.session_state.available_models = models
        return models
    except Exception as e:
        st.error(f"Failed to fetch available models: {str(e)}")
        return {}
    

def get_api_key(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key_env_var = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    if api_key is None:
        api_key = st.session_state.get(api_key_env_var)
    return api_key


def get_llm_provider(api_key=None, api_url=None, provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    provider_module = importlib.import_module(f"llm_providers.{provider}_provider")
    provider_class = getattr(provider_module, f"{provider.capitalize()}Provider")
    if api_url is None:
        api_url = st.session_state.get(f'{provider.upper()}_API_URL')
    return provider_class(api_url=api_url, api_key=api_key)


def make_api_request(url, data, headers, api_key):
    time.sleep(RETRY_DELAY)  # Throttle the request to ensure at least 2 seconds between calls
    try:
        if not api_key:
            llm = LLM_PROVIDER.upper()
            raise ValueError(f"{llm}_API_KEY not found. Please enter your API key.")
        headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            error_message = response.json().get("error", {}).get("message", "")
            st.error(f"Rate limit reached for the current model. If you click 'Update' again, we'll retry with a reduced token count.  Or you can try selecting a different model.")
            st.error(f"Error details: {error_message}")
            return None
        else:
            print(f"Error: API request failed with status {response.status_code}, response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error: Request failed {e}")
        return None
    

def send_request_with_retry(url, data, headers, api_key):
    response = make_api_request(url, data, headers, api_key)
    if response is None:
        # Add a retry button
        if st.button("Retry with decreased token limit"):
            # Update the token limit in the request data
            data["max_tokens"] = RETRY_TOKEN_LIMIT
            # Retry the request with the decreased token limit
            print(f"Retrying the request with decreased token limit.")
            print(f"URL: {url}")
            print(f"Retry token limit: {RETRY_TOKEN_LIMIT}")
            response = make_api_request(url, data, headers, api_key)
            if response is not None:
                print(f"Retry successful. Response: {response}")
            else:
                print("Retry failed.")
    return response    


def set_llm_provider_title():
    # "What's life without whimsy?" ~Sheldon Cooper
    if LLM_PROVIDER == "groq":
        st.title("AutoGroq™")
    elif LLM_PROVIDER == "ollama":
        st.title("Auto̶G̶r̶o̶qOllama")
    elif LLM_PROVIDER == "lmstudio":
        st.title("Auto̶G̶r̶o̶qLM_Studio")
    elif LLM_PROVIDER == "openai":
        st.title("Auto̶G̶r̶o̶qChatGPT")
    elif LLM_PROVIDER == "anthropic":
        st.title("Auto̶G̶r̶o̶qClaude")


```

# AutoGroq\utils\auth_utils.py

```python

import os
import streamlit as st

from configs.config import LLM_PROVIDER
from utils.api_utils import display_api_key_input

        
def check_api_key(provider=None):
    # Ensure we have a warning placeholder
    if 'warning_placeholder' not in st.session_state:
        st.session_state.warning_placeholder = st.empty()

    # Check for API key of the default provider on initial load
    if 'initial_api_check' not in st.session_state:
        st.session_state.initial_api_check = True
        default_provider = st.session_state.get('provider', LLM_PROVIDER)
        if not check_api_key(default_provider):
            display_api_key_input(default_provider)
    return True


def get_api_url():
    api_url_env_var = f"{LLM_PROVIDER.upper()}_API_URL"
    api_url = os.environ.get(api_url_env_var)
    if api_url is None:
        api_url = globals().get(api_url_env_var)
        if api_url is None:
            if api_url_env_var not in st.session_state:
                api_url = st.text_input(f"Enter the {LLM_PROVIDER.upper()} API URL:", type="password", key=f"{LLM_PROVIDER}_api_url_input")
                if api_url:
                    st.session_state[api_url_env_var] = api_url
                    st.success("API URL entered successfully.")
                else:
                    st.warning(f"Please enter the {LLM_PROVIDER.upper()} API URL to use the app.")
            else:
                api_url = st.session_state.get(api_url_env_var)
    return api_url

```

# AutoGroq\utils\db_utils.py

```python
# db_utils.py

import datetime
import json
import sqlite3
import streamlit as st
import traceback
import uuid

from configs.config import FRAMEWORK_DB_PATH

from utils.text_utils import normalize_config
from utils.workflow_utils import get_workflow_from_agents


def export_to_autogen():
    db_path = FRAMEWORK_DB_PATH
    print(f"Database path: {db_path}")
    if db_path:
        export_data(db_path)
    else:
        st.warning("Please provide a valid database path in config.py.")


def export_data(db_path):
    print(f"Exporting data to: {db_path}")

    if db_path:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            print("Connected to the database successfully.")

            agents = st.session_state.agents
            print(f"Number of agents: {len(agents)}")

            for index, agent in enumerate(agents):
                try:
                    print(f"Processing agent {index + 1}: {agent.name}")
                    
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Normalize the config
                    normalized_config = normalize_config(agent.to_dict(), agent.name)
                    
                    agent_data = (
                        None,  # id (AUTO INCREMENT)
                        current_time,  # created_at
                        current_time,  # updated_at
                        'guestuser@gmail.com',  # user_id
                        '0.0.1',  # version
                        'assistant',  # type
                        json.dumps(normalized_config),  # config (JSON)
                        normalized_config['system_message']  # task_instruction
                    )
                    
                    print(f"Inserting agent data: {agent_data}")
                    
                    cursor.execute("""
                        INSERT INTO agent (id, created_at, updated_at, user_id, version, type, config, task_instruction) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, agent_data)
                    
                    print(f"Inserted agent: {agent.name}")

                except Exception as e:
                    print(f"Error processing agent {index + 1}: {str(e)}")
                    print(f"Agent data: {agent.__dict__}")
                    traceback.print_exc()

            # Handle skills/tools
            for tool in st.session_state.tool_models:
                try:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    skill_data = (
                        None,  # id (AUTO INCREMENT)
                        current_time,  # created_at
                        current_time,  # updated_at
                        'guestuser@gmail.com',  # user_id
                        '0.0.1',  # version
                        tool.name,
                        tool.content,
                        tool.description,
                        json.dumps(tool.secrets) if hasattr(tool, 'secrets') else '{}',
                        json.dumps(tool.libraries) if hasattr(tool, 'libraries') else '[]'
                    )
                    cursor.execute("""
                        INSERT INTO skill (id, created_at, updated_at, user_id, version, name, content, description, secrets, libraries)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, skill_data)
                    print(f"Inserted skill: {tool.name}")
                except Exception as e:
                    print(f"Error inserting skill {tool.name}: {str(e)}")
                    traceback.print_exc()

            # Handle the workflow
            try:
                workflow_data, _ = get_workflow_from_agents(agents)
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                workflow_insert_data = (
                    None,  # id (AUTO INCREMENT)
                    current_time,  # created_at
                    current_time,  # updated_at
                    'guestuser@gmail.com',  # user_id
                    '0.0.1',  # version
                    workflow_data.get('name', 'AutoGroq Workflow'),
                    workflow_data.get('description', 'Workflow auto-generated by AutoGroq.'),
                    workflow_data.get('type', 'autonomous'),  # Default to 'autonomous' if not specified
                    workflow_data.get('summary_method', 'last')[:4],  # VARCHAR(4)
                    json.dumps(workflow_data.get('sample_tasks', []))
                )
                cursor.execute("""
                    INSERT INTO workflow (id, created_at, updated_at, user_id, version, name, description, type, summary_method, sample_tasks)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, workflow_insert_data)
                print("Inserted workflow data.")
            except Exception as e:
                print(f"Error inserting workflow: {str(e)}")
                traceback.print_exc()

            conn.commit()
            print("Changes committed to the database.")

            conn.close()
            print("Database connection closed.")

            st.success("Data exported to Autogen successfully!")
        except sqlite3.Error as e:
            st.error(f"Error exporting data to Autogen: {str(e)}")
            print(f"Error exporting data to Autogen: {str(e)}")
            traceback.print_exc()


def get_table_info(table_name):
    conn = sqlite3.connect(FRAMEWORK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return columns


def insert_or_get_skill(cursor, tool):
    tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', '')
    cursor.execute("SELECT id FROM skill WHERE name = ?", (tool_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        print(f"Inserting new skill: {tool}")
        
        skill_data = (
            None,  # id is INTEGER PRIMARY KEY, let SQLite auto-increment
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # updated_at
            'default',  # user_id
            '0.0.1',  # version
            str(tool_name),
            str(tool.content if hasattr(tool, 'content') else tool.get('content', '')),
            str(tool.description if hasattr(tool, 'description') else tool.get('description', '')),
            json.dumps(tool.secrets if hasattr(tool, 'secrets') else tool.get('secrets', {})),
            json.dumps(tool.libraries if hasattr(tool, 'libraries') else tool.get('libraries', []))
        )
        
        print(f"Skill data to be inserted: {skill_data}")
        
        try:
            cursor.execute("""
                INSERT INTO skill (id, created_at, updated_at, user_id, version, name, content, description, secrets, libraries) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, skill_data)
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            print("Data types:")
            for i, item in enumerate(skill_data):
                print(f"  {i}: {type(item)}")
            raise
    

def insert_or_get_model(cursor, model_config):
    cursor.execute("SELECT id FROM model WHERE model = ?", (model_config['model'],))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        model_data = (
            str(uuid.uuid4()),  # id
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # updated_at
            'guestuser@gmail.com',  # user_id
            '0.0.1',  # version
            model_config['model'],
            model_config.get('api_key'),
            model_config.get('base_url'),
            model_config.get('api_type', '')[:6],  # VARCHAR(6)
            model_config.get('api_version'),
            model_config.get('description', '')
        )
        cursor.execute("""
            INSERT INTO model (id, created_at, updated_at, user_id, version, model, api_key, base_url, api_type, api_version, description) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, model_data)
        return cursor.lastrowid
    

def insert_workflow(cursor, workflow_data):
    workflow_insert_data = (
        None,  # id is INTEGER PRIMARY KEY, let SQLite auto-increment
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # updated_at
        'guestuser@gmail.com',  # user_id (matching existing entries)
        '0.0.1',  # version
        workflow_data.get('name', 'AutoGroq Workflow'),
        workflow_data.get('description', 'Workflow auto-generated by AutoGroq.'),
        workflow_data.get('type', 'groupchat')[:10],  # VARCHAR(10)
        workflow_data.get('summary_method', 'last')[:4],  # VARCHAR(4)
        json.dumps(workflow_data.get('sample_tasks', []))
    )
    print(f"Inserting workflow data: {workflow_insert_data}")
    try:
        cursor.execute("""
            INSERT INTO workflow (id, created_at, updated_at, user_id, version, name, description, type, summary_method, sample_tasks) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, workflow_insert_data)
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        print("Data types:")
        for i, item in enumerate(workflow_insert_data):
            print(f"  {i}: {type(item)}")
        raise


def sql_to_db(sql: str, params: tuple = None):
    try:
        conn = sqlite3.connect(FRAMEWORK_DB_PATH)
        cursor = conn.cursor()
        print("Connected to the database successfully.")
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        print("SQL executed successfully.")
    except sqlite3.Error as e:
        print(f"Error executing SQL: {str(e)}")
        print(f"SQL: {sql}")
        print(f"Params: {params}")
        raise
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")
            

#FUTURE functions for exporting to new Autogen Studio schema:

# def create_or_update_agent(agent: dict, db_path: str):
#     with sqlite3.connect(db_path) as conn:
#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT OR REPLACE INTO Agent (id, skills, created_at, updated_at, user_id, workflows, type, config, models)
#             VALUES (:id, :skills, :created_at, :updated_at, :user_id, :workflows, :type, :config, :models)
#         """, agent)
#         conn.commit()

# def create_or_update_skill(skill: dict, db_path: str):
#     with sqlite3.connect(db_path) as conn:
#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT OR REPLACE INTO Skill (id, created_at, updated_at, user_id, name, content, description, secrets, libraries)
#             VALUES (:id, :created_at, :updated_at, :user_id, :name, :content, :description, :secrets, :libraries)
#         """, skill)
#         conn.commit()

# def create_or_update_workflow(workflow: dict, db_path: str):
#     with sqlite3.connect(db_path) as conn:
#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT OR REPLACE INTO Workflow (id, agents, created_at, updated_at, user_id, name, description, type, summary_method)
#             VALUES (:id, :agents, :created_at, :updated_at, :user_id, :name, :description, :type, :summary_method)
#         """, workflow)
#         conn.commit()

# def get_agent_by_id(agent_id: int, db_path: str) -> Optional[dict]:
#     with sqlite3.connect(db_path) as conn:
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Agent WHERE id = ?", (agent_id,))
#         row = cursor.fetchone()
#         if row:
#             columns = [column[0] for column in cursor.description]
#             return dict(zip(columns, row))
#     return None

# def get_skill_by_id(skill_id: int, db_path: str) -> Optional[dict]:
#     with sqlite3.connect(db_path) as conn:
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Skill WHERE id = ?", (skill_id,))
#         row = cursor.fetchone()
#         if row:
#             columns = [column[0] for column in cursor.description]
#             return dict(zip(columns, row))
#     return None

# def get_workflow_by_id(workflow_id: int, db_path: str) -> Optional[dict]:
#     with sqlite3.connect(db_path) as conn:
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Workflow WHERE id = ?", (workflow_id,))
#         row = cursor.fetchone()
#         if row:
#             columns = [column[0] for column in cursor.description]
#             return dict(zip(columns, row))
#     return None

```

# AutoGroq\utils\error_handling.py

```python
import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_error(error_message):
    logging.error(error_message)

def log_tool_execution(tool_name, args, result):
    logging.info(f"Executed tool: {tool_name} with args: {args}. Result: {result}")
```

# AutoGroq\utils\file_utils.py

```python

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

```

# AutoGroq\utils\sandbox.py

```python
import os
import subprocess

def execute_in_sandbox(tool_name, *args):
    # Create a temporary Python file with the tool execution
    with open('temp_tool_execution.py', 'w') as f:
        f.write(f"from tools.{tool_name} import {tool_name}\n")
        f.write(f"result = {tool_name}(*{args})\n")
        f.write("print(result)\n")
    
    # Execute the temporary file in a separate process with restricted permissions
    try:
        result = subprocess.run(['python', 'temp_tool_execution.py'], 
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    finally:
        os.remove('temp_tool_execution.py')
```

# AutoGroq\utils\session_utils.py

```python

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
```

# AutoGroq\utils\text_utils.py

```python
import re


def normalize_config(config, agent_name):
    """Normalize the config dictionary to match the format of default entries."""
    normalized = {
        "name": normalize_name(config.get('name', agent_name)),
        "human_input_mode": "NEVER",
        "max_consecutive_auto_reply": 25,
        "system_message": config.get('system_message', f"You are a helpful AI assistant that can act as {agent_name}."),
        "is_termination_msg": None,
        "code_execution_config": "none",
        "default_auto_reply": "",
        "description": "Assistant Agent",
        "llm_config": {
            "config_list": [],
            "temperature": 0,
            "cache_seed": None,
            "timeout": None,
            "max_tokens": 2048,
            "extra_body": None
        },
        "admin_name": "Admin",
        "messages": [],
        "max_round": 100,
        "speaker_selection_method": "auto",
        "allow_repeat_speaker": True
    }
    
    return normalized


def normalize_name(name):
    """Convert name to lowercase and replace spaces with underscores."""
    return sanitize_text(name).lower().replace(' ', '_')


def sanitize_text(text): 
    # Remove non-ASCII characters 
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    # Remove non-alphanumeric characters except for standard punctuation 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?:;\'"-]+', '', text) 
    return text 
```

# AutoGroq\utils\tool_execution.py

```python
# utils/tool_execution.py

import inspect
import logging

from utils.sandbox import execute_in_sandbox


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def execute_tool(tool_name, function_map, *args, **kwargs):
    logger.debug(f"Attempting to execute tool: {tool_name}")
    logger.debug(f"Available tools: {list(function_map.keys())}")
    logger.debug(f"Args: {args}")
    logger.debug(f"Kwargs: {kwargs}")
    
    if tool_name not in function_map:
        raise ValueError(f"Tool '{tool_name}' not found in function map")
    
    tool_function = function_map[tool_name]
    logger.debug(f"Tool function: {tool_function}")
    
    try:
        result = tool_function(*args, **kwargs)
        logger.debug(f"Tool execution result: {result[:500]}...")  # Log first 500 characters of result
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
        raise


def get_tool_signature(tool_name, function_map):
    if tool_name not in function_map:
        raise ValueError(f"Tool '{tool_name}' not found in function map")
    
    tool_function = function_map[tool_name]
    return inspect.signature(tool_function)
```

# AutoGroq\utils\tool_utils.py

```python

import datetime
import importlib
import json
import os
import re
import sqlite3
import streamlit as st
import uuid

from models.tool_base_model import ToolBaseModel
from prompts import get_generate_tool_prompt
from utils.api_utils import get_api_key
from utils.db_utils import sql_to_db
from utils.file_utils import regenerate_zip_files
from utils.ui_utils import get_llm_provider


def create_tool_data(python_code):
    # Extract the function name from the Python code
    function_name_match = re.search(r"def\s+(\w+)\(", python_code)
    if function_name_match:
        function_name = function_name_match.group(1)    
    else:
        function_name = "unnamed_function"

    # Extract the tool description from the docstring
    docstring_match = re.search(r'"""(.*?)"""', python_code, re.DOTALL)
    if docstring_match:
        tool_description = docstring_match.group(1).strip()
    else:
        tool_description = "No description available"

    # Get the current timestamp
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update st.session_state.tool_model with the tool data
    st.session_state.tool_model.name = function_name
    st.session_state.tool_model.description = tool_description
    st.session_state.tool_model.title = function_name
    st.session_state.tool_model.file_name = f"{function_name}.py"
    st.session_state.tool_model.content = python_code
    st.session_state.tool_model.user_id = "default"
    st.session_state.tool_model.created_at = current_time
    st.session_state.tool_model.updated_at = current_time
    st.session_state.tool_model.version = "0.0.1"


    secrets = []
    libraries = []
    
    # Simple regex to find import statements
    import_pattern = r'import\s+(\w+)'
    libraries = re.findall(import_pattern, python_code)
    
    # Simple regex to find potential API keys or secrets
    secret_pattern = r'([A-Z_]+_API_KEY|[A-Z_]+_SECRET)'
    secrets = re.findall(secret_pattern, python_code)
    
    st.session_state.tool_model.secrets = [{"secret": s, "value": None} for s in secrets]
    st.session_state.tool_model.libraries = libraries


def export_tool_as_skill(tool_name: str, edited_skill: str):
    print(f"Exporting skill '{tool_name}'...")
    try:
        create_tool_data(edited_skill)
        print(f"Skill data: {st.session_state.tool_model.to_dict()}")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        skill_tuple = (
            str(uuid.uuid4()),  # id (TEXT)
            current_time,  # created_at (TEXT)
            current_time,  # updated_at (TEXT)
            'default',  # user_id (TEXT)
            '0.0.1',  # version (TEXT)
            tool_name,  # name (TEXT)
            edited_skill,  # content (TEXT)
            st.session_state.tool_model.description,  # description (TEXT)
            json.dumps(st.session_state.tool_model.secrets),  # secrets (TEXT)
            json.dumps(st.session_state.tool_model.libraries)  # libraries (TEXT)
        )
        print(f"Inserting skill data: {skill_tuple}")
        sql = """
        INSERT INTO skill (id, created_at, updated_at, user_id, version, name, content, description, secrets, libraries) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        sql_to_db(sql, skill_tuple)
        st.success(f"Skill '{tool_name}' exported to Autogen successfully!")
    except sqlite3.Error as e:
        st.error(f"Error exporting skill: {str(e)}")
        print(f"Error exporting skill: {str(e)}")
        print(f"Skill tuple: {skill_tuple}")  


def generate_tool(rephrased_tool_request):  
    temperature_value = st.session_state.get('temperature', 0.1)
    max_tokens_value = st.session_state.get('max_tokens', 100)
    top_p_value = st.session_state.get('top_p', 1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": max_tokens_value,
        "top_p": top_p_value,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": get_generate_tool_prompt(rephrased_tool_request)
            }
        ]
    }
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    response = llm_provider.send_request(llm_request_data)
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        print(f"Response data: {response_data}")
        if "choices" in response_data and response_data["choices"]:
            proposed_tool = response_data["choices"][0]["message"]["content"].strip()
            match = re.search(r"def\s+(\w+)\(", proposed_tool)
            if match:
                tool_name = match.group(1)
                
                # Update the st.session_state.tool_model with the proposed tool data
                create_tool_data(proposed_tool)
                
                return proposed_tool, tool_name
            else:
                print("Error: Failed to extract tool name from the proposed tool.")
                return None, None
    return None, None


def extract_tool_description(proposed_tool):
    docstring_match = re.search(r'"""(.*?)"""', proposed_tool, re.DOTALL)
    if docstring_match:
        return docstring_match.group(1).strip()
    else:
        return "No description available"


def load_tool_functions():
    st.session_state.tool_functions = {}
    st.session_state.tool_models = []

    parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools_folder_path = os.path.join(parent_directory, 'tools')
    tool_files = [f for f in os.listdir(tools_folder_path) if f.endswith('.py') and f != '__init__.py']

    for tool_file in tool_files:
        tool_name = os.path.splitext(tool_file)[0]
        try:
            tool_module = importlib.import_module(f"tools.{tool_name}")
            
            if hasattr(tool_module, 'get_tool'):
                tool = tool_module.get_tool()
                if isinstance(tool, ToolBaseModel):
                    st.session_state.tool_models.append(tool)
                    st.session_state.tool_functions[tool.name] = tool.function
                    print(f"Loaded tool: {tool.name}")
                else:
                    print(f"Warning: get_tool() in {tool_file} did not return a ToolBaseModel instance")
            else:
                print(f"Warning: {tool_file} does not have a get_tool() function")
        except Exception as e:
            print(f"Error loading tool from {tool_file}: {str(e)}")

    print(f"Loaded {len(st.session_state.tool_models)} tools.")
    
    # Debug: Print loaded tools
    for tool in st.session_state.tool_models:
        print(f"Loaded tool model: {tool.name}")
    for tool_name, tool_function in st.session_state.tool_functions.items():
        print(f"Loaded tool function: {tool_name} -> {tool_function}")
        

def populate_tool_models():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tool_folder = os.path.join(project_root, "tools")
    tool_files = [f for f in os.listdir(tool_folder) if f.endswith(".py")]

    tool_models = []
    for tool_file in tool_files:
        tool_name = os.path.splitext(tool_file)[0]
        tool_file_path = os.path.join(tool_folder, tool_file)
        with open(tool_file_path, 'r') as file:
            tool_data = file.read()
            create_tool_data(tool_data)
            tool_model = ToolBaseModel(
                name=st.session_state.tool_model.name,
                description=st.session_state.tool_model.description,
                title=st.session_state.tool_model.title,
                file_name=st.session_state.tool_model.file_name,
                content=st.session_state.tool_model.content,
                id=len(tool_models) + 1,
                created_at=datetime.datetime.now().isoformat(),
                updated_at=datetime.datetime.now().isoformat(),
                user_id=st.session_state.tool_model.user_id,
                secrets=st.session_state.tool_model.secrets,
                libraries=st.session_state.tool_model.libraries,
                timestamp=st.session_state.tool_model.timestamp
            )
            tool_models.append(tool_model)

    st.session_state.tool_models = tool_models
    st.session_state.project_model.tools = tool_models
    

def process_tool_request():
    if st.session_state.tool_request and not st.session_state.get('tool_processed', False):
        tool_request = st.session_state.tool_request
        rephrased_tool_request = rephrase_tool(tool_request)
        if rephrased_tool_request:
            proposed_tool, tool_name = generate_tool(rephrased_tool_request)
            if proposed_tool:
                match = re.search(r"def\s+(\w+(?:_\w+)*)\(", proposed_tool)
                if match:
                    tool_name = match.group(1)
                    st.write(f"Proposed tool: {tool_name}")
                    st.code(proposed_tool)

                    with st.form(key=f"export_form_{tool_name}"):
                        submit_export = st.form_submit_button("Export/Write")
                        if submit_export:
                            new_tool = ToolBaseModel(
                                name=tool_name,
                                description=extract_tool_description(proposed_tool),
                                title=tool_name,
                                file_name=f"{tool_name}.py",
                                content=proposed_tool,
                                id=len(st.session_state.tool_models) + 1,
                                created_at=datetime.datetime.now().isoformat(),
                                updated_at=datetime.datetime.now().isoformat(),
                                user_id="default",
                                secrets={},
                                libraries=[],
                                timestamp=datetime.datetime.now().isoformat()
                            )
                            st.session_state.tool_models.append(new_tool)
                            st.session_state.selected_tools.append(tool_name)  # Add this line
                            export_tool_as_skill(tool_name, proposed_tool)
                            st.success(f"Tool {tool_name} exported and added to the tool list!")
                            st.session_state.show_tool_input = False
                            st.session_state.tool_request = ""
                            st.session_state.proposed_tool = None
                            st.session_state.tool_name = None
                            st.session_state.tool_processed = True
                            st.experimental_rerun()
                else:
                    st.error("Failed to extract tool name from the proposed tool.")
            else:
                st.error("No proposed tool generated.")


def rephrase_tool(tool_request):
    print("Debug: Rephrasing tool: ", tool_request)
    temperature_value = st.session_state.get('temperature', 0.1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": f"""
                Act as a professional tool creator and rephrase the following tool request into an optimized prompt:

                tool request: "{tool_request}"

                Rephrased:
                """
            }
        ]
    }
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    response = llm_provider.send_request(llm_request_data)
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            rephrased = response_data["choices"][0]["message"]["content"].strip()
            print(f"Debug: Rephrased tool: {rephrased}")
            return rephrased
    return None                


def save_tool(tool_name, edited_tool):
    with open(f"{tool_name}.py", "w") as f:
        f.write(edited_tool)
    st.success(f"tool {tool_name} saved successfully!")


def show_tools():
    with st.expander("Tools"):
        selected_tools = []
        select_all = st.checkbox("Select All", key="select_all_tools")
        for idx, tool_model in enumerate(st.session_state.tool_models):
            tool_name = tool_model.name
            if select_all:
                tool_checkbox = st.checkbox(f"Add {tool_name} tool to all agents", value=True, key=f"tool_{tool_name}_{idx}")
            else:
                tool_checkbox = st.checkbox(f"Add {tool_name} tool to all agents", value=tool_name in st.session_state.selected_tools, key=f"tool_{tool_name}_{idx}")
            if tool_checkbox:
                selected_tools.append(tool_name)

        if select_all:
            st.session_state.selected_tools = [tool_model.name for tool_model in st.session_state.tool_models]
        else:
            st.session_state.selected_tools = selected_tools

        # Update the 'tools' attribute of each agent with the selected tools
        for agent in st.session_state.agents:
            agent.tools = [tool_model for tool_model in st.session_state.tool_models if tool_model.name in st.session_state.selected_tools]

        regenerate_zip_files()

        if st.button("Add Tool", key="add_tool_button"):
            st.session_state.show_tool_input = True
            st.session_state.tool_request = ""
            st.session_state.tool_processed = False 

        if st.session_state.get('show_tool_input'):
            tool_request = st.text_input("Need a new tool? Describe what it should do:", key="tool_request_input")
            if tool_request:
                st.session_state.tool_request = tool_request
                process_tool_request()

```

# AutoGroq\utils\ui_utils.py

```python
import datetime
import json
import os
import pandas as pd
import re
import requests
import streamlit as st
import time

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from configs.config import (DEBUG, LLM_PROVIDER, MAX_RETRIES, 
        MODEL_CHOICES, MODEL_TOKEN_LIMITS, RETRY_DELAY, SUPPORTED_PROVIDERS)

from anthropic.types import Message
from configs.current_project import Current_Project
from models.agent_base_model import AgentBaseModel
from models.workflow_base_model import WorkflowBaseModel
from prompts import create_project_manager_prompt, get_agents_prompt, get_rephrased_user_prompt, get_moderator_prompt  
from tools.fetch_web_content import fetch_web_content
from typing import Any, List, Dict, Tuple
from utils.agent_utils import create_agent_data
from utils.api_utils import fetch_available_models, get_api_key, get_llm_provider
from utils.auth_utils import display_api_key_input
from utils.db_utils import export_to_autogen
from utils.file_utils import zip_files_in_memory
from utils.workflow_utils import get_workflow_from_agents
    

def create_agents(json_data: List[Dict[str, Any]]) -> Tuple[List[AgentBaseModel], List[Dict[str, Any]]]:
    autogen_agents = []
    crewai_agents = []
    
    for agent_data in json_data:
        expert_name = agent_data.get('expert_name', '')
        description = agent_data.get('description', '')
        
        if not expert_name:
            print("Missing agent name. Skipping...")
            continue

        autogen_agent_data, crewai_agent_data = create_agent_data({
            "name": expert_name,
            "description": description,
            "role": agent_data.get('role', expert_name),
            "goal": agent_data.get('goal', f"Assist with tasks related to {description}"),
            "backstory": agent_data.get('backstory', f"As an AI assistant, I specialize in {description}")
        })
        
        try:
            agent_model = AgentBaseModel(
                name=autogen_agent_data['name'],
                description=autogen_agent_data['description'],
                tools=autogen_agent_data.get('tools', []),
                config=autogen_agent_data.get('config', {}),
                role=autogen_agent_data['role'],
                goal=autogen_agent_data['goal'],
                backstory=autogen_agent_data['backstory'],
                provider=autogen_agent_data.get('provider', ''),
                model=autogen_agent_data.get('model', '')
            )
            print(f"Created agent: {agent_model.name} with description: {agent_model.description}")
            autogen_agents.append(agent_model)
            crewai_agents.append(crewai_agent_data)
        except Exception as e:
            print(f"Error creating agent {expert_name}: {str(e)}")
            print(f"Agent data: {autogen_agent_data}")
            continue

    return autogen_agents, crewai_agents


def create_project_manager(rephrased_text):
    print(f"Creating Project Manager")
    temperature_value = st.session_state.get('temperature', 0.1)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": create_project_manager_prompt(rephrased_text)    
            }
        ]
    }

    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    response = llm_provider.send_request(llm_request_data)
    
    if response is not None:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            return content.strip()
    
    return None


def display_discussion_and_whiteboard():
    tabs = st.tabs(["Discussion", "Whiteboard", "History", "Deliverables", "Download", "Debug"])
    discussion_history = get_discussion_history()

    with tabs[0]:
        # Display only the most recent agent response
        if 'most_recent_response' in st.session_state and st.session_state.most_recent_response:
            st.text_area("Most Recent Response", value=st.session_state.most_recent_response, height=400, key="discussion")
        else:
            st.text_area("Discussion", value="No responses yet.", height=400, key="discussion")

    with tabs[1]:
        # Extract code snippets from the full discussion history
        code_snippets = extract_code_from_response(discussion_history)
        
        # Display code snippets in the whiteboard, allowing editing
        new_whiteboard_content = st.text_area("Whiteboard (Code Snippets)", value=code_snippets, height=400, key="whiteboard")
        
        # Update the whiteboard content in the session state if it has changed
        if new_whiteboard_content != st.session_state.get('whiteboard_content', ''):
            st.session_state.whiteboard_content = new_whiteboard_content

    with tabs[2]:
        st.write(discussion_history)


    with tabs[3]:
        if "current_project" in st.session_state:
            current_project = st.session_state.current_project
            for index, deliverable in enumerate(current_project.deliverables):
                if deliverable["text"].strip():  # Check if the deliverable text is not empty
                    checkbox_key = f"deliverable_{index}"
                    done = st.checkbox(
                        deliverable["text"], 
                        value=current_project.is_deliverable_complete(index),
                        key=checkbox_key,
                        on_change=update_deliverable_status,
                        args=(index,)
                    )
                    if done != deliverable["done"]:
                        if done:
                            current_project.mark_deliverable_phase_done(index, current_project.current_phase)
                        else:
                            current_project.deliverables[index]["done"] = False
                            for phase in current_project.implementation_phases:
                                current_project.deliverables[index]["phase"][phase] = False


    with tabs[4]:
        display_download_button() 
        if st.button("Export to Autogen"):
            export_to_autogen()

    with tabs[5]:
        if DEBUG:
            if "project_model" in st.session_state:
                project_model = st.session_state.project_model
                with st.expander("Project Details"):
                    st.write("ID:", project_model.id)
                    st.write("Re-engineered Prompt:", project_model.re_engineered_prompt)
                    st.write("Deliverables:", project_model.deliverables)
                    st.write("Created At:", project_model.created_at)
                    st.write("Updated At:", project_model.updated_at)
                    st.write("User ID:", project_model.user_id)
                    st.write("Name:", project_model.name)
                    st.write("Description:", project_model.description)
                    st.write("Status:", project_model.status)
                    st.write("Due Date:", project_model.due_date)
                    st.write("Priority:", project_model.priority)
                    st.write("Tags:", project_model.tags)
                    st.write("Attachments:", project_model.attachments)
                    st.write("Notes:", project_model.notes)
                    st.write("Collaborators:", project_model.collaborators)
                    st.write("Workflows:", project_model.workflows)
                    if project_model.tools:
                        st.write("Tools:")
                        for tool in project_model.tools:
                            substring = "init"
                            if not substring in tool.name:
                                st.write(f"- {tool.name}")
                                st.code(tool.content, language="python")
                    else:
                        st.write("Tools: []")
                    

            if "project_model" in st.session_state and st.session_state.project_model.workflows:
                workflow_data = st.session_state.project_model.workflows[0]
                workflow = WorkflowBaseModel.from_dict({**workflow_data, 'settings': workflow_data.get('settings', {})})
                with st.expander("Workflow Details"):
                    st.write("ID:", workflow.id)
                    st.write("Name:", workflow.name)
                    st.write("Description:", workflow.description)
                    
                    # Display the agents in the workflow
                    st.write("Agents:")
                    for agent in workflow.receiver.groupchat_config["agents"]:
                        st.write(f"- {agent['config']['name']}")
                    
                    st.write("Settings:", workflow.settings)    
                    st.write("Created At:", workflow.created_at)
                    st.write("Updated At:", workflow.updated_at)
                    st.write("User ID:", workflow.user_id)
                    st.write("Type:", workflow.type)
                    st.write("Summary Method:", workflow.summary_method)
                    
                    # Display sender details
                    st.write("Sender:")
                    st.write("- Type:", workflow.sender.type)
                    st.write("- Config:", workflow.sender.config)
                    st.write("- Timestamp:", workflow.sender.timestamp)
                    st.write("- User ID:", workflow.sender.user_id)
                    st.write("- Tools:", workflow.sender.tools)
                    
                    # Display receiver details
                    st.write("Receiver:")
                    st.write("- Type:", workflow.receiver.type)
                    st.write("- Config:", workflow.receiver.config)
                    st.write("- Groupchat Config:", workflow.receiver.groupchat_config)
                    st.write("- Timestamp:", workflow.receiver.timestamp)
                    st.write("- User ID:", workflow.receiver.user_id)
                    st.write("- Tools:", workflow.receiver.tools)
                    st.write("- Agents:", [agent.to_dict() for agent in workflow.receiver.agents])
                    
                    st.write("Timestamp:", workflow.timestamp)
            else:
                st.warning("No workflow data available.")
            

            if "agents" in st.session_state:
                with st.expander("Agent Details"):
                    agent_names = ["Select one..."] + [agent.get('name', f"Agent {index + 1}") for index, agent in enumerate(st.session_state.agents)]
                    selected_agent = st.selectbox("Select an agent:", agent_names)

                    if selected_agent != "Select one...":
                        agent_index = agent_names.index(selected_agent) - 1
                        agent = st.session_state.agents[agent_index]

                        st.subheader(selected_agent)
                        st.write("ID:", agent.get('id'))
                        st.write("Name:", agent.get('name'))
                        st.write("Description:", agent.get('description'))
                        
                        # Display the selected tools for the agent
                        st.write("Tools:", ", ".join(agent.get('tools', [])))
                        
                        st.write("Config:", agent.get('config'))
                        st.write("Created At:", agent.get('created_at'))
                        st.write("Updated At:", agent.get('updated_at'))
                        st.write("User ID:", agent.get('user_id'))
                        st.write("Workflows:", agent.get('workflows'))
                        st.write("Type:", agent.get('type'))
                        st.write("Models:", agent.get('models'))
                        st.write("Verbose:", agent.get('verbose'))
                        st.write("Allow Delegation:", agent.get('allow_delegation'))
                        st.write("New Description:", agent.get('new_description'))
                        st.write("Timestamp:", agent.get('timestamp'))
            else:
                st.warning("No agent data available.")

            if len(st.session_state.tool_models) > 0:
                with st.expander("Tool Details"):
                    tool_names = ["Select one..."] + [tool.name for tool in st.session_state.tool_models]
                    selected_tool = st.selectbox("Select a tool:", tool_names)

                    if selected_tool != "Select one...":
                        tool_index = tool_names.index(selected_tool) - 1
                        tool = st.session_state.tool_models[tool_index]
                        
                        st.subheader(selected_tool)
                        
                        # Display tool details in a more visually appealing way
                        col1, col2 = st.columns(RETRY_DELAY)
                        
                        with col1:
                            st.markdown(f"**ID:** {tool.id}")
                            st.markdown(f"**Name:** {tool.name}")
                            st.markdown(f"**Created At:** {tool.created_at}")
                            st.markdown(f"**Updated At:** {tool.updated_at}")
                            st.markdown(f"**User ID:** {tool.user_id}")
                        
                        with col2:
                            st.markdown(f"**Secrets:** {tool.secrets}")
                            st.markdown(f"**Libraries:** {tool.libraries}")
                            st.markdown(f"**File Name:** {tool.file_name}")
                            st.markdown(f"**Timestamp:** {tool.timestamp}")
                            st.markdown(f"**Title:** {tool.title}")

                        st.markdown(f"**Description:** {tool.description}")
                        
                        # Display the tool's content in a code block
                        st.markdown("**Content:**")
                        st.code(tool.content, language="python")
            else:
                st.warning("No tool data available.")

        else:
            st.warning("Debugging disabled.")   
                                    

def display_download_button():
    col1, col2 = st.columns(RETRY_DELAY)
    
    with col1:
        if st.session_state.get('autogen_zip_buffer') is not None:
            st.download_button(
                label="Download Autogen Files",
                data=st.session_state.autogen_zip_buffer,
                file_name="autogen_files.zip",
                mime="application/zip",
                key=f"autogen_download_button_{int(time.time())}"
            )
        else:
            st.warning("Autogen files are not available for download.")
    
    with col2:
        if st.session_state.get('crewai_zip_buffer') is not None:
            st.download_button(
                label="Download CrewAI Files",
                data=st.session_state.crewai_zip_buffer,
                file_name="crewai_files.zip",
                mime="application/zip",
                key=f"crewai_download_button_{int(time.time())}"
            )
        else:
            st.warning("CrewAI files are not available for download.")


def display_download_and_export_buttons():
    display_download_button() 
    if st.button("Export to Autogen"):
            export_to_autogen() 


def display_goal():
    if "current_project" in st.session_state:
        current_project = st.session_state.current_project
        if current_project.re_engineered_prompt:
            st.expander("Goal").markdown(f"**OUR CURRENT GOAL:**\n\r {current_project.re_engineered_prompt}")


def display_user_input():
    user_input = st.text_area("Additional Input:", value=st.session_state.get("user_input", ""), key="user_input_widget", height=100, on_change=update_user_input)
    reference_url = st.text_input("URL:", key="reference_url_widget")

    if user_input:
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        url_match = url_pattern.search(user_input)
        if url_match:
            url = url_match.group()
            if "reference_html" not in st.session_state or url not in st.session_state.reference_html:
                html_content = fetch_web_content(url)
                if html_content:
                    st.session_state.reference_html[url] = html_content
                else:
                    st.warning("Failed to fetch HTML content.")
            else:
                st.session_state.reference_html = {}
        else:
            st.session_state.reference_html = {}
    else:
        st.session_state.reference_html = {}

    return user_input, reference_url


def display_reset_and_upload_buttons():
    col1, col2 = st.columns(RETRY_DELAY)  
    with col1:
        if st.button("Reset", key="reset_button"):
            # Define the keys of session state variables to clear
            keys_to_reset = [
                "rephrased_request", "discussion", "whiteboard", "user_request",
                "user_input", "agents", "zip_buffer", "crewai_zip_buffer",
                "autogen_zip_buffer", "uploaded_file_content", "discussion_history",
                "last_comment", "user_api_key", "reference_url"
            ]
            # Reset each specified key
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            # Additionally, explicitly reset user_input to an empty string
            st.session_state.user_input = ""
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
    if st.session_state.show_request_input:
        if st.session_state.get("previous_user_request") != st.session_state.get("user_request", ""):
            st.session_state.previous_user_request = st.session_state.get("user_request", "")
            if st.session_state.get("user_request", ""):
                handle_user_request(st.session_state)
            else:
                st.session_state.agents = []
                st.session_state.show_request_input = False
            st.experimental_rerun()


def extract_code_from_response(response):
    code_pattern = r"```(.*?)```"
    code_blocks = re.findall(code_pattern, response, re.DOTALL)

    html_pattern = r"<html.*?>.*?</html>"
    html_blocks = re.findall(html_pattern, response, re.DOTALL | re.IGNORECASE)

    js_pattern = r"<script.*?>.*?</script>"
    js_blocks = re.findall(js_pattern, response, re.DOTALL | re.IGNORECASE)

    css_pattern = r"<style.*?>.*?</style>"
    css_blocks = re.findall(css_pattern, response, re.DOTALL | re.IGNORECASE)

    all_code_blocks = code_blocks + html_blocks + js_blocks + css_blocks
    unique_code_blocks = list(set(all_code_blocks))

    return "\n\n".join(unique_code_blocks) 


def extract_content(response: Any) -> str:
    if hasattr(response, 'content') and isinstance(response.content, list):
        # Anthropic-specific handling
        return response.content[0].text
    elif isinstance(response, requests.models.Response):
        # Groq and potentially other providers using requests.Response
        try:
            json_response = response.json()
            if 'choices' in json_response and json_response['choices']:
                return json_response['choices'][0]['message']['content']
        except json.JSONDecodeError:
            print("Failed to decode JSON from response")
            return ""
    elif isinstance(response, dict):
        if 'choices' in response and response['choices']:
            return response['choices'][0]['message']['content']
        elif 'content' in response:
            return response['content']
    elif isinstance(response, str):
        return response
    print(f"Unexpected response format: {type(response)}")
    return ""
 

def extract_json_objects(text: str) -> List[Dict]:
    objects = []
    stack = []
    start_index = 0
    for i, char in enumerate(text):
        if char == "{":
            if not stack:
                start_index = i
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack:
                    objects.append(text[start_index:i+1])
    parsed_objects = []
    for obj_str in objects:
        try:
            parsed_obj = json.loads(obj_str)
            parsed_objects.append(parsed_obj)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON object: {e}")
            print(f"JSON string: {obj_str}")
    return parsed_objects


def get_agents_from_text(text: str) -> Tuple[List[AgentBaseModel], List[Dict[str, Any]]]:
    print("Getting agents from text...")
    
    instructions = get_agents_prompt()
    combined_content = f"{instructions}\n\nTeam of Experts:\n{text}"
    
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "messages": [
            {"role": "user", "content": combined_content}
        ]
    }
    
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    
    try:
        response = llm_provider.send_request(llm_request_data)
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")

        content = extract_content(response)
        
        if not content:
            print("No content extracted from response.")
            return [], []

        print(f"Extracted content: {content}")

        json_data = parse_json(content)
        
        if not json_data:
            print("Failed to parse JSON data.")
            return [], []

        return create_agents(json_data)
    
    except Exception as e:
        print(f"Error in get_agents_from_text: {e}")
        return [], []
    

def get_discussion_history():
    return st.session_state.discussion_history


def get_provider_models(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    return MODEL_CHOICES.get(provider, {})


def handle_user_request(session_state):
    print("Debug: Handling user request for session state: ", session_state)
    user_request = session_state.user_request
    max_retries = MAX_RETRIES
    retry_delay = RETRY_DELAY

    for retry in range(max_retries):
        try:
            print("Debug: Sending request to rephrase_prompt")
            model = session_state.model
            print(f"Debug: Model: {model}")
            rephrased_text = rephrase_prompt(user_request, model)
            print(f"Debug: Rephrased text: {rephrased_text}")
            if rephrased_text:
                session_state.rephrased_request = rephrased_text
                break
            else:
                print("Error: Failed to rephrase the user request.")
                st.warning("Failed to rephrase the user request. Please try again.")
                return
        except Exception as e:
            print(f"Error occurred in handle_user_request: {str(e)}")
            if retry < max_retries - 1:
                print(f"Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
            else:
                print("Max retries exceeded.")
                st.warning("An error occurred. Please try again.")
                return

    if "rephrased_request" not in session_state:
        st.warning("Failed to rephrase the user request. Please try again.")
        return

    session_state.project_model.description = session_state.user_request
    rephrased_text = session_state.rephrased_request
    session_state.project_model.set_re_engineered_prompt(rephrased_text)

    if "project_manager_output" not in session_state:
        project_manager_output = create_project_manager(rephrased_text)

        if not project_manager_output:
            print("Error: Failed to create Project Manager.")
            st.warning("Failed to create Project Manager. Please try again.")
            return

        session_state.project_manager_output = project_manager_output

        current_project = Current_Project()
        current_project.set_re_engineered_prompt(rephrased_text)

        deliverables_patterns = [
            r"(?:Deliverables|Key Deliverables):\n(.*?)(?=Timeline|Team of Experts|$)",
            r"\*\*(?:Deliverables|Key Deliverables):\*\*\n(.*?)(?=\*\*Timeline|\*\*Team of Experts|$)"
        ]

        deliverables_text = None
        for pattern in deliverables_patterns:
            match = re.search(pattern, project_manager_output, re.DOTALL)
            if match:
                deliverables_text = match.group(1).strip()
                break

        if deliverables_text:
            deliverables = re.findall(r'\d+\.\s*(.*)', deliverables_text)
            for deliverable in deliverables:
                current_project.add_deliverable(deliverable.strip())
                session_state.project_model.add_deliverable(deliverable.strip())
        else:
            print("Warning: 'Deliverables' or 'Key Deliverables' section not found in Project Manager's output.")

        session_state.current_project = current_project

        update_discussion_and_whiteboard("Project Manager", project_manager_output, "")
    else:
        project_manager_output = session_state.project_manager_output

    team_of_experts_patterns = [
        r"\*\*Team of Experts:\*\*\n(.*)",
        r"Team of Experts:\n(.*)"
    ]

    team_of_experts_text = None
    for pattern in team_of_experts_patterns:
        match = re.search(pattern, project_manager_output, re.DOTALL)
        if match:
            team_of_experts_text = match.group(1).strip()
            break

    if team_of_experts_text:
        autogen_agents, crewai_agents = get_agents_from_text(team_of_experts_text)

        if not autogen_agents:
            print("Error: No agents created.")
            st.warning("Failed to create agents. Please try again.")
            return

        session_state.agents = autogen_agents
        session_state.workflow.agents = session_state.agents

        # Generate the workflow data
        workflow_data, _ = get_workflow_from_agents(autogen_agents)
        workflow_data["created_at"] = datetime.datetime.now().isoformat()
        print(f"Debug: Workflow data: {workflow_data}")
        print(f"Debug: CrewAI agents: {crewai_agents}")

        if workflow_data:
            autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
            session_state.autogen_zip_buffer = autogen_zip_buffer
            session_state.crewai_zip_buffer = crewai_zip_buffer
        else:
            session_state.autogen_zip_buffer = None
            session_state.crewai_zip_buffer = None

        # Update the project session state with the workflow data
        session_state.project_model.workflows = [workflow_data]

        print("Debug: Agents in session state project workflow:")
        for agent in workflow_data["receiver"]["groupchat_config"]["agents"]:
            print(agent)

        # Indicate that a rerun is needed
        session_state.need_rerun = True
    else:
        print("Error: 'Team of Experts' section not found in Project Manager's output.")
        st.warning("Failed to extract the team of experts from the Project Manager's output. Please try again.")
        return
    

def key_prompt():
    api_key = get_api_key()
    api_key = display_api_key_input()
    if api_key is None:
        llm = LLM_PROVIDER.upper()
        st.warning(f"{llm}_API_KEY not found, or select a different provider.")
        return


def parse_json(content: str) -> List[Dict[str, Any]]:
    try:
        json_data = json.loads(content)
        if isinstance(json_data, list):
            return json_data
        else:
            print("JSON data is not a list as expected.")
            return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Content: {content}")
        return []


def rephrase_prompt(user_request, model, max_tokens=None, llm_provider=None, provider=None):
    print("Executing rephrase_prompt()")

    refactoring_prompt = get_rephrased_user_prompt(user_request)

    if llm_provider is None:
        api_key = get_api_key()
        try:
            llm_provider = get_llm_provider(api_key=api_key, provider=provider)
        except Exception as e:
            print(f"Error initializing LLM provider: {str(e)}")
            return None

    if max_tokens is None:
        max_tokens = llm_provider.get_available_models().get(model, 4096)

    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": refactoring_prompt,
            },
        ],
    }

    try:
        print("Sending request to LLM API...")
        print(f"Request Details:")
        print(f"Provider: {provider}")
        print(f"llm_provider: {llm_provider}")
        print(f" Model: {model}")
        print(f" Max Tokens: {max_tokens}")
        print(f" Messages: {llm_request_data['messages']}")

        response = llm_provider.send_request(llm_request_data)
        
        if response is None:
            print("Error: No response received from the LLM provider.")
            return None

        print(f"Response received. Processing response...")
        response_data = llm_provider.process_response(response)
        print(f"Response Data: {json.dumps(response_data, indent=2)}")

        if "choices" in response_data and len(response_data["choices"]) > 0:
            rephrased = response_data["choices"][0]["message"]["content"]
            return rephrased.strip()
        else:
            print("Error: Unexpected response format. 'choices' field missing or empty.")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def select_model():
    provider = st.session_state.get('provider', LLM_PROVIDER)
    
    if 'available_models' not in st.session_state or not st.session_state.available_models:
        fetch_available_models(provider)
    
    provider_models = st.session_state.available_models
    
    if not provider_models:
        st.warning(f"No models available for {provider}. Please check your API key and connection.")
        return None

    if 'model' not in st.session_state or st.session_state.model not in provider_models:
        default_model = next(iter(provider_models))
    else:
        default_model = st.session_state.model
    
    selected_model = st.selectbox(
        'Select Model',
        options=list(provider_models.keys()),
        index=list(provider_models.keys()).index(default_model),
        key='model_selection'
    )
    
    st.session_state.model = selected_model
    st.session_state.max_tokens = provider_models[selected_model]
    
    return selected_model


def select_provider():
    selected_provider = st.selectbox(
        'Select Provider',
        options=SUPPORTED_PROVIDERS,
        index=SUPPORTED_PROVIDERS.index(st.session_state.get('provider', LLM_PROVIDER)),
        key='provider_selection'
    )
    
    if selected_provider != st.session_state.get('provider'):
        st.session_state.provider = selected_provider
        update_api_url(selected_provider)
        
        # Clear any existing warnings
        st.session_state.warning_placeholder.empty()
        
        # Check for API key and prompt if not found
        api_key = get_api_key(selected_provider)
        if api_key is None:
            display_api_key_input(selected_provider)
        else:
            # Fetch available models for the selected provider
            fetch_available_models(selected_provider)
        
        # Clear the model selection when changing providers
        if 'model' in st.session_state:
            del st.session_state.model
        
        # Trigger a rerun to update the UI
        st.experimental_rerun()
    
    return selected_provider


def set_css():
    parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css_file = os.path.join(parent_directory, "style.css")

    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found: {os.path.abspath(css_file)}")


def set_temperature():
    def update_temperature(value):
        st.session_state.temperature = value

    temperature_slider = st.slider(
        "Set Temperature",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        key='temperature_slider',
        on_change=update_temperature,
        args=(st.session_state.temperature_slider,)
    )

    if 'temperature' not in st.session_state:
        st.session_state.temperature = temperature_slider


def show_interfaces():
    st.markdown('<div class="discussion-whiteboard">', unsafe_allow_html=True)
    display_discussion_and_whiteboard()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="user-input">', unsafe_allow_html=True)
    auto_moderate = st.checkbox("Auto-moderate (slow, eats tokens, but very cool)", key="auto_moderate", on_change=trigger_moderator_agent_if_checked)
    if auto_moderate:
        with st.spinner("Auto-moderating..."):
            moderator_response = trigger_moderator_agent()
        if moderator_response:
            if st.session_state.next_agent:
                st.session_state.user_input = f"To {st.session_state.next_agent}: {moderator_response}"
            else:
                st.session_state.user_input = moderator_response
            st.success("Auto-moderation complete. New input has been generated.")
        else:
            st.warning("Auto-moderation failed due to rate limiting. Please wait a moment and try again, or proceed manually.")
    
    user_input = st.text_area("Additional Input:", value=st.session_state.user_input, height=200, key="user_input_widget")
    reference_url = st.text_input("URL:", key="reference_url_widget")
    
    st.markdown('</div>', unsafe_allow_html=True)

    return user_input, reference_url


def trigger_moderator_agent():
    current_project = st.session_state.current_project
    goal = current_project.re_engineered_prompt
    last_speaker = st.session_state.last_agent
    last_comment = st.session_state.last_comment
    discussion_history = st.session_state.discussion_history

    deliverable_index, current_deliverable = current_project.get_next_unchecked_deliverable()
    
    if current_deliverable is None:
        if current_project.current_phase != "Deployment":
            current_project.move_to_next_phase()
            st.success(f"Moving to {current_project.current_phase} phase!")
            deliverable_index, current_deliverable = current_project.get_next_unchecked_deliverable()
        else:
            st.success("All deliverables have been completed and deployed!")
            return None

    current_phase = current_project.get_next_uncompleted_phase(deliverable_index)
    
    team_members = []
    for agent in st.session_state.agents:
        if isinstance(agent, AgentBaseModel):
            team_members.append(f"{agent.name}: {agent.description}")
        else:
            # Fallback for dictionary-like structure
            agent_name = agent.get('config', {}).get('name', agent.get('name', 'Unknown'))
            agent_description = agent.get('description', 'No description')
            team_members.append(f"{agent_name}: {agent_description}")
    team_members_str = "\n".join(team_members)

    moderator_prompt = get_moderator_prompt(discussion_history, goal, last_comment, last_speaker, team_members_str, current_deliverable, current_phase)

    for attempt in range(MAX_RETRIES):
        api_key = get_api_key()
        llm_provider = get_llm_provider(api_key=api_key)
        llm_request_data = {
            "model": st.session_state.model,
            "temperature": st.session_state.temperature,
            "max_tokens": st.session_state.max_tokens,
            "top_p": 1,
            "stop": "TERMINATE",
            "messages": [
                {
                    "role": "user",
                    "content": moderator_prompt
                }
            ]
        }
        retry_delay = RETRY_DELAY
        time.sleep(retry_delay)
        response = llm_provider.send_request(llm_request_data)

        if isinstance(response, dict) and 'choices' in response:
            # Handle response from providers like Groq
            content = response['choices'][0]['message']['content']
        elif hasattr(response, 'content') and isinstance(response.content, list):
            # Handle Anthropic-style response
            content = response.content[0].text
        else:
            print(f"Unexpected response format: {type(response)}")
            continue

        if content:
            # Extract the agent name from the content
            agent_name_match = re.match(r"To (\w+( \w+)*):", content)
            if agent_name_match:
                next_agent = agent_name_match.group(1)
                # Check if the extracted name is a valid agent and not a tool
                if any(agent.name.lower() == next_agent.lower() for agent in st.session_state.agents):
                    st.session_state.next_agent = next_agent
                    # Remove the "To [Agent Name]:" prefix from the content
                    content = re.sub(r"^To \w+( \w+)*:\s*", "", content).strip()
                else:
                    st.warning(f"'{next_agent}' is not a valid agent. Please select a valid agent.")
                    st.session_state.next_agent = None
            else:
                st.session_state.next_agent = None
            
            if "PHASE_COMPLETED" in content:
                current_project.mark_deliverable_phase_done(deliverable_index, current_phase)
                content = content.replace("PHASE_COMPLETED", "").strip()
                st.success(f"Phase {current_phase} completed for deliverable: {current_deliverable}")
            
            if "DELIVERABLE_COMPLETED" in content:
                current_project.mark_deliverable_done(deliverable_index)
                content = content.replace("DELIVERABLE_COMPLETED", "").strip()
                st.success(f"Deliverable completed: {current_deliverable}")
            
            return content.strip()

    logger.error("All retry attempts failed.")
    return None


def trigger_moderator_agent_if_checked():
    if st.session_state.get("auto_moderate", False):
        with st.spinner("Auto-moderating..."):
            moderator_response = trigger_moderator_agent()
        if moderator_response:
            st.session_state.user_input = moderator_response
            st.success("Auto-moderation complete. New input has been generated.")
        else:
            st.warning("Auto-moderation did not produce a response. Please try again or proceed manually.")
    st.experimental_rerun()


def update_api_url(provider):
    api_url_key = f"{provider.upper()}_API_URL"
    st.session_state.api_url = st.session_state.get(api_url_key)


def update_deliverable_status(index):
    current_project = st.session_state.current_project
    is_checked = st.session_state[f"deliverable_{index}"]
    if is_checked:
        for phase in current_project.implementation_phases:
            current_project.mark_deliverable_phase_done(index, phase)
    else:
        current_project.deliverables[index]["done"] = False
        for phase in current_project.implementation_phases:
            current_project.deliverables[index]["phase"][phase] = False
    st.experimental_rerun()


def update_discussion_and_whiteboard(agent_name, response, user_input):
    # Update the full discussion history
    if user_input:
        user_input_text = f"\n\nUser: {user_input}\n\n"
        st.session_state.discussion_history += user_input_text

    # Format the most recent response
    st.session_state.most_recent_response = f"{agent_name}:\n\n{response}\n\n"

    # Add the new response to the full discussion history
    st.session_state.discussion_history += st.session_state.most_recent_response

    st.session_state.last_agent = agent_name
    st.session_state.last_comment = response

    # Force a rerun to update the UI
    st.experimental_rerun()


def update_user_input():
    if st.session_state.get("auto_moderate"):
        st.session_state.user_input = st.session_state.user_input_widget_auto_moderate
    else:
        st.session_state.user_input = st.session_state.user_input_widget

```

# AutoGroq\utils\workflow_utils.py

```python
# utils/workflow_utils.py
import datetime
import streamlit as st

from configs.config import MODEL_TOKEN_LIMITS

from tools.fetch_web_content import fetch_web_content_tool
from utils.agent_utils import create_agent_data
from utils.text_utils import sanitize_text


def get_workflow_from_agents(agents):
    current_timestamp = datetime.datetime.now().isoformat()
    temperature_value = st.session_state.get('temperature', 0.3)
    selected_model = st.session_state.get('model')  # Get the selected model from session state

    workflow = {
        "name": "AutoGroq Workflow",
        "description": "Workflow auto-generated by AutoGroq.",
        "sender": {
            "type": "userproxy",
            "config": {
                "name": "userproxy",
                "llm_config": False,
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 5,
                "system_message": "You are a helpful assistant.",
                "is_termination_msg": None,
                "code_execution_config": {
                    "work_dir": None,
                    "use_docker": False
                },
                "default_auto_reply": "",
                "description": None
            },
            "timestamp": current_timestamp,
            "user_id": "default",
            "tools": []
        },
        "receiver": {
            "type": "groupchat",
            "config": {
                "name": "group_chat_manager",
                "llm_config": {
                    "config_list": [
                        {
                            "user_id": "default",
                            "timestamp": current_timestamp,
                            "model": selected_model,  # Use the selected model
                            "base_url": None,
                            "api_type": None,
                            "api_version": None,
                            "description": "OpenAI model configuration"
                        }
                    ],
                    "temperature": temperature_value,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": MODEL_TOKEN_LIMITS.get(selected_model, 4096),  # Use the selected model
                    "extra_body": None
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 10,
                "system_message": "Group chat manager",
                "is_termination_msg": None,
                "code_execution_config": None,
                "default_auto_reply": "",
                "description": None
            },
            "groupchat_config": {
                "agents": [],
                "admin_name": "Admin",
                "messages": [],
                "max_round": 10,
                "speaker_selection_method": "auto",
                "allow_repeat_speaker": True
            },
            "timestamp": current_timestamp,
            "user_id": "default",
            "tools": []
        },
        "type": "autonomous",
        "user_id": "default",
        "timestamp": current_timestamp,
        "summary_method": "last",
        "sample_tasks": [],
    }

    for index, agent in enumerate(agents):
        agent_dict = agent.to_dict()
        agent_name = agent_dict["name"]
        description = agent_dict["description"]
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        sanitized_description = sanitize_text(description)
        
        system_message = f"You are a helpful assistant that can act as {agent_name} who {sanitized_description}."
        if index == 0:
            other_agent_names = [sanitize_text(a.name).lower().replace(' ', '_') for a in agents[1:]]
            system_message += f" You are the primary coordinator who will receive suggestions or advice from all the other agents ({', '.join(other_agent_names)}). You must ensure that the final response integrates the suggestions from other agents or team members. YOUR FINAL RESPONSE MUST OFFER THE COMPLETE RESOLUTION TO THE USER'S REQUEST. When the user's request has been satisfied and all perspectives are integrated, you can respond with TERMINATE."

        agent_config = {
            "type": "assistant",
            "config": {
                "name": formatted_agent_name,
                "llm_config": {
                    "config_list": [
                        {
                            "user_id": "default",
                            "timestamp": current_timestamp,
                            "model": selected_model,  # Use the selected model
                            "base_url": None,
                            "api_type": None,
                            "api_version": None,
                            "description": "OpenAI model configuration"
                        }
                    ],
                    "temperature": temperature_value,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": MODEL_TOKEN_LIMITS.get(selected_model, 4096),  # Use the selected model
                    "extra_body": None
                },
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 8,
                "system_message": system_message,
                "is_termination_msg": None,
                "code_execution_config": None,
                "default_auto_reply": "",
                "description": None
            },
            "timestamp": current_timestamp,
            "user_id": "default",
            "tools": [],
            "role": agent_dict["role"],
            "goal": agent_dict["goal"],
            "backstory": agent_dict["backstory"]
        }

        if agent.name == "Web Content Retriever":
            agent_config['tools'] = [fetch_web_content_tool.to_dict()]

        workflow["receiver"]["groupchat_config"]["agents"].append(agent_config)



    print("Debug: Workflow agents assigned:")
    for agent in workflow["receiver"]["groupchat_config"]["agents"]:
        print(agent)

    crewai_agents = []
    for agent in agents:
        _, crewai_agent_data = create_agent_data(agent.to_dict())
        crewai_agents.append(crewai_agent_data)

    return workflow, crewai_agents

```

