"""yt-dlp binary manager: download and auto-update.

yt-dlp is shipped as a runtime-downloaded binary rather than a bundled
dependency on purpose. YouTube changes its player often enough that a pinned
copy goes stale within weeks, and self-updating the binary is far cheaper than
rebuilding and redistributing the whole app every time that happens.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

GITHUB_RELEASES_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
_RELEASE_BASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download"
UPDATE_CHECK_INTERVAL_HOURS = 24

_SUBPROCESS_FLAGS = (
    getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
)


def _asset_name() -> str:
    if sys.platform == "win32":
        return "yt-dlp.exe"
    if sys.platform == "darwin":
        return "yt-dlp_macos"
    return "yt-dlp_linux"


def _binary_name() -> str:
    return "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"


def get_download_url() -> str:
    return f"{_RELEASE_BASE}/{_asset_name()}"


def get_data_dir() -> Path:
    """Where the database, cookies and yt-dlp binary live.

    From source it is always ``data/`` beside the code. Frozen builds differ by
    platform: Windows stays portable next to the .exe, while macOS and Linux
    use the per-user data directory because the app there may sit in a
    read-only location (inside a .app bundle, or ``/usr/local/bin``).

    ``CAPTION_SEARCH_DATA_DIR`` overrides all of it.
    """
    override = os.environ.get("CAPTION_SEARCH_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent / "data"

    if sys.platform == "win32":
        return Path(sys.executable).parent / "data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Caption Search"

    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "caption-search"


def get_ytdlp_path() -> Path:
    return get_data_dir() / _binary_name()


def get_version_file() -> Path:
    return get_data_dir() / ".ytdlp-version"


def get_local_version() -> Optional[str]:
    ytdlp = get_ytdlp_path()
    if not ytdlp.exists():
        return None
    try:
        result = subprocess.run(
            [str(ytdlp), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=_SUBPROCESS_FLAGS,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def get_latest_version() -> Optional[str]:
    try:
        request = urllib.request.Request(
            GITHUB_RELEASES_URL, headers={"User-Agent": "caption-search"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode())
            return data.get("tag_name", "").lstrip("v")
    except Exception:
        return None


def should_check_update() -> bool:
    version_file = get_version_file()
    if not version_file.exists():
        return True
    try:
        data = json.loads(version_file.read_text())
        last_check = datetime.fromisoformat(data.get("last_check", ""))
        hours_since = (datetime.now(timezone.utc) - last_check).total_seconds() / 3600
        return hours_since >= UPDATE_CHECK_INTERVAL_HOURS
    except Exception:
        return True


def save_version_info(version: str) -> None:
    version_file = get_version_file()
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(
        json.dumps(
            {"version": version, "last_check": datetime.now(timezone.utc).isoformat()}
        )
    )


def download_ytdlp(on_progress: Optional[Callable[[int, int], None]] = None) -> bool:
    ytdlp = get_ytdlp_path()
    ytdlp.parent.mkdir(parents=True, exist_ok=True)
    temp_path = ytdlp.with_suffix(".tmp")

    try:
        request = urllib.request.Request(
            get_download_url(), headers={"User-Agent": "caption-search"}
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(temp_path, "wb") as handle:
                while chunk := response.read(65536):
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if on_progress and total:
                        on_progress(downloaded, total)

        if ytdlp.exists():
            ytdlp.unlink()
        temp_path.rename(ytdlp)
        if sys.platform != "win32":
            ytdlp.chmod(ytdlp.stat().st_mode | 0o111)

        version = get_local_version()
        if version:
            save_version_info(version)
        return True
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to download yt-dlp: {exc}") from exc


def ensure_ytdlp(on_status: Optional[Callable[[str], None]] = None) -> Path:
    """Make sure a usable yt-dlp exists, updating it at most once a day.

    A failed update check is not fatal when a binary is already present -- the
    app still works offline against whatever is on disk.
    """
    ytdlp = get_ytdlp_path()

    def status(message: str) -> None:
        if on_status:
            on_status(message)

    if not ytdlp.exists():
        status("Downloading yt-dlp...")
        download_ytdlp()
        status("yt-dlp ready")
        return ytdlp

    if should_check_update():
        status("Checking for yt-dlp updates...")
        local_version = get_local_version()
        latest_version = get_latest_version()
        if latest_version and local_version and latest_version != local_version:
            status(f"Updating yt-dlp ({local_version} -> {latest_version})...")
            try:
                download_ytdlp()
                status("yt-dlp updated")
            except RuntimeError as exc:
                status(f"yt-dlp update failed, keeping {local_version}: {exc}")
        else:
            if local_version:
                save_version_info(local_version)
            status("yt-dlp is up to date")

    return ytdlp


def resolve_ytdlp() -> str:
    """Path to the yt-dlp to run.

    ``CAPTION_SEARCH_YTDLP`` overrides it, which keeps tests and development off
    the managed copy.
    """
    override = os.environ.get("CAPTION_SEARCH_YTDLP")
    if override:
        return override
    return str(get_ytdlp_path())
