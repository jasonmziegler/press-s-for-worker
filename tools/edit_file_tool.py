def edit_file(file_path, old_text, new_text):
    """Replace the first occurrence of old_text with new_text in a file.

    Args:
        file_path (str): Path to the file to edit.
        old_text (str): The exact text to find in the file.
        new_text (str): The text to replace it with.
    """
    with open(file_path, 'r') as file:
        content = file.read()
    if old_text not in content:
        return f"ERROR: old_text not found in {file_path}"
    modified_content = content.replace(old_text, new_text, 1)
    with open(file_path, 'w') as file:
        file.write(modified_content)
    return f"OK: replaced in {file_path}"
