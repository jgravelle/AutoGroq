
import json
import requests
from llm_providers.base_provider import BaseLLMProvider

class LmstudioProvider(BaseLLMProvider):
    def __init__(self, api_url):
        self.api_url = api_url


    def send_request(self, data):
        headers = {
            "Content-Type": "application/json",
        }

        # Construct the request data in the format expected by the LM Studio API
        lm_studio_request_data = {
            "model": data["model"],
            "messages": data["messages"],
            "temperature": data.get("temperature", 0.1),
            "max_tokens": data.get("max_tokens", 2048),
            "stop": data.get("stop", "TERMINATE"),
        }

        # Ensure data is a JSON string
        if isinstance(lm_studio_request_data, dict):
            json_data = json.dumps(lm_studio_request_data)
        else:
            json_data = lm_studio_request_data

        response = requests.post(f"{self.api_url}", data=json_data, headers=headers)
        return response

    def process_response(self, response):
        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data:
                content = response_data["choices"][0]["message"]["content"]
                return {
                    "choices": [
                        {
                            "message": {
                                "content": content.strip()
                            }
                        }
                    ]
                }
            else:
                raise Exception("Unexpected response format. 'choices' field missing.")
        else:
            raise Exception(f"Request failed with status code {response.status_code}")