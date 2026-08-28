import os
from collections.abc import Callable
from typing import Any

import click

from ..bandcamp.client import DOWNLOAD_FORMATS

DEFAULT_PATTERN = f"{os.getcwd()}/{{artist}}/{{album}}/{{title}}"


def pattern_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--pattern",
        type=click.Path(file_okay=False),
        default=DEFAULT_PATTERN,
        help=(
            "Destination path pattern, substituted with tinytag fields "
            "(e.g. ~/Music/{albumartist}/{album}/{title}). Use "
            "{fieldA,fieldB,...} to fall back through fields in order when "
            "one is missing (e.g. {albumartist,artist}). The file "
            "extension is appended automatically."
        ),
    )(f)


def no_track_padding_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--no-track-padding",
        is_flag=True,
        default=False,
        help=(
            "Disable zero-padding the track number to the width of the "
            "highest track number in the album, minimum 2 digits "
            "(padding is on by default)."
        ),
    )(f)


def replacement_text_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--replacement-text",
        default="",
        help=(
            "Text used to replace path-unsafe symbols (e.g. /, :, ?) found in "
            "tinytag metadata before it's substituted into the pattern. "
            "Defaults to removing them."
        ),
    )(f)


def strip_spaces_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--strip-spaces",
        is_flag=True,
        default=False,
        help=(
            "Also replace spaces in tinytag metadata with --replacement-text "
            "(spaces are left alone by default)."
        ),
    )(f)


def format_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--format",
        "download_format",
        type=click.Choice(DOWNLOAD_FORMATS),
        default=None,
        help=(
            "Audio download format (e.g. flac, mp3-320). If omitted, "
            "interactive commands prompt with a picker and sync defaults to "
            "the existing sync config or 'flac'."
        ),
    )(f)


def sync_file_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--sync-file",
        type=click.Path(dir_okay=False, writable=True),
        default=None,
        help=(
            "Path to sync state TOML file (defaults to ~/.config/bcextr/sync.toml). "
            "Created automatically if it does not exist."
        ),
    )(f)
