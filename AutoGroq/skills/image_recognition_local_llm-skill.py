# Thanks to csabakecskemeti @ https://github.com/csabakecskemeti

# image recognition with local LLM
# I've use LMStudio to run the llava 1.5 13B model as a service
from openai import OpenAI
import base64
def get_image_description(image_path):
    """
    Sends an image to a local LLM model and retrieves a response describing the content of the image.
    Args:
        image_path (str): The file path to the image.
    Returns:
        str: The description of the image.
    """
    # Point to the local server
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
    # Read the image and encode it to base64:
    base64_image = ""
    try:
        image = open(image_path.replace("'", ""), "rb").read()
        base64_image = base64.b64encode(image).decode("utf-8")
    except:
        return "Couldn't read the image. Make sure the path is correct and the file exists."
    completion = client.chat.completions.create(
        model="local-model", # not used
        messages=[
            {
                "role": "system",
                "content": "This is a chat between a user and an assistant. The assistant is helping the user to describe an image.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
        stream=True
    )
    description = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            description += chunk.choices[0].delta.content
    return description