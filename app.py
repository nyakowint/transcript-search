import os
from pathlib import Path

import webview

from backend import Api


def main() -> None:
    ui_path = Path(__file__).resolve().parent / "ui" / "index.html"
    api = Api()
    window = webview.create_window(
        "Caption Search",
        url=ui_path.as_uri(),
        js_api=api,
        width=1200,
        height=800,
    )
    api.set_window(window)
    debug = os.getenv("CAPTION_SEARCH_DEBUG", "").lower() in {"1", "true", "yes", "on"}
    webview.start(debug=debug, http_server=True)


if __name__ == "__main__":
    main()
