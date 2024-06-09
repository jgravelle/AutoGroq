
import datetime
import json
import os
import sqlite3
import streamlit as st
import uuid

from config import AUTOGEN_DB_PATH, MODEL_CHOICES, MODEL_TOKEN_LIMITS

# from typing import Optional
from utils.file_utils import create_agent_data, create_tool_data, sanitize_text
from utils.workflow_utils import get_workflow_from_agents


def export_to_autogen():
    # Check if the app is running on Streamlit Sharing
    url_params = st.query_params
    if "streamlit.app" in url_params.get("url", ""):
        st.warning("Exporting to Autogen is only possible with a locally running copy of AutoGroq™.")
        return

    db_path = AUTOGEN_DB_PATH
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
            skill_folder = os.path.join(project_root, "skills")
            for skill_name in st.session_state.selected_skills:
                if skill_name not in inserted_skills:
                    skill_file_path = os.path.join(skill_folder, f"{skill_name}.py")
                    with open(skill_file_path, 'r') as file:
                        skill_data = file.read()
                        skill_json = create_tool_data(skill_data)
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
                        inserted_skills.add(skill_name)  # Add the inserted skill to the set

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


def export_tool_to_autogen_as_skill(skill_name, edited_skill):
    print(f"Exporting skill '{skill_name}' to Autogen...")
    try:
        conn = sqlite3.connect(AUTOGEN_DB_PATH)
        cursor = conn.cursor()
        print("Connected to the database successfully.")

        skill_data = create_tool_data(edited_skill)
        print(f"Skill data: {skill_data}")
        skill_data = (
            str(uuid.uuid4()),  # Generate a unique ID for the skill
            'default',  # Set the user ID to 'default'
            datetime.datetime.now().isoformat(),
            edited_skill,
            skill_data['title'],
            skill_data['file_name']
        )
        print(f"Inserting skill data: {skill_data}")
        cursor.execute("INSERT INTO skills (id, user_id, timestamp, content, title, file_name) VALUES (?, ?, ?, ?, ?, ?)", skill_data)

        conn.commit()
        print("Skill exported to Autogen successfully.")
        conn.close()
        print("Database connection closed.")
        st.success(f"Skill '{skill_name}' exported to Autogen successfully!")
        st.experimental_rerun()
    except sqlite3.Error as e:
        st.error(f"Error exporting skill to Autogen: {str(e)}")
        print(f"Error exporting skill to Autogen: {str(e)}")



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