import os
from collections.abc import Callable
from typing import Any

import click

DEFAULT_PATTERN = f"{os.getcwd()}/{{artist}}/{{album}}/{{title}}"


def pattern_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--pattern",
        type=click.Path(file_okay=False),
        default=DEFAULT_PATTERN,
        help=(
            "Destination path pattern, substituted with tinytag fields "
            "(e.g. ~/Music/{albumartist}/{album}/{title}). The file "
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
            "highest track number in the album (padding is on by default)."
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
