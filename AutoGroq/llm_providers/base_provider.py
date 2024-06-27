from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    def __init__(self, api_key, api_url=None):
        pass

    @abstractmethod
    def send_request(self, data):
        pass

    @abstractmethod
    def process_response(self, response):
        pass

    @abstractmethod
    def get_available_models(self):
        pass