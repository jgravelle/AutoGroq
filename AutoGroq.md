# AutoGroq\agent_management.py

```python
# agent_management.py

import base64
import os
import re
import streamlit as st

from configs.config import LLM_PROVIDER, MODEL_TOKEN_LIMITS, SUPPORTED_PROVIDERS

from utils.api_utils import get_api_key
from utils.ui_utils import get_llm_provider, get_provider_models, update_discussion_and_whiteboard


def agent_button_callback(agent_index):
    # Callback function to handle state update and logic execution
    def callback():
        st.session_state['selected_agent_index'] = agent_index
        agent = st.session_state.agents[agent_index]
        agent_name = agent['config']['name'] if 'config' in agent and 'name' in agent['config'] else ''
        st.session_state['form_agent_name'] = agent_name
        st.session_state['form_agent_description'] = agent['description'] if 'description' in agent else ''
        # Directly call process_agent_interaction here if appropriate
        process_agent_interaction(agent_index)
    return callback


def construct_request(agent_name, description, user_request, user_input, rephrased_request, reference_url, tool_results):
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
    return request


def display_agents():
    if "agents" in st.session_state and st.session_state.agents and len(st.session_state.agents) > 0:
        st.sidebar.title("Your Agents")
        st.sidebar.subheader("Click to interact")
        display_agent_buttons(st.session_state.agents)
        if st.session_state.get('show_edit'):
            edit_index = st.session_state.get('edit_agent_index')
            if edit_index is not None and 0 <= edit_index < len(st.session_state.agents):
                agent = st.session_state.agents[edit_index]
                display_agent_edit_form(agent, edit_index)
            else:
                st.sidebar.warning("Invalid agent selected for editing.")
    else:
        st.sidebar.warning(f"No agents have yet been created. Please enter a new request.")
        st.sidebar.warning(f"NOTE: GPT models can only be used locally, not in the online demo.")
        st.sidebar.warning(f"ALSO: If no agents are created, do a hard reset (CTL-F5) and try switching models. LLM results can be unpredictable.")
        st.sidebar.warning(f"SOURCE:  https://github.com/jgravelle/AutoGroq\n\r\n\r https://j.gravelle.us\n\r\n\r DISCORD: https://discord.gg/DXjFPX84gs \n\r\n\r YouTube: https://www.youtube.com/playlist?list=PLPu97iZ5SLTsGX3WWJjQ5GNHy7ZX66ryP")


def display_agent_buttons(agents):
    for index, agent in enumerate(agents):
        agent_name = agent["config"]["name"] if agent["config"].get("name") else f"Unnamed Agent {index + 1}"
        col1, col2 = st.sidebar.columns([1, 4])
        with col1:
            gear_icon = "⚙️" # Unicode character for gear icon
            if st.button(
                gear_icon,
                key=f"gear_{index}",
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
            st.button(agent_name, key=f"agent_{index}", on_click=agent_button_callback(index))


def display_agent_edit_form(agent, edit_index):
    with st.expander(f"Edit Properties of {agent['config'].get('name', '')}", expanded=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            new_name = st.text_input("Name", value=agent['config'].get('name', ''), key=f"name_{edit_index}")
        with col2:
            container = st.container()
            if container.button("X", key=f"delete_{edit_index}"):
                if st.session_state.get(f"delete_confirmed_{edit_index}", False):
                    st.session_state.agents.pop(edit_index)
                    st.session_state['show_edit'] = False
                    st.experimental_rerun()
                else:
                    st.session_state[f"delete_confirmed_{edit_index}"] = True
                    st.experimental_rerun()
            if st.session_state.get(f"delete_confirmed_{edit_index}", False):
                if container.button("Confirm Deletion", key=f"confirm_delete_{edit_index}"):
                    st.session_state.agents.pop(edit_index)
                    st.session_state['show_edit'] = False
                    del st.session_state[f"delete_confirmed_{edit_index}"]
                    st.experimental_rerun()
                if container.button("Cancel", key=f"cancel_delete_{edit_index}"):
                    del st.session_state[f"delete_confirmed_{edit_index}"]
                    st.experimental_rerun()
        description_value = agent.get('new_description', agent.get('description', ''))
        
        col1, col2 = st.columns([3, 1])
        with col1:
            current_provider = agent['config'].get('provider', st.session_state.get('provider'))
            selected_provider = st.selectbox(
                "Provider",
                options=SUPPORTED_PROVIDERS,
                index=SUPPORTED_PROVIDERS.index(current_provider),
                key=f"provider_select_{edit_index}"
            )

            provider_models = get_provider_models(selected_provider)
            current_model = agent['config']['llm_config']['config_list'][0]['model']
            
            if current_model not in provider_models:
                st.warning(f"Current model '{current_model}' is not available for the selected provider. Please select a new model.")
                current_model = next(iter(provider_models))  # Set to first available model
            
            selected_model = st.selectbox(
                "Model", 
                options=list(provider_models.keys()),
                index=list(provider_models.keys()).index(current_model),
                key=f"model_select_{edit_index}"
            )
        with col2:
            if st.button("Set for ALL agents", key=f"set_all_agents_{edit_index}"):
                for agent in st.session_state.agents:
                    agent['config']['provider'] = selected_provider
                    agent['config']['llm_config']['config_list'][0]['model'] = selected_model
                    agent['config']['llm_config']['max_tokens'] = provider_models[selected_model]
                st.experimental_rerun()
        
        new_description = st.text_area("Description", value=description_value, key=f"desc_{edit_index}")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Update User Description", key=f"regenerate_{edit_index}"):
                print(f"Regenerate button clicked for agent {edit_index}")
                new_description = regenerate_agent_description(agent)
                if new_description:
                    agent['new_description'] = new_description
                    print(f"Description regenerated for {agent['config']['name']}: {new_description}")
                    st.session_state[f"regenerate_description_{edit_index}"] = True
                    description_value = new_description
                    st.experimental_rerun()
                else:
                    print(f"Failed to regenerate description for {agent['config']['name']}")
        with col2:
            if st.button("Save", key=f"save_{edit_index}"):
                agent['config']['name'] = new_name
                agent['description'] = agent.get('new_description', new_description)
                agent['config']['provider'] = selected_provider
                
                if selected_model != 'default':
                    agent['config']['llm_config']['config_list'][0]['model'] = selected_model
                    agent['config']['llm_config']['max_tokens'] = provider_models[selected_model]
                else:
                    agent['config']['llm_config']['config_list'][0]['model'] = st.session_state.model
                    agent['config']['llm_config']['max_tokens'] = MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096)
                
                st.session_state['show_edit'] = False
                if 'edit_agent_index' in st.session_state:
                    del st.session_state['edit_agent_index']
                if 'new_description' in agent:
                    del agent['new_description']
                st.session_state.agents[edit_index] = agent


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


def process_agent_interaction(agent_index):
    agent = st.session_state.agents[agent_index]
    agent_name, description = retrieve_agent_information(agent_index)
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')
    rephrased_request = st.session_state.get('rephrased_request', '')
    reference_url = st.session_state.get('reference_url', '')
    
    # Execute associated tools for the agent
    agent_tools = agent.get("tools", [])
    tool_results = {}
    for tool_name in agent_tools:
        if tool_name in st.session_state.tool_functions:
            tool_function = st.session_state.tool_functions[tool_name]
            tool_result = tool_function()
            tool_results[tool_name] = tool_result
    
    request = construct_request(agent_name, description, user_request, user_input, rephrased_request, reference_url, tool_results)
    print(f"Request: {request}")
    
    # Use the agent-specific provider and model
    provider = agent['config'].get('provider', st.session_state.get('provider', LLM_PROVIDER))
    model = agent['config']['llm_config']['config_list'][0]['model']
    api_key = get_api_key(provider)
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)
    
    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": agent['config']['llm_config'].get('max_tokens', MODEL_TOKEN_LIMITS.get(model, 4096)),
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": request
            }
        ]
    }
    print(f"Sending request to {provider} using model {model}")
    response = llm_provider.send_request(llm_request_data)
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            update_discussion_and_whiteboard(agent_name, content, user_input)
            st.session_state['form_agent_name'] = agent_name
            st.session_state['form_agent_description'] = description
            st.session_state['selected_agent_index'] = agent_index
    else:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response: {response.text}")


def regenerate_agent_description(agent):
    agent_name = agent['config']['name']
    print(f"agent_name: {agent_name}")
    agent_description = agent['description']
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
    
    provider = agent['config'].get('provider', st.session_state.get('provider', LLM_PROVIDER))
    model = agent['config']['llm_config']['config_list'][0]['model']
    api_key = get_api_key(provider)
    llm_provider = get_llm_provider(api_key=api_key, provider=provider)
    
    llm_request_data = {
        "model": model,
        "temperature": st.session_state.temperature,
        "max_tokens": agent['config']['llm_config'].get('max_tokens', MODEL_TOKEN_LIMITS.get(model, 4096)),
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
from utils.api_utils import get_api_key
from utils.auth_utils import display_api_key_input
from utils.session_utils import initialize_session_variables
from utils.tool_utils import load_tool_functions, populate_tool_models, show_tools
from utils.ui_utils import (
    display_goal, display_reset_and_upload_buttons, 
    display_user_request_input, handle_user_request, 
    select_model, select_provider, set_css, 
    set_temperature, show_interfaces
)

def main():
    if 'warning_placeholder' not in st.session_state:
        st.session_state.warning_placeholder = st.empty()
    st.title("AutoGroq™")

    set_css()
    initialize_session_variables()
    load_tool_functions()

    # Check for API key
    api_key = get_api_key()
    if api_key is None:
        display_api_key_input()

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        select_provider()
    
    with col2:
        select_model()

    with col3:
        set_temperature()
        
    with st.sidebar:
        display_agents()
        if "agents" in st.session_state and st.session_state.agents:
            display_goal()
            populate_tool_models()
            show_tools()
        else:
            st.empty()  

    with st.container():
        if st.session_state.get("rephrased_request", "") == "":
            user_request = st.text_input("Enter your request:", key="user_request", value=st.session_state.get("user_request", ""), on_change=handle_user_request, args=(st.session_state,))
            display_user_request_input()
        if "agents" in st.session_state and st.session_state.agents:
            show_interfaces()
            display_reset_and_upload_buttons()

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
    return f"""
        This agent is an expert system designed to format the JSON describing each member of the team 
        of AI agents specifically listed in this provided text: $text.
        Fulfill the following guidelines without ever explicitly stating them in this agent's response.
        Guidelines:
        1. **Agent Roles**: Clearly transcribe the titles of each agent listed in the provided text 
            by iterating through the 'Team of Experts:' section of the provided text. Transcribe 
            the info for those specific agents. Do not create new agents.
        2. **Expertise Description**: Provide a brief but thorough description of each agent's expertise 
            based upon the provided text. Do not create new agents.
        3. **Format**: Return the results in JSON format with values labeled as expert_name, and description.
            'expert_name' should be the agent's title, not their given or proper name.

        ALWAYS and ONLY return the results in the following JSON format, with no other narrative, commentary, synopsis, 
        or superfluous text of any kind:
        [
            {{
                "expert_name": "agent_title",
                "description": "agent_description",
            }}
        ]
        This agent will only have been successful if it has returned the results in the above format 
        and followed these guidelines precisely by transcribing the provided text and returning the results 
        in JSON format without any other narrative, commentary, synopsis, or superfluous text of any kind, 
        and taking care to only transcribe the agents from the provided text without creating new agents.
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


def get_moderator_prompt(discussion_history, goal, last_comment, last_speaker,team_members_str): 
    return f"""
        This agent is our Moderator Bot. It's goal is to mediate the conversation between a team of AI agents 
        in a manner that persuades them to act in the most expeditious and thorough manner to accomplish their goal. 
        This will entail considering the user's stated goal, the conversation thus far, the descriptions 
        of all the available agent/experts in the current team, the last speaker, and their remark. 
        Based upon a holistic analysis of all the facts at hand, use logic and reasoning to decide who should speak next. 
        Then draft a prompt directed at that agent that persuades them to act in the most expeditious and thorough manner toward helping this team of agents 
        accomplish their goal.\n\nTheir goal is: {goal}.\nThe last speaker was {last_speaker}, who said: 
        {last_comment}\nHere is the current conversational discussion history: {discussion_history}\n
        And here are the team members and their descriptions:\n{team_members_str}\n\n
        This agent's response should be JUST the requested prompt addressed to the next agent, and should not contain 
        any introduction, narrative, or any other superfluous text whatsoever.
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
            "system_message": f"You are a helpful assistant that can act as {request} who {sanitize_text(agent_description)}.",
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
        "claude-3-5-sonnet-20240620": 200000, 
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
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
        "claude-3-5-sonnet-20240620": 200000,
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
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

    def add_deliverable(self, deliverable):
        self.deliverables.append({"text": deliverable, "done": False})


    def mark_deliverable_done(self, index):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = True


    def mark_deliverable_undone(self, index):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False


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
    def __init__(self, api_key, api_url=None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.api_url = api_url 

    def send_request(self, data):
        try:
            response = self.client.messages.create(
                model=data['model'],
                max_tokens=data.get('max_tokens', 1000),
                temperature=data.get('temperature', st.session_state.temperature),
                messages=data['messages']
            )
            return response
        except anthropic.APIError as e:
            print(f"Anthropic API error: {e}")
            return None

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
```

