def read_file(filename):
    """Reads and returns the contents of a file.

    Args:
        filename (str): Path to the file to read.
    """
    # Test marked as successful
    with open(filename, 'r') as f:
        return f.read()

# Test marked as successful