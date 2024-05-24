import datetime
import json
import os
import sqlite3
import streamlit as st
import uuid

from config import AUTOGEN_DB_PATH
from file_utils import create_agent_data, create_skill_data, sanitize_text
from ui_utils import get_workflow_from_agents


def export_to_autogen():
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
                agent_data = (
                    str(uuid.uuid4()),  # Generate a unique ID for the agent
                    'default',
                    datetime.datetime.now().isoformat(),
                    json.dumps(autogen_agent_data['config']),
                    autogen_agent_data['type'],
                    json.dumps(autogen_agent_data['skills'])
                )
                cursor.execute("INSERT INTO agents (id, user_id, timestamp, config, type, skills) VALUES (?, ?, ?, ?, ?, ?)", agent_data)
                print(f"Inserted agent: {formatted_agent_name}")

                script_dir = os.path.dirname(os.path.abspath(__file__))
                skill_folder = os.path.join(script_dir, "skills")
                skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]
                for skill_file in skill_files:
                    skill_name = os.path.splitext(skill_file)[0]
                    if agent.get(skill_name, False) and skill_name not in inserted_skills:
                        skill_file_path = os.path.join(skill_folder, skill_file)
                        with open(skill_file_path, 'r') as file:
                            skill_data = file.read()
                            skill_json = create_skill_data(skill_data)
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