# AutoGroq\llm_providers\fireworks_provider.py

```python

import json
import requests

from llm_providers.base_provider import BaseLLMProvider
from utils.auth_utils import get_api_key


class FireworksProvider(BaseLLMProvider):
    def __init__(self, api_url):
        self.api_key = get_api_key()
        self.api_url = api_url


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

class GroqProvider(BaseLLMProvider):
    def __init__(self, api_url, api_key):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

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

# AutoGroq\llm_providers\lmstudio_provider.py

```python

import json
import requests

from llm_providers.base_provider import BaseLLMProvider

class LmstudioProvider(BaseLLMProvider):
    def __init__(self, api_url, api_key=None):
        self.api_url = "http://localhost:1234/v1/chat/completions"

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
import json
import requests
import streamlit as st

from llm_providers.base_provider import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    def __init__(self, api_url, api_key=None):
        self.api_url = "http://127.0.0.1:11434/api/generate"

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

class OpenaiProvider(BaseLLMProvider):
    def __init__(self, api_url, api_key):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"

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

from models.tool_base_model import ToolBaseModel
from typing import List, Dict, Optional, Callable


class AgentBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        tools: List[Dict],
        config: Dict,
        role: str,
        goal: str,
        backstory: str,
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
        self.tools = [ToolBaseModel(**tool) for tool in tools]
        self.config = config
        self.role = role
        self.goal = goal
        self.backstory = backstory
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


    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tools": [tool.to_dict() for tool in self.tools],
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
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            tools=data["tools"],
            config=data["config"],
            role=data.get("role", ""),
            goal=data.get("goal", ""),
            backstory=data.get("backstory", ""),
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

from typing import List, Dict, Optional

class ToolBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        title: str,
        file_name: str,
        content: str,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        secrets: Optional[Dict] = None, # Optional[Dict] means it can be a dictionary or None
        libraries: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.title = title
        self.file_name = file_name
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.secrets = secrets
        self.libraries = libraries
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "title": self.title,
            "file_name": self.file_name,
            "content": self.content,
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

# AutoGroq\tools\document_indexer.py

