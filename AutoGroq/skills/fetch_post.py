# Note to AutoGen, please follow these instructions to run the skill properly
# Example of fetching messages using the fetch_post skill:
# from skills import fetch_post CONFIG
# response = fetch_post(action='fetch')
# print(response)

# # Ensure that you replace the above 'fetch' action with 'post' when you want to post a message,
# # and provide the necessary 'message' arguments.
# Example of posting messages using the fetch_post skill:
# from skills import fetch_post
# response = fetch_post(action='post', message=<message>)
# print(response)

import requests
import logging
from datetime import datetime

# Global configuration variables
USERNAME = "AutoGen-Proxy-User"  # Change this value to your user name
LAMBDA_URL = "https://m7cjbptdpsuj56rrx7e6qhq7ou0svley.lambda-url.us-west-2.on.aws/"  # Playground Chat
TOPICS = ["autogen"]
PERSONALITY = "Technical"

def fetch_post(action='fetch', message=None, username=None):
    """
    Processes the given action, either fetching or posting a message.
    """
    global USERNAME
    username = username or USERNAME
    if action == 'fetch':
        return fetch_messages()
    elif action == 'post':
        return post_message(message, username)
    else:
        return "Invalid action specified."

def fetch_messages():
    """
    Fetches messages from the lambda URL endpoint.
    """
    global LAMBDA_URL, TOPICS, PERSONALITY
    lambda_url = LAMBDA_URL + "fetch"

    try:
        response = requests.get(lambda_url)
        if response.ok:
            raw_messages = response.json()
            formatted_messages = format_messages(raw_messages, TOPICS, PERSONALITY)
            return {"messages": formatted_messages, "system_message": system_message(TOPICS, PERSONALITY)}
        else:
            logging.error(f"Failed to fetch posts. Response: {response.text}")
            return "Failed to fetch posts."
    except Exception as e:
        logging.exception(f"An error occurred while fetching posts: {str(e)}")
        return f"An error occurred while fetching posts: {str(e)}"

def post_message(message, username):
    """
    Posts a message to the lambda URL endpoint.
    """
    global LAMBDA_URL
    lambda_url = LAMBDA_URL + "post"
    payload = {'username': username, 'message': message}

    try:
        response = requests.post(lambda_url, json=payload)
        if response.ok:
            return f"Message from {username}: '{message}' posted successfully to Fetch Post."
        else:
            logging.error(f"Failed to post message. Response: {response.text}")
            return "Failed to post message."
    except Exception as e:
        logging.exception("An error occurred while posting the message.")
        return f"An error occurred while posting the message: {str(e)}"

def format_messages(raw_messages, topics, personality):
    """
    Formats the raw messages into a readable structure based on the topics and personality.
    
    Parameters:
    - raw_messages (list): The list of message dictionaries to format.
    - topics (list): The list of topics to focus on.
    - personality (str): The personality setting for the messages.
    
    Returns:
    - A list of formatted message dictionaries.
    """
    formatted_messages = []
    for message in raw_messages:
        timestamp = datetime.fromtimestamp(message['Timestamp'])
        formatted_time = timestamp.strftime('%H:%M:%S %m/%d/%Y')
        formatted_messages.append({
            "Timestamp": formatted_time,
            "Message": message['Message'],
            "Username": message['Username'],
            "MessageID": message['MessageID']
        })
    return formatted_messages

def system_message(topics, personality):
    """
    Generates a system message for fetched posts, providing context for the AI.
    
    Parameters:
    - topics (list): The list of topics that the messages are about.
    - personality (str): The personality setting of the AI.
    
    Returns:
    - A formatted string with the system message.
    """
    return (
        "AutoGenStudio, you've fetched the latest messages from the Fetch Post. "
        "Focus on topics: " + ', '.join(topics) + ". "
        "Use this information for formulating responses, if needed. "
        "Personality setting: " + personality + "."
    )

# Example usage of the fetch_post function
# response = fetch_post(action='fetch')
# print(response)
