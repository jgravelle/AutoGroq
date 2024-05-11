import re
import requests
import streamlit as st
import time

def make_api_request(url, data, headers, api_key):
    time.sleep(2)  # Throttle the request to ensure at least 2 seconds between calls
    try:
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
    

def send_request_to_groq_api(expert_name, request, api_key):
    temperature_value = st.session_state.get('temperature', 0.1)
    if api_key is None:
        if 'api_key' in st.session_state and st.session_state.api_key:
            api_key = st.session_state.api_key
        else:
            st.error("API key not found. Please enter your API key.")
            return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    data = {
        "model": st.session_state.model,
        "temperature": temperature_value,
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
        response = make_api_request(url, data, headers, api_key)
        if response:
            if "choices" in response and len(response["choices"]) > 0:
                message_content = response["choices"][0]["message"]["content"]
                return message_content
            else:
                print("Error: Unexpected response format from the Groq API.")
                print("Response data:", response)
                return None
    except Exception as e:
        print(f"Error occurred while making the request to Groq API: {str(e)}")
        return None