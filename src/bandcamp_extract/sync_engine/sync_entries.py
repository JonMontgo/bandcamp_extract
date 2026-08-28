import os
import shutil
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

import tomli_w

from bandcamp_extract.bandcamp.types import CollectionItem, DownloadFormat

SYNC_CONFIG_DIR = os.path.expanduser("~/.config/bcextr")
SYNC_CONFIG_PATH = os.path.join(SYNC_CONFIG_DIR, "sync.toml")


class SkipReason(StrEnum):
    REMOVED = "removed"
    PATTERN_ERROR = "pattern_error"


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
    skip_reason: SkipReason | None = None
    synced_paths: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"[{self.purchase_id}] ({self.format}) {self.bc_entry}"

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
        skip_reason: SkipReason | None = None,
        synced_paths: list[str] | None = None,
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
            skip_reason=skip_reason,
            synced_paths=synced_paths or [],
            bc_entry=item,
        )


def remove_synced_entry_files(entry: SyncEntry) -> list[str]:
    """Delete synced files and empty folders for an entry from disk. Returns list of removed paths."""
    removed: list[str] = []

    def _cleanup_empty_dirs(start_dir: str) -> None:
        parent = os.path.abspath(start_dir)
        while parent and parent != os.path.dirname(parent):
            if os.path.isdir(parent) and not os.listdir(parent):
                try:
                    os.rmdir(parent)
                except OSError:
                    break
                parent = os.path.dirname(parent)
            else:
                break

    # 1. Try deleting explicit tracked synced paths
    if entry.synced_paths:
        for path in entry.synced_paths:
            abs_path = os.path.expanduser(path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                    removed.append(abs_path)
                    _cleanup_empty_dirs(os.path.dirname(abs_path))
                except OSError:
                    pass
            elif os.path.isdir(abs_path):
                try:
                    shutil.rmtree(abs_path)
                    removed.append(abs_path)
                    _cleanup_empty_dirs(os.path.dirname(abs_path))
                except OSError:
                    pass

    # 2. If nothing was removed or synced_paths was empty, infer directory/file from pattern & bc_entry
    if not removed and entry.last_pattern:
        from bandcamp_extract.extract import _resolve_fallback_groups
        from bandcamp_extract.lib import sanitize_dict_values

        band = entry.bc_entry.band_name or ""
        title = entry.bc_entry.item_title or ""
        album = entry.bc_entry.album_title or title

        sub_dict = sanitize_dict_values(
            {
                "artist": band,
                "albumartist": band,
                "album": album,
                "title": title,
            },
            entry.replacement_text,
            entry.strip_spaces,
        )

        try:
            resolved = _resolve_fallback_groups(entry.last_pattern, sub_dict)
            for k, v in sub_dict.items():
                resolved = resolved.replace(f"{{{k}}}", str(v))

            if "{" in resolved:
                prefix = resolved.split("{")[0].rstrip("/\\")
                candidate_dir = prefix
            else:
                candidate_dir = os.path.dirname(resolved)

            candidate_dir = os.path.expanduser(candidate_dir)
            if candidate_dir and os.path.isdir(candidate_dir):
                try:
                    shutil.rmtree(candidate_dir)
                    removed.append(candidate_dir)
                    _cleanup_empty_dirs(os.path.dirname(candidate_dir))
                except OSError:
                    pass
            elif os.path.isfile(os.path.expanduser(resolved)):
                try:
                    file_p = os.path.expanduser(resolved)
                    os.remove(file_p)
                    removed.append(file_p)
                    _cleanup_empty_dirs(os.path.dirname(file_p))
                except OSError:
                    pass
        except Exception:
            pass

    return removed


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
        sync_entries = []
        for e in data.get("sync_entries", []):
            skip_reason_val = e.get("skip_reason")
            skip_reason = None
            if skip_reason_val is not None:
                try:
                    skip_reason = SkipReason(skip_reason_val)
                except ValueError:
                    skip_reason = None
            sync_entries.append(
                SyncEntry(
                    purchase_id=e["purchase_id"],
                    format=e["format"],
                    last_sync=e.get("last_sync"),
                    last_pattern=e["last_pattern"],
                    strip_spaces=e.get("strip_spaces", False),
                    no_track_padding=e.get("no_track_padding", False),
                    replacement_text=e.get("replacement_text", ""),
                    skip=e.get("skip", False),
                    skip_reason=skip_reason,
                    synced_paths=e.get("synced_paths", []),
                    bc_entry=CollectionItem.model_validate(e["bc_entry"]),
                )
            )
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
            if e.skip_reason is not None:
                entry_data["skip_reason"] = str(e.skip_reason)
            if e.synced_paths:
                entry_data["synced_paths"] = e.synced_paths
            if e.last_sync is not None:
                entry_data["last_sync"] = e.last_sync
            entries.append(entry_data)
        parent_dir = os.path.dirname(os.path.abspath(target_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(target_path, "wb") as fh:
            tomli_w.dump({"format": self.format, "path": self.path, "sync_entries": entries}, fh)
