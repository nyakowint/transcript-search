# AGENTS

## Architecture (current plan)
- **App type:** Local Python app (single process)
- **GUI:** Embedded web UI built with **Svelte + Vite** (bundled to /ui)
- **IPC:** JS↔Python bridge via pywebview (no external browser, no HTTP API)
- **YouTube ingestion:** yt-dlp invoked from Python
- **Subtitles:** Prefer manual captions, fall back to auto; flag none
- **Transcript format:** Normalize VTT to match YouTube UI (text + timestamps)
- **Storage:** SQLite for video/channel metadata + subtitle availability
- **Search/filter:** String/phrase match over transcript text

## Key flows
1. Input single video, multiple videos, or playlist.
2. Expand playlist to video list.
3. Fetch subtitles (manual → auto → none) per video.
4. Normalize transcript and store metadata.
5. Search/filter transcripts; surface summary of missing captions.

## Next steps (from plan)
- Iterate on Svelte UI components and layout.
- Improve transcript formatting and filtering controls.
- Package/distribute the app for easier setup.

## Conventions
- If corrected, you should remember the preferred syntax or other conventions