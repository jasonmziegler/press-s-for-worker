def read_file(filename):
    """Reads and returns the contents of a file."""
    with open(filename, 'r') as f:
        return f.read()
