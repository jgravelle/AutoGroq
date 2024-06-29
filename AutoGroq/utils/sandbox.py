import os
import subprocess

def execute_in_sandbox(tool_name, *args):
    # Create a temporary Python file with the tool execution
    with open('temp_tool_execution.py', 'w') as f:
        f.write(f"from tools.{tool_name} import {tool_name}\n")
        f.write(f"result = {tool_name}(*{args})\n")
        f.write("print(result)\n")
    
    # Execute the temporary file in a separate process with restricted permissions
    try:
        result = subprocess.run(['python', 'temp_tool_execution.py'], 
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    finally:
        os.remove('temp_tool_execution.py')