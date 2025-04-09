#This file contains the logic to fetch a random CAP XML from a given directory

import os
import random

def get_random_cap(directory: str) -> str:
    """
    Selects a random CAP file from the specified directory.

    Args:
        directory (str): Path to the directory containing CAP XML files.

    Returns:
        str: The content of the selected CAP XML file as a string.
    """
    try:
        # Get a list of all XML files in the directory
        cap_files = [file for file in os.listdir(directory) if file.endswith('.xml')]
        if not cap_files:
            raise FileNotFoundError("No CAP files found in the directory.")

        # Select a random CAP file
        random_file = random.choice(cap_files)
        file_path = os.path.join(directory, random_file)

        # Read and return the content of the CAP file
        with open(file_path, 'r') as file:
            cap_content = file.read()
        return cap_content

    except Exception as e:
        raise Exception(f"Error fetching CAP file: {e}")
