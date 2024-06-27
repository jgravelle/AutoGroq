
import json
import os
import requests

from llm_providers.base_provider import BaseLLMProvider

class OpenaiProvider:
    def __init__(self, api_url, api_key):
        self.api_key = api_key
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"


    def get_available_models(self):
        response = requests.get("https://api.openai.com/v1/models", headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        if response.status_code == 200:
            models_data = response.json().get("data", [])
            return {model["id"]: model.get("max_tokens", 4096) for model in models_data}
        else:
            raise Exception(f"Failed to retrieve models: {response.status_code}")
    

    def process_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed with status code {response.status_code}")


    def send_request(self, data):
        print("self.api_url: ", self.api_url)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Ensure data is a JSON string
        if isinstance(data, dict):
            json_data = json.dumps(data)
        else:
            json_data = data
        
        response = requests.post(self.api_url, data=json_data, headers=headers)
        print("response.status_code: ", response.status_code)
        print("response.text: ", response.text)
        return response
    