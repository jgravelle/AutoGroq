# utils/tool_execution.py

import inspect
import logging

from utils.sandbox import execute_in_sandbox


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def execute_tool(tool_name, function_map, *args, **kwargs):
    logger.debug(f"Attempting to execute tool: {tool_name}")
    logger.debug(f"Available tools: {list(function_map.keys())}")
    logger.debug(f"Args: {args}")
    logger.debug(f"Kwargs: {kwargs}")
    
    if tool_name not in function_map:
        raise ValueError(f"Tool '{tool_name}' not found in function map")
    
    tool_function = function_map[tool_name]
    logger.debug(f"Tool function: {tool_function}")
    
    try:
        result = tool_function(*args, **kwargs)
        logger.debug(f"Tool execution result: {result[:500]}...")  # Log first 500 characters of result
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
        raise


def get_tool_signature(tool_name, function_map):
    if tool_name not in function_map:
        raise ValueError(f"Tool '{tool_name}' not found in function map")
    
    tool_function = function_map[tool_name]
    return inspect.signature(tool_function)