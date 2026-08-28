import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bandcamp_extract.bandcamp.types import CollectionItem
from bandcamp_extract.commands.sync import sync
from bandcamp_extract.sync_engine.sync_engine import SyncEngine
from bandcamp_extract.sync_engine.sync_entries import SkipReason, SyncConfig, SyncEntry


def _make_item(item_id: int, title: str = "Test Album", updated_dt: datetime | None = None) -> CollectionItem:
    item = CollectionItem(
        item_id=item_id,
        item_type="album",
        sale_item_type="a",
        sale_item_id=item_id,
        band_name="Test Band",
        item_title=title,
        redownload_url=f"https://bandcamp.com/download/{item_id}",
    )
    if updated_dt:
        item.updated = updated_dt
    return item


def test_sync_config_save_load_round_trip():
    item = _make_item(100, "Album A", datetime(2026, 8, 1, 12, 0, tzinfo=UTC))
    entry = SyncEntry.from_collection_item(
        item=item,
        pattern="{artist}/{album}/{title}",
        format="flac",
        strip_spaces=True,
        no_track_padding=True,
        replacement_text="_",
    )
    entry.last_sync = datetime(2026, 8, 10, 0, 0, tzinfo=UTC)

    config = SyncConfig(format="flac", sync_entries=[entry])

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "sync.toml")
        config.save(config_path)

        loaded = SyncConfig.load(config_path)
        assert loaded.format == "flac"
        assert len(loaded.sync_entries) == 1

        e = loaded.sync_entries[0]
        assert e.purchase_id == "100"
        assert e.format == "flac"
        assert e.last_pattern == "{artist}/{album}/{title}"
        assert e.strip_spaces is True
        assert e.no_track_padding is True
        assert e.replacement_text == "_"
        assert e.last_sync == datetime(2026, 8, 10, 0, 0, tzinfo=UTC)
        assert e.bc_entry.item_title == "Album A"


def test_sync_config_save_with_nested_null_values():
    item = CollectionItem(
        item_id=101,
        item_title="Album with Nested Nulls",
        package_details={"shipping": None, "note": "fragile"},
        releases=[{"details": None, "id": 1}],
    )
    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "flac")
    config = SyncConfig(format="flac", sync_entries=[entry])

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "sync.toml")
        config.save(config_path)

        loaded = SyncConfig.load(config_path)
        assert len(loaded.sync_entries) == 1
        assert loaded.sync_entries[0].bc_entry.item_title == "Album with Nested Nulls"


def test_plan_sync_new_items():
    engine = SyncEngine(SyncConfig(format="flac"))
    items = [_make_item(1, "Album 1"), _make_item(2, "Album 2")]

    plan = engine.plan_sync(
        bc_entries=items,
        pattern="{artist}/{album}/{title}",
        format="flac",
    )

    assert len(plan.to_sync) == 2
    assert plan.to_sync[0].reason == "new"
    assert plan.to_sync[1].reason == "new"
    assert len(plan.up_to_date) == 0
    assert len(plan.removed) == 0


def test_plan_sync_skips_no_redownload_url():
    engine = SyncEngine(SyncConfig(format="flac"))
    item = CollectionItem(item_id=999, item_type="merch", item_title="T-Shirt", redownload_url=None)

    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac")
    assert len(plan.to_sync) == 0
    assert len(plan.up_to_date) == 0


def test_plan_sync_up_to_date():
    sync_time = datetime(2026, 8, 15, tzinfo=UTC)
    item = _make_item(1, "Album 1", updated_dt=datetime(2026, 8, 10, tzinfo=UTC))
    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "flac")
    entry.last_sync = sync_time

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac")

    assert len(plan.to_sync) == 0
    assert len(plan.up_to_date) == 1
    assert plan.up_to_date[0].purchase_id == "1"


def test_plan_sync_outdated_item():
    sync_time = datetime(2026, 8, 10, tzinfo=UTC)
    update_time = datetime(2026, 8, 15, tzinfo=UTC)
    item = _make_item(1, "Album 1", updated_dt=update_time)

    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "flac")
    entry.last_sync = sync_time

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac")

    assert len(plan.to_sync) == 1
    assert plan.to_sync[0].reason == "updated"


