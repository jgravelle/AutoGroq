# Thanks to aj47:  https://github.com/aj47

import os

def save_file_to_disk(contents, file_name):
    """
    Saves the given contents to a file with the given file name.

    Parameters:
    contents (str): The string contents to save to the file.
    file_name (str): The name of the file, including its extension.

    Returns:
    str: A message indicating the success of the operation.
    """
    # Ensure the directory exists; create it if it doesn't
    directory = os.path.dirname(file_name)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # Write the contents to the file
    with open(file_name, 'w') as file:
        file.write(contents)
    
    return f"File '{file_name}' has been saved successfully."

# Example usage:
# contents_to_save = "Hello, world!"
# file_name = "example.txt"
# print(save_file_to_disk(contents_to_save, file_name))