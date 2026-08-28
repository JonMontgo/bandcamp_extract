import os
import tomllib
from typing import cast

import click
from iterfzf import iterfzf

from ..bandcamp import BandcampClient, load_session
from ..bandcamp.types import DownloadFormat
from ..extract import PatternParamError
from ..sync_engine.sync_engine import SyncEngine
from ..sync_engine.sync_entries import (
    SYNC_CONFIG_PATH,
    SkipReason,
    SyncConfig,
    remove_synced_entry_files,
)
from .options import (
    format_option,
    no_track_padding_option,
    pattern_option,
    remove_option,
    replacement_text_option,
    strip_spaces_option,
    sync_file_option,
)


def _client_from_session() -> BandcampClient:
    session = load_session()
    client = BandcampClient(session["username"], session["identity_cookie"])
    try:
        client.check_session()
    except Exception as err:
        raise click.ClickException(str(err)) from err
    return client


@click.command()
@pattern_option
@no_track_padding_option
@replacement_text_option
@strip_spaces_option
@format_option
@sync_file_option
@remove_option
def sync(
    pattern: str,
    no_track_padding: bool,
    replacement_text: str,
    strip_spaces: bool,
    download_format: DownloadFormat | None,
    sync_file: str | None,
    remove: bool,
) -> None:
    sync_path = os.path.expanduser(sync_file) if sync_file else SYNC_CONFIG_PATH

    if remove:
        try:
            config = SyncConfig.load(sync_path)
        except (FileNotFoundError, tomllib.TOMLDecodeError):
            click.echo("No sync entries found.")
            return

        active_entries = [e for e in config.sync_entries if not e.skip]
        if not active_entries:
            click.echo("No active sync entries found to remove.")
            return

        labels_to_entries = {}
        for e in active_entries:
            band = e.bc_entry.band_name or "Unknown"
            title = e.bc_entry.item_title or "Unknown"
            base_label = f"{band} - {title} ({e.format})"
            label = base_label
            counter = 1
            while label in labels_to_entries:
                label = f"{base_label} [{e.purchase_id}-{counter}]"
                counter += 1
            labels_to_entries[label] = e

        selected_labels = cast(
            list[str] | None,
            iterfzf(labels_to_entries.keys(), multi=True, bind={"ctrl-a": "select-all"}),
        )
        if not selected_labels:
            click.echo("No entries selected.")
            return

        for label in selected_labels:
            entry = labels_to_entries[label]
            removed = remove_synced_entry_files(entry)
            entry.skip = True
            entry.skip_reason = SkipReason.REMOVED
            entry.synced_paths = []
            if removed:
                click.echo(f"Removed {len(removed)} file(s)/folder(s) for '{label}' and marked as skipped.")
            else:
                click.echo(f"Marked '{label}' as skipped (no local files found).")
        config.save()
        click.echo("Removal complete!")
        return

    client = _client_from_session()

    try:
        config = SyncConfig.load(sync_path)
        if download_format:
            config.format = download_format
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        target_format: DownloadFormat = download_format or "mp3-320"
        config = SyncConfig(format=target_format, path=sync_path)
        config.save()

    target_format = config.format
    engine = SyncEngine(sync_config=config)

    click.echo("Fetching collection from Bandcamp...")
    items = client.list_collection()
    if not items:
        raise click.ClickException("Your collection is empty.")

    plan = engine.plan_sync(
        bc_entries=items,
        pattern=pattern,
        format=target_format,
        strip_spaces=strip_spaces,
        no_track_padding=no_track_padding,
        replacement_text=replacement_text,
    )

    for removed_entry in plan.removed:
        label = f"{removed_entry.bc_entry.band_name or 'Unknown'} - {removed_entry.bc_entry.item_title or 'Unknown'}"
        msg = (
            f"Warning: '{label}' (ID {removed_entry.purchase_id}) is in your sync config "
            "but was not found in your Bandcamp collection."
        )
        click.secho(msg, fg="yellow")

    for skipped_entry in plan.skipped:
        label = f"{skipped_entry.bc_entry.band_name or 'Unknown'} - {skipped_entry.bc_entry.item_title or 'Unknown'}"
        if skipped_entry.skip_reason == SkipReason.REMOVED:
            msg = f"Skipping '{label}' (marked skipped because it was removed with --remove)."
        elif skipped_entry.skip_reason == SkipReason.PATTERN_ERROR:
            msg = (
                f"Skipping '{label}' (marked skipped due to missing pattern params; "
                "retry by updating --pattern with fallbacks)."
            )
        else:
            msg = (
                f"Skipping '{label}' (marked skipped due to choosing remove or "
                "sync failed due to missing pattern params; retry by updating --pattern with fallbacks)."
            )
        click.secho(msg, fg="yellow")

    skip_msg = f", {len(plan.skipped)} skipped" if plan.skipped else ""
    if not plan.to_sync:
        click.echo(f"All {len(plan.up_to_date)} item(s) are already in sync{skip_msg}.")
        return

    click.echo(
        f"Found {len(plan.to_sync)} item(s) to sync "
        f"({len(plan.up_to_date)} already in sync{skip_msg})..."
    )

    for plan_item in plan.to_sync:
        item = plan_item.item
        label = f"{item.band_name or 'Unknown'} - {item.item_title or 'Unknown'}"
        click.echo(f"Syncing [{plan_item.reason}] {label} ({target_format})...")
        try:
            engine.sync_item(
                client=client,
                item=item,
                pattern=pattern,
                format=target_format,
                strip_spaces=strip_spaces,
                no_track_padding=no_track_padding,
                replacement_text=replacement_text,
            )
        except PatternParamError as err:
            msg = (
                f"Skipped '{label}': Param {{{err.param}}} not found in metadata. "
                f"Retry with fallback params (e.g. {{{err.param},artist}} or {{{err.param},title}}) "
                "to sync this entry."
            )
            click.secho(msg, fg="yellow")
        config.save()

    click.echo("Sync complete!")
