# Thanks to aj47:  https://github.com/aj47 

import subprocess

def execute_powershell_command(command):
    """
    Execute a command in PowerShell from Python.
    
    :param command: The PowerShell command to execute as a string.
    :return: The output of the command as a string.
    """
    # Ensure the command is executed in PowerShell
    cmd = ['powershell', '-Command', command]
    
    # Execute the command and capture the output
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"An error occurred: {e.stderr}"

# Example usage
if __name__ == "__main__":
    command = "Get-Date"  # Example command to get the current date and time
    output = execute_powershell_command(command)
    print(output)