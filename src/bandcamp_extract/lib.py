from functools import wraps
from typing import Any, cast

import click
from pathvalidate import replace_symbol

from .bandcamp.client import BandcampClient
from .bandcamp.types import CollectionItem, DownloadFormat


# Replace path-unsafe symbols so metadata can't break the destination path
def sanitize_for_path(string: str, replacement_text: str = "", strip_spaces: bool = False) -> str:
    exclude_symbols = [] if strip_spaces else [" "]
    return replace_symbol(string, replacement_text=replacement_text, exclude_symbols=exclude_symbols)


# Sanitizes path-unsafe symbols on all of the values of the dictionary if they are strings or lists
def sanitize_dict_values(
    dictionary: dict[str, Any], replacement_text: str = "", strip_spaces: bool = False
) -> dict[str, Any]:
    sanitized = {}
    for key, value in dictionary.items():
        if type(value) is str:
            sanitized[key] = sanitize_for_path(value, replacement_text, strip_spaces)
        elif type(value) is list:
            sanitized[key] = sanitize_for_path(", ".join(value), replacement_text, strip_spaces)
        else:
            sanitized[key] = value
    return sanitized


def click_safe(method):
    """Wrap a method so any non-click exception is re-raised as a click.ClickException."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except click.ClickException:
            raise
        except Exception as err:
            raise click.ClickException(str(err)) from err
    return wrapper


class ClickAwareBandcampClient(BandcampClient):
    """BandcampClient subclass that converts errors into click.ClickException for CLI use."""

    @classmethod
    @click_safe
    def from_session(cls) -> "ClickAwareBandcampClient":
        client = cast("ClickAwareBandcampClient", super().from_session())
        client.check_session()
        return client

    @classmethod
    def login(cls, username: str, identity_cookie: str) -> "ClickAwareBandcampClient":
        try:
            return cast("ClickAwareBandcampClient", super().login(username, identity_cookie))
        except click.ClickException:
            raise
        except Exception as err:
            raise click.ClickException(f"Login failed: {err}") from err

    @click_safe
    def list_collection(self) -> list[CollectionItem]:
        return super().list_collection()

    @click_safe
    def get_download_link(self, download_url: str, format: DownloadFormat) -> str:
        return super().get_download_link(download_url, format)

    @click_safe
    def download_file(self, url: str, dest_path: str) -> None:
        super().download_file(url, dest_path)