def test_plan_sync_format_changed():
    item = _make_item(1, "Album 1")
    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "mp3-320")
    entry.last_sync = datetime.now(UTC)

    engine = SyncEngine(SyncConfig(format="mp3-320", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac")

    assert len(plan.to_sync) == 1
    assert plan.to_sync[0].reason == "format_changed"


def test_plan_sync_pattern_changed():
    item = _make_item(1, "Album 1")
    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "flac")
    entry.last_sync = datetime.now(UTC)

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{albumartist}/{album}/{title}", format="flac")

    assert len(plan.to_sync) == 1
    assert plan.to_sync[0].reason == "pattern_changed"


def test_plan_sync_options_changed():
    item = _make_item(1, "Album 1")
    entry = SyncEntry.from_collection_item(
        item, "{artist}/{album}", "flac", strip_spaces=False, no_track_padding=False, replacement_text=""
    )
    entry.last_sync = datetime.now(UTC)

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))

    # Test strip_spaces change
    plan1 = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac", strip_spaces=True)
    assert len(plan1.to_sync) == 1
    assert plan1.to_sync[0].reason == "options_changed"

    # Test no_track_padding change
    plan2 = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac", no_track_padding=True)
    assert len(plan2.to_sync) == 1
    assert plan2.to_sync[0].reason == "options_changed"

    # Test replacement_text change
    plan3 = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac", replacement_text="-")
    assert len(plan3.to_sync) == 1
    assert plan3.to_sync[0].reason == "options_changed"


def test_plan_sync_removed_from_bandcamp():
    item_old = _make_item(99, "Removed Album")
    entry = SyncEntry.from_collection_item(item_old, "{artist}/{album}", "flac")
    entry.last_sync = datetime.now(UTC)

    item_current = _make_item(1, "Current Album")

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item_current], pattern="{artist}/{album}", format="flac")

    assert len(plan.to_sync) == 1
    assert plan.to_sync[0].item.item_id == 1
    assert len(plan.removed) == 1
    assert plan.removed[0].purchase_id == "99"


def test_record_synced_entry_updates_existing():
    item = _make_item(1, "Album 1")
    entry1 = SyncEntry.from_collection_item(item, "pattern1", "mp3-320")
    engine = SyncEngine(SyncConfig(format="mp3-320", sync_entries=[entry1]))

    entry2 = SyncEntry.from_collection_item(item, "pattern2", "flac")
    entry2.last_sync = datetime.now(UTC)
    engine.record_synced_entry(entry2)

    assert len(engine.sync_config.sync_entries) == 1
    assert engine.sync_config.sync_entries[0].last_pattern == "pattern2"
    assert engine.sync_config.sync_entries[0].format == "flac"


def test_sync_purchases_orchestration():
    item = _make_item(1, "Album 1")
    mock_client = MagicMock()
    mock_client.get_download_link.return_value = "https://example.com/download.zip"

    engine = SyncEngine(SyncConfig(format="flac"))

    # Mock sync_item so it doesn't download a real network zip
    def fake_sync_item(client, item, pattern, format, strip_spaces, no_track_padding, replacement_text):
        entry = SyncEntry.from_collection_item(
            item, pattern, format, strip_spaces, no_track_padding, replacement_text
        )
        entry.last_sync = datetime.now(UTC)
        engine.record_synced_entry(entry)
        return entry

    engine.sync_item = fake_sync_item  # type: ignore

    progress_messages = []
    plan = engine.sync_purchases(
        client=mock_client,
        bc_entries=[item],
        pattern="{artist}/{album}",
        format="flac",
        on_progress=lambda msg: progress_messages.append(msg),
    )

    assert len(plan.to_sync) == 1
    assert len(progress_messages) == 1
    assert "Syncing [new] [a-1] Test Band - Album 1 (flac)..." in progress_messages[0]
    assert len(engine.sync_config.sync_entries) == 1
    assert engine.sync_config.sync_entries[0].purchase_id == "1"


def test_plan_sync_skipped_entry_same_pattern():
    item = _make_item(1, "Album 1")
    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "flac", skip=True)
    entry.last_sync = datetime.now(UTC)

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album}", format="flac")

    assert len(plan.to_sync) == 0
    assert len(plan.up_to_date) == 0
    assert len(plan.skipped) == 1
    assert plan.skipped[0].purchase_id == "1"


