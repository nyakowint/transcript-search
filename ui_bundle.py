"""Locating, and when running from source rebuilding, the bundled UI.

Vite builds the whole frontend into one self-contained ``index.html``. A frozen
build carries that file inside the executable. From source it is rebuilt
whenever it is missing or older than the frontend sources, so a fresh clone,
a wiped ``build/`` or a forgotten ``deno task build`` never leaves the window
without a UI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

UI_RELATIVE_PATH = Path("build") / "ui" / "index.html"
# Everything that feeds the Vite build.
SOURCE_PATHS = ("src", "vite.config.js", "deno.json")


def resource_dir() -> Path:
    """Root the UI and icon paths resolve against.

    PyInstaller unpacks bundled data into ``sys._MEIPASS``; from source it is
    just the project directory.
    """
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


def _newest_source_mtime(root: Path) -> float:
    newest = 0.0
    for name in SOURCE_PATHS:
        path = root / name
        files = path.rglob("*") if path.is_dir() else [path]
        for file in files:
            if file.is_file():
                newest = max(newest, file.stat().st_mtime)
    return newest


def needs_build(root: Path) -> bool:
    ui_path = root / UI_RELATIVE_PATH
    if not ui_path.exists():
        return True
    return _newest_source_mtime(root) > ui_path.stat().st_mtime


def _build(root: Path) -> bool:
    deno = shutil.which("deno")
    if not deno:
        print("UI build skipped: deno is not on PATH.", file=sys.stderr)
        return False
    print("Building UI...", file=sys.stderr)
    result = subprocess.run([deno, "task", "build"], cwd=root)
    return result.returncode == 0


def resolve_ui(root: Optional[Path] = None) -> Optional[Path]:
    """Path to a usable ``index.html``, building it first if needed.

    A stale UI is still returned when the rebuild fails: an older frontend
    beats no frontend.
    """
    root = root or resource_dir()
    ui_path = root / UI_RELATIVE_PATH
    frozen = getattr(sys, "frozen", False)
    if not frozen and needs_build(root) and not _build(root):
        print(f"UI build failed; using {ui_path} if it exists.", file=sys.stderr)
    return ui_path if ui_path.exists() else None


def missing_ui_page(root: Path) -> str:
    """Shown in place of the app so a missing UI is never a silent exit."""
    return f"""<!DOCTYPE html>
<html><body style="font-family: system-ui, sans-serif; background: #0a0c0f; color: #f2f2f2; padding: 32px;">
<h2>The UI could not be loaded</h2>
<p>Expected it at <code>{root / UI_RELATIVE_PATH}</code>.</p>
<p>From source, install <a href="https://deno.com" style="color: #6b9bff">Deno</a> and run
<code>deno task build</code>, then restart. For a release build, download it again.</p>
</body></html>"""