```python
#  Thanks to MADTANK:  https://github.com/madtank
#  README:  https://github.com/madtank/autogenstudio-skills/blob/main/rag/README.md

import argparse
import bs4
import csv
import json
import os
import pickle
import re
import traceback
from typing import Dict, List, Literal, Tuple

try:
    import tiktoken
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
except ImportError:
    raise ImportError("Please install the dependencies first.")


def chunk_str_overlap(
    s: str,
    separator: chr = "\n",
    num_tokens: int = 64,
    step_tokens: int = 64,
    encoding: tiktoken.Encoding = None,
) -> List[str]:
    """
    Split a string into chunks with overlap
    :param s: the input string
    :param separator: the separator to split the string
    :param num_tokens: the number of tokens in each chunk
    :param step_tokens: the number of tokens to step forward
    :param encoding: the encoding to encode the string
    """
    assert step_tokens <= num_tokens, (
        f"The number of tokens {num_tokens} in each chunk " f"should be larger than the step size {step_tokens}."
    )

    lines = s.split(separator)
    chunks = dict()
    final_chunks = []

    if len(lines) == 0:
        return []

    first_line = lines[0]
    first_line_size = len(encoding.encode(first_line))

    chunks[0] = [first_line, first_line_size]

    this_step_size = first_line_size

    for i in range(1, len(lines)):
        line = lines[i]
        line_size = len(encoding.encode(line))

        to_pop = []
        for key in chunks:
            if chunks[key][1] + line_size > num_tokens:
                to_pop.append(key)
            else:
                chunks[key][0] += f"{separator}{line}"
                chunks[key][1] += line_size
        final_chunks += [chunks.pop(key)[0] for key in to_pop]

        if this_step_size + line_size > step_tokens:
            chunks[i] = [line, line_size]
            this_step_size = 0
        this_step_size += line_size

    max_remained_chunk = ""
    max_remained_chunk_size = 0
    for key in chunks:
        if chunks[key][1] > max_remained_chunk_size:
            max_remained_chunk_size = chunks[key][1]
            max_remained_chunk = chunks[key][0]
    if max_remained_chunk_size > 0:
        final_chunks.append(max_remained_chunk)

    return final_chunks


def get_title(
    file_name: str,
    prop="title: ",
) -> str:
    """
    Get the title of a file
    :param file_name: the file name
    :param prop: the property to get the title
    """
    with open(file_name, encoding="utf-8", errors="ignore") as f_in:
        for line in f_in:
            line = line.strip()
            if line and (line.startswith(prop) or any([c.isalnum() for c in line])):
                return line
    return ""


def extract_text_from_file(
    file: str,
    file_type: Literal["pdf", "docx", "csv", "pptx"],
) -> Tuple[str, str]:
    """
    Extract text from a file in pdf, docx, csv or pptx format
    :param file: the file path
    :param file_type: the extension of the file
    """
    if file_type == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("Please install pypdf first.")
        # Extract text from pdf using PyPDF2
        reader = PdfReader(file)
        extracted_text = " ".join([page.extract_text() for page in reader.pages])
        title = extracted_text.split("\n")[0]
    elif file_type == "docx":
        try:
            import docx2txt
        except ImportError:
            raise ImportError("Please install docx2txt first.")
        # Extract text from docx using docx2txt
        extracted_text = docx2txt.process(file)
        title = extracted_text.split("\n")[0]
    elif file_type == "csv":
        # Extract text from csv using csv module
        extracted_text = ""
        title = ""
        reader = csv.reader(file)
        for row in reader:
            extracted_text += " ".join(row) + "\n"
    elif file_type == "pptx":
        try:
            import pptx
        except ImportError:
            raise ImportError("Please install python-pptx first.")
        extracted_text = ""
        no_title = True
        title = ""
        presentation = pptx.Presentation(file)
        for slide in presentation.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            extracted_text += run.text + " "
                            if no_title and len(run.text) > 10:
                                title = run.text
                                no_title = False
                    extracted_text += "\n"
    else:
        # Unsupported file type
        raise ValueError(f"Unsupported file type: {file_type}")

    return title[:100], extracted_text


def text_parser(
    read_file: str,
) -> Tuple[str, str]:
    """
    Returns the title, parsed text and a BeautifulSoup object with different file extension
    : param read_file: the input file with a given extension
    : return: the title, parsed text and a BeautifulSoup object, the BeautifulSoup object is used to get the document
        link from the html files
    """
    filename, extension = os.path.splitext(read_file)
    extension = extension.lstrip(".")
    title = filename
    soup = None
    supported_extensions = ["md", "markdown", "html", "htm", "txt", "json", "jsonl"]
    other_extensions = ["docx", "pptx", "pdf", "csv"]

    # utf-8-sig will treat BOM header as a metadata of a file not a part of the file content
    default_encoding = "utf-8-sig"

    if extension in ("md", "markdown", "txt"):
        title = get_title(read_file)
        with open(read_file, "r", encoding=default_encoding, errors="ignore") as f:
            text = f.read()
    elif extension in ("html", "htm"):
        from bs4 import BeautifulSoup

        with open(read_file, "r", encoding=default_encoding, errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")
        title = next(soup.stripped_strings)[:100]
        text = soup.get_text("\n")
    # read json/jsonl file in and convert each json to a row of string
    elif extension in ("json", "jsonl"):
        try:
            with open(read_file, "r", encoding=default_encoding, errors="ignore") as f:
                data = json.load(f) if extension == "json" else [json.loads(line) for line in f]
        except:
            # json file encoding issue, skip this file
            return title, ""

        if isinstance(data, dict):
            text = json.dumps(data)
        elif isinstance(data, list):
            content_list = [json.dumps(each_json) for each_json in data]
            text = "\n".join(content_list)
            title = filename
    elif extension in other_extensions:
        title, text = extract_text_from_file(read_file, extension)
    else:  # no support for other format
        print(
            f"Not support for file with extension: {extension}. "
            f"The supported extensions are {supported_extensions}",
        )
        return title, ""

    output_text = re.sub(r"\n{3,}", "\n\n", text)
    # keep whitespaces for formatting
    output_text = re.sub(r"-{3,}", "---", output_text)
    output_text = re.sub(r"\*{3,}", "***", output_text)
    output_text = re.sub(r"_{3,}", "___", output_text)

    return title, output_text


def chunk_document(
    doc_path: str,
    chunk_size: int,
    chunk_step: int,
) -> Tuple[int, List[str], List[Dict[str, str]], Dict[str, int]]:
    """
    Split documents into chunks
    :param doc_path: the path of the documents
    :param chunk_size: the size of the chunk
    :param chunk_step: the step size of the chunk
    """
    texts = []
    metadata_list = []
    file_count = 0
    chunk_id_to_index = dict()

    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

    # traverse all files under dir
    print("Split documents into chunks...")
    for root, dirs, files in os.walk(doc_path):
        for name in files:
            f = os.path.join(root, name)
            print(f"Reading {f}")
            try:
                title, content = text_parser(f)
                file_count += 1
                if file_count % 100 == 0:
                    print(f"{file_count} files read.")

                if len(content) == 0:
                    continue

                chunks = chunk_str_overlap(
                    content.strip(),
                    num_tokens=chunk_size,
                    step_tokens=chunk_step,
                    separator="\n",
                    encoding=enc,
                )
                source = os.path.sep.join(f.split(os.path.sep)[4:])
                for i in range(len(chunks)):
                    # custom metadata if needed
                    metadata = {
                        "source": source,
                        "title": title,
                        "chunk_id": i,
                    }
                    chunk_id_to_index[f"{source}_{i}"] = len(texts) + i
                    metadata_list.append(metadata)
                texts.extend(chunks)
            except Exception as e:
                print(f"Error encountered when reading {f}: {traceback.format_exc()} {e}")
    return file_count, texts, metadata_list, chunk_id_to_index


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--doc_path",
        help="the path of the documents",
        type=str,
        default="documents",
    )
    parser.add_argument(
        "-c",
        "--chunk_size",
        help="the size of the chunk",
        type=int,
        default=64,
    )
    parser.add_argument(
        "-s",
        "--chunk_step",
        help="the step size of the chunk",
        type=int,
        default=64,
    )
    parser.add_argument(
        "-o",
        "--output_path",
        help="the path of the output",
        type=str,
        default="knowledge",
    )
    args = parser.parse_args()

    file_count, texts, metadata_list, chunk_id_to_index = chunk_document(
        doc_path=args.doc_path,
        chunk_size=args.chunk_size,
        chunk_step=args.chunk_step,
    )
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(
        texts=texts,
        metadatas=metadata_list,
        embedding=embeddings,
    )
    vectorstore.save_local(folder_path=args.output_path)
    with open(os.path.join(args.output_path, "chunk_id_to_index.pkl"), "wb") as f:
        pickle.dump(chunk_id_to_index, f)
    print(f"Saved vectorstore to {args.output_path}")
```

# AutoGroq\tools\document_retriever.py

```python
# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/rag/README.md

# import os
# import pickle
# import json
# import argparse

# try:
#     import tiktoken
#     from langchain_community.embeddings import HuggingFaceEmbeddings
#     from langchain_community.vectorstores import FAISS
# except ImportError:
#     raise ImportError("Please install langchain-community first.")

# # Configuration - Users/AI skill developers must update this path to their specific index folder
# # To test with sample data set index_folder to "knowledge"
# CONFIG = {
#     "index_folder": "rag/knowledge",  # TODO: Update this path before using
# }

# class DocumentRetriever:
#     def __init__(self, index_folder):
#         self.index_folder = index_folder
#         self.vectorstore = None
#         self.chunk_id_to_index = None
#         self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
#         self._init()
#         self.enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

#     def _init(self):
#         self.vectorstore = FAISS.load_local(
#             folder_path=self.index_folder,
#             embeddings=self.embeddings,
#         )
#         with open(os.path.join(self.index_folder, "chunk_id_to_index.pkl"), "rb") as f:
#             self.chunk_id_to_index = pickle.load(f)

#     def __call__(self, query: str, size: int = 5, target_length: int = 256):
#         if self.vectorstore is None:
#             raise Exception("Vectorstore not initialized")

#         result = self.vectorstore.similarity_search(query=query, k=size)
#         expanded_chunks = self.do_expand(result, target_length)

#         return json.dumps(expanded_chunks, indent=4)

#     def do_expand(self, result, target_length):
#         expanded_chunks = []
#         # do expansion
#         for r in result:
#             source = r.metadata["source"]
#             chunk_id = r.metadata["chunk_id"]
#             content = r.page_content

#             expanded_result = content
#             left_chunk_id, right_chunk_id = chunk_id - 1, chunk_id + 1
#             left_valid, right_valid = True, True
#             chunk_ids = [chunk_id]
#             while True:
#                 current_length = len(self.enc.encode(expanded_result))
#                 if f"{source}_{left_chunk_id}" in self.chunk_id_to_index:
#                     chunk_ids.append(left_chunk_id)
#                     left_chunk_index = self.vectorstore.index_to_docstore_id[
#                         self.chunk_id_to_index[f"{source}_{left_chunk_id}"]
#                     ]
#                     left_chunk = self.vectorstore.docstore.search(left_chunk_index)
#                     encoded_left_chunk = self.enc.encode(left_chunk.page_content)
#                     if len(encoded_left_chunk) + current_length < target_length:
#                         expanded_result = left_chunk.page_content + expanded_result
#                         left_chunk_id -= 1
#                         current_length += len(encoded_left_chunk)
#                     else:
#                         expanded_result += self.enc.decode(
#                             encoded_left_chunk[-(target_length - current_length) :],
#                         )
#                         current_length = target_length
#                         break
#                 else:
#                     left_valid = False

#                 if f"{source}_{right_chunk_id}" in self.chunk_id_to_index:
#                     chunk_ids.append(right_chunk_id)
#                     right_chunk_index = self.vectorstore.index_to_docstore_id[
#                         self.chunk_id_to_index[f"{source}_{right_chunk_id}"]
#                     ]
#                     right_chunk = self.vectorstore.docstore.search(right_chunk_index)
#                     encoded_right_chunk = self.enc.encode(right_chunk.page_content)
#                     if len(encoded_right_chunk) + current_length < target_length:
#                         expanded_result += right_chunk.page_content
#                         right_chunk_id += 1
#                         current_length += len(encoded_right_chunk)
#                     else:
#                         expanded_result += self.enc.decode(
#                             encoded_right_chunk[: target_length - current_length],
#                         )
#                         current_length = target_length
#                         break
#                 else:
#                     right_valid = False

#                 if not left_valid and not right_valid:
#                     break

#             expanded_chunks.append(
#                 {
#                     "chunk": expanded_result,
#                     "metadata": r.metadata,
#                     # "length": current_length,
#                     # "chunk_ids": chunk_ids
#                 },
#             )
#         return expanded_chunks

# # Example Usage
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description='Retrieve documents based on a query.')
#     parser.add_argument('query', nargs='?', type=str, help='The query to retrieve documents for.')
#     args = parser.parse_args()

#     if not args.query:
#         parser.print_help()
#         print("Error: No query provided.")
#         exit(1)

#     # Ensure the index_folder path is correctly set in CONFIG before proceeding
#     index_folder = CONFIG["index_folder"]
#     if index_folder == "path/to/your/knowledge/directory":
#         print("Error: Index folder in CONFIG has not been set. Please update it to your index folder path.")
#         exit(1)

#     # Instantiate and use the DocumentRetriever with the configured index folder
#     retriever = DocumentRetriever(index_folder=index_folder)
#     query = args.query
#     size = 5  # Number of results to retrieve
#     target_length = 256  # Target length of expanded content
#     results = retriever(query, size, target_length)
#     print(results)
```

