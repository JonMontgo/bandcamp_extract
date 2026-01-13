from typing import Any


# Replace slashes with dashes to not break paths
def sanitize_for_path(string: str):
    return string.replace("/", "-")


# Sanitizes slashes on all of the values of the dictionary if they are strings or lists
def sanitize_dict_values(dictionary: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for key, value in dictionary.items():
        if type(value) is str:
            sanitized[key] = sanitize_for_path(value)
        elif type(value) is list:
            sanitized[key] = sanitize_for_path(", ".join(value))
        else:
            sanitized[key] = value
    return sanitized
