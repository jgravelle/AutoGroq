import datetime
import requests
import json
import os
import streamlit as st
import re
import time
from file_utils import create_agent_data, sanitize_text


def make_api_request(url, data, headers):
    time.sleep(2)  # Throttle the request to ensure at least 2 seconds between calls
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Please enter your API key.")
    
        headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API request failed with status {response.status_code}, response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error: Request failed {e}")
        return None


def rephrase_prompt(user_request):
    print("Executing rephrase_prompt()")
    try:
        api_key = os.environ["GROQ_API_KEY"]
    except KeyError:
        st.error("GROQ_API_KEY not found. Please enter your API key.")
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    refactoring_prompt = f"""
    Refactor the following user request into an optimized prompt for an LLM,
    focusing on clarity, conciseness, and effectiveness. Provide specific details
    and examples where relevant. Do NOT reply with a direct response to the request;
    instead, rephrase the request as a well-structured prompt, and return ONLY that rephrased prompt.\n\nUser request: \"{user_request}\"\n\nrephrased:
    """

    groq_request = {
        "model": st.session_state.model,  # Use the selected model from the session state
        "temperature": 0.5,
        "max_tokens": 100,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "user",
                "content": refactoring_prompt,
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=groq_request, headers=headers)
        time.sleep(2)
        response.raise_for_status()
        response_data = response.json()
        if "choices" in response_data and len(response_data["choices"]) > 0:
            rephrased = response_data["choices"][0]["message"]["content"]
            return rephrased.strip()
        else:
            print("Error: Empty response received from the API.")
            return None
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        print(f"Error occurred while rephrasing the prompt:")
        print(f"Request URL: {url}")
        print(f"Request Headers: {headers}")
        print(f"Request Payload: {json.dumps(groq_request, indent=2)}")
        print(f"Response Content: {response.text}")
        print(f"Error Details: {str(e)}")
        return None


def get_agents_from_text(text):
    try:
        api_key = os.environ["GROQ_API_KEY"]
    except KeyError:
        st.error("GROQ_API_KEY not found. Please enter your API key.")
        return [], []

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    groq_request = {
        "model": st.session_state.model,
        "temperature": 0.5,
        "max_tokens": st.session_state.max_tokens,
        "top_p": 1,
        "stop": "TERMINATE",
        "messages": [
            {
                "role": "system",
                "content": f"""
                You are an expert system designed to identify and recommend the optimal team of experts
                required to fulfill this specific user's request: $userRequest Your analysis should
                consider the complexity, domain, and specific needs of the request to assemble
                a multidisciplinary team of experts. Each recommended expert should come with a defined role,
                a brief description of their expertise, their skill set, and the tools they would utilize
                to achieve the user's goal. The first agent must be qualified to manage the entire project,
                aggregate the work done by all the other agents, and produce a robust, complete,
                and reliable solution. Return the results in JSON values labeled as expert_name, description,
                skills, and tools. Their 'expert_name' is their title, not their given name.
                Skills and tools are arrays (one expert can have multiple skills and use multiple tools).
                Return ONLY this JSON response, with no other narrative, commentary, synopsis,
                or superfluous remarks/text of any kind. Tools should be single-purpose methods,
                very specific and narrow in their scope, and not at all ambiguous (e.g.: 'add_numbers'
                would be good, but simply 'do_math' would be bad) Skills and tools should be all lower case
                with underscores instead of spaces, and they should be named per their functionality,
                e.g.: calculate_surface_area, or search_web
                """
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }

    response_data = make_api_request(url, groq_request, headers)
    if response_data and "choices" in response_data and response_data["choices"]:
        content_json_string = response_data["choices"][0].get("message", {}).get("content", "")
        try:
            content_json = json.loads(content_json_string)
            autogen_agents = []
            crewai_agents = []
            if isinstance(content_json, list):
                for agent_data in content_json:
                    if isinstance(agent_data, dict):
                        expert_name = agent_data.get("expert_name", "")
                        description = agent_data.get("description", "")
                        skills = agent_data.get("skills", [])
                        tools = agent_data.get("tools", [])
                    else:
                        expert_name = ""
                        description = ""
                        skills = []
                        tools = []
                    autogen_agent_data, crewai_agent_data = create_agent_data(expert_name, description, skills, tools)
                    autogen_agents.append(autogen_agent_data)
                    crewai_agents.append(crewai_agent_data)
            elif isinstance(content_json, dict):
                for expert_name, agent_data in content_json.items():
                    description = agent_data.get("description", "")
                    skills = agent_data.get("skills", [])
                    tools = agent_data.get("tools", [])
                    autogen_agent_data, crewai_agent_data = create_agent_data(expert_name, description, skills, tools)
                    autogen_agents.append(autogen_agent_data)
                    crewai_agents.append(crewai_agent_data)
            return autogen_agents, crewai_agents
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON response: {e}, Response content: {content_json_string}")
    else:
        if response_data is not None:
            print("Error: Unexpected response format from the API. Full response: ", response_data)
        else:
            print("Error: No response data received from API.")
    return [], []


def create_agent_data(expert_name, description, skills, tools):
    autogen_agent_data = {
        "type": "assistant",
        "config": {
            "name": expert_name,
            "llm_config": {
                "config_list": [{"model": "gpt-4-1106-preview"}],
                "temperature": 0.1,
                "timeout": 600,
                "cache_seed": 42
            },
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 8,
            "system_message": f"You are a helpful assistant that can act as {expert_name} who {description}."
        },
        "description": description,
        "skills": skills,
        "tools": tools
    }
    crewai_agent_data = {
        "name": expert_name,
        "description": description,
        "skills": skills,
        "tools": tools,
        "verbose": True,
        "allow_delegation": True
    }
    return autogen_agent_data, crewai_agent_data



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
    try:
        api_key = os.environ["GROQ_API_KEY"]
    except KeyError:
        st.error("GROQ_API_KEY not found. Please enter your API key.")
        return None
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
            time.sleep(2)
            response.raise_for_status()
            try:
                response_data = response.json()
                if "summary" in response_data:
                    summary = response_data["summary"].strip()
                else:
                    summary = ""
            except ValueError:
                summary = response.text.strip()
        except requests.exceptions.RequestException as e:
            print(f"Error occurred while making the request: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    api_key = os.environ.get("GROQ_API_KEY")  # Get the Groq API key from environment variables
    
    if not api_key:
        raise ValueError("Groq API key not found in environment variables.")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
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
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        time.sleep(2)
        response.raise_for_status()
        response_data = response.json()
        
        if "choices" in response_data and len(response_data["choices"]) > 0:
            message_content = response_data["choices"][0]["message"]["content"]
            return message_content
        else:
            print("Error: Unexpected response format from the Groq API.")
            print("Response data:", response_data)
            return None
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        print(f"Error occurred while making the request to Groq API:")
        print(f"Request URL: {url}")
        print(f"Request Headers: {headers}")
        print(f"Request Data: {json.dumps(data, indent=2)}")
        print(f"Response Content: {response.text}")
        print(f"Error Details: {str(e)}")
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