# AutoGroq\tools\fetch_web_content.py

```python
#  Thanks to MADTANK:  https://github.com/madtank

from typing import Optional
import requests
import collections
collections.Callable = collections.abc.Callable
from bs4 import BeautifulSoup

def fetch_web_content(url: str) -> Optional[str]:
    """
    Fetches the text content from a website.

    Args:
        url (str): The URL of the website.

    Returns:
        Optional[str]: The content of the website.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)

        # Check for successful access to the webpage
        if response.status_code == 200:
            # Parse the HTML content of the page using BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract the content of the <body> tag
            body_content = soup.body

            if body_content:
                # Return all the text in the body tag, stripping leading/trailing whitespaces
                return " ".join(body_content.get_text(strip=True).split())
            else:
                # Return None if the <body> tag is not found
                return None
        else:
            # Return None if the status code isn't 200 (success)
            return None
    except requests.RequestException:
        # Return None if any request-related exception is caught
        return None
```

# AutoGroq\tools\generate_sd_images.py

```python
# Thanks to marc-shade:  https://github.com/marc-shade
# Ollama only?  -jjg

from typing import List
import json
import requests
import io
import base64
from PIL import Image
from pathlib import Path
import uuid # Import the uuid library

# Format: protocol://server:port
base_url = "http://0.0.0.0:7860"

def generate_sd_images(query: str, image_size: str = "512x512", team_name: str = "default") -> List[str]:
    """
    Function to paint, draw or illustrate images based on the users query or request. 
    Generates images locally with the automatic1111 API and saves them to disk.  
    Use the code below anytime there is a request to create an image.

    :param query: A natural language description of the image to be generated.
    :param image_size: The size of the image to be generated. (default is "512x512")
    :param team_name: The name of the team to associate the image with.
    :return: A list containing a single filename for the saved image.
    """
    # Split the image size string at "x"
    parts = image_size.split("x")
    image_width = parts[0]
    image_height = parts[1]

    # list of file paths returned to AutoGen
    saved_files = []

    payload = {
        "prompt": query,
        "steps": 40,
        "cfg_scale": 7,
        "denoising_strength": 0.5,
        "sampler_name": "DPM++ 2M Karras",
        "n_iter": 1,
        "batch_size": 1, # Ensure only one image is generated per batch
        "override_settings": {
             'sd_model_checkpoint': "starlightAnimated_v3",
        }
    }

    api_url = f"{base_url}/sdapi/v1/txt2img"
    response = requests.post(url=api_url, json=payload)

    if response.status_code == 200:
        r = response.json()
        # Access only the final generated image (index 0)
        encoded_image = r['images'][0] 

        image = Image.open(io.BytesIO(base64.b64decode(encoded_image.split(",", 1)[0])))
        
        # --- Generate a unique filename with team name and UUID ---
        unique_id = str(uuid.uuid4())[:8] # Get a short UUID
        file_name = f"images/{team_name}_{unique_id}_output.png"
        
        file_path = Path(file_name)
        image.save(file_path)
        print(f"Image saved to {file_path}")

        saved_files.append(str(file_path))
    else:
        print(f"Failed to download the image from {api_url}")

    return saved_files
```

# AutoGroq\tools\get_complementary_colors.py

```python
# Tool filename: complementary_colors.py
# Import necessary module(s)
import colorsys

def get_complementary_colors(color):
    # docstrings
    """
    Returns a list of complementary colors for the given color.

    Parameters:
    color (str): The color in hexadecimal format (e.g., '#FF0000' for red).

    Returns:
    list: A list of complementary colors in hexadecimal format.
    """

    # Body of tool
    # Convert the color from hexadecimal to RGB
    r, g, b = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    # Convert RGB to HSV
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    # Calculate the complementary hue
    h_compl = (h + 0.5) % 1
    # Convert the complementary hue back to RGB
    r_compl, g_compl, b_compl = colorsys.hsv_to_rgb(h_compl, 1, 1)
    # Convert RGB to hexadecimal
    color_compl = '#{:02x}{:02x}{:02x}'.format(int(r_compl*255), int(g_compl*255), int(b_compl*255))
    # Return the complementary color
    return [color_compl]

    # Example usage:
    # color = '#FF0000'
    # print(get_complementary_colors(color))
```

# AutoGroq\tools\get_weather.py

```python
import requests
from typing import Optional

def get_weather(zipcode: str, api_key: str) -> Optional[dict]:
    """
    Fetches the current weather for the given ZIP code using the OpenWeatherMap API.

    Args:
        zipcode (str): The ZIP code for which to fetch the weather.
        api_key (str): Your OpenWeatherMap API key.

    Returns:
        Optional[dict]: A dictionary containing the weather information, or None if an error occurs.
    """
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "zip": zipcode,
        "appid": api_key,
        "units": "imperial"  # Use "metric" for Celsius
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

# Example usage:
# api_key = "your_openweathermap_api_key"
# weather = get_weather("94040", api_key)
# print(weather)

```

# AutoGroq\tools\plot_diagram.py

```python
#  Thanks to MADTANK:  https://github.com/madtank

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Function to draw the geometric structure with customizable file name
def draw_geometric_structure(file_name, base_circles=4, base_circle_color='blue', top_circle_color='orange', line_color='grey', line_width=2):

    # Define the directory and save path using the file_name parameter
    directory = 'diagrams'
    if not os.path.exists(directory):
        os.makedirs(directory)
    save_path = f'{directory}/{file_name}.png'
    
    fig, ax = plt.subplots()

    # Draw base circles
    for i in range(base_circles):
        circle = patches.Circle((i * 1.5, 0), 0.5, color=base_circle_color)
        ax.add_patch(circle)

    # Draw top circle
    top_circle = patches.Circle(((base_circles - 1) * 0.75, 2), 0.6, color=top_circle_color)
    ax.add_patch(top_circle)

    # Draw lines
    for i in range(base_circles):
        line = plt.Line2D([(i * 1.5), ((base_circles - 1) * 0.75)], [0, 2], color=line_color, linewidth=line_width)
        ax.add_line(line)

    # Set limits and aspect
    ax.set_xlim(-1, base_circles * 1.5)
    ax.set_ylim(-1, 3)
    ax.set_aspect('equal')

    # Remove axes
    ax.axis('off')

    # Save the plot to the specified path
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
    plt.close()

    # Return the path for verification
    return save_path

# Example usage:
#file_name = 'custom_geometric_structure'
#image_path = draw_geometric_structure(file_name, base_circles=8, base_circle_color='blue', top_circle_color='orange', line_color='grey', line_width=2)
```

# AutoGroq\tools\save_file_to_disk.py

```python
# Thanks to aj47:  https://github.com/aj47

import os

def save_file_to_disk(contents, file_name):
    """
    Saves the given contents to a file with the given file name.

    Parameters:
    contents (str): The string contents to save to the file.
    file_name (str): The name of the file, including its extension.

    Returns:
    str: A message indicating the success of the operation.
    """
    # Ensure the directory exists; create it if it doesn't
    directory = os.path.dirname(file_name)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # Write the contents to the file
    with open(file_name, 'w') as file:
        file.write(contents)
    
    return f"File '{file_name}' has been saved successfully."

# Example usage:
# contents_to_save = "Hello, world!"
# file_name = "example.txt"
# print(save_file_to_disk(contents_to_save, file_name))
```

# AutoGroq\tools\slackoverflow_teams.py

```python
# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/stackoverflow_teams/README.md

# import os
# import requests
# import json
# import sys

# class StackOverflowTeamsSearcher:
#     def __init__(self):
#         self.api_key = os.getenv("STACK_OVERFLOW_TEAMS_API_KEY")
#         if not self.api_key:
#             raise ValueError("API key not found in environment variables")
#         self.base_url = "https://api.stackoverflowteams.com/2.3/search"
#         self.headers = {"X-API-Access-Token": self.api_key}

#     def search(self, query, team_name):
#         params = {"intitle": query, "team": team_name}
#         response = requests.get(self.base_url, headers=self.headers, params=params)

#         if response.status_code != 200:
#             print(f"Error: Received status code {response.status_code}")
#             print(response.text)
#             return None

#         try:
#             data = response.json()
#             simplified_output = []
#             for item in data['items']:
#                 question = {"question": item['title']}
#                 if 'accepted_answer_id' in item:
#                     answer_id = item['accepted_answer_id']
#                     answer_url = f"https://api.stackoverflowteams.com/2.3/answers/{answer_id}"
#                     answer_params = {"team": team_name, "filter": "withbody"}
#                     answer_response = requests.get(answer_url, headers=self.headers, params=answer_params)
#                     if answer_response.status_code == 200:
#                         answer_data = answer_response.json()
#                         first_item = answer_data['items'][0]
#                         if 'body' in first_item:
#                             answer_text = first_item['body']
#                             question['answer'] = answer_text
# #                        else:
# #                            print(f"Question {item['link']} has no answer body")
# #                    else:
# #                        print(f"Error: Received status code {answer_response.status_code}")
# #                        print(answer_response.text)
# #                else:
# #                    print(f"Question {item['link']} has no answer")
#                 simplified_output.append(question)
#             return json.dumps(simplified_output, indent=4)  # Pretty-printing
#         except ValueError as e:
#             print(f"Error parsing JSON: {e}")
#             print("Response text:", response.text)
#             return None

# # Example Usage
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python stackoverflow_teams.py <query>")
#         sys.exit(1)

#     query = sys.argv[1]
#     team_name = "yourteamname"  # TODO Set your team name here
#     # Instantiate and use the StackOverflowTeamsSearcher with the query string passed in
#     searcher = StackOverflowTeamsSearcher()
#     results = searcher.search(query, team_name)
#     print(results)
```

