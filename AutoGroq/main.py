
import os
import re
import streamlit as st 

from config import LLM_PROVIDER, MODEL_TOKEN_LIMITS

from agent_management import display_agents
from utils.auth_utils import get_api_key
from utils.db_utils import export_skill_to_autogen, export_to_autogen
from utils.ui_utils import display_api_key_input, display_discussion_and_whiteboard, display_download_button, display_reset_and_upload_buttons, display_user_input, display_user_request_input, generate_skill, handle_user_request, load_skill_functions, regenerate_zip_files, rephrase_skill


def main():
    # Construct the relative path to the CSS file
    css_file = "AutoGroq/style.css"

    # Check if the CSS file exists
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found: {os.path.abspath(css_file)}")

    load_skill_functions()

    api_key = get_api_key()
    if api_key is None:
        api_key = display_api_key_input()
    if api_key is None:
        llm = LLM_PROVIDER.upper()
        st.warning(f"{llm}_API_KEY not found. Please enter your API key.")
        return

    # If the LLM Provider is "groq", the title is "AutoGroq"
    if LLM_PROVIDER == "groq":
        st.title("AutoGroq™")
    elif LLM_PROVIDER == "ollama":
        st.title("Auto̶G̶r̶o̶qOllama")
    elif LLM_PROVIDER == "lmstudio":
        st.title("Auto̶G̶r̶o̶qLM_Studio")
    elif LLM_PROVIDER == "openai":
        st.title("Auto̶G̶r̶o̶qChatGPT")

    col1, col2 = st.columns([1, 1])  # Adjust the column widths as needed
    with col1:
        selected_model = st.selectbox(
            'Select Model',
            options=list(MODEL_TOKEN_LIMITS.keys()),
            index=0,
            key='model_selection'
        )
        st.session_state.model = selected_model
        st.session_state.max_tokens = MODEL_TOKEN_LIMITS[selected_model]

    with col2:
        temperature = st.slider(
            "Set Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.get('temperature', 0.3),
            step=0.01,
            key='temperature'
        )


    with st.sidebar:
        display_agents()

    with st.container():
        if st.session_state.get("rephrased_request", "") == "":
            user_request = st.text_input("Enter your request:", key="user_request", value=st.session_state.get("user_request", ""), on_change=handle_user_request, args=(st.session_state,))
            display_user_request_input()

        st.markdown('<div class="discussion-whiteboard">', unsafe_allow_html=True)
        display_discussion_and_whiteboard()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="user-input">', unsafe_allow_html=True)
        display_user_input()
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("Skills"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            skill_folder = os.path.join(script_dir, "skills")
            skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]

            selected_skills = []
            select_all = st.checkbox("Select All", key="select_all_skills")
            for skill_file in skill_files:
                skill_name = os.path.splitext(skill_file)[0]
                if select_all:
                    skill_checkbox = st.checkbox(f"Add {skill_name} skill to all agents", value=True, key=f"skill_{skill_name}")
                else:
                    skill_checkbox = st.checkbox(f"Add {skill_name} skill to all agents", value=False, key=f"skill_{skill_name}")
                if skill_checkbox:
                    selected_skills.append(skill_name)

            if select_all:
                st.session_state.selected_skills = [os.path.splitext(f)[0] for f in skill_files]
            else:
                st.session_state.selected_skills = selected_skills

            regenerate_zip_files()

            if st.button("Add Skill", key="add_skill_button"):
                st.session_state.show_skill_input = True  # Flag to show the input field
                st.session_state.skill_request = ""  # Clear previous request

            if st.session_state.get('show_skill_input'):
                skill_request = st.text_input("Need a new skill? Describe what it should do:", key="skill_request_input")
                if skill_request:
                    st.session_state.skill_request = skill_request  # Store in session state
                    rephrased_skill_request = rephrase_skill(skill_request)
                    if rephrased_skill_request:
                        proposed_skill = generate_skill(rephrased_skill_request)
                        if proposed_skill:
                            st.session_state.proposed_skill = proposed_skill
                            match = re.search(r"def\s+(\w+)\(", proposed_skill)
                            if match:
                                skill_name = match.group(1)
                                st.session_state.skill_name = skill_name
                                st.write(f"Proposed Skill: {skill_name}")
                                st.session_state.proposed_skill = st.text_area("Edit Proposed Skill", value=proposed_skill, height=300)

            if 'proposed_skill' in st.session_state and 'skill_name' in st.session_state:
                if st.button("Attempt to Export Skill to Autogen (experimental)", key=f"export_button_{st.session_state.skill_name}"):
                    skill_name = st.session_state.skill_name
                    proposed_skill = st.session_state.proposed_skill
                    print(f"Exporting skill {skill_name} to Autogen")
                    export_skill_to_autogen(skill_name, proposed_skill)
                    st.success(f"Skill {skill_name} exported to Autogen successfully!")
                    st.session_state.show_skill_input = False  # Reset input flag
                    st.session_state.proposed_skill = None  # Clear proposed skill
                    st.session_state.skill_name = None  # Clear skill name
                    st.experimental_rerun()

    display_reset_and_upload_buttons()
    if "agents" in st.session_state and st.session_state.agents:
        if "autogen_zip_buffer" in st.session_state and "crewai_zip_buffer" in st.session_state:
            display_download_button() 
            if st.button("Export to Autogen"):
                export_to_autogen()  
    

if __name__ == "__main__":
    main()
