import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bandcamp_extract.bandcamp.client import FORMAT_EXTENSIONS, BandcampClient
from bandcamp_extract.bandcamp.types import CollectionItem, DownloadFormat
from bandcamp_extract.extract import PatternParamError, extract_zip
from bandcamp_extract.sync_engine.sync_entries import SyncConfig, SyncEntry


def get_item_purchase_id(item: CollectionItem) -> str | None:
    if item.item_id is not None:
        return str(item.item_id)
    if item.sale_item_id is not None:
        return str(item.sale_item_id)
    return None


@dataclass
class SyncPlanItem:
    item: CollectionItem
    entry: SyncEntry | None
    reason: str


@dataclass
class SyncPlan:
    to_sync: list[SyncPlanItem]
    up_to_date: list[SyncEntry]
    removed: list[SyncEntry]
    skipped: list[SyncEntry] = field(default_factory=list)


class SyncEngine:
    def __init__(self, sync_config: SyncConfig | None = None):
        self.sync_config = sync_config or SyncConfig(format="flac")

    def plan_sync(
        self,
        bc_entries: list[CollectionItem],
        pattern: str,
        format: DownloadFormat,
        strip_spaces: bool = False,
        no_track_padding: bool = False,
        replacement_text: str = "",
    ) -> SyncPlan:
        entry_map = {e.purchase_id: e for e in self.sync_config.sync_entries}
        to_sync: list[SyncPlanItem] = []
        up_to_date: list[SyncEntry] = []
        skipped: list[SyncEntry] = []
        seen_pids: set[str] = set()

        for item in bc_entries:
            if not item.redownload_url:
                continue
            pid = get_item_purchase_id(item)
            if not pid:
                continue
            seen_pids.add(pid)

            existing = entry_map.get(pid)
            if existing is None:
                to_sync.append(SyncPlanItem(item=item, entry=None, reason="new"))
                continue

            format_changed = existing.format != format
            pattern_changed = existing.last_pattern != pattern
            options_changed = (
                existing.strip_spaces != strip_spaces
                or existing.no_track_padding != no_track_padding
                or existing.replacement_text != replacement_text
            )

            if existing.skip:
                if pattern_changed:
                    to_sync.append(SyncPlanItem(item=item, entry=existing, reason="pattern_changed"))
                elif format_changed:
                    to_sync.append(SyncPlanItem(item=item, entry=existing, reason="format_changed"))
                elif options_changed:
                    to_sync.append(SyncPlanItem(item=item, entry=existing, reason="options_changed"))
                else:
                    skipped.append(existing)
                continue

            is_outdated = (existing.last_sync is None) or (
                item.updated is not None and item.updated > existing.last_sync
            )
            if is_outdated:
                to_sync.append(SyncPlanItem(item=item, entry=existing, reason="updated"))
            elif format_changed:
                to_sync.append(SyncPlanItem(item=item, entry=existing, reason="format_changed"))
            elif pattern_changed:
                to_sync.append(SyncPlanItem(item=item, entry=existing, reason="pattern_changed"))
            elif options_changed:
                to_sync.append(SyncPlanItem(item=item, entry=existing, reason="options_changed"))
            else:
                up_to_date.append(existing)

        removed: list[SyncEntry] = [entry for pid, entry in entry_map.items() if pid not in seen_pids]

        return SyncPlan(to_sync=to_sync, up_to_date=up_to_date, removed=removed, skipped=skipped)

    def record_synced_entry(self, entry: SyncEntry) -> None:
        for i, existing in enumerate(self.sync_config.sync_entries):
            if existing.purchase_id == entry.purchase_id:
                self.sync_config.sync_entries[i] = entry
                return
        self.sync_config.sync_entries.append(entry)

    def sync_item(
        self,
        client: BandcampClient,
        item: CollectionItem,
        pattern: str,
        format: DownloadFormat,
        strip_spaces: bool = False,
        no_track_padding: bool = False,
        replacement_text: str = "",
    ) -> SyncEntry:
        redownload_url = item.redownload_url
        if not redownload_url:
            raise ValueError(f"Item {item.item_title or item.item_id} has no redownload URL")

        link = client.get_download_link(redownload_url, format)
        ext = FORMAT_EXTENSIONS.get(format, ".mp3")
        with tempfile.TemporaryDirectory() as tmpdir:
            download_path = os.path.join(tmpdir, f"download{ext}")
            client.download_file(link, download_path)
            try:
                extract_zip(
                    download_path,
                    pattern,
                    pad_track_numbers=not no_track_padding,
                    replacement_text=replacement_text,
                    strip_spaces=strip_spaces,
                )
            except PatternParamError as err:
                entry = SyncEntry.from_collection_item(
                    item=item,
                    pattern=pattern,
                    format=format,
                    strip_spaces=strip_spaces,
                    no_track_padding=no_track_padding,
                    replacement_text=replacement_text,
                    skip=True,
                )
                entry.last_sync = datetime.now(UTC)
                self.record_synced_entry(entry)
                raise err

        entry = SyncEntry.from_collection_item(
            item=item,
            pattern=pattern,
            format=format,
            strip_spaces=strip_spaces,
            no_track_padding=no_track_padding,
            replacement_text=replacement_text,
            skip=False,
        )
        entry.last_sync = datetime.now(UTC)
        self.record_synced_entry(entry)
        return entry

    def sync_purchases(
        self,
        client: BandcampClient,
        bc_entries: list[CollectionItem],
        pattern: str,
        format: DownloadFormat,
        strip_spaces: bool = False,
        no_track_padding: bool = False,
        replacement_text: str = "",
        on_progress: Callable[[str], None] | None = None,
        on_skip: Callable[[CollectionItem, PatternParamError], None] | None = None,
    ) -> SyncPlan:
        plan = self.plan_sync(
            bc_entries=bc_entries,
            pattern=pattern,
            format=format,
            strip_spaces=strip_spaces,
            no_track_padding=no_track_padding,
            replacement_text=replacement_text,
        )
        self.sync_config.format = format

        for plan_item in plan.to_sync:
            label = f"{plan_item.item.band_name or 'Unknown'} - {plan_item.item.item_title or 'Unknown'}"
            if on_progress:
                on_progress(f"Syncing [{plan_item.reason}] {label} ({format})...")
            try:
                self.sync_item(
                    client=client,
                    item=plan_item.item,
                    pattern=pattern,
                    format=format,
                    strip_spaces=strip_spaces,
                    no_track_padding=no_track_padding,
                    replacement_text=replacement_text,
                )
            except PatternParamError as err:
                if on_skip:
                    on_skip(plan_item.item, err)

        return plan
