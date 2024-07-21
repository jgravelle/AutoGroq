# agent_management.py

import base64
import json
import logging
import os   
import re
import requests
import streamlit as st

from configs.config import BUILT_IN_AGENTS, LLM_PROVIDER, FALLBACK_MODEL_TOKEN_LIMITS, SUPPORTED_PROVIDERS

from models.agent_base_model import AgentBaseModel
from models.tool_base_model import ToolBaseModel
from utils.api_utils import fetch_available_models, get_api_key
from utils.error_handling import log_error
from utils.tool_utils import populate_tool_models, show_tools
from utils.ui_utils import display_goal, get_llm_provider, update_discussion_and_whiteboard

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
                options=SUPPORTED_PROVIDERS,
                index=SUPPORTED_PROVIDERS.index(current_provider),
                key=f"provider_select_{edit_index}_{agent.name}"
            )

            # Fetch available models for the selected provider
            with st.spinner(f"Fetching models for {selected_provider}..."):
                provider_models = fetch_available_models(selected_provider)
            
            if not provider_models:
                st.warning(f"No models available for {selected_provider}. Using fallback list.")
                provider_models = FALLBACK_MODEL_TOKEN_LIMITS.get(selected_provider, {})

            current_model = agent.model or st.session_state.get('model', 'default')
            
            if current_model not in provider_models:
                st.warning(f"Current model '{current_model}' is not available for {selected_provider}. Please select a new model.")
                current_model = next(iter(provider_models)) if provider_models else None
            
            if provider_models:
                selected_model = st.selectbox(
                    "Model", 
                    options=list(provider_models.keys()),
                    index=list(provider_models.keys()).index(current_model) if current_model in provider_models else 0,
                    key=f"model_select_{edit_index}_{agent.name}"
                )
            else:
                st.error(f"No models available for {selected_provider}.")
                selected_model = None

        with col2:
            if st.button("Set for ALL agents", key=f"set_all_agents_{edit_index}_{agent.name}"):
                for agent in st.session_state.agents:
                    agent.config['provider'] = selected_provider
                    if 'llm_config' not in agent.config:
                        agent.config['llm_config'] = {'config_list': [{}]}
                    if not agent.config['llm_config']['config_list']:
                        agent.config['llm_config']['config_list'] = [{}]
                    agent.config['llm_config']['config_list'][0]['model'] = selected_model
                    agent.config['llm_config']['max_tokens'] = provider_models.get(selected_model, 4096)
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
                agent.config['llm_config']['max_tokens'] = provider_models.get(selected_model, 4096)
                
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
        "max_tokens": FALLBACK_MODEL_TOKEN_LIMITS.get(model, 4096),
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
