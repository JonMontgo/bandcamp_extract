"""Tests for the pydantic wire models in bandcamp_extract.bandcamp.types.

Covers the Bandcamp date format ("%d %b %Y %H:%M:%S GMT") end-to-end:
the `BandcampDate` annotation on its own, on a CollectionItem, and on a
DownloadItem, plus a round-trip of a real captured response when the local
scripts/.api_samples/ fixtures are present (they're gitignored, so these
integration cases no-op on a fresh checkout).
"""

import json
import os
from datetime import UTC, datetime

import pytest

from bandcamp_extract.bandcamp.types import (
    BANDCAMP_DATE_FORMAT,
    CollectionItem,
    CollectionItemsResponse,
    DownloadItem,
    DownloadPageData,
    parse_bandcamp_date,
)

SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    ".api_samples",
)

# Real value captured from a live collection_items response.
SAMPLE_DATE_STR = "06 Aug 2026 04:01:26 GMT"


def testparse_bandcamp_date_returns_utc_datetime():
    dt = parse_bandcamp_date(SAMPLE_DATE_STR)
    assert isinstance(dt, datetime)
    assert dt == datetime(2026, 8, 6, 4, 1, 26, tzinfo=UTC)
    assert dt.tzinfo is UTC


def testparse_bandcamp_date_none_passthrough():
    assert parse_bandcamp_date(None) is None


def testparse_bandcamp_date_idempotent_on_datetime():
    dt = datetime(2026, 8, 6, 4, 1, 26, tzinfo=UTC)
    assert parse_bandcamp_date(dt) is dt


def testparse_bandcamp_date_bad_format_raises():
    with pytest.raises(ValueError):
        parse_bandcamp_date("2026-08-06T04:01:26Z")


def test_collection_item_parses_dates_to_datetimes():
    item = CollectionItem.model_validate(
        {
            "item_type": "album",
            "added": SAMPLE_DATE_STR,
            "updated": SAMPLE_DATE_STR,
            "purchased": "06 Aug 2026 04:01:27 GMT",
            "band_name": "death's dynamic shroud.wmv",
            "item_title": "WAXEN SCREAM",
            "url_hints": {"subdomain": "deathsdynamicshroud", "slug": "waxen-scream"},
        }
    )
    assert item.added == datetime(2026, 8, 6, 4, 1, 26, tzinfo=UTC)
    assert item.purchased == datetime(2026, 8, 6, 4, 1, 27, tzinfo=UTC)
    assert item.band_name == "death's dynamic shroud.wmv"
    assert item.url_hints is not None and item.url_hints.slug == "waxen-scream"


def test_collection_item_is_track_and_is_album():
    album = CollectionItem.model_validate({"item_type": "album", "sale_item_type": "a"})
    assert album.is_album is True
    assert album.is_track is False

    track = CollectionItem.model_validate({"item_type": "track", "sale_item_type": "t"})
    assert track.is_track is True
    assert track.is_album is False


def test_collection_item_ignores_unmodeled_keys_and_missing_dates():
    item = CollectionItem.model_validate({"item_type": "album", "some_unknown_bandcamp_key": 123, "added": None})
    assert item.added is None
    # Unmodeled key dropped, not stored on the model.
    assert not hasattr(item, "some_unknown_bandcamp_key")


def test_download_item_parses_release_and_sold_dates():
    item = DownloadItem.model_validate(
        {
            "downloads": {"flac": {"url": "https://example.com/a.zip"}},
            "sale_item_type": "a",
            "sale_item_id": 1,
            "sold_date": SAMPLE_DATE_STR,
            "release_date": "06 Aug 2026 00:00:00 GMT",
            "tralbum_release_date": "06 Aug 2026 00:00:00 GMT",
            "sale_release_date": None,
        }
    )
    assert item.sold_date == datetime(2026, 8, 6, 4, 1, 26, tzinfo=UTC)
    assert item.release_date == datetime(2026, 8, 6, tzinfo=UTC)
    assert item.sale_release_date is None
    assert item.downloads["flac"].url == "https://example.com/a.zip"


def test_download_item_required_fields():
    with pytest.raises(ValueError):
        DownloadItem.model_validate({"sale_item_type": "a"})  # missing downloads + sale_item_id


def test_bandcamp_date_format_constant_matches_sample():
    # Sanity: the format string we depend on round-trips the sample value.
    parsed = datetime.strptime(SAMPLE_DATE_STR, BANDCAMP_DATE_FORMAT)
    assert parsed.strftime(BANDCAMP_DATE_FORMAT) == SAMPLE_DATE_STR


# --- Integration: round-trip real captured responses when present locally ---


def _sample(name: str) -> dict | None:
    path = os.path.join(SAMPLES_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


@pytest.mark.skipif(
    not os.path.exists(os.path.join(SAMPLES_DIR, "collection_items.json")),
    reason="scripts/.api_samples/ not populated (run probe_bandcamp_api.py)",
)
def test_real_collection_items_response_validates():
    data = _sample("collection_items.json")
    assert data is not None
    resp = CollectionItemsResponse.model_validate(data)
    assert len(resp.items) >= 1
    first = resp.items[0]
    assert isinstance(first.added, datetime)
    assert first.added.tzinfo is UTC
    assert first.band_name  # non-empty on a real response


@pytest.mark.skipif(
    not os.path.exists(os.path.join(SAMPLES_DIR, "pagedata_download.json")),
    reason="scripts/.api_samples/ not populated (run probe_bandcamp_api.py)",
)
def test_real_download_page_validates():
    data = _sample("pagedata_download.json")
    assert data is not None
    page = DownloadPageData.model_validate(data)
    assert len(page.download_items) >= 1
    di = page.download_items[0]
    assert isinstance(di.sold_date, datetime)
    assert di.downloads  # has at least one format -> DownloadInfo