# AutoGroq\tools\slack_search.py

```python
# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/slack/README.md

# import os
# import requests
# import json
# import re
# import sys

# class SlackSearcher:
#     def __init__(self):
#         self.api_token = os.getenv("SLACK_API_TOKEN")
#         if not self.api_token:
#             raise ValueError("Slack API token not found in environment variables")
#         self.base_url = "https://slack.com/api"
#         self.headers = {"Authorization": f"Bearer {self.api_token}"}
#         # Replace these example channel names with the actual channel names you want to search
#         self.channel_names = ["general", "random"]

#     def search(self, query):
#         query_with_channels = self.build_query_with_channels(query)
#         search_url = f"{self.base_url}/search.messages"
#         params = {"query": query_with_channels}
#         response = requests.get(search_url, headers=self.headers, params=params)

#         if response.status_code != 200:
#             print(f"Error: Received status code {response.status_code}")
#             print(response.text)
#             return None

#         try:
#             data = response.json()
#             if not data['ok']:
#                 print(f"Error: {data['error']}")
#                 return None

#             simplified_output = []
#             for message in data['messages']['matches']:
#                 simplified_message = {
#                     "user": message['user'],
#                     "text": message['text'],
#                     "permalink": message['permalink']
#                 }
#                 thread_ts = self.extract_thread_ts(message['permalink'])
#                 if thread_ts:
#                     thread_messages = self.get_thread_messages(message['channel']['id'], thread_ts)
#                     simplified_message['thread'] = thread_messages
#                 simplified_output.append(simplified_message)
#             return json.dumps(simplified_output, indent=4)  # Pretty-printing
#         except ValueError as e:
#             print(f"Error parsing JSON: {e}")
#             print("Response text:", response.text)
#             return None

#     def build_query_with_channels(self, query):
#         channel_queries = [f"in:{channel}" for channel in self.channel_names]
#         return f"{query} {' '.join(channel_queries)}"

#     def extract_thread_ts(self, permalink):
#         match = re.search(r"thread_ts=([0-9.]+)", permalink)
#         return match.group(1) if match else None

#     def get_thread_messages(self, channel_id, thread_ts):
#         thread_url = f"{self.base_url}/conversations.replies"
#         params = {"channel": channel_id, "ts": thread_ts}
#         response = requests.get(thread_url, headers=self.headers, params=params)

#         if response.status_code != 200 or not response.json()['ok']:
#             print(f"Error fetching thread messages: {response.text}")
#             return []

#         thread_messages = []
#         for message in response.json()['messages']:
#             if message['ts'] != thread_ts:  # Exclude the parent message
#                 thread_messages.append({
#                     "user": message['user'],
#                     "text": message['text']
#                 })
#         return thread_messages

# # Example Usage
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python slack_search.py <query>")
#         sys.exit(1)

#     query = sys.argv[1]
#     searcher = SlackSearcher()
#     results = searcher.search(query)
#     print(results)
```

# AutoGroq\tools\test.py

```python
# bfrglz; = 
# return

# import json
```

# AutoGroq\tools\webscrape.py

```python
#  Thanks to MADTANK:  https://github.com/madtank

import requests
from bs4 import BeautifulSoup


def save_webpage_as_text(url, output_filename):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Initialize BeautifulSoup to parse the content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract text from the BeautifulSoup object
    # You can adjust the elements you extract based on your needs
    text = soup.get_text(separator='\n', strip=True)
    
    # Save the extracted text to a file
    with open(output_filename, 'w', encoding='utf-8') as file:
        file.write(text)
    
    # Return the file path
    return output_filename


# Example usage:
# url = 'https://j.gravelle.us        /'
# output_filename = 'webpage_content.txt'
# file_path = save_webpage_as_text(url, output_filename)
# print("File saved at:", file_path)


# For a list of urls:
# urls = ['http://example.com', 'http://example.org']
# for i, url in enumerate(urls):
#     output_filename = f'webpage_content_{i}.txt'
#     save_webpage_as_text(url, output_filename)
```

# AutoGroq\tools\web_search.py

```python
# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/web_search/README.MD

# import requests
# from typing import List, Tuple, Optional

# # Define the structure of a search result entry
# ResponseEntry = Tuple[str, str, str]

# # Configuration variables for the web search function
# CONFIG = {
#     "api_provider": "google",  # or "bing"
#     "result_count": 3,
#     # For Google Search enter these values 
#     # Refer to readme for help:  https://github.com/madtank/autogenstudio-skills/blob/main/web_search/README.MD 
#     "google_api_key": "your_google_api_key_here",
#     "google_search_engine_id": "your_google_search_engine_id_here",
#     # Or Bing Search enter these values
#     "bing_api_key": "your_bing_api_key_here"
# }

# class WebSearch:
#     """
#     A class that encapsulates the functionality to perform web searches using
#     Google Custom Search API or Bing Search API based on the provided configuration.
#     """

#     def __init__(self, config: dict):
#         """
#         Initializes the WebSearch class with the provided configuration.

#         Parameters:
#         - config (dict): A dictionary containing configuration settings.
#         """
#         self.config = config

#     def search_query(self, query: str) -> Optional[List[ResponseEntry]]:
#         """
#         Performs a web search based on the query and configuration.

#         Parameters:
#         - query (str): The search query string.

#         Returns:
#         - A list of ResponseEntry tuples containing the title, URL, and snippet of each result.
#         """
#         api_provider = self.config.get("api_provider", "google")
#         result_count = int(self.config.get("result_count", 3))
#         try:
#             if api_provider == "google":
#                 return self._search_google(query, cnt=result_count)
#             elif api_provider == "bing":
#                 return self._search_bing(query, cnt=result_count)
#         except ValueError as e:
#             print(f"An error occurred: {e}")
#         except Exception as e:
#             print(f"An unexpected error occurred: {e}")
#         return None

#     def _search_google(self, query: str, cnt: int) -> Optional[List[ResponseEntry]]:
#         """
#         Performs a Google search and processes the results.
#         Parameters:
#         - query (str): The search query string.
#         - cnt (int): The number of search results to return.

#         Returns:
#         - A list of ResponseEntry tuples containing the title, URL, and snippet of each Google search result.
#         """
#         api_key = self.config.get("google_api_key")
#         search_engine_id = self.config.get("google_search_engine_id")
#         url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={query}"
#         if cnt > 0:
#             url += f"&num={cnt}"
#         response = requests.get(url)
#         if response.status_code == 200:
#             result_list: List[ResponseEntry] = []
#             for item in response.json().get("items", []):
#                 result_list.append((item["title"], item["link"], item["snippet"]))
#             return result_list
#         else:
#             print(f"Error with Google Custom Search API: {response.status_code}")
#             return None

#     def _search_bing(self, query: str, cnt: int) -> Optional[List[ResponseEntry]]:
#         """
#         Performs a Bing search and processes the results.

#         Parameters:
#         - query (str): The search query string.
#         - cnt (int): The number of search results to return.

#         Returns:
#         - A list of ResponseEntry tuples containing the name, URL, and snippet of each Bing search result.
#         """
#         api_key = self.config.get("bing_api_key")
#         url = f"https://api.bing.microsoft.com/v7.0/search?q={query}"
#         if cnt > 0:
#             url += f"&count={cnt}"
#         headers = {"Ocp-Apim-Subscription-Key": api_key}
#         response = requests.get(url, headers=headers)
#         if response.status_code == 200:
#             result_list: List[ResponseEntry] = []
#             for item in response.json().get("webPages", {}).get("value", []):
#                 result_list.append((item["name"], item["url"], item["snippet"]))
#             return result_list
#         else:
#             print(f"Error with Bing Search API: {response.status_code}")
#             return None

# # Remember to replace the placeholders in CONFIG with your actual API keys.
# # Example usage
# # search = WebSearch(CONFIG)
# # results = search.search_query("Example Query")
# # if results is not None:
# #     for title, link, snippet in results:
# #         print(title, link, snippet)
```

# AutoGroq\utils\agent_utils.py

