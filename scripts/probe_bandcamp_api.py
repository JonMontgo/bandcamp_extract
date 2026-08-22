"""Dev tool: capture real Bandcamp response shapes to sanity-check the
pydantic models in bandcamp_extract.bandcamp.types.

Uses the locally saved session (~/.config/bcextr/session.json, created via
`bcextr api login`). Strictly read-only: it never downloads a zip or mutates
anything, only lists/reads data. Dumps raw JSON into scripts/.api_samples/
(gitignored) since responses contain account-specific data.

Run with: python scripts/probe_bandcamp_api.py
"""

import json
import os
import time

from bandcamp_extract.bandcamp import BandcampClient, load_session

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".api_samples")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    session = load_session()
    client = BandcampClient(session["username"], session["identity_cookie"])

    # 1. Profile page pagedata blob (fan_data etc.) — fetched once via the
    #    cached profile_data property and dumped as its validated pydantic shape.
    _dump("pagedata_profile.json", client.profile_data.model_dump(mode="json"))
    fan_id = client.fan_id

    # 2. collection_summary response
    resp = client.session.get("https://bandcamp.com/api/fan/2/collection_summary")
    resp.raise_for_status()
    _dump("collection_summary.json", resp.json())

    # 3. collection_items response (one page only)
    resp = client.session.post(
        "https://bandcamp.com/api/fancollection/1/collection_items",
        json={"fan_id": fan_id, "count": 5, "older_than_token": f"{int(time.time())}::a::"},
    )
    resp.raise_for_status()
    collection_items = resp.json()
    _dump("collection_items.json", collection_items)

    # 4. download page pagedata, if a redownload url is available
    redownload_urls = collection_items.get("redownload_urls", {})
    items = collection_items.get("items", [])
    download_url = None
    if items:
        first_item = items[0]
        key = f"{first_item.get('sale_item_type')}{first_item.get('sale_item_id')}"
        download_url = redownload_urls.get(key)

    if download_url:
        resp = client.session.get(download_url)
        resp.raise_for_status()
        _dump("pagedata_download.json", client._parse_pagedata(resp.text))
    else:
        print("No redownload_url found on first item; skipping download pagedata capture.")

    print(f"\nDone. Raw JSON dumped to: {OUT_DIR}")


def _dump(filename: str, data: object) -> None:
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, default=str)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
