def edit_file(file_path, old_text, new_text):
    with open(file_path, 'r') as file:
        content = file.read()
    modified_content = content.replace(old_text, new_text, 1)
    with open(file_path, 'w') as file:
        file.write(modified_content)