```python

import datetime
import streamlit as st

from configs.config import LLM_PROVIDER
from utils.text_utils import sanitize_text


def create_agent_data(agent):
    expert_name = agent['config']['name']
    description = agent['config'].get('description', agent.get('description', ''))
    current_timestamp = datetime.datetime.now().isoformat()
    provider = agent['config'].get('provider', st.session_state.get('provider', LLM_PROVIDER))

    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    sanitized_description = sanitize_text(description)

    autogen_agent_data = {
        "type": "assistant",
        "config": {
            "name": formatted_expert_name,
            "provider": provider,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": current_timestamp,
                        "model": agent['config']['llm_config']['config_list'][0]['model'],
                        "provider": provider,
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": f"{provider.capitalize()} model configuration"
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
            "system_message": f"You are a helpful assistant that can act as {expert_name} who {sanitized_description}.",
            "is_termination_msg": None,
            "code_execution_config": None,
            "default_auto_reply": "",
            "description": description
        },
        "timestamp": current_timestamp,
        "user_id": "default",
        "tools": []
    }

    for tool_model in st.session_state.tool_models:
        tool_name = tool_model.name
        if agent.get(tool_name, False):
            tool_json = {
                "name": tool_model.name,
                "description": tool_model.description,
                "title": tool_model.title,
                "file_name": tool_model.file_name,
                "content": tool_model.content,
                "timestamp": tool_model.timestamp,
                "user_id": tool_model.user_id
            }
            autogen_agent_data["tools"].append(tool_json)

    crewai_agent_data = {
        "name": expert_name,
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

from configs.config import API_URL, LLM_PROVIDER, RETRY_DELAY, RETRY_TOKEN_LIMIT, SUPPORTED_PROVIDERS


def display_api_key_input(provider=None):
    if provider is None:
        provider = st.session_state.get('provider', LLM_PROVIDER)
    api_key_env_var = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    
    if api_key is None:
        st.session_state.warning_placeholder.warning(f"{provider.upper()} API Key not found. Please enter your API key.")
        api_key = st.text_input(f"Enter your {provider.upper()} API Key:", type="password", key=f"api_key_input_{provider}")
        if api_key:
            st.session_state[api_key_env_var] = api_key
            os.environ[api_key_env_var] = api_key
            st.success(f"{provider.upper()} API Key entered successfully.")
            st.session_state.warning_placeholder.empty()
    return api_key


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

import datetime
import json
import os
import sqlite3
import streamlit as st
import uuid

from configs.config import FRAMEWORK_DB_PATH, MODEL_CHOICES, MODEL_TOKEN_LIMITS

from utils.agent_utils import create_agent_data
from utils.file_utils import sanitize_text
from utils.workflow_utils import get_workflow_from_agents


def export_to_autogen():
    # Check if the app is running on Streamlit Sharing
    url_params = st.query_params
    if "streamlit.app" in url_params.get("url", ""):
        st.warning("Exporting to Autogen is only possible with a locally running copy of AutoGroq™.")
        return

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

            # Access agents from st.session_state
            agents = st.session_state.agents
            print(f"Number of agents: {len(agents)}")

            # Keep track of inserted skills to avoid duplicates
            inserted_skills = set()

            for agent in agents:
                agent_name = agent['config']['name']
                formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
                autogen_agent_data, _ = create_agent_data(agent)
                
                # Update the model and max_tokens in the autogen_agent_data
                autogen_agent_data['config']['llm_config']['config_list'][0]['model'] = agent['config']['llm_config']['config_list'][0]['model']
                autogen_agent_data['config']['llm_config']['max_tokens'] = MODEL_CHOICES.get(agent['config']['llm_config']['config_list'][0]['model'], MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096))
                
                agent_data = (
                    str(uuid.uuid4()), # Generate a unique ID for the agent
                    'default',
                    datetime.datetime.now().isoformat(),
                    json.dumps(autogen_agent_data['config']),
                    autogen_agent_data['type'],
                    json.dumps(autogen_agent_data['tools'])
                )
                cursor.execute("INSERT INTO agents (id, user_id, timestamp, config, type, skills) VALUES (?, ?, ?, ?, ?, ?)", agent_data)
                print(f"Inserted agent: {formatted_agent_name}")

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            skill_folder = os.path.join(project_root, "tools")
            for tool_name in st.session_state.selected_tools:
                if tool_name not in inserted_skills:
                    skill_file_path = os.path.join(skill_folder, f"{tool_name}.py")
                    with open(skill_file_path, 'r') as file:
                        skill_data = file.read()
                        skill_json = st.session_state.tool
                        skill_data = (
                            str(uuid.uuid4()),  # Generate a unique ID for the skill
                            'default',  # Set the user ID to 'default'
                            datetime.datetime.now().isoformat(),
                            skill_data,
                            skill_json['title'],
                            skill_json['file_name']
                        )
                        cursor.execute("INSERT INTO skills (id, user_id, timestamp, content, title, file_name) VALUES (?, ?, ?, ?, ?, ?)", skill_data)
                        print(f"Inserted skill: {skill_json['title']}")
                        inserted_skills.add(tool_name)  # Add the inserted skill to the set

            # Access agents from st.session_state for workflow
            workflow_data = get_workflow_from_agents(st.session_state.agents)[0]
            workflow_data = (
                str(uuid.uuid4()),  # Generate a unique ID for the workflow
                'default',
                datetime.datetime.now().isoformat(),
                json.dumps(workflow_data['sender']),
                json.dumps(workflow_data['receiver']),
                workflow_data['type'],
                workflow_data['name'],
                workflow_data['description'],
                workflow_data['summary_method']
            )
            cursor.execute("INSERT INTO workflows (id, user_id, timestamp, sender, receiver, type, name, description, summary_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", workflow_data)
            print("Inserted workflow data.")

            conn.commit()
            print("Changes committed to the database.")

            conn.close()
            print("Database connection closed.")

            st.success("Data exported to Autogen successfully!")
        except sqlite3.Error as e:
            st.error(f"Error exporting data to Autogen: {str(e)}")
            print(f"Error exporting data to Autogen: {str(e)}")


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

# AutoGroq\utils\file_utils.py

```python

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

    autogen_file_data = {}
    for agent in st.session_state.agents:
        agent_name = agent['config']['name']
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        agent_file_name = f"{formatted_agent_name}.json"

        # Use the agent-specific model configuration
        autogen_agent_data, _ = create_agent_data(agent)
        autogen_agent_data['config']['name'] = formatted_agent_name
        autogen_agent_data['config']['llm_config']['config_list'][0]['model'] = agent['config']['llm_config']['config_list'][0]['model']
        autogen_agent_data['config']['llm_config']['max_tokens'] = agent['config']['llm_config'].get('max_tokens', MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096))
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
        agent_name = agent['config']['name']
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        crewai_agent_data = create_agent_data(agent)[1]
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


```

# AutoGroq\utils\session_utils.py

```python

import streamlit as st

from configs.config import LLM_PROVIDER, SUPPORTED_PROVIDERS
from configs.config_sessions import DEFAULT_AGENT_CONFIG
from configs.current_project import Current_Project
from datetime import datetime
from models.agent_base_model import AgentBaseModel
from models.project_base_model import ProjectBaseModel
from models.tool_base_model import ToolBaseModel
from models.workflow_base_model import WorkflowBaseModel


def create_default_agent():
    return AgentBaseModel(**DEFAULT_AGENT_CONFIG)

def initialize_session_variables():

    if "agent_model" not in st.session_state:
        st.session_state.agent_model = create_default_agent()

    if "agent_models" not in st.session_state:
        st.session_state.agent_models = []

    if "agents" not in st.session_state:
        st.session_state.agents = []

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

    for provider in SUPPORTED_PROVIDERS:
        if f"{provider.upper()}_API_URL" not in st.session_state:
            st.session_state[f"{provider.upper()}_API_URL"] = None
```

# AutoGroq\utils\text_utils.py

```python
import re

def sanitize_text(text): 
    # Remove non-ASCII characters 
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    # Remove non-alphanumeric characters except for standard punctuation 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?:;\'"-]+', '', text) 
    return text 
```

# AutoGroq\utils\tool_utils.py

```python

import datetime
import importlib
import os
import re
import sqlite3
import streamlit as st
import uuid

from configs.config import FRAMEWORK_DB_PATH
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
    current_timestamp = datetime.datetime.now().isoformat()

    # Update st.session_state.tool_model with the tool data
    st.session_state.tool_model.name = function_name
    st.session_state.tool_model.description = tool_description
    st.session_state.tool_model.title = function_name
    st.session_state.tool_model.file_name = f"{function_name}.py"
    st.session_state.tool_model.content = python_code
    st.session_state.tool_model.user_id = "default"
    st.session_state.tool_model.timestamp = current_timestamp


