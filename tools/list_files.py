import os

def list_files(dir_path):
    """
    Lists all filenames in the specified directory.
    
    Args:
        dir_path (str): The path to the directory to be listed.
        
    Returns:
        list: A list of filenames in the directory. If the directory does not exist or is not a valid directory, returns an empty list.
    """
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        return os.listdir(dir_path)
    else:
        return []
