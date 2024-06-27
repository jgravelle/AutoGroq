# db_utils.py

import datetime
import json
import sqlite3
import streamlit as st
import traceback
import uuid

from configs.config import FRAMEWORK_DB_PATH
from utils.agent_utils import create_agent_data
from utils.file_utils import sanitize_text
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
                    print(f"Processing agent {index + 1}: {agent.name if hasattr(agent, 'name') else 'Unknown'}")
                    
                    if not isinstance(agent, dict):
                        agent_dict = agent.to_dict()
                    else:
                        agent_dict = agent

                    agent_name = agent_dict.get('name', f"Agent_{index}")
                    formatted_agent_name = sanitize_text(agent_name).lower().replace(' ', '_')
                    
                    autogen_agent_data, _ = create_agent_data(agent_dict)
                    
                    # Enhance the config with additional required fields
                    enhanced_config = autogen_agent_data['config']
                    enhanced_config.update({
                        "admin_name": "Admin",
                        "messages": [],
                        "max_round": 100,
                        "speaker_selection_method": "auto",
                        "allow_repeat_speaker": True
                    })
                    
                    # Enhance the system message
                    system_message = f"You are a helpful assistant that can act as {agent_name} who {agent_dict.get('description', '')}. {enhanced_config.get('system_message', '')}"
                    
                    agent_data = (
                        None,  # id is INTEGER, let SQLite auto-increment
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # updated_at
                        'guestuser@gmail.com',  # user_id (use a consistent user ID)
                        '0.0.1',  # version (match existing entries)
                        autogen_agent_data.get('type', 'assistant')[:9],  # type VARCHAR(9)
                        json.dumps(enhanced_config),
                        system_message
                    )
                    
                    print(f"Inserting agent data: {agent_data}")
                    
                    cursor.execute("""
                        INSERT INTO agent (id, created_at, updated_at, user_id, version, type, config, task_instruction) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, agent_data)
                    
                    print(f"Inserted agent: {formatted_agent_name}")

                    agent_id = cursor.lastrowid

                    # Insert agent-skill links
                    for tool in autogen_agent_data.get('tools', []):
                        skill_id = insert_or_get_skill(cursor, tool)
                        cursor.execute("INSERT INTO agentskilllink (agent_id, skill_id) VALUES (?, ?)", (agent_id, skill_id))

                    # Insert agent-model links
                    model_config = autogen_agent_data['config']['llm_config']['config_list'][0]
                    model_id = insert_or_get_model(cursor, model_config)
                    cursor.execute("INSERT INTO agentmodellink (agent_id, model_id) VALUES (?, ?)", (agent_id, model_id))

                except Exception as e:
                    print(f"Error processing agent {index + 1}: {str(e)}")
                    print(f"Agent data: {agent_dict}")
                    traceback.print_exc()

            # Insert workflow data
            try:
                workflow_data, _ = get_workflow_from_agents(st.session_state.agents)
                workflow_id = insert_workflow(cursor, workflow_data)

                # Insert workflow-agent links
                for idx, agent in enumerate(st.session_state.agents):
                    agent_dict = agent.to_dict() if not isinstance(agent, dict) else agent
                    cursor.execute("""
                        INSERT INTO workflowagentlink (workflow_id, agent_id, agent_type, sequence_id) 
                        VALUES (?, ?, ?, ?)
                    """, (workflow_id, agent_dict.get('id', str(uuid.uuid4())), agent_dict.get('type', 'assistant'), idx))
            except Exception as e:
                print(f"Error processing workflow: {str(e)}")
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
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            print(f"Unexpected error: {str(e)}")
            traceback.print_exc()


def insert_or_get_skill(cursor, tool):
    cursor.execute("SELECT id FROM skill WHERE name = ?", (tool['name'],))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        skill_data = (
            str(uuid.uuid4()),
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat(),
            'default',
            '1.0',
            tool['name'],
            tool['content'],
            tool.get('description', ''),
            json.dumps(tool.get('secrets', {})),
            json.dumps(tool.get('libraries', []))
        )
        cursor.execute("""
            INSERT INTO skill (id, created_at, updated_at, user_id, version, name, content, description, secrets, libraries) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, skill_data)
        return cursor.lastrowid

def insert_or_get_model(cursor, model_config):
    cursor.execute("SELECT id FROM model WHERE model = ?", (model_config['model'],))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        model_data = (
            str(uuid.uuid4()),
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat(),
            'default',
            '1.0',
            model_config['model'],
            model_config.get('api_key'),
            model_config.get('base_url'),
            model_config.get('api_type'),
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
        str(uuid.uuid4()),
        datetime.datetime.now().isoformat(),
        datetime.datetime.now().isoformat(),
        'default',
        '1.0',
        workflow_data['name'],
        workflow_data['description'],
        workflow_data['type'],
        workflow_data['summary_method'],
        json.dumps(workflow_data.get('sample_tasks', []))
    )
    cursor.execute("""
        INSERT INTO workflow (id, created_at, updated_at, user_id, version, name, description, type, summary_method, sample_tasks) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, workflow_insert_data)
    return cursor.lastrowid

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