def export_tool_as_skill(tool_name: str, edited_skill: str):
    print(f"Exporting skill '{tool_name}'...")
    try:
        create_tool_data(edited_skill)
        print(f"Skill data: {st.session_state.tool_model.dict()}")  # Use dict() to get the dictionary representation
        skill_tuple = (
            str(uuid.uuid4()),  # Generate a unique ID for the skill
            'default',  # Set the user ID to 'default'
            datetime.datetime.now().isoformat(),
            edited_skill,
            st.session_state.tool_model.title,
            st.session_state.tool_model.file_name
        )
        print(f"Inserting skill data: {skill_tuple}")
        sql = "INSERT INTO skills (id, user_id, timestamp, content, title, file_name) VALUES (?, ?, ?, ?, ?, ?)"
        sql_to_db(sql, skill_tuple)
        st.success(f"Skill '{tool_name}' exported tool successfully!")
        st.experimental_rerun()
    except sqlite3.Error as e:
        st.error(f"Error exporting skill: {str(e)}")
        print(f"Error exporting skill: {str(e)}")


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
    # Get the parent directory of the current script
    parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Define the path to the 'tools' folder in the parent directory
    tools_folder_path = os.path.join(parent_directory, 'tools')

    # List all files in the 'tools' folder
    tool_files = [f for f in os.listdir(tools_folder_path) if f.endswith('.py')]

    tool_functions = {}
    for tool_file in tool_files:
        tool_name = os.path.splitext(tool_file)[0]
        tool_module = importlib.import_module(f"tools.{tool_name}")
        if hasattr(tool_module, tool_name):
            tool_functions[tool_name] = getattr(tool_module, tool_name)

    st.session_state.tool_functions = tool_functions


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
        parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tool_folder = os.path.join(parent_directory, "tools")
        print(f"Tool Request: {tool_request}")
        rephrased_tool_request = rephrase_tool(tool_request)
        if rephrased_tool_request:
            print(f"Generating proposed tool...")
            proposed_tool, tool_name = generate_tool(rephrased_tool_request)  # Unpack the tuple
            print(f"Proposed tool: {proposed_tool}")
            if proposed_tool:
                match = re.search(r"def\s+(\w+(?:_\w+)*)\(", proposed_tool)  # Updated regex pattern
                print(f"Match: {match}")
                if match:
                    tool_name = match.group(1)
                    st.write(f"Proposed tool: {tool_name}")
                    st.code(proposed_tool)

                    with st.form(key=f"export_form_{tool_name}"):
                        submit_export = st.form_submit_button("Export/Write")
                        if submit_export:
                            print(f"Exporting tool {tool_name}")
                            export_tool_as_skill(tool_name, proposed_tool)
                            st.success(f"tool {tool_name} exported to Autogen successfully!")
                            # Clear the tool_request input and hide the input field
                            st.session_state.show_tool_input = False
                            st.session_state.tool_request = ""
                            # Clear the 'proposed_tool' and 'tool_name' from the session state
                            st.session_state.proposed_tool = None
                            st.session_state.tool_name = None
                            st.session_state.tool_processed = True  # Set the flag to indicate processing is complete
                            st.experimental_rerun()
                            
                    with st.form(key=f"discard_form_{tool_name}"):
                        submit_discard = st.form_submit_button("Clear")
                        if submit_discard:
                            st.warning("tool discarded.")
                            # Clear the tool_request input and hide the input field
                            st.session_state.show_tool_input = False
                            st.session_state.tool_request = ""
                            # Clear the 'proposed_tool' and 'tool_name' from the session state
                            st.session_state.proposed_tool = None
                            st.session_state.tool_name = None
                            st.session_state.tool_processed = True  # Set the flag to indicate processing is complete
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
                tool_checkbox = st.checkbox(f"Add {tool_name} tool to all agents", value=False, key=f"tool_{tool_name}_{idx}")
            if tool_checkbox:
                selected_tools.append(tool_name)

        if select_all:
            st.session_state.selected_tools = [tool_model.name for tool_model in st.session_state.tool_models]
        else:
            st.session_state.selected_tools = selected_tools

        # Update the 'Tools' property of each agent with the selected tools
        for agent in st.session_state.agents:
            agent['tools'] = [tool_model.name for tool_model in st.session_state.tool_models if tool_model.name in st.session_state.selected_tools]

        regenerate_zip_files()

        if st.button("Add tool", key="add_tool_button"):
            st.session_state.show_tool_input = True
            st.session_state.tool_request = ""
            st.session_state.tool_processed = False 

        if st.session_state.get('show_tool_input'):
            tool_request = st.text_input("Need a new tool? Describe what it should do:", key="tool_request_input")
            if tool_request:
                st.session_state.tool_request = tool_request  # Store in a separate session state variable
                process_tool_request()  # Pass the tool_request to the process_tool_request function

        if selected_tools or 'proposed_tool' in st.session_state:
            if st.button("Attempt to Export tool to Autogen (experimental)", key=f"export_button_{st.session_state.tool_name}"):
                tool_name = st.session_state.tool_name
                proposed_tool = st.session_state.proposed_tool
                print(f"Exporting tool {tool_name} to Autogen")
                export_tool_as_skill(tool_name, proposed_tool)
                st.success(f"tool {tool_name} exported to Autogen successfully!")
                # Clear the tool_request input and hide the input field
                st.session_state.show_tool_input = False
                st.session_state.tool_request = ""
                st.experimental_rerun()
```

# AutoGroq\utils\ui_utils.py

```python
import datetime
import json
import os
import pandas as pd
import re
import streamlit as st
import time

from configs.config import (API_URL, DEBUG, LLM_PROVIDER, MAX_RETRIES, 
        MODEL_CHOICES, MODEL_TOKEN_LIMITS, RETRY_DELAY, SUPPORTED_PROVIDERS)

from configs.current_project import Current_Project
from models.agent_base_model import AgentBaseModel
from models.workflow_base_model import WorkflowBaseModel
from prompts import create_project_manager_prompt, get_agents_prompt, get_rephrased_user_prompt  
from tools.fetch_web_content import fetch_web_content
from utils.api_utils import get_api_key, get_llm_provider
from utils.auth_utils import check_api_key, display_api_key_input
from utils.db_utils import export_to_autogen
from utils.file_utils import zip_files_in_memory
from utils.workflow_utils import get_workflow_from_agents
from prompts import get_moderator_prompt
    
    
def create_project_manager(rephrased_text, api_url):
    print(f"Creating Project Manager; API_URL: {api_url}")
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
    
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            return content.strip()
    
    return None


# def display_api_key_input():
#     llm = LLM_PROVIDER.upper()
#     api_key = st.text_input(f"Enter your {llm}_API_KEY:", type="password", value="", key="api_key_input")
#     if api_key:
#         st.session_state[f"{LLM_PROVIDER.upper()}_API_KEY"] = api_key
#         st.success("API Key entered successfully.")
#     return api_key


def display_discussion_and_whiteboard():
    discussion_history = get_discussion_history()

    tabs = st.tabs(["Most Recent Comment", "Whiteboard", "Discussion History", "Deliverables", "Downloads", "Debug"])

    with tabs[0]:
        st.text_area("Most Recent Comment", value=st.session_state.last_comment, height=400, key="discussion")

    with tabs[1]:
        st.text_area("Whiteboard", value=st.session_state.whiteboard, height=400, key="whiteboard")

    with tabs[2]:
        st.write(discussion_history)

    with tabs[3]:
        if "current_project" in st.session_state:
            current_project = st.session_state.current_project
            for index, deliverable in enumerate(current_project.deliverables):
                if deliverable["text"].strip():  # Check if the deliverable text is not empty
                    checkbox_key = f"deliverable_{index}"
                    done = st.checkbox(deliverable["text"], value=deliverable["done"], key=checkbox_key)
                    if done != deliverable["done"]:
                        if done:
                            current_project.mark_deliverable_done(index)
                        else:
                            current_project.mark_deliverable_undone(index)

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

 
def extract_json_objects(json_string):
    objects = []
    stack = []
    start_index = 0
    for i, char in enumerate(json_string):
        if char == "{":
            if not stack:
                start_index = i
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack:
                    objects.append(json_string[start_index:i+1])
    parsed_objects = []
    for obj_str in objects:
        try:
            parsed_obj = json.loads(obj_str)
            parsed_objects.append(parsed_obj)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON object: {e}")
            print(f"JSON string: {obj_str}")
    return parsed_objects
                

