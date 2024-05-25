#  Thanks to MADTANK:  https://github.com/madtank

import requests
from bs4 import BeautifulSoup


def save_webpage_as_text(url, output_filename):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Initialize BeautifulSoup to parse the content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract text from the BeautifulSoup object
    # You can adjust the elements you extract based on your needs
    text = soup.get_text(separator='\n', strip=True)
    
    # Save the extracted text to a file
    with open(output_filename, 'w', encoding='utf-8') as file:
        file.write(text)
    
    # Return the file path
    return output_filename


# Example usage:
# url = 'https://j.gravelle.us        /'
# output_filename = 'webpage_content.txt'
# file_path = save_webpage_as_text(url, output_filename)
# print("File saved at:", file_path)


# For a list of urls:
# urls = ['http://example.com', 'http://example.org']
# for i, url in enumerate(urls):
#     output_filename = f'webpage_content_{i}.txt'
#     save_webpage_as_text(url, output_filename)