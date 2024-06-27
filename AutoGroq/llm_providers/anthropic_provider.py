# llm_providers/anthropic_provider.py

import anthropic
import streamlit as st

from llm_providers.base_provider import BaseLLMProvider

class AnthropicProvider:
    def __init__(self, api_url, api_key):
        self.api_key = api_key
        self.api_url = api_url or "https://api.anthropic.com/v1/messages"


    def get_available_models(self):
        return {
            "claude-3-5-sonnet-20240620": 200000,
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 100000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000,
        }
                

    def process_response(self, response):
        if response is not None:
            return {
                "choices": [
                    {
                        "message": {
                            "content": response.content[0].text
                        }
                    }
                ]
            }
        return None
    

    def send_request(self, data):
        try:
            response = self.client.messages.create(
                model=data['model'],
                max_tokens=data.get('max_tokens', 1000),
                temperature=data.get('temperature', st.session_state.temperature),
                messages=data['messages']
            )
            return response
        except anthropic.APIError as e:
            print(f"Anthropic API error: {e}")
            return None