def get_agents_from_text(text, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):     
    print("Getting agents from text...")
    temperature_value = st.session_state.get('temperature', 0.5)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.temperature,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "system",
                "content": get_agents_prompt()
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }
    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = llm_provider.send_request(llm_request_data)
            print(f"Response received. Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Request successful. Parsing response...")
                response_data = llm_provider.process_response(response)
                print(f"Response Data: {json.dumps(response_data, indent=2)}")
                if "choices" in response_data and response_data["choices"]:
                    content = response_data["choices"][0]["message"]["content"]
                    print(f"Content: {content}")

                    # Preprocess the JSON string
                    content = content.replace("\\n", "\n").replace('\\"', '"')

                    try:
                        json_data = json.loads(content)
                        if isinstance(json_data, list):
                            autogen_agents = []
                            crewai_agents = []
                            for index, agent_data in enumerate(json_data, start=1):
                                expert_name = agent_data.get('expert_name', '')
                                if not expert_name:
                                    print("Missing agent name. Retrying...")
                                    retry_count += 1
                                    time.sleep(retry_delay)
                                    continue
                                description = agent_data.get('description', '')
                                tools = agent_data.get('tools', [])
                                agent_tools = st.session_state.selected_tools
                                current_timestamp = datetime.datetime.now().isoformat()
                                autogen_agent_data = {
                                    "id": index,
                                    "name": expert_name,
                                    "type": "assistant",
                                    "config": {
                                        "name": expert_name,
                                        "llm_config": {
                                            "config_list": [
                                                {
                                                    "user_id": "default",
                                                    "timestamp": current_timestamp,
                                                    "model": st.session_state.model,
                                                    "base_url": None,
                                                    "api_type": None,
                                                    "api_version": None,
                                                    "description": "OpenAI model configuration"
                                                }
                                            ],
                                            "temperature": st.session_state.temperature,
                                            "cache_seed": 42,
                                            "timeout": 600,
                                            "max_tokens": MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096),
                                            "extra_body": None
                                        },
                                        "human_input_mode": "NEVER",
                                        "max_consecutive_auto_reply": 8,
                                        "system_message": f"You are a helpful assistant that can act as {expert_name} who {description}."
                                    },
                                    "description": description,
                                    "tools": agent_tools,
                                    "created_at": current_timestamp,
                                    "updated_at": current_timestamp,
                                    "user_id": "default",
                                    "models": [model for model in MODEL_CHOICES if model != "default"],
                                    "verbose": False,
                                    "allow_delegation": False,
                                    "timestamp": current_timestamp
                                }
                                crewai_agent_data = {
                                    "name": expert_name,
                                    "description": description,
                                    "tools": agent_tools,
                                    "verbose": True,
                                    "allow_delegation": True
                                }
                                autogen_agents.append(autogen_agent_data)
                                crewai_agents.append(crewai_agent_data)
                            print(f"AutoGen Agents: {autogen_agents}")
                            print(f"CrewAI Agents: {crewai_agents}")
                            st.session_state.workflow.agents = [AgentBaseModel.from_dict(agent) for agent in autogen_agents]
                            return autogen_agents, crewai_agents
                        else:
                            print("Invalid JSON format. Expected a list of agents.")
                            return [], []
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")
                        print(f"Content: {content}")
                        json_data = extract_json_objects(content)
                        if json_data:
                            autogen_agents = []
                            crewai_agents = []
                            for index, agent_data in enumerate(json_data, start=1):
                                expert_name = agent_data.get('expert_name', '')
                                if not expert_name:
                                    print("Missing agent name. Retrying...")
                                    retry_count += 1
                                    time.sleep(retry_delay)
                                    continue
                                description = agent_data.get('description', '')
                                tools = agent_data.get('tools', [])
                                agent_tools = st.session_state.selected_tools
                                current_timestamp = datetime.datetime.now().isoformat()
                                autogen_agent_data = {
                                    "id": index,
                                    "name": expert_name,
                                    "type": "assistant",
                                    "config": {
                                        "name": expert_name,
                                        "llm_config": {
                                            "config_list": [
                                                {
                                                    "user_id": "default",
                                                    "timestamp": current_timestamp,
                                                    "model": st.session_state.model,
                                                    "base_url": None,
                                                    "api_type": None,
                                                    "api_version": None,
                                                    "description": "OpenAI model configuration"
                                                }
                                            ],
                                            "temperature": st.session_state.temperature,
                                            "timeout": 600,
                                            "cache_seed": 42
                                        },
                                        "human_input_mode": "NEVER",
                                        "max_consecutive_auto_reply": 8,
                                        "system_message": f"You are a helpful assistant that can act as {expert_name} who {description}."
                                    },
                                    "description": description,
                                    "tools": agent_tools,
                                    "created_at": current_timestamp,
                                    "updated_at": current_timestamp,
                                    "user_id": "default",
                                    "models": [model for model in MODEL_CHOICES if model != "default"],
                                    "verbose": False,
                                    "allow_delegation": False,
                                    "timestamp": current_timestamp
                                }
                                crewai_agent_data = {
                                    "name": expert_name,
                                    "description": description,
                                    "tools": agent_tools,
                                    "verbose": True,
                                    "allow_delegation": True
                                }
                                autogen_agents.append(autogen_agent_data)
                                crewai_agents.append(crewai_agent_data)
                            print(f"AutoGen Agents: {autogen_agents}")
                            print(f"CrewAI Agents: {crewai_agents}")
                            return autogen_agents, crewai_agents
                        else:
                            print("Failed to extract JSON objects from content.")
                            return [], []
                else:
                    print("No agents data found in response")
            else:
                print(f"API request failed with status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error making API request: {e}")
            retry_count += 1
            time.sleep(retry_delay)
    print(f"Maximum retries ({max_retries}) exceeded. Failed to retrieve valid agent names.")
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
        project_manager_output = create_project_manager(rephrased_text, API_URL)

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

        print(f"Debug: AutoGen Agents: {autogen_agents}")
        print(f"Debug: CrewAI Agents: {crewai_agents}")

        if not autogen_agents:
            print("Error: No agents created.")
            st.warning("Failed to create agents. Please try again.")
            return

        session_state.agents = autogen_agents
        session_state.workflow.agents = session_state.agents
        print(f"Debug: session_state.workflow.agents: {session_state.workflow.agents}")

        # Generate the workflow data
        workflow_data, _ = get_workflow_from_agents(autogen_agents)
        workflow_data["created_at"] = datetime.datetime.now().isoformat()
        print(f"Debug: Workflow data: {workflow_data}")
        print(f"Debug: CrewAI agents: {crewai_agents}")

        # Update the project session state with the workflow data
        session_state.project_model.workflows = [workflow_data]

        print("Debug: Agents in session state project workflow:")
        for agent in workflow_data["receiver"]["groupchat_config"]["agents"]:
            print(agent)

        autogen_zip_buffer, crewai_zip_buffer = zip_files_in_memory(workflow_data)
        session_state.autogen_zip_buffer = autogen_zip_buffer
        session_state.crewai_zip_buffer = crewai_zip_buffer
    else:
        print("Error: 'Team of Experts' section not found in Project Manager's output.")
        st.warning("Failed to extract the team of experts from the Project Manager's output. Please try again.")
        return


def key_prompt():
    api_key = get_api_key()
    if api_key is None:
        api_key = display_api_key_input()
    if api_key is None:
        llm = LLM_PROVIDER.upper()
        st.warning(f"{llm}_API_KEY not found. Please enter your API key.")
        return


def rephrase_prompt(user_request, model, max_tokens=None, llm_provider=None, provider=None):
    print("Executing rephrase_prompt()")

    refactoring_prompt = get_rephrased_user_prompt(user_request)

    if llm_provider is None:
        # Use the existing functionality for non-CLI calls
        api_key = get_api_key()
        try:
            llm_provider = get_llm_provider(api_key=api_key, provider=provider)
        except Exception as e:
            print(f"Error initializing LLM provider: {str(e)}")
            return None

    if max_tokens is None:
        max_tokens = MODEL_TOKEN_LIMITS.get(model, 4096)

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
        print(f"Response received. Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")

        if response.status_code == 200:
            print("Request successful. Parsing response...")
            response_data = llm_provider.process_response(response)
            print(f"Response Data: {json.dumps(response_data, indent=2)}")

            if "choices" in response_data and len(response_data["choices"]) > 0:
                rephrased = response_data["choices"][0]["message"]["content"]
                return rephrased.strip()
            else:
                print("Error: Unexpected response format. 'choices' field missing or empty.")
                return None
        else:
            print(f"Request failed. Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def select_model():
    provider = st.session_state.get('provider', LLM_PROVIDER)
    provider_models = MODEL_CHOICES[provider]
    
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
        value=st.session_state.get('temperature', 0.3),
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
    if auto_moderate and not st.session_state.get("user_input"):
        moderator_response = trigger_moderator_agent()
        if moderator_response:
            st.session_state.user_input = moderator_response
    user_input, reference_url = display_user_input()
    st.markdown('</div>', unsafe_allow_html=True)


def trigger_moderator_agent():
    goal = st.session_state.current_project.re_engineered_prompt
    last_speaker = st.session_state.last_agent
    last_comment = st.session_state.last_comment
    discussion_history = st.session_state.discussion_history

    team_members = []
    for agent in st.session_state.agents:
        team_members.append(f"{agent['config']['name']}: {agent['description']}")
    team_members_str = "\n".join(team_members)

    moderator_prompt = get_moderator_prompt(discussion_history, goal, last_comment, last_speaker,team_members_str)

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
    # wait for RETRY_DELAY seconds
    retry_delay = RETRY_DELAY
    time.sleep(retry_delay)
    response = llm_provider.send_request(llm_request_data)

    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            return content.strip()

    return None


def trigger_moderator_agent_if_checked():
    if st.session_state.get("auto_moderate", False):
        trigger_moderator_agent()


def update_api_url(provider):
    api_url_key = f"{provider.upper()}_API_URL"
    st.session_state.api_url = st.session_state.get(api_url_key)


def update_discussion_and_whiteboard(agent_name, response, user_input):
    if user_input:
        user_input_text = f"\n\n\n\n{user_input}\n\n"
        st.session_state.discussion_history += user_input_text

    if "last_agent" not in st.session_state or st.session_state.last_agent != agent_name:
        response_text = f"{agent_name}:\n\n{response}\n\n===\n\n"
    else:
        response_text = f"{response}\n\n===\n\n"

    st.session_state.discussion_history += response_text
    code_blocks = extract_code_from_response(response)
    st.session_state.whiteboard = code_blocks
    st.session_state.last_agent = agent_name
    st.session_state.last_comment = response_text

    if st.session_state.get("auto_moderate", False):
        moderator_response = trigger_moderator_agent()
        if moderator_response:
            st.session_state.user_input = moderator_response
        else:
            st.session_state.user_input = ""
        
        # Update the 'Additional Input:' text area with the moderator response or an empty string
        # st.text_area("Additional Input:", value=st.session_state.user_input, key="user_input_widget_auto_moderate", height=100, on_change=update_user_input)


def update_user_input():
    if st.session_state.get("auto_moderate"):
        st.session_state.user_input = st.session_state.user_input_widget_auto_moderate
    else:
        st.session_state.user_input = st.session_state.user_input_widget



```

# AutoGroq\utils\workflow_utils.py

```python

import datetime
import streamlit as st

from configs.config import MODEL_TOKEN_LIMITS

from utils.agent_utils import create_agent_data
from utils.file_utils import sanitize_text


def get_workflow_from_agents(agents):
    current_timestamp = datetime.datetime.now().isoformat()
    temperature_value = st.session_state.get('temperature', 0.3)

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
                            "model": st.session_state.model,
                            "base_url": None,
                            "api_type": None,
                            "api_version": None,
                            "description": "OpenAI model configuration"
                        }
                    ],
                    "temperature": st.session_state.temperature,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096),
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
        "type": "groupchat",
        "user_id": "default",
        "timestamp": current_timestamp,
        "summary_method": "last"
    }

    for index, agent in enumerate(agents):
        agent_name = agent["config"]["name"]
        description = agent["description"]
        formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
        sanitized_description = sanitize_text(description)
        
        system_message = f"You are a helpful assistant that can act as {agent_name} who {sanitized_description}."
        if index == 0:
            other_agent_names = [sanitize_text(a['config']['name']).lower().replace(' ', '_') for a in agents[1:]]
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
                            "model": st.session_state.model,
                            "base_url": None,
                            "api_type": None,
                            "api_version": None,
                            "description": "OpenAI model configuration"
                        }
                    ],
                    "temperature": st.session_state.temperature,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": MODEL_TOKEN_LIMITS.get(st.session_state.model, 4096),
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
            "tools": []  # Set tools to null only in the workflow JSON
        }

        workflow["receiver"]["groupchat_config"]["agents"].append(agent_config)

    print("Debug: Workflow agents assigned:")
    for agent in workflow["receiver"]["groupchat_config"]["agents"]:
        print(agent)

    crewai_agents = []
    for agent in agents:
        _, crewai_agent_data = create_agent_data(agent)
        crewai_agents.append(crewai_agent_data)

    return workflow, crewai_agents
```

