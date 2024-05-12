import requests
import streamlit as st
import time

from config import RETRY_TOKEN_LIMIT


def make_api_request(url, data, headers, api_key):
    time.sleep(2)  # Throttle the request to ensure at least 2 seconds between calls
    try:
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Please enter your API key.")
        headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            error_message = response.json().get("error", {}).get("message", "")
            st.error(f"Rate limit reached for the current model. If you click 'Regenerate' again, we'll retry with a reduced token count.  Or you can try selecting a different model.")
            st.error(f"Error details: {error_message}")
            return None
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