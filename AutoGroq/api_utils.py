import datetime
import requests
import json
import streamlit as st
import re
import time

from file_utils import create_agent_data, sanitize_text
from skills.stock_info_skill import GetStockInfo


def get_next_agent(last_agent, last_comment, expert_names, enhanced_prompt):
    url = "https://j.gravelle.us/APIs/Groq/groqApiChatCoordinator.php"
    data = {
        "last_agent": last_agent,
        "last_contribution": last_comment,
        "agents": expert_names,  # Pass the expert names instead of the entire agent objects
        "enhanced_prompt": enhanced_prompt
    }
    headers = {"Content-Type": "application/json"}

    print("Payload:")
    print(json.dumps(data, indent=2))

    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Debug: RESPONSE: {response.text}")
        response.raise_for_status()
        response_data = response.json()
        print(f"Debug: RESPONSE DATA: {response_data}")
        next_agent = response_data["next_agent"].strip()
        assignment = response_data["assignment"].strip()

        if next_agent not in expert_names:
            print(f"Warning: The returned next agent '{next_agent}' is not one of the provided expert names: {expert_names}")
            print("Falling back to the last agent.")
            next_agent = last_agent
            assignment = "Please continue working on the task based on the previous assignment and the enhanced prompt."

        return f"Next Suggested Agent: {next_agent}\n\nAssignment: {assignment}\n"
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        print(f"Error occurred while coordinating agents:")
        print(f"Request URL: {url}")
        print(f"Request Headers: {headers}")
        print(f"Request Payload: {json.dumps(data, indent=2)}")
        print(f"Response Content: {response.text}")
        print(f"Error Details: {str(e)}")
        return "Error occurred while coordinating agents."
    except Exception as e:
        print(f"An unexpected error occurred:")
        print(f"Error Details: {str(e)}")
        return "Error occurred while coordinating agents."


def extract_tasks(comment, agents):
    url = "https://j.gravelle.us/APIs/Groq/groqApiTaskExtractor.php"
    data = {
        "comment": comment,
        "agents": agents
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    response_data = response.json()

    return response_data


def make_api_request(url, data, headers):
    print("Executing make_api_request()")
    max_retries = 3
    retry_delay = 1  # in seconds

    for retry in range(max_retries):
        try:
            time.sleep(1)
            response = requests.post(url, data=json.dumps(data), headers=headers)
            print(f"Debug: API request sent: {json.dumps(data)}")
            print(f"Debug: API response received: {response.text}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    print(f"Error: Unexpected response format: {response.text}")
                    return None
            else:
                st.error(f"Error: API request failed with status code {response.status_code}. Retrying...")
                if retry < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return None
        except requests.exceptions.RequestException as e:
            st.error(f"Error: {str(e)}. Retrying...")
            if retry < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                return None
    
    return None


def rephrase_prompt(user_request):
    print("Executing rephrase_prompt()")
    url = "https://j.gravelle.us/APIs/Groq/groqApiRephrasePrompt.php"
    data = {"user_request": user_request}
    headers = {"Content-Type": "application/json"}
    response_data = make_api_request(url, data, headers)
    if response_data:
        rephrased = response_data.get("rephrased", "")
        if rephrased:
            return rephrased
        else:
            print("Error: Empty response received from the API.")
    return None



def get_agents_from_text(text):
    url = "https://j.gravelle.us/APIs/Groq/groqApiGetAgentsFromPrompt.php"
    data = {"user_request": text}
    headers = {"Content-Type": "application/json"}
    response_data = make_api_request(url, data, headers)
    if response_data:
        autogen_agents = []
        crewai_agents = []
        
        if isinstance(response_data, dict):
            for expert_name, agent_data in response_data.items():
                expert_name = agent_data.get("expert_name", "")
                description = agent_data.get("description", "")
                skills = agent_data.get("skills", [])
                tools = agent_data.get("tools", [])
                autogen_agent_data, crewai_agent_data = create_agent_data(expert_name, description, skills, tools)
                autogen_agents.append(autogen_agent_data)
                crewai_agents.append(crewai_agent_data)
        elif isinstance(response_data, list):
            for agent_data in response_data:
                expert_name = agent_data.get("expert_name", "")
                description = agent_data.get("description", "")
                skills = agent_data.get("skills", [])
                tools = agent_data.get("tools", [])
                autogen_agent_data, crewai_agent_data = create_agent_data(expert_name, description, skills, tools)
                autogen_agents.append(autogen_agent_data)
                crewai_agents.append(crewai_agent_data)
        else:
            print("Error: Unexpected response format from the API.")
            
        return autogen_agents, crewai_agents
    
    return [], []



def get_workflow_from_agents(agents):
    current_timestamp = datetime.datetime.now().isoformat()

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
            "skills": None
        },
        "receiver": {
            "type": "groupchat",
            "config": {
                "name": "group_chat_manager",
                "llm_config": {
                    "config_list": [
                        {
                            "model": "gpt-4-1106-preview"
                        }
                    ],
                    "temperature": 0.1,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": None,
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
            "skills": None
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
                            "model": "gpt-4-1106-preview"
                        }
                    ],
                    "temperature": 0.1,
                    "cache_seed": 42,
                    "timeout": 600,
                    "max_tokens": None,
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
            "skills": None  # Set skills to null only in the workflow JSON
        }
        workflow["receiver"]["groupchat_config"]["agents"].append(agent_config)

    crewai_agents = []
    for index, agent in enumerate(agents):
        agent_name = agent["config"]["name"]
        description = agent["description"]
        _, crewai_agent_data = create_agent_data(agent_name, description, agent.get("skills"), agent.get("tools"))
        crewai_agents.append(crewai_agent_data)

    return workflow, crewai_agents


# api_utils.py
def send_request_to_groq_api(expert_name, request):
    url = "https://j.gravelle.us/APIs/Groq/groqApiStockDiscerner.php"
    
    # Extract the text that follows "Additional input:" from the request
    additional_input_index = request.find("Additional input:")
    if additional_input_index != -1:
        additional_input = request[additional_input_index + len("Additional input:"):].strip()
    else:
        additional_input = ""
    
    if additional_input:
        data = {"user_request": additional_input}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            try:
                response_data = response.json()
                if "summary" in response_data:
                    summary = response_data["summary"].strip()
                else:
                    summary = ""
            except ValueError:
                summary = response.text.strip()
            
            if summary.startswith("LOOKUP"):
                ticker = summary.split("LOOKUP")[1].strip()
                stock_info = GetStockInfo(ticker)
                request += f"\n\nStock info: {stock_info}"
            
        except requests.exceptions.RequestException as e:
            print(f"Error occurred while making the request: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    url = "https://j.gravelle.us/APIs/Groq/groqAPI.php"
    data = {
        "model": st.session_state.model,
        "temperature": 0.5,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "system",
                "content": "You are a chatbot capable of anything and everything."
            },
            {
                "role": "user",
                "content": request
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    response_data = make_api_request(url, data, headers)
    if response_data:
        if "choices" in response_data and len(response_data["choices"]) > 0:
            message_content = response_data["choices"][0]["message"]["content"]
            return message_content
        else:
            print("Error: Unexpected response format from the Groq API.")
            print("Response data:", response_data)
            return None
    return ""


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