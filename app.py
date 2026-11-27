import sys
from typing import Any

import webview

from backend import Api
from ui_bundle import missing_ui_page, resolve_ui, resource_dir


def main() -> None:
    root = resource_dir()
    ui_path = resolve_ui(root)
    icon_path = root / "src" / "public" / "favicon.ico"
    window_kwargs: dict[str, Any] = {"width": 1280, "height": 860, "min_size": (900, 600)}

    if ui_path is None:
        webview.create_window("Transcript Search", html=missing_ui_page(root), **window_kwargs)
        webview.start()
        return

    api = Api()
    window = webview.create_window("Transcript Search", url=str(ui_path), js_api=api, **window_kwargs)
    api.set_window(window)

    debug = "--debug" in sys.argv
    webview.settings["SHOW_DEFAULT_MENUS"] = debug

    # yt-dlp is checked for updates once the window exists, so a slow or
    # offline network delays the first fetch rather than app startup.
    def on_started() -> None:
        api.prepare_ytdlp()

    start_kwargs: dict[str, Any] = {"debug": debug, "http_server": True, "func": on_started}
    if icon_path.exists():
        start_kwargs["icon"] = str(icon_path)
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
