import sys
from pathlib import Path

import webview

from backend import Api


def _resource_dir() -> Path:
    """Root the UI and icon paths resolve against.

    PyInstaller unpacks bundled data into ``sys._MEIPASS``; from source it is
    just the project directory. Resolving explicitly keeps the app working when
    it is launched from some other working directory.
    """
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


def main() -> None:
    root = _resource_dir()
    ui_path = root / "build" / "ui" / "index.html"
    if not ui_path.exists():
        raise SystemExit(
            f"UI not built at {ui_path}. Run `deno task build` first."
        )

    icon_path = root / "src" / "public" / "favicon.ico"
    api = Api()
    window = webview.create_window(
        "Caption Search",
        url=str(ui_path),
        js_api=api,
        width=1280,
        height=860,
        min_size=(900, 600),
    )
    api.set_window(window)

    debug = "--debug" in sys.argv
    webview.settings["SHOW_DEFAULT_MENUS"] = debug

    # yt-dlp is checked for updates once the window exists, so a slow or
    # offline network delays the first fetch rather than app startup.
    def on_started() -> None:
        api.prepare_ytdlp()

    start_kwargs = {"debug": debug, "http_server": True, "func": on_started}
    if icon_path.exists():
        start_kwargs["icon"] = str(icon_path)
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
