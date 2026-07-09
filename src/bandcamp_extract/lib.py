from typing import Any

from pathvalidate import replace_symbol


# Replace path-unsafe symbols so metadata can't break the destination path
def sanitize_for_path(string: str, replacement_text: str = "") -> str:
    return replace_symbol(string, replacement_text=replacement_text)


# Sanitizes path-unsafe symbols on all of the values of the dictionary if they are strings or lists
def sanitize_dict_values(dictionary: dict[str, Any], replacement_text: str = "") -> dict[str, Any]:
    sanitized = {}
    for key, value in dictionary.items():
        if type(value) is str:
            sanitized[key] = sanitize_for_path(value, replacement_text)
        elif type(value) is list:
            sanitized[key] = sanitize_for_path(", ".join(value), replacement_text)
        else:
            sanitized[key] = value
    return sanitized
