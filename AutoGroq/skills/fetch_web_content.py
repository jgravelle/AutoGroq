from typing import Optional
import requests
import collections
collections.Callable = collections.abc.Callable
from bs4 import BeautifulSoup

def fetch_web_content(url: str) -> Optional[str]:
    """
    Fetches the text content from a website.

    Args:
        url (str): The URL of the website.

    Returns:
        Optional[str]: The content of the website.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)

        # Check for successful access to the webpage
        if response.status_code == 200:
            # Parse the HTML content of the page using BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract the content of the <body> tag
            body_content = soup.body

            if body_content:
                # Return all the text in the body tag, stripping leading/trailing whitespaces
                return " ".join(body_content.get_text(strip=True).split())
            else:
                # Return None if the <body> tag is not found
                return None
        else:
            # Return None if the status code isn't 200 (success)
            return None
    except requests.RequestException:
        # Return None if any request-related exception is caught
        return None