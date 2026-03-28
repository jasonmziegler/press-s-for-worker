import subprocess

def run_script(file_path, timeout=10):
    """Execute a Python script file and return its output.

    Args:
        file_path (str): Path to the Python script to execute.
        timeout (str): Max seconds to wait before killing the script. Default 10.
    """
    try:
        result = subprocess.run(
            ["python", file_path],
            capture_output=True,
            text=True,
            timeout=int(timeout)
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Script timed out after {timeout} seconds"}
    except Exception as e:
        return {"error": str(e)}