def test_plan_sync_skipped_entry_new_pattern_retries():
    item = _make_item(1, "Album 1")
    entry = SyncEntry.from_collection_item(
        item, "{artist}/{album}", "flac", skip=True, skip_reason=SkipReason.PATTERN_ERROR
    )
    entry.last_sync = datetime.now(UTC)

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album,title}", format="flac")

    assert len(plan.to_sync) == 1
    assert plan.to_sync[0].reason == "pattern_changed"
    assert len(plan.skipped) == 0


def test_plan_sync_removed_entry_stays_skipped_on_pattern_change():
    item = _make_item(1, "Album 1")
    entry = SyncEntry.from_collection_item(item, "{artist}/{album}", "flac", skip=True, skip_reason=SkipReason.REMOVED)
    entry.last_sync = datetime.now(UTC)

    engine = SyncEngine(SyncConfig(format="flac", sync_entries=[entry]))
    plan = engine.plan_sync(bc_entries=[item], pattern="{artist}/{album,title}", format="flac")

    # Should remain skipped because it was deliberately removed
    assert len(plan.to_sync) == 0
    assert len(plan.skipped) == 1


def test_sync_config_save_load_with_skip_reason():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "sync.toml")
        entry = SyncEntry.from_collection_item(
            item=_make_item(1, "Album 1"),
            pattern="{artist}/{album}",
            format="flac",
            skip=True,
            skip_reason=SkipReason.REMOVED,
        )
        config = SyncConfig(format="flac", path=config_path, sync_entries=[entry])
        config.save()

        loaded = SyncConfig.load(config_path)
        assert len(loaded.sync_entries) == 1
        assert loaded.sync_entries[0].skip is True
        assert loaded.sync_entries[0].skip_reason == SkipReason.REMOVED


def test_sync_config_load_or_create_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "nested", "sync.toml")
        assert not os.path.exists(config_path)

        config = SyncConfig.load_or_create(config_path, default_format="mp3-320")
        assert os.path.exists(config_path)
        assert config.format == "mp3-320"
        assert config.path == config_path
        assert config.sync_entries == []


