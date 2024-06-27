# tools/code_test.py

import inspect
import subprocess
import tempfile
from models.tool_base_model import ToolBaseModel

def test_code(language: str, code: str, test_cases: str) -> str:
    """
    Tests the given code with provided test cases.

    Args:
        language (str): The programming language of the code (e.g., "Python", "JavaScript").
        code (str): The code to be tested.
        test_cases (str): A string containing test cases, each on a new line.

    Returns:
        str: The test results as a string.
    """
    if language.lower() != "python":
        return f"Testing for {language} is not supported yet."

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file.write("\n\n# Test cases\n")
        temp_file.write(test_cases)
        temp_file_name = temp_file.name

    try:
        result = subprocess.run(['python', temp_file_name], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"Tests passed successfully.\nOutput:\n{result.stdout}"
        else:
            return f"Tests failed.\nError:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Test execution timed out."
    except Exception as e:
        return f"An error occurred during testing: {str(e)}"

code_test_tool = ToolBaseModel(
    name="test_code",
    description="Tests the given code with provided test cases.",
    title="Code Tester",
    file_name="code_test.py",
    content=inspect.getsource(test_code),
    function=test_code,
)

def get_tool():
    return code_test_tool
