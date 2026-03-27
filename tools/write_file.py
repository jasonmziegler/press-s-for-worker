# tools/write_file.py

def write_file(file_path: str, content: str) -> None:
    """
    Writes a given string content to a specified file path.

    Args:
        file_path (str): The path of the file to be written.
        content (str): The content to be written into the file.
    """
    with open(file_path, 'w') as f:
        f.write(content)
