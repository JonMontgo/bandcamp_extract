import html
import json
import re
import time

import requests

PAGEDATA_RE = re.compile(r'<div id="pagedata" data-blob="([^"]*)"')
COLLECTION_SUMMARY_URL = "https://bandcamp.com/api/fan/2/collection_summary"

DOWNLOAD_FORMATS = [
    "mp3-320",
    "mp3-v0",
    "flac",
    "aac-hi",
    "vorbis",
    "alac",
    "wav",
    "aiff-lossless",
]


class BandcampAuthError(Exception):
    pass


class BandcampClient:
    def __init__(self, username: str, identity_cookie: str):
        self.username = username
        self.session = requests.Session()
        self.session.cookies.set("identity", identity_cookie, domain=".bandcamp.com")
        self.session.headers.update({"User-Agent": "bcextr/0.2.0"})

    def _parse_pagedata(self, html_text: str) -> dict:
        match = PAGEDATA_RE.search(html_text)
        if not match:
            raise BandcampAuthError(
                "Could not find collection data on the page. "
                "Your identity cookie may be invalid or expired."
            )
        return json.loads(html.unescape(match.group(1)))

    def get_fan_id(self) -> int:
        resp = self.session.get(f"https://bandcamp.com/{self.username}")
        resp.raise_for_status()
        data = self._parse_pagedata(resp.text)
        try:
            return data["fan_data"]["fan_id"]
        except KeyError as err:
            raise BandcampAuthError(
                "Logged-in fan data not found on page; check your username and cookie."
            ) from err

    def check_session(self) -> None:
        """Confirm the identity cookie is actually authenticated.

        Unlike get_fan_id (which just scrapes a profile page that renders
        for anyone, logged in or not), this hits an endpoint that only
        returns real data for an authenticated session, so it catches a
        stale/expired cookie before we waste time listing a collection with
        no working download links.
        """
        resp = self.session.get(COLLECTION_SUMMARY_URL)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise BandcampAuthError(
                "Bandcamp says you're not logged in "
                f"({data.get('error_message', 'must be logged in')}). "
                "Your identity cookie is likely stale or expired — log in again "
                "in your browser, copy the fresh 'identity' cookie value, and "
                "re-run `bcextr api login`."
            )

    def list_collection(self, fan_id: int) -> list[dict]:
        items = []
        older_than_token = f"{int(time.time())}::a::"
        while True:
            resp = self.session.post(
                "https://bandcamp.com/api/fancollection/1/collection_items",
                json={"fan_id": fan_id, "count": 50, "older_than_token": older_than_token},
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("items", [])
            if not batch:
                break
            redownload_urls = data.get("redownload_urls", {})
            for item in batch:
                key = f"{item.get('sale_item_type')}{item.get('sale_item_id')}"
                item["redownload_url"] = redownload_urls.get(key)
            items.extend(batch)
            older_than_token = data.get("last_token", older_than_token)
            if not data.get("more_available", False):
                break
        return items

    def get_download_link(self, download_url: str, format: str) -> str:
        resp = self.session.get(download_url)
        resp.raise_for_status()
        data = self._parse_pagedata(resp.text)
        downloads = data["download_items"][0]["downloads"]
        if format not in downloads:
            raise ValueError(
                f"Format {format!r} not available; choices are {sorted(downloads)}"
            )
        return downloads[format]["url"]

    def download_zip(self, url: str, dest_path: str) -> None:
        with self.session.get(url, stream=True) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    fh.write(chunk)
