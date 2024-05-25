# Thanks to marc-shade:  https://github.com/marc-shade
# Ollama only?  -jjg

from typing import List
import json
import requests
import io
import base64
from PIL import Image
from pathlib import Path
import uuid # Import the uuid library

# Format: protocol://server:port
base_url = "http://0.0.0.0:7860"

def generate_sd_images(query: str, image_size: str = "512x512", team_name: str = "default") -> List[str]:
    """
    Function to paint, draw or illustrate images based on the users query or request. 
    Generates images locally with the automatic1111 API and saves them to disk.  
    Use the code below anytime there is a request to create an image.

    :param query: A natural language description of the image to be generated.
    :param image_size: The size of the image to be generated. (default is "512x512")
    :param team_name: The name of the team to associate the image with.
    :return: A list containing a single filename for the saved image.
    """
    # Split the image size string at "x"
    parts = image_size.split("x")
    image_width = parts[0]
    image_height = parts[1]

    # list of file paths returned to AutoGen
    saved_files = []

    payload = {
        "prompt": query,
        "steps": 40,
        "cfg_scale": 7,
        "denoising_strength": 0.5,
        "sampler_name": "DPM++ 2M Karras",
        "n_iter": 1,
        "batch_size": 1, # Ensure only one image is generated per batch
        "override_settings": {
             'sd_model_checkpoint': "starlightAnimated_v3",
        }
    }

    api_url = f"{base_url}/sdapi/v1/txt2img"
    response = requests.post(url=api_url, json=payload)

    if response.status_code == 200:
        r = response.json()
        # Access only the final generated image (index 0)
        encoded_image = r['images'][0] 

        image = Image.open(io.BytesIO(base64.b64decode(encoded_image.split(",", 1)[0])))
        
        # --- Generate a unique filename with team name and UUID ---
        unique_id = str(uuid.uuid4())[:8] # Get a short UUID
        file_name = f"images/{team_name}_{unique_id}_output.png"
        
        file_path = Path(file_name)
        image.save(file_path)
        print(f"Image saved to {file_path}")

        saved_files.append(str(file_path))
    else:
        print(f"Failed to download the image from {api_url}")

    return saved_files