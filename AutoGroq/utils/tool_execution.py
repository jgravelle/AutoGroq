# utils/tool_execution.py

import inspect

from utils.sandbox import execute_in_sandbox

def execute_tool(tool_name, function_map, *args, **kwargs):
    if tool_name not in function_map:
        raise ValueError(f"Tool '{tool_name}' not found in function map")
    
    return execute_in_sandbox(tool_name, *args)


# def execute_tool(tool_name, function_map, *args, **kwargs):
#     if tool_name not in function_map:
#         raise ValueError(f"Tool '{tool_name}' not found in function map")
    
#     tool_function = function_map[tool_name]
    
#     # Check if the function is a method that requires 'self'
#     if inspect.ismethod(tool_function):
#         # If it's a method, we need to pass 'self' as the first argument
#         return tool_function(*args, **kwargs)
#     else:
#         # If it's a regular function, we can call it directly
#         return tool_function(*args, **kwargs)

def get_tool_signature(tool_name, function_map):
    if tool_name not in function_map:
        raise ValueError(f"Tool '{tool_name}' not found in function map")
    
    tool_function = function_map[tool_name]
    return inspect.signature(tool_function)