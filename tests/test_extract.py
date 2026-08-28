import pytest

from bandcamp_extract.extract import _resolve_fallback_groups


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
