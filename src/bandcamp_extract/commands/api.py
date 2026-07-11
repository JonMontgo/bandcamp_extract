import os
import tempfile
from typing import Any

import click
from iterfzf import iterfzf

from ..bandcamp import BandcampClient, load_session, save_session
from ..bandcamp.client import DOWNLOAD_FORMATS
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


def _label(item: dict[str, Any]) -> str:
    return f"{item.get('band_name', 'Unknown Artist')} - {item.get('item_title', 'Unknown Album')}"


@click.group()
def api() -> None:
    pass


@api.command()
@click.option("--username", prompt="Bandcamp username")
@click.option("--identity-cookie", prompt="Bandcamp 'identity' cookie value", hide_input=True)
def login(username: str, identity_cookie: str) -> None:
    client = BandcampClient(username, identity_cookie)
    try:
        client.get_fan_id()
        client.check_session()
    except Exception as err:
        raise click.ClickException(f"Login failed: {err}") from err
    save_session(username, identity_cookie)
    click.echo("Logged in and session saved.")


@api.command(name="list")
def list_() -> None:
    client = _client_from_session()
    fan_id = client.get_fan_id()
    items = client.list_collection(fan_id)
    for item in items:
        label = _label(item)
        if not item.get("redownload_url"):
            label += " [no download]"
        click.echo(label)


@api.command()
@pattern_option
@no_track_padding_option
@replacement_text_option
@strip_spaces_option
@click.option("--format", "format_", type=click.Choice(DOWNLOAD_FORMATS), default=None)
def choose(
    pattern: str,
    no_track_padding: bool,
    replacement_text: str,
    strip_spaces: bool,
    format_: str | None,
) -> None:
    client = _client_from_session()
    fan_id = client.get_fan_id()
    items = client.list_collection(fan_id)
    if not items:
        raise click.ClickException("Your collection is empty.")

    items = [item for item in items if item.get("redownload_url")]
    if not items:
        raise click.ClickException(
            "No downloadable items in your collection. If you expected some, your "
            "session may not have full download rights — try logging in again with "
            "a fresh identity cookie via `bcextr api login`."
        )

    labels_to_items = {_label(item): item for item in items}
    selected_labels = iterfzf(labels_to_items.keys(), multi=True)
    if not selected_labels:
        raise click.ClickException("No albums selected.")

    if format_ is None:
        format_ = iterfzf(DOWNLOAD_FORMATS)
        if not format_:
            raise click.ClickException("No format selected.")

    for label in selected_labels:
        item = labels_to_items[label]
        click.echo(f"Downloading {label} ({format_})...")
        link = client.get_download_link(item["redownload_url"], format_)
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
