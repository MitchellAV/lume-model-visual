import re


def sanitize_string(s: str) -> str:
    """Sanitize a string to be used as a key in state dictionaries.

    This function replaces characters that may cause issues in JavaScript
    variable names or HTML element IDs. JavaScript identifiers can only
    contain letters, digits, underscores, and dollar signs.

    Args:
        s (str): The input string to sanitize.
    Returns:
        str: The sanitized string.
    """
    # Replace any character that is not a letter, digit, or underscore
    return re.sub(r"[^a-zA-Z0-9_]", "_", s)


def validate_state_key(key: str) -> None:
    """Validate that a state key is safe for use in trame/JavaScript.

    Trame state keys are used as JavaScript property names on the client.
    Invalid characters (like ':') will cause a client-side SyntaxError
    that is invisible to the Python backend.

    Args:
        key: The state key to validate.
    Raises:
        ValueError: If the key contains characters invalid for JavaScript identifiers.
    """
    if not re.match(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$", key):
        raise ValueError(
            f"Invalid trame state key: '{key}'. "
            f"State keys must be valid JavaScript identifiers "
            f"(letters, digits, underscores, dollar signs; cannot start with a digit). "
            f"Use sanitize_string() to convert variable names to safe keys."
        )
