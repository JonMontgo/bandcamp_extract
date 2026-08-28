import os
import tempfile
from typing import cast

import click
from iterfzf import iterfzf

from ..bandcamp.client import DOWNLOAD_FORMATS, FORMAT_EXTENSIONS
from ..bandcamp.types import DownloadFormat
from ..extract import extract_zip
from ..lib import ClickAwareBandcampClient
from .options import (
    format_option,
    no_track_padding_option,
    pattern_option,
    replacement_text_option,
    strip_spaces_option,
)


@click.group()
def api() -> None:
    pass


@api.command()
@click.option("--username", prompt="Bandcamp username")
@click.option("--identity-cookie", prompt="Bandcamp 'identity' cookie value", hide_input=True)
def login(username: str, identity_cookie: str) -> None:
    ClickAwareBandcampClient.login(username, identity_cookie)
    click.echo("Logged in and session saved.")


@api.command(name="list")
def list_collection() -> None:
    client = ClickAwareBandcampClient.from_session()
    items = client.list_collection()
    for item in items:
        label = f"{item} [no download]" if not item.redownload_url else str(item)
        click.echo(label)


@api.command()
@pattern_option
@no_track_padding_option
@replacement_text_option
@strip_spaces_option
@format_option
@click.option("--all", "all_", is_flag=True, help="Download every downloadable purchase, skipping the picker.")
def choose(
    pattern: str,
    no_track_padding: bool,
    replacement_text: str,
    strip_spaces: bool,
    download_format: DownloadFormat | None,
    all_: bool,
) -> None:
    client = ClickAwareBandcampClient.from_session()
    items = client.list_collection()
    if not items:
        raise click.ClickException("Your collection is empty.")

    items = [item for item in items if item.redownload_url]
    if not items:
        raise click.ClickException(
            "No downloadable items in your collection. If you expected some, your "
            "session may not have full download rights — try logging in again with "
            "a fresh identity cookie via `bcextr api login`."
        )

    labels_to_items = {str(item): item for item in items}
    if all_:
        selected_labels = list(labels_to_items.keys())
    else:
        selected_labels = cast(list[str], iterfzf(labels_to_items.keys(), multi=True, bind={"ctrl-a": "select-all"}))
    if not selected_labels:
        raise click.ClickException("No albums selected.")

    if download_format is None:
        download_format = cast(DownloadFormat | None, iterfzf(DOWNLOAD_FORMATS))
        if not download_format:
            raise click.ClickException("No format selected.")

    for label in selected_labels:
        item = labels_to_items[label]
        redownload_url = item.redownload_url
        assert redownload_url is not None  # guaranteed by the filter above
        click.echo(f"Downloading {label} ({download_format})...")
        link = client.get_download_link(redownload_url, download_format)
        ext = FORMAT_EXTENSIONS.get(download_format, ".mp3")
        with tempfile.TemporaryDirectory() as tmpdir:
            download_path = os.path.join(tmpdir, f"download{ext}")
            client.download_file(link, download_path)
            extract_zip(
                download_path,
                pattern,
                pad_track_numbers=not no_track_padding,
                replacement_text=replacement_text,
                strip_spaces=strip_spaces,
            )
