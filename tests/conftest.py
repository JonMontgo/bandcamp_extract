"""Pytest configuration: refresh scripts/.api_samples/ before the test session.

Behavior:
- If no session file (~/.config/bcextr/session.json) is present, skip the probe
  silently — the fast unit tests still run, and the integration tests in
  test_types.py self-skip on missing samples.
- If a session is present, run scripts/probe_bandcamp_api.py as a subprocess
  so tests exercise current Bandcamp response shapes. Failures (expired
  cookie, network error) are logged as a warning but never fail the suite —
  the integration tests will then skip on their own.
- Set BCEXTR_SKIP_PROBE=1 to skip the probe entirely (CI / offline / fast
  unit-test loops).

The probe is read-only against Bandcamp; it only writes to the gitignored
scripts/.api_samples/ directory.
"""

import os
import subprocess
import sys

import pytest

_SESSION_PATH = os.path.expanduser("~/.config/bcextr/session.json")
_PROBE_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "probe_bandcamp_api.py",
)
_SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    ".api_samples",
)


def _samples_present() -> bool:
    return all(
        os.path.exists(os.path.join(_SAMPLES_DIR, name)) for name in ("collection_items.json", "pagedata_download.json")
    )


@pytest.fixture(scope="session", autouse=True)
def _refresh_api_samples() -> None:
    """Best-effort refresh of scripts/.api_samples/ before the test session."""
    if os.environ.get("BCEXTR_SKIP_PROBE"):
        return
    if not os.path.exists(_SESSION_PATH):
        return  # nothing to auth with; integration tests will self-skip
    if not os.path.exists(_PROBE_SCRIPT):
        return

    try:
        proc = subprocess.run(
            [sys.executable, _PROBE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("\n[conftest] probe timed out; integration tests will be skipped if samples are stale")
        return

    if proc.returncode != 0:
        print(
            f"\n[conftest] probe failed (rc={proc.returncode}); "
            f"integration tests will skip if samples are stale.\n"
            f"  stdout: {proc.stdout.strip()}\n"
            f"  stderr: {proc.stderr.strip()}"
        )
        return

    if not _samples_present():
        print("\n[conftest] probe ran but expected sample files are missing; integration tests will be skipped.")
