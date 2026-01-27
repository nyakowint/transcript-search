"""yt-dlp binary manager: download and auto-update."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GITHUB_RELEASES_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
UPDATE_CHECK_INTERVAL_HOURS = 24


def get_data_dir() -> Path:
    """Get the data directory (next to exe when frozen, next to script otherwise)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "data"
    return Path(__file__).resolve().parent / "data"


def get_ytdlp_path() -> Path:
    """Get the path to the yt-dlp binary."""
    return get_data_dir() / "yt-dlp.exe"


def get_version_file() -> Path:
    """Get the path to the version cache file."""
    return get_data_dir() / ".ytdlp-version"


def get_local_version() -> str | None:
    """Get the version of the local yt-dlp binary."""
    ytdlp = get_ytdlp_path()
    if not ytdlp.exists():
        return None
    try:
        result = subprocess.run(
            [str(ytdlp), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_latest_version() -> str | None:
    """Fetch the latest version tag from GitHub."""
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_URL,
            headers={"User-Agent": "caption-search"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("tag_name", "").lstrip("v")
    except Exception:
        return None


def should_check_update() -> bool:
    """Check if enough time has passed since last update check."""
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
    """Save version and check timestamp."""
    version_file = get_version_file()
    version_file.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": version,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }
    version_file.write_text(json.dumps(data))


def download_ytdlp(on_progress: callable = None) -> bool:
    """Download yt-dlp.exe from GitHub."""
    ytdlp = get_ytdlp_path()
    ytdlp.parent.mkdir(parents=True, exist_ok=True)
    temp_path = ytdlp.with_suffix(".tmp")
    
    try:
        req = urllib.request.Request(
            DOWNLOAD_URL,
            headers={"User-Agent": "caption-search"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(temp_path, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress and total:
                        on_progress(downloaded, total)
        
        # Replace old binary
        if ytdlp.exists():
            ytdlp.unlink()
        temp_path.rename(ytdlp)
        
        # Save version info
        version = get_local_version()
        if version:
            save_version_info(version)
        
        return True
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to download yt-dlp: {e}")


def ensure_ytdlp(on_status: callable = None) -> Path:
    """Ensure yt-dlp is available and up-to-date. Returns path to binary."""
    ytdlp = get_ytdlp_path()
    
    if not ytdlp.exists():
        if on_status:
            on_status("Downloading yt-dlp...")
        download_ytdlp()
        if on_status:
            on_status("yt-dlp ready")
        return ytdlp
    
    if should_check_update():
        if on_status:
            on_status("Checking for yt-dlp updates...")
        local_ver = get_local_version()
        latest_ver = get_latest_version()
        
        if latest_ver and local_ver and latest_ver != local_ver:
            if on_status:
                on_status(f"Updating yt-dlp ({local_ver} → {latest_ver})...")
            download_ytdlp()
            if on_status:
                on_status("yt-dlp updated")
        else:
            # Save check timestamp even if no update needed
            if local_ver:
                save_version_info(local_ver)
            if on_status:
                on_status("yt-dlp is up to date")
    
    return ytdlp
