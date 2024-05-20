
import base64
import os
import re
import streamlit as st

from config import API_URL

from ui_utils import get_llm_provider, regenerate_json_files_and_zip, update_discussion_and_whiteboard


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


def construct_request(agent_name, description, user_request, user_input, rephrased_request, reference_url, skill_results):
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
    if skill_results:
        request += f" Skill results: {skill_results}."
    return request


def display_agents():
    if "agents" in st.session_state and st.session_state.agents:
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
        st.sidebar.warning(f"ALSO: 'No secrets files found' warning is normal and inconsequential in local mode.")
        st.sidebar.warning(f"FINALLY: If no agents are created, do a hard reset (CTL-F5) and try switching models. LLM results can be unpredictable.")
        st.sidebar.warning(f"SOURCE:  https://github.com/jgravelle/AutoGroq")


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
            space = container.empty()
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
        new_description = st.text_area("Description", value=description_value, key=f"desc_{edit_index}")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Re-roll 🎲", key=f"regenerate_{edit_index}"):
                print(f"Regenerate button clicked for agent {edit_index}")
                new_description = regenerate_agent_description(agent)
                if new_description:
                    agent['new_description'] = new_description
                    print(f"Description regenerated for {agent['config']['name']}: {new_description}")
                    st.session_state[f"regenerate_description_{edit_index}"] = True
                    # Update the value parameter of st.text_area to display the new description
                    description_value = new_description
                    st.experimental_rerun()
                else:
                    print(f"Failed to regenerate description for {agent['config']['name']}")
        with col2:
            if st.button("Save Changes", key=f"save_{edit_index}"):
                agent['config']['name'] = new_name
                agent['description'] = agent.get('new_description', new_description)
                st.session_state['show_edit'] = False
                if 'edit_agent_index' in st.session_state:
                    del st.session_state['edit_agent_index']
                if 'new_description' in agent:
                    del agent['new_description']
                st.session_state.agents[edit_index] = agent
                regenerate_json_files_and_zip()
                st.session_state['show_edit'] = False
        with col3:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            skill_folder = os.path.join(script_dir, "skills")
            skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]
            for skill_file in skill_files:
                skill_name = os.path.splitext(skill_file)[0]
                if skill_name not in agent:
                    agent[skill_name] = False
                skill_checkbox = st.checkbox(
                    f"Add {skill_name} skill to this agent in Autogen™",
                    value=agent[skill_name],
                    key=f"{skill_name}_{edit_index}"
                )
                if skill_checkbox != agent[skill_name]:
                    agent[skill_name] = skill_checkbox
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
    agent_name, description = retrieve_agent_information(agent_index)
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')
    rephrased_request = st.session_state.get('rephrased_request', '')
    reference_url = st.session_state.get('reference_url', '')
    # Execute associated skills for the agent
    agent = st.session_state.agents[agent_index]
    agent_skills = agent.get("skills", [])
    skill_results = {}
    for skill_name in agent_skills:
        if skill_name in st.session_state.skill_functions:
            skill_function = st.session_state.skill_functions[skill_name]
            skill_result = skill_function()
            skill_results[skill_name] = skill_result
    request = construct_request(agent_name, description, user_request, user_input, rephrased_request, reference_url, skill_results)
    print(f"Request: {request}")
    # Use the dynamic LLM provider to send the request
    llm_provider = get_llm_provider(API_URL)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.get('temperature', 0.1),
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": request
            }
        ]
    }
    response = llm_provider.send_request(llm_request_data)
    if response.status_code == 200:
        response_data = llm_provider.process_response(response)
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0]["message"]["content"]
            update_discussion_and_whiteboard(agent_name, content, user_input)
            st.session_state['form_agent_name'] = agent_name
            st.session_state['form_agent_description'] = description
            st.session_state['selected_agent_index'] = agent_index
            st.experimental_rerun() # Trigger a rerun to update the UI


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
    Please generate a revised description for this agent that defines it in the best manner possible to address the current user request, taking into account the discussion thus far. Return only the revised description, without any additional commentary or narrative. It is imperative that you return ONLY the text of the new description. No preamble, no narrative, no superfluous commentary whatsoever. Just the description, unlabeled, please.
    """
    print(f"regenerate_agent_description called with agent_name: {agent_name}")
    print(f"regenerate_agent_description called with prompt: {prompt}")
    llm_provider = get_llm_provider(API_URL)
    llm_request_data = {
        "model": st.session_state.model,
        "temperature": st.session_state.get('temperature', 0.1),
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
    llm_provider = get_llm_provider(API_URL)
    response = llm_provider.send_request(request)
    return response