def test_sync_cli_with_sync_file(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        sync_file = os.path.join(tmpdir, "custom_sync.toml")
        assert not os.path.exists(sync_file)

        mock_client = MagicMock()
        mock_client.list_collection.return_value = [
            _make_item(100, "Album X"),
        ]
        mock_client.get_download_link.return_value = "https://example.com/download.zip"

        runner = CliRunner()
        song_path = os.path.join(tmpdir, "song.mp3")
        with (
            patch("bandcamp_extract.bandcamp.client.BandcampClient.from_session", return_value=mock_client),
            patch("bandcamp_extract.sync_engine.sync_engine.extract_zip", return_value=[song_path]),
            patch("bandcamp_extract.bandcamp.client.BandcampClient.download_file"),
        ):
            result = runner.invoke(
                sync,
                [
                    "--sync-file",
                    sync_file,
                    "--format",
                    "mp3-320",
                    "--pattern",
                    os.path.join(tmpdir, "music", "{artist}", "{album}", "{title}"),
                ],
            )
            assert result.exit_code == 0
            assert os.path.exists(sync_file)

            loaded = SyncConfig.load(sync_file)
            assert loaded.format == "mp3-320"
            assert len(loaded.sync_entries) == 1
            assert loaded.sync_entries[0].purchase_id == "100"


def test_remove_synced_entry_files_with_synced_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        album_dir = os.path.join(tmpdir, "Artist", "Album")
        os.makedirs(album_dir)
        file1 = os.path.join(album_dir, "01-Song1.mp3")
        file2 = os.path.join(album_dir, "02-Song2.mp3")
        with open(file1, "w") as fh:
            fh.write("audio1")
        with open(file2, "w") as fh:
            fh.write("audio2")

        item = _make_item(200, "Album")
        entry = SyncEntry.from_collection_item(
            item=item,
            pattern=os.path.join(tmpdir, "{artist}", "{album}", "{title}"),
            format="mp3-320",
            synced_paths=[file1, file2],
        )

        from bandcamp_extract.sync_engine.sync_entries import remove_synced_entry_files

        removed = remove_synced_entry_files(entry)
        assert len(removed) == 2
        assert not os.path.exists(file1)
        assert not os.path.exists(file2)
        # Empty directories should also be cleaned up
        assert not os.path.exists(album_dir)
        assert not os.path.exists(os.path.join(tmpdir, "Artist"))


def test_remove_synced_entry_files_fallback_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        album_dir = os.path.join(tmpdir, "Test Band", "Test Album")
        os.makedirs(album_dir)
        file1 = os.path.join(album_dir, "01-Song.mp3")
        with open(file1, "w") as fh:
            fh.write("audio")

        item = _make_item(201, "Test Album")
        # No synced_paths provided -> fallback to pattern inference
        entry = SyncEntry.from_collection_item(
            item=item,
            pattern=os.path.join(tmpdir, "{artist}", "{album}", "{track}-{title}"),
            format="mp3-320",
        )

        from bandcamp_extract.sync_engine.sync_entries import remove_synced_entry_files

        removed = remove_synced_entry_files(entry)
        assert len(removed) >= 1
        assert not os.path.exists(file1)
        assert not os.path.exists(album_dir)


def test_sync_cli_remove():
    with tempfile.TemporaryDirectory() as tmpdir:
        sync_file = os.path.join(tmpdir, "sync.toml")
        album_dir = os.path.join(tmpdir, "music", "Band", "Album")
        os.makedirs(album_dir)
        track_file = os.path.join(album_dir, "track.mp3")
        with open(track_file, "w") as fh:
            fh.write("data")

        item = CollectionItem(
            item_id=300,
            sale_item_type="a",
            sale_item_id=300,
            band_name="Band",
            item_title="Album",
            redownload_url="https://url",
        )
        entry = SyncEntry.from_collection_item(
            item=item,
            pattern=os.path.join(tmpdir, "music", "{artist}", "{album}", "{title}"),
            format="mp3-320",
            synced_paths=[track_file],
        )
        entry.last_sync = datetime.now(UTC)

        config = SyncConfig(format="mp3-320", path=sync_file, sync_entries=[entry])
        config.save()

        runner = CliRunner()
        with patch("bandcamp_extract.commands.sync.iterfzf", return_value=[str(entry)]):
            result = runner.invoke(
                sync,
                [
                    "--remove",
                    "--sync-file",
                    sync_file,
                ],
            )
            assert result.exit_code == 0
            assert "Removed 1 file(s)/folder(s)" in result.output
            assert not os.path.exists(track_file)
            assert not os.path.exists(album_dir)

            reloaded = SyncConfig.load(sync_file)
            assert len(reloaded.sync_entries) == 1
            assert reloaded.sync_entries[0].skip is True


def test_remove_synced_entry_files_hierarchical_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        foo_dir = os.path.join(tmpdir, "foo")
        bar_dir = os.path.join(foo_dir, "bar")
        too_dir = os.path.join(foo_dir, "too")
        os.makedirs(bar_dir)
        os.makedirs(too_dir)

        baz_file = os.path.join(bar_dir, "baz.mp3")
        bat_file = os.path.join(bar_dir, "bat.mp3")
        yap_file = os.path.join(too_dir, "yap.mp3")
        yip_file = os.path.join(too_dir, "yip.mp3")

        for f in (baz_file, bat_file, yap_file, yip_file):
            with open(f, "w") as fh:
                fh.write("music")

        from bandcamp_extract.sync_engine.sync_entries import remove_synced_entry_files

        # Entry for bar
        entry_bar = SyncEntry.from_collection_item(
            item=_make_item(10, "bar"),
            pattern=os.path.join(foo_dir, "bar", "{title}"),
            format="mp3-320",
            synced_paths=[baz_file, bat_file],
        )

        # Entry for too
        entry_too = SyncEntry.from_collection_item(
            item=_make_item(20, "too"),
            pattern=os.path.join(foo_dir, "too", "{title}"),
            format="mp3-320",
            synced_paths=[yap_file, yip_file],
        )

        # Step 1: Remove bar
        removed_bar = remove_synced_entry_files(entry_bar)
        assert len(removed_bar) == 2
        assert not os.path.exists(bar_dir)
        # foo and too are still intact
        assert os.path.exists(too_dir)
        assert os.path.exists(foo_dir)
        assert os.path.exists(yap_file)

        # Step 2: Remove too
        removed_too = remove_synced_entry_files(entry_too)
        assert len(removed_too) == 2
        assert not os.path.exists(too_dir)
        # foo is now empty, so foo is deleted
        assert not os.path.exists(foo_dir)
