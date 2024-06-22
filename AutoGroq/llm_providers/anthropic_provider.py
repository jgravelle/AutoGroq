# llm_providers/anthropic_provider.py

import anthropic
import streamlit as st

from llm_providers.base_provider import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key, api_url=None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.api_url = api_url 

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