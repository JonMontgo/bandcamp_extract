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

# Matches a fallback group like {albumartist,artist} or {albumartist,artist,year}.
# Plain single params (e.g. {artist}) have no "," and are left for str.format.
FALLBACK_GROUP_RE = re.compile(r"\{(\w+(?:,\w+)+)\}")


class PatternParamError(click.ClickException):
    def __init__(self, param: str, pattern: str):
        self.param = param
        self.pattern = pattern
        super().__init__(f"Param {{{param}}} in pattern {pattern} not found")


KNOWN_TAG_FIELDS = {
    "album",
    "albumartist",
    "artist",
    "audio_offset",
    "bitdepth",
    "bitrate",
    "channels",
    "comment",
    "composer",
    "disc",
    "disc_total",
    "duration",
    "filename",
    "filesize",
    "genre",
    "samplerate",
    "title",
    "track",
    "track_total",
    "year",
}


def _collect_song_paths(root_dir: str) -> list[str]:
    return [path for path in glob.glob(f"{root_dir}/**/*", recursive=True) if os.path.isfile(path)]


def _resolve_fallback_groups(pattern: str, substitution_dict: dict[str, Any]) -> str:
    def resolve(match: re.Match[str]) -> str:
        fields = match.group(1).split(",")
        for field in fields:
            if field not in KNOWN_TAG_FIELDS and field not in substitution_dict:
                raise KeyError(field)
            value = substitution_dict.get(field)
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
) -> list[str]:
    song_paths = _collect_song_paths(root_dir)
    max_track_digits = _max_track_digits(song_paths) if pad_track_numbers else None
    transferred_paths: list[str] = []

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
            subed_path = resolved_pattern.format(**substitution_dict)
            new_path = f"{subed_path}{song_ext}"
            if not os.path.exists(os.path.dirname(new_path)):
                os.makedirs(os.path.dirname(new_path))
            transfer(potential_song_path, new_path)
            transferred_paths.append(new_path)
        except TinyTagException:
            pass
        except KeyError as err:
            raise PatternParamError(err.args[0], pattern) from err
    return transferred_paths


def move_to_pattern(
    root_dir: str,
    pattern: str,
    pad_track_numbers: bool = True,
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> list[str]:
    return _transfer_to_pattern(root_dir, pattern, pad_track_numbers, shutil.move, replacement_text, strip_spaces)


def copy_to_pattern(
    root_dir: str,
    pattern: str,
    pad_track_numbers: bool = True,
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> list[str]:
    return _transfer_to_pattern(root_dir, pattern, pad_track_numbers, shutil.copy2, replacement_text, strip_spaces)


def extract_zip(
    zip_path: str,
    pattern: str,
    pad_track_numbers: bool = True,
    replacement_text: str = "",
    strip_spaces: bool = False,
) -> list[str]:
    if zipfile.is_zipfile(zip_path):
        with zipfile.ZipFile(zip_path) as zipfh, tempfile.TemporaryDirectory() as tmpdirname:
            zipfh.extractall(path=tmpdirname)
            return move_to_pattern(tmpdirname, pattern, pad_track_numbers, replacement_text, strip_spaces)
    else:
        # Standalone audio track file (e.g. single track purchase from Bandcamp)
        file_dir = os.path.dirname(os.path.abspath(zip_path))
        return move_to_pattern(file_dir, pattern, pad_track_numbers, replacement_text, strip_spaces)
