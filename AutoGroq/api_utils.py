import requests
import json
import streamlit as st
import re

def make_api_request(url, data, headers):
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(f"Debug: API request sent: {json.dumps(data)}")
        print(f"Debug: API response received: {response.text}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: API request failed with status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")
        return None

def rephrase_prompt(user_request):
    url = "https://j.gravelle.us/APIs/Groq/groqApiRephrasePrompt.php"
    data = {"user_request": user_request}
    headers = {"Content-Type": "application/json"}
    response_data = make_api_request(url, data, headers)
    if response_data:
        return response_data.get("rephrased", "")
    return ""

def get_agents_from_text(text):
    url = "https://j.gravelle.us/APIs/Groq/groqApiGetAgentsFromPrompt.php"
    data = {"user_request": text}
    headers = {"Content-Type": "application/json"}
    response_data = make_api_request(url, data, headers)
    if response_data:
        return response_data
    return []

def send_request_to_groq_api(expert_name, request):
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
        message_content = response_data["choices"][0]["message"]["content"]
        return message_content
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

    code_blocks.extend(html_blocks)
    code_blocks.extend(js_blocks)
    code_blocks.extend(css_blocks)

    code_blocks = [block.strip() for block in code_blocks]
    return "\n\n".join(code_blocks)