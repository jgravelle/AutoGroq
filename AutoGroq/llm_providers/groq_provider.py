import requests
from auth_utils import get_api_key
from llm_providers.base_provider import BaseLLMProvider

class GroqProvider(BaseLLMProvider):
    def __init__(self, api_url):
        self.api_key = get_api_key()
        self.api_url = api_url


    def send_request(self, data):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(self.api_url, json=data, headers=headers)
        return response

    def process_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed with status code {response.status_code}")
