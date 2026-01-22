def sanitize_string(s: str) -> str:
    """Sanitize a string to be used as a key in state dictionaries.

    This function replaces characters that may cause issues in JavaScript
    variable names or HTML element IDs.

    Args:
        s (str): The input string to sanitize.
    Returns:
        str: The sanitized string.
    """
    return s.replace(":", "_")
