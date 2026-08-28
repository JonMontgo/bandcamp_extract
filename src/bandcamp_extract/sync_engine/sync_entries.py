import os
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Self

import tomli_w

from bandcamp_extract.bandcamp.types import CollectionItem, DownloadFormat

SYNC_CONFIG_DIR = os.path.expanduser("~/.config/bcextr")
SYNC_CONFIG_PATH = os.path.join(SYNC_CONFIG_DIR, "sync.toml")


def _clean_for_toml(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _clean_for_toml(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean_for_toml(x) for x in obj if x is not None]
    return obj


@dataclass
class SyncEntry:
    purchase_id: str
    format: DownloadFormat
    # Used to find if purchase has updated so need to re sync
    last_sync: datetime | None
    # Used to find out if file output pattern has changed and I need delete + re-sync
    last_pattern: str
    bc_entry: CollectionItem
    strip_spaces: bool = False
    no_track_padding: bool = False
    replacement_text: str = ""
    skip: bool = False

    @classmethod
    def from_collection_item(
        cls,
        item: CollectionItem,
        pattern: str,
        format: DownloadFormat,
        strip_spaces: bool = False,
        no_track_padding: bool = False,
        replacement_text: str = "",
        skip: bool = False,
    ) -> Self:
        return cls(
            purchase_id=str(item.item_id),
            format=format,
            last_sync=None,
            last_pattern=pattern,
            strip_spaces=strip_spaces,
            no_track_padding=no_track_padding,
            replacement_text=replacement_text,
            skip=skip,
            bc_entry=item,
        )


@dataclass
class SyncConfig:
    format: DownloadFormat
    path: str = SYNC_CONFIG_PATH
    sync_entries: list[SyncEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: str = SYNC_CONFIG_PATH) -> Self:
        expanded_path = os.path.expanduser(path)
        with open(expanded_path, "rb") as fh:
            data = tomllib.load(fh)
        sync_entries = [
            SyncEntry(
                purchase_id=e["purchase_id"],
                format=e["format"],
                last_sync=e.get("last_sync"),
                last_pattern=e["last_pattern"],
                strip_spaces=e.get("strip_spaces", False),
                no_track_padding=e.get("no_track_padding", False),
                replacement_text=e.get("replacement_text", ""),
                skip=e.get("skip", False),
                bc_entry=CollectionItem.model_validate(e["bc_entry"]),
            )
            for e in data.get("sync_entries", [])
        ]
        return cls(
            format=data["format"],
            path=expanded_path,
            sync_entries=sync_entries,
        )

    @classmethod
    def load_or_create(cls, path: str = SYNC_CONFIG_PATH, default_format: DownloadFormat = "mp3-320") -> Self:
        expanded_path = os.path.expanduser(path)
        try:
            return cls.load(expanded_path)
        except (FileNotFoundError, tomllib.TOMLDecodeError):
            config = cls(format=default_format, path=expanded_path)
            config.save()
            return config

    def save(self, path: str | None = None) -> None:
        target_path = os.path.expanduser(path or self.path)
        self.path = target_path
        entries = []
        for e in self.sync_entries:
            entry_data: dict = {
                "purchase_id": e.purchase_id,
                "format": e.format,
                "last_pattern": e.last_pattern,
                "strip_spaces": e.strip_spaces,
                "no_track_padding": e.no_track_padding,
                "replacement_text": e.replacement_text,
                "skip": e.skip,
                "bc_entry": _clean_for_toml(e.bc_entry.model_dump(exclude_none=True)),
            }
            if e.last_sync is not None:
                entry_data["last_sync"] = e.last_sync
            entries.append(entry_data)
        parent_dir = os.path.dirname(os.path.abspath(target_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(target_path, "wb") as fh:
            tomli_w.dump({"format": self.format, "path": self.path, "sync_entries": entries}, fh)
