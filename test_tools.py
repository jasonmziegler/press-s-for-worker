import os
import shutil
tempfile = __import__('tempfile')
from tools.file_reader import read_file
from tools.write_file import write_file
from tools.edit_file_tool import edit_file
from tools.list_files import list_files
from tools.run_script import run_script

def test_tools():
    temp_dir = tempfile.mkdtemp()
    try:
        # Test read_file and write_file
        test_file_path = os.path.join(temp_dir, 'test.txt')
        test_content = 'Hello, this is a test file.'
        write_file(test_file_path, test_content)
        read_result = read_file(test_file_path)
        print(f"Read test: {'Passed' if read_result == test_content else 'Failed'}")

        # Test edit_file
        edit_file_path = os.path.join(temp_dir, 'edit_test.txt')
        original_content = 'Original text to replace.'
        new_content = 'Modified text.'
        write_file(edit_file_path, original_content)
        result = edit_file(edit_file_path, 'Original', new_content)
        with open(edit_file_path, 'r') as f:
            modified_content = f.read()
        expected_modified = 'Modified text. text to replace.'
        print(f"Edit test: {'Passed' if modified_content == expected_modified else 'Failed'}")

        # Test list_files
        sub_dir = os.path.join(temp_dir, 'subdir')
        os.makedirs(sub_dir)
        file1_path = os.path.join(sub_dir, 'file1.txt')
        file2_path = os.path.join(sub_dir, 'file2.txt')
        with open(file1_path, 'w') as f:
            f.write('')
        with open(file2_path, 'w') as f:
            f.write('')
        files_list = list_files(sub_dir)
        expected_files = ['file1.txt', 'file2.txt']
        print(f"List test: {'Passed' if sorted(files_list) == expected_files else 'Failed'}")

        # Test run_script
        script_path = os.path.join(temp_dir, 'test_script.py')
        with open(script_path, 'w') as f:
            f.write('print("Hello from test script.")')
        result = run_script(script_path)
        print(f"Run test: {'Passed' if 'Hello from test script.' in result['stdout'] else 'Failed'}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_tools()