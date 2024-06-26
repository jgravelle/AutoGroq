# tools/fetch_web_content.py

import inspect
import json
import logging
import requests

from bs4 import BeautifulSoup
from models.tool_base_model import ToolBaseModel
from urllib.parse import urlparse, urlunparse


def fetch_web_content(url: str) -> str:
    """
    Fetches the text content from a website.

    Args:
        url (str): The URL of the website.

    Returns:
        str: The content of the website, or an error message if fetching failed.
    """
    try:
        cleaned_url = clean_url(url)
        logging.info(f"Fetching content from cleaned URL: {cleaned_url}")
        
        response = requests.get(cleaned_url, timeout=10)
        response.raise_for_status()
        
        logging.info(f"Response status code: {response.status_code}")
        logging.info(f"Response headers: {response.headers}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        logging.info(f"Parsed HTML structure: {soup.prettify()[:5000]}...")  # Log first 5000 characters of prettified HTML
        
        body_content = soup.body

        if body_content:
            content = body_content.get_text(strip=True)
            logging.info(f"Extracted text content (first 5000 chars): {content[:5000]}...")
            result = json.dumps({
                "status": "success",
                "url": cleaned_url,
                "content": content[:5000]  # Limit to first 5000 characters
            })
            print(f"DEBUG: fetch_web_content result: {result[:5000]}...")  # Debug print
            return result
        else:
            logging.warning(f"No <body> tag found in the content from {cleaned_url}")
            return json.dumps({
                "status": "error",
                "url": cleaned_url,
                "message": f"No <body> tag found in the content from {cleaned_url}"
            })

    except requests.RequestException as e:
        error_message = f"Error fetching content from {cleaned_url}: {str(e)}"
        logging.error(error_message)
        return json.dumps({
            "status": "error",
            "url": cleaned_url,
            "message": error_message
        })
    except Exception as e:
        error_message = f"Unexpected error while fetching content from {cleaned_url}: {str(e)}"
        logging.error(error_message)
        return json.dumps({
            "status": "error",
            "url": cleaned_url,
            "message": error_message
        })

# Create the ToolBaseModel instance
fetch_web_content_tool = ToolBaseModel(
    name="fetch_web_content",
    description="Fetches the text content from a website.",
    title="Fetch Web Content",
    file_name="fetch_web_content.py",
    content=inspect.getsource(fetch_web_content),
    function=fetch_web_content,
)

# Function to get the tool
def get_tool():
    return fetch_web_content_tool


def clean_url(url: str) -> str:
    """
    Clean and validate the URL.
    
    Args:
        url (str): The URL to clean.
    
    Returns:
        str: The cleaned URL.
    """
    url = url.strip().strip("'\"")
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    return urlunparse(parsed)