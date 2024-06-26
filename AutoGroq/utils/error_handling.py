import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_error(error_message):
    logging.error(error_message)

def log_tool_execution(tool_name, args, result):
    logging.info(f"Executed tool: {tool_name} with args: {args}. Result: {result}")