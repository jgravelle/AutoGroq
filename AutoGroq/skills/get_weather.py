import requests
from typing import Optional

def get_weather(zipcode: str, api_key: str) -> Optional[dict]:
    """
    Fetches the current weather for the given ZIP code using the OpenWeatherMap API.

    Args:
        zipcode (str): The ZIP code for which to fetch the weather.
        api_key (str): Your OpenWeatherMap API key.

    Returns:
        Optional[dict]: A dictionary containing the weather information, or None if an error occurs.
    """
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "zip": zipcode,
        "appid": api_key,
        "units": "imperial"  # Use "metric" for Celsius
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

# Example usage:
# api_key = "your_openweathermap_api_key"
# weather = get_weather("94040", api_key)
# print(weather)
