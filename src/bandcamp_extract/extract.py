import contextlib
import glob
import os
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from typing import Any

import click
from tinytag import TinyTag
from tinytag.tinytag import TinyTagException

from .lib import sanitize_dict_values


def _collect_song_paths(root_dir: str) -> list[str]:
    return [path for path in glob.glob(f"{root_dir}/**/*", recursive=True) if os.path.isfile(path)]


def _max_track_digits(song_paths: list[str]) -> int | None:
    track_numbers = []
    for song_path in song_paths:
        try:
            tags = TinyTag.get(song_path)
        except TinyTagException:
            continue
        for value in (tags.track, tags.track_total):
            if value is not None:
                with contextlib.suppress(TypeError, ValueError):
                    track_numbers.append(int(value))
    return len(str(max(track_numbers))) if track_numbers else None


def _transfer_to_pattern(
    root_dir: str,
    pattern: str,
    pad_track_numbers: bool,
    transfer: Callable[[str, str], Any],
    replacement_text: str = "",
) -> None:
    song_paths = _collect_song_paths(root_dir)
    max_track_digits = _max_track_digits(song_paths) if pad_track_numbers else None

    for potential_song_path in song_paths:
        try:
            song_ext = os.path.splitext(potential_song_path)[1]
            potential_song = TinyTag.get(potential_song_path)
            substitution_dict: dict[str, Any] = sanitize_dict_values(potential_song.as_dict(), replacement_text)
            if max_track_digits and substitution_dict.get("track") is not None:
                with contextlib.suppress(TypeError, ValueError):
                    substitution_dict["track"] = str(int(substitution_dict["track"])).zfill(max_track_digits)
            new_path = pattern.format(**substitution_dict) + song_ext
            if not os.path.exists(os.path.dirname(new_path)):
                os.makedirs(os.path.dirname(new_path))
            transfer(potential_song_path, new_path)
        except TinyTagException:
            pass
        except KeyError as err:
            raise click.ClickException(f"Param {{{err.args[0]}}} in pattern {pattern} not found") from err


def move_to_pattern(
    root_dir: str, pattern: str, pad_track_numbers: bool = True, replacement_text: str = ""
) -> None:
    _transfer_to_pattern(root_dir, pattern, pad_track_numbers, shutil.move, replacement_text)


def copy_to_pattern(
    root_dir: str, pattern: str, pad_track_numbers: bool = True, replacement_text: str = ""
) -> None:
    _transfer_to_pattern(root_dir, pattern, pad_track_numbers, shutil.copy2, replacement_text)


def extract_zip(
    zip_path: str, pattern: str, pad_track_numbers: bool = True, replacement_text: str = ""
) -> None:
    if not zipfile.is_zipfile(zip_path):
        raise click.ClickException(f"{zip_path} is not a zip file!")
    with zipfile.ZipFile(zip_path) as zipfh, tempfile.TemporaryDirectory() as tmpdirname:
        zipfh.extractall(path=tmpdirname)
        move_to_pattern(tmpdirname, pattern, pad_track_numbers, replacement_text)
