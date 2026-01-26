# AGENTS

## Architecture (current plan)
- **App type:** Local Python app (single process)
- **GUI:** Embedded web UI via **pywebview** (HTML/JS/CSS in app window)
- **IPC:** JS↔Python bridge (no external browser, no HTTP API)
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
- Scaffold Python app + pywebview shell.
- Implement input parsing and yt-dlp integration.
- Add transcript normalization + search.
- Add SQLite storage + summary reporting.
