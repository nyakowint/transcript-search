import sys
from pathlib import Path

import webview

from backend import Api
from ytdlp_manager import ensure_ytdlp


def main() -> None:
    # Ensure yt-dlp is available before starting
    ensure_ytdlp()
    
    ui_path = "build/ui/index.html"
    api = Api()
    window = webview.create_window(
        "Caption Search",
        url=ui_path,
        js_api=api,
        width=1200,
        height=800,
    )
    api.set_window(window)
    debug = "--debug" in sys.argv
    webview.settings["SHOW_DEFAULT_MENUS"] = debug
    webview.start(debug=debug, http_server=True, icon="src/public/favicon.ico")


if __name__ == "__main__":
    main()
