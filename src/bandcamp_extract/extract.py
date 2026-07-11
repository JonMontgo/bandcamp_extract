import contextlib
import glob
import os
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from typing import Any

import click
from tinytag import TinyTag
from tinytag.tinytag import TinyTagException

from .lib import sanitize_dict_values

# Matches a fallback group like {albumartist|artist} or {albumartist|artist|year}.
# Plain single params (e.g. {artist}) have no "|" and are left for str.format.
FALLBACK_GROUP_RE = re.compile(r"\{(\w+(?:\|\w+)+)\}")


def _collect_song_paths(root_dir: str) -> list[str]:
    return [path for path in glob.glob(f"{root_dir}/**/*", recursive=True) if os.path.isfile(path)]


def _resolve_fallback_groups(pattern: str, substitution_dict: dict[str, Any]) -> str:
    def resolve(match: re.Match[str]) -> str:
        fields = match.group(1).split("|")
        for field in fields:
            if field not in substitution_dict:
                raise KeyError(field)
            value = substitution_dict[field]
            if value not in (None, ""):
                return str(value).replace("{", "{{").replace("}", "}}")
        return ""

    return FALLBACK_GROUP_RE.sub(resolve, pattern)


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
    return max(2, len(str(max(track_numbers)))) if track_numbers else None


def _transfer_to_pattern(
    root_dir: str,
    pattern: str,
    pad_track_numbers: bool,
    transfer: Callable[[str, str], Any],
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> None:
    song_paths = _collect_song_paths(root_dir)
    max_track_digits = _max_track_digits(song_paths) if pad_track_numbers else None

    for potential_song_path in song_paths:
        try:
            song_ext = os.path.splitext(potential_song_path)[1]
            potential_song = TinyTag.get(potential_song_path)
            substitution_dict: dict[str, Any] = sanitize_dict_values(
                potential_song.as_dict(), replacement_text, strip_spaces
            )
            if max_track_digits and substitution_dict.get("track") is not None:
                with contextlib.suppress(TypeError, ValueError):
                    substitution_dict["track"] = str(int(substitution_dict["track"])).zfill(max_track_digits)
            resolved_pattern = _resolve_fallback_groups(pattern, substitution_dict)
            new_path = resolved_pattern.format(**substitution_dict) + song_ext
            if not os.path.exists(os.path.dirname(new_path)):
                os.makedirs(os.path.dirname(new_path))
            transfer(potential_song_path, new_path)
        except TinyTagException:
            pass
        except KeyError as err:
            raise click.ClickException(f"Param {{{err.args[0]}}} in pattern {pattern} not found") from err


def move_to_pattern(
    root_dir: str,
    pattern: str,
    pad_track_numbers: bool = True,
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> None:
    _transfer_to_pattern(root_dir, pattern, pad_track_numbers, shutil.move, replacement_text, strip_spaces)


def copy_to_pattern(
    root_dir: str,
    pattern: str,
    pad_track_numbers: bool = True,
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> None:
    _transfer_to_pattern(root_dir, pattern, pad_track_numbers, shutil.copy2, replacement_text, strip_spaces)


def extract_zip(
    zip_path: str,
    pattern: str,
    pad_track_numbers: bool = True,
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> None:
    if not zipfile.is_zipfile(zip_path):
        raise click.ClickException(f"{zip_path} is not a zip file!")
    with zipfile.ZipFile(zip_path) as zipfh, tempfile.TemporaryDirectory() as tmpdirname:
        zipfh.extractall(path=tmpdirname)
        move_to_pattern(tmpdirname, pattern, pad_track_numbers, replacement_text, strip_spaces)
