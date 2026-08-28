import html
import json
import re
import time
from typing import get_args

import requests

from .types import (
    CollectionItem,
    CollectionItemsResponse,
    CollectionSummaryResponse,
    DownloadFormat,
    DownloadPageData,
    ProfilePageData,
)

PAGEDATA_RE = re.compile(r'<div id="pagedata" data-blob="([^"]*)"')
COLLECTION_SUMMARY_URL = "https://bandcamp.com/api/fan/2/collection_summary"

FORMAT_EXTENSIONS: dict[DownloadFormat, str] = {
    "mp3-320": ".mp3",
    "mp3-v0": ".mp3",
    "flac": ".flac",
    "aac-hi": ".m4a",
    "vorbis": ".ogg",
    "alac": ".m4a",
    "wav": ".wav",
    "aiff-lossless": ".aiff",
}

# Derived from the DownloadFormat Literal in types.py so there's one place
# to edit when Bandcamp adds/removes a format.
DOWNLOAD_FORMATS: list[DownloadFormat] = list(get_args(DownloadFormat))


class BandcampAuthError(Exception):
    pass


class BandcampClient:
    def __init__(self, username: str, identity_cookie: str):
        self.username = username
        self.session = requests.Session()
        self.session.cookies.set("identity", identity_cookie, domain=".bandcamp.com")
        self.session.headers.update({"User-Agent": "bcextr/0.2.0"})
        # Lazy caches for the profile-page fetch (populated on first access).
        self._profile_data: ProfilePageData | None = None
        self._fan_id: int | None = None

    def _parse_pagedata(self, html_text: str) -> dict:
        match = PAGEDATA_RE.search(html_text)
        if not match:
            raise BandcampAuthError(
                "Could not find collection data on the page. Your identity cookie may be invalid or expired."
            )
        return json.loads(html.unescape(match.group(1)))

    def _fetch_profile_data(self) -> ProfilePageData:
        """Fetch and validate the fan's profile-page pagedata blob."""
        resp = self.session.get(f"https://bandcamp.com/{self.username}")
        resp.raise_for_status()
        data = ProfilePageData.model_validate(self._parse_pagedata(resp.text))
        if data.fan_data is None or data.fan_data.fan_id is None:
            raise BandcampAuthError("Logged-in fan data not found on page; check your username and cookie.")
        return data

    @property
    def profile_data(self) -> ProfilePageData:
        """The fan's profile-page pagedata (ProfilePageData); fetched once and cached."""
        if self._profile_data is None:
            self._profile_data = self._fetch_profile_data()
        return self._profile_data

    @property
    def fan_id(self) -> int:
        """The logged-in fan's numeric id; resolved from the profile page on first access."""
        if self._fan_id is None:
            # profile_data caches the full blob; fan_id caches just the int.
            self._fan_id = self.profile_data.fan_data.fan_id
            assert self._fan_id is not None  # guaranteed by _fetch_profile_data's guard
        return self._fan_id

    def check_session(self) -> None:
        """Confirm the identity cookie is actually authenticated.

        Unlike the profile_data/fan_id properties (which just scrape a profile
        page that renders for anyone, logged in or not), this hits an endpoint
        that only returns real data for an authenticated session, so it catches
        a stale/expired cookie before we waste time listing a collection with
        no working download links.
        """
        resp = self.session.get(COLLECTION_SUMMARY_URL)
        resp.raise_for_status()
        data = CollectionSummaryResponse.model_validate(resp.json())
        if data.error:
            raise BandcampAuthError(
                "Bandcamp says you're not logged in "
                f"({data.error_message or 'must be logged in'}). "
                "Your identity cookie is likely stale or expired — log in again "
                "in your browser, copy the fresh 'identity' cookie value, and "
                "re-run `bcextr api login`."
            )

    def list_collection(self) -> list[CollectionItem]:
        items: list[CollectionItem] = []
        older_than_token = f"{int(time.time())}::a::"
        while True:
            resp = self.session.post(
                "https://bandcamp.com/api/fancollection/1/collection_items",
                json={"fan_id": self.fan_id, "count": 50, "older_than_token": older_than_token},
            )
            resp.raise_for_status()
            data = CollectionItemsResponse.model_validate(resp.json())
            if not data.items:
                break
            for item in data.items:
                key = f"{item.sale_item_type}{item.sale_item_id}"
                item.redownload_url = data.redownload_urls.get(key)
            items.extend(data.items)
            older_than_token = data.last_token or older_than_token
            if not data.more_available:
                break
        return items

    def get_download_link(self, download_url: str, format: DownloadFormat) -> str:
        resp = self.session.get(download_url)
        resp.raise_for_status()
        data = DownloadPageData.model_validate(self._parse_pagedata(resp.text))
        downloads = data.download_items[0].downloads
        download_info = downloads.get(format)
        if download_info is None or not download_info.url:
            raise ValueError(f"Format {format!r} not available; choices are {sorted(downloads)}")
        return download_info.url

    def download_file(self, url: str, dest_path: str) -> None:
        """Download a file (zip archive or audio track) directly to `dest_path`."""
        with self.session.get(url, stream=True) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    fh.write(chunk)

    download_zip = download_file
