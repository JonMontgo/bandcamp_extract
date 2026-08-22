import os
import tempfile
from typing import cast

import click
from iterfzf import iterfzf

from ..bandcamp import BandcampClient, load_session, save_session
from ..bandcamp.client import DOWNLOAD_FORMATS
from ..bandcamp.types import CollectionItem, DownloadFormat
from ..extract import extract_zip
from .options import no_track_padding_option, pattern_option, replacement_text_option, strip_spaces_option


def _client_from_session() -> BandcampClient:
    session = load_session()
    client = BandcampClient(session["username"], session["identity_cookie"])
    try:
        client.check_session()
    except Exception as err:
        raise click.ClickException(str(err)) from err
    return client


def _label(item: CollectionItem) -> str:
    return f"{item.band_name or 'Unknown Artist'} - {item.item_title or 'Unknown Album'}"


@click.group()
def api() -> None:
    pass


@api.command()
@click.option("--username", prompt="Bandcamp username")
@click.option("--identity-cookie", prompt="Bandcamp 'identity' cookie value", hide_input=True)
def login(username: str, identity_cookie: str) -> None:
    client = BandcampClient(username, identity_cookie)
    try:
        _ = client.fan_id  # triggers the profile-page fetch (validates username/cookie shape)
        client.check_session()  # strong auth check on a true auth-required endpoint
    except Exception as err:
        raise click.ClickException(f"Login failed: {err}") from err
    save_session(username, identity_cookie)
    click.echo("Logged in and session saved.")


@api.command(name="list")
def list_() -> None:
    client = _client_from_session()
    items = client.list_collection()
    for item in items:
        label = _label(item)
        if not item.redownload_url:
            label += " [no download]"
        click.echo(label)


@api.command()
@pattern_option
@no_track_padding_option
@replacement_text_option
@strip_spaces_option
@click.option("--format", "format_", type=click.Choice(DOWNLOAD_FORMATS), default=None)
@click.option("--all", "all_", is_flag=True, help="Download every downloadable purchase, skipping the picker.")
def choose(
    pattern: str,
    no_track_padding: bool,
    replacement_text: str,
    strip_spaces: bool,
    format_: DownloadFormat | None,
    all_: bool,
) -> None:
    client = _client_from_session()
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

    labels_to_items = {_label(item): item for item in items}
    if all_:
        selected_labels = list(labels_to_items.keys())
    else:
        selected_labels = cast(list[str], iterfzf(labels_to_items.keys(), multi=True, bind={"ctrl-a": "select-all"}))
    if not selected_labels:
        raise click.ClickException("No albums selected.")

    if format_ is None:
        format_ = cast(DownloadFormat | None, iterfzf(DOWNLOAD_FORMATS))
        if not format_:
            raise click.ClickException("No format selected.")

    for label in selected_labels:
        item = labels_to_items[label]
        redownload_url = item.redownload_url
        assert redownload_url is not None  # guaranteed by the filter above
        click.echo(f"Downloading {label} ({format_})...")
        link = client.get_download_link(redownload_url, format_)
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "album.zip")
            client.download_zip(link, zip_path)
            extract_zip(
                zip_path,
                pattern,
                pad_track_numbers=not no_track_padding,
                replacement_text=replacement_text,
                strip_spaces=strip_spaces,
            )
