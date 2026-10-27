import os
import zipfile

import pytest
from mutagen.easyid3 import EasyID3

from bandcamp_extract.extract import _resolve_fallback_groups, copy_to_pattern, extract_zip


def test_resolve_fallback_uses_first_present_value():
    pattern = "./music/{albumartist,artist}/{album}/{title}"
    sub_dict = {
        "albumartist": "Various Artists",
        "artist": "Specific Artist",
        "album": "Compilation",
        "title": "Track 1",
    }

    resolved = _resolve_fallback_groups(pattern, sub_dict)
    assert resolved == "./music/Various Artists/{album}/{title}"
    final = resolved.format(**sub_dict)
    assert final == "./music/Various Artists/Compilation/Track 1"


def test_resolve_fallback_skips_missing_field_and_uses_next():
    pattern = "./music/{albumartist,artist}/{album}/{title}"
    # albumartist is not present in tags (omitted by TinyTag.as_dict)
    sub_dict = {"artist": "death's dynamic shroud.wmv", "album": "Babel Archives", "title": "Track 1"}

    resolved = _resolve_fallback_groups(pattern, sub_dict)
    assert resolved == "./music/death's dynamic shroud.wmv/{album}/{title}"
    final = resolved.format(**sub_dict)
    assert final == "./music/death's dynamic shroud.wmv/Babel Archives/Track 1"


def test_resolve_fallback_skips_empty_or_none_string():
    pattern = "./music/{albumartist,artist,genre}/{album}/{title}"
    sub_dict = {"albumartist": "", "artist": None, "genre": "Vaporwave", "album": "Album", "title": "Song"}

    resolved = _resolve_fallback_groups(pattern, sub_dict)
    assert resolved == "./music/Vaporwave/{album}/{title}"


def test_resolve_fallback_all_missing_resolves_to_empty():
    pattern = "./music/{albumartist,comment}/{album}/{title}"
    sub_dict = {"album": "Album", "title": "Song"}

    resolved = _resolve_fallback_groups(pattern, sub_dict)
    assert resolved == "./music//{album}/{title}"


def test_resolve_fallback_raises_on_unknown_field_typo():
    pattern = "./music/{not_a_real_field,artist}/{album}/{title}"
    sub_dict = {"artist": "Artist", "album": "Album", "title": "Song"}

    with pytest.raises(KeyError) as exc_info:
        _resolve_fallback_groups(pattern, sub_dict)
    assert exc_info.value.args[0] == "not_a_real_field"


def test_format_extensions_mapping():
    from bandcamp_extract.bandcamp.client import DOWNLOAD_FORMATS, FORMAT_EXTENSIONS

    for fmt in DOWNLOAD_FORMATS:
        assert fmt in FORMAT_EXTENSIONS
        assert FORMAT_EXTENSIONS[fmt].startswith(".")


def test_truncate_by_bytes_ascii():
    from bandcamp_extract.lib import _truncate_by_bytes
    assert _truncate_by_bytes("a" * 300, max_bytes=10) == "a" * 10
    assert _truncate_by_bytes("hello", max_bytes=10) == "hello"


def test_truncate_by_bytes_unicode():
    from bandcamp_extract.lib import _truncate_by_bytes
    # "ä" is 2 bytes: \xc3\xa4
    assert _truncate_by_bytes("ä" * 10, max_bytes=5) == "ää"  # 4 bytes used, 5th byte was partial and ignored


def test_sanitize_dict_values_truncates():
    from bandcamp_extract.lib import sanitize_dict_values
    input_dict = {
        "artist": "a" * 300,
        "album": ["b" * 150, "c" * 150],
        "track": 12,
    }
    sanitized = sanitize_dict_values(input_dict)
    assert len(sanitized["artist"].encode("utf-8")) == 240
    assert len(sanitized["album"].encode("utf-8")) == 240
    assert sanitized["track"] == 12


def tag_mp3_file(
    path: str,
    *,
    title: str,
    artist: str,
    album: str,
    track: str,
    albumartist: str | None = None,
    disc: str | None = None,
) -> None:
    """Create a tagged .mp3 file using mutagen's EasyID3."""
    tags = EasyID3()
    tags["title"] = title
    tags["artist"] = artist
    tags["album"] = album
    tags["tracknumber"] = track
    if albumartist is not None:
        tags["albumartist"] = albumartist
    if disc is not None:
        tags["discnumber"] = disc
    tags.save(path)


def test_extract_zip_with_tinytag_and_track_padding(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    track1 = src_dir / "track1.mp3"
    track2 = src_dir / "track2.mp3"
    cover = src_dir / "cover.jpg"

    tag_mp3_file(
        str(track1),
        title="Opening",
        artist="Test Artist",
        album="Test Album",
        track="1/12",
        disc="1/1",
    )
    tag_mp3_file(
        str(track2),
        title="Finale",
        artist="Test Artist",
        album="Test Album",
        track="12/12",
        disc="1/1",
    )
    cover.write_bytes(b"not an audio file")

    zip_path = tmp_path / "album.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(track1, arcname="01 Opening.mp3")
        zf.write(track2, arcname="12 Finale.mp3")
        zf.write(cover, arcname="cover.jpg")

    dest_root = tmp_path / "out"
    pattern = str(dest_root / "{albumartist,artist}" / "{album}" / "{disc}-{track} {title}")
    transferred = sorted(extract_zip(str(zip_path), pattern, pad_track_numbers=True))

    expected = [
        str(dest_root / "Test Artist" / "Test Album" / "1-01 Opening.mp3"),
        str(dest_root / "Test Artist" / "Test Album" / "1-12 Finale.mp3"),
    ]
    assert transferred == expected
    for p in expected:
        assert os.path.isfile(p)


def test_copy_to_pattern_without_track_padding(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    track = src_dir / "song.mp3"
    tag_mp3_file(
        str(track),
        title="Solo Song",
        artist="Track Artist",
        albumartist="Album Artist",
        album="The Record",
        track="3/9",
    )

    dest_root = tmp_path / "out"
    pattern = str(dest_root / "{albumartist,artist}" / "{album}" / "{track} - {title}")
    transferred = copy_to_pattern(str(src_dir), pattern, pad_track_numbers=False)

    expected_path = str(dest_root / "Album Artist" / "The Record" / "3 - Solo Song.mp3")
    assert transferred == [expected_path]
    assert track.is_file()  # original preserved by copy_to_pattern

