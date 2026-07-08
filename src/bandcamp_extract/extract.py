import contextlib
import glob
import os
import shutil
import tempfile
import zipfile
from typing import Any

import click
from tinytag import TinyTag
from tinytag.tinytag import TinyTagException

from .lib import sanitize_dict_values


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


def extract_zip(zip_path: str, pattern: str, pad_track_numbers: bool = True) -> None:
    if not zipfile.is_zipfile(zip_path):
        raise click.ClickException(f"{zip_path} is not a zip file!")
    with zipfile.ZipFile(zip_path) as zipfh, tempfile.TemporaryDirectory() as tmpdirname:
        zipfh.extractall(path=tmpdirname)
        song_paths = glob.glob(f"{tmpdirname}/*")

        max_track_digits = _max_track_digits(song_paths) if pad_track_numbers else None

        for potential_song_path in song_paths:
            try:
                song_ext = os.path.splitext(potential_song_path)[1]
                potential_song = TinyTag.get(potential_song_path)
                substitution_dict: dict[str, Any] = sanitize_dict_values(potential_song.as_dict())
                if max_track_digits and substitution_dict.get("track") is not None:
                    with contextlib.suppress(TypeError, ValueError):
                        substitution_dict["track"] = str(int(substitution_dict["track"])).zfill(
                            max_track_digits
                        )
                new_path = pattern.format(**substitution_dict) + song_ext
                if not os.path.exists(os.path.dirname(new_path)):
                    os.makedirs(os.path.dirname(new_path))
                shutil.move(potential_song_path, new_path)
            except TinyTagException:
                pass
            except KeyError as err:
                raise click.ClickException(
                    f"Param {{{err.args[0]}}} in pattern {pattern} not found"
                ) from err
