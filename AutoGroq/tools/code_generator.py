# tools/code_generator.py

import inspect
import json
import logging
from models.tool_base_model import ToolBaseModel
from utils.api_utils import get_api_key, get_llm_provider
import streamlit as st

logger = logging.getLogger(__name__)

def generate_code(request: str, language: str = "Python") -> str:
    logger.debug(f"Generating code for request: {request}")
    logger.debug(f"Language: {language}")
    
    if not request.strip():
        return "Error: No specific code generation request provided."

    prompt = f"""
    You are an advanced AI language model with expertise in software development. Your task is to generate the best possible software solution for the following request:
    **Request:**
    {request}
    **Language:**
    {language}
    Please ensure that the code follows best practices for {language}, is optimized for performance and maintainability, and includes comprehensive comments explaining each part of the code. Additionally, provide any necessary context or explanations to help understand the implementation. The solution should be robust, scalable, and adhere to industry standards.
    If there are multiple ways to solve the problem, choose the most efficient and elegant approach. If any libraries or frameworks are beneficial, include their usage with appropriate explanations.
    Begin your response with a brief overview of the approach you are taking, and then provide the complete code.
    Example overview: "To solve the problem of {request}, we will implement a {{specific algorithm/pattern}} using {{specific features/libraries of the language}}. This approach ensures {{benefits of the approach}}."
    Here is the code:
    """

    api_key = get_api_key()
    llm_provider = get_llm_provider(api_key=api_key)
    
    llm_request_data = {
        "model": st.session_state.get('model', 'default'),
        "temperature": st.session_state.get('temperature', 0.7),
        "max_tokens": st.session_state.get('max_tokens', 2000),
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert code generator."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = llm_provider.send_request(llm_request_data)
        logger.debug(f"LLM response status code: {response.status_code}")
        logger.debug(f"LLM response content: {response.text[:500]}...")  # Log first 500 characters of response
        
        if response.status_code == 200:
            response_data = llm_provider.process_response(response)
            if "choices" in response_data and response_data["choices"]:
                generated_code = response_data["choices"][0]["message"]["content"]
                return generated_code.strip()
            else:
                return "Error: Unexpected response format from the language model."
        else:
            return f"Error: Received status code {response.status_code} from the language model API."
    except Exception as e:
        logger.error(f"Error generating code: {str(e)}", exc_info=True)
        return f"Error generating code: {str(e)}"

code_generator_tool = ToolBaseModel(
    name="generate_code",
    description="Generates code for a specified feature in a given programming language.",
    title="Code Generator",
    file_name="code_generator.py",
    content=inspect.getsource(generate_code),
    function=generate_code,
)

def get_tool():
    return code_generator_tool