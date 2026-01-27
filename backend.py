from __future__ import annotations

import glob
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# Hide console windows on Windows when running subprocess
_SUBPROCESS_FLAGS = (
    getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
)

from ytdlp_manager import get_ytdlp_path

TIME_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")


def parse_input_urls(input_text: str) -> list[str]:
    tokens = re.split(r"[\s,]+", input_text.strip())
    return [token for token in tokens if token]


def select_caption_language(captions: dict) -> Optional[str]:
    if not captions:
        return None
    if "en" in captions:
        return "en"
    for key in captions:
        if key.startswith("en"):
            return key
    return next(iter(captions))


def _parse_timestamp(value: str) -> int:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return int(total_seconds * 1000)


def _clean_caption_text(text: str) -> str:
    cleaned = TAG_RE.sub("", html.unescape(text))
    return " ".join(cleaned.split())


def parse_vtt(content: str) -> list[dict]:
    segments: list[dict] = []
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith("WEBVTT"):
            index += 1
            continue
        if line.startswith("NOTE") or line.startswith("STYLE"):
            index += 1
            continue
        match = TIME_RANGE_RE.match(line)
        if not match and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            match = TIME_RANGE_RE.match(next_line)
            if match:
                index += 1
        if not match:
            index += 1
            continue
        start_ms = _parse_timestamp(match.group("start"))
        end_ms = _parse_timestamp(match.group("end"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        caption_text = _clean_caption_text(" ".join(text_lines))
        if caption_text:
            segments.append(
                {"start_ms": start_ms, "end_ms": end_ms, "text": caption_text}
            )
    return _dedupe_segments(segments)


def _dedupe_segments(segments: list[dict]) -> list[dict]:
    """Deduplicate VTT segments to match YouTube's transcript display.

    YouTube auto-generated captions have a rolling pattern:
    - Short (10ms) segments with just new words
    - Longer segments with accumulated text that overlap subsequent short ones

    We keep only the "accumulated" segments (longer duration, more text) and
    skip the short snippet segments whose text is contained in a nearby segment.
    Then we trim/merge overlapping segments to remove rolling duplicates.
    """
    if not segments:
        return []

    sorted_segments = sorted(segments, key=lambda s: (s["start_ms"], s["end_ms"]))

    # First pass: for segments with same start_ms, keep only the longest text
    by_start: dict[int, dict] = {}
    for seg in sorted_segments:
        start = seg["start_ms"]
        if start not in by_start or len(seg["text"]) > len(by_start[start]["text"]):
            by_start[start] = seg

    candidates = sorted(by_start.values(), key=lambda s: s["start_ms"])

    # Second pass: remove short "snippet" segments whose text is a prefix of
    # the next segment's text (the rolling caption pattern)
    filtered: list[dict] = []
    i = 0
    while i < len(candidates):
        current = candidates[i]
        duration = current["end_ms"] - current["start_ms"]

        # Check if this is a short snippet that should be skipped
        if duration <= 50 and i + 1 < len(candidates):
            next_seg = candidates[i + 1]
            # Skip if next segment starts soon and contains our text
            if (
                next_seg["start_ms"] - current["end_ms"] <= 100
                and current["text"] in next_seg["text"]
            ):
                i += 1
                continue

        filtered.append(current)
        i += 1

    # Third pass: trim overlapping prefixes and merge short continuations
    def _tokenize(text: str) -> list[str]:
        return text.split()

    def _overlap(prev_text: str, curr_text: str) -> int:
        prev_words = _tokenize(prev_text)
        curr_words = _tokenize(curr_text)
        max_len = min(len(prev_words), len(curr_words))
        for size in range(max_len, 0, -1):
            if prev_words[-size:] == curr_words[:size]:
                return size
        return 0

    deduped: list[dict] = []
    for seg in filtered:
        if not deduped:
            deduped.append(seg)
            continue

        prev = deduped[-1]
        if seg["start_ms"] - prev["end_ms"] > 1000:
            deduped.append(seg)
            continue

        if seg["text"] in prev["text"]:
            continue

        overlap_words = _overlap(prev["text"], seg["text"])
        if overlap_words:
            curr_words = _tokenize(seg["text"])
            trimmed_words = curr_words[overlap_words:]
            if not trimmed_words:
                continue
            trimmed_text = " ".join(trimmed_words)
            overlap_ratio = overlap_words / max(1, len(curr_words))
            if len(trimmed_words) <= 3 or overlap_ratio >= 0.6:
                prev["text"] = f"{prev['text']} {trimmed_text}".strip()
                prev["end_ms"] = max(prev["end_ms"], seg["end_ms"])
            else:
                deduped.append(
                    {
                        "start_ms": seg["start_ms"],
                        "end_ms": seg["end_ms"],
                        "text": trimmed_text,
                    }
                )
            continue

        deduped.append(seg)

    return deduped


class CaptionStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        conn = self._connect()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    channel TEXT,
                    channel_id TEXT,
                    upload_date TEXT,
                    subtitle_type TEXT,
                    subtitle_language TEXT,
                    source_url TEXT,
                    fetched_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transcript_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    start_ms INTEGER,
                    end_ms INTEGER,
                    text TEXT,
                    FOREIGN KEY(video_id) REFERENCES videos(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_segments_video ON transcript_segments(video_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_segments_text ON transcript_segments(text)"
            )
        conn.close()

    def upsert_video(self, video: dict, segments: Iterable[dict]) -> None:
        conn = self._connect()
        with conn:
            conn.execute(
                """
                INSERT INTO videos (
                    id, title, channel, channel_id, upload_date,
                    subtitle_type, subtitle_language, source_url, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    channel=excluded.channel,
                    channel_id=excluded.channel_id,
                    upload_date=excluded.upload_date,
                    subtitle_type=excluded.subtitle_type,
                    subtitle_language=excluded.subtitle_language,
                    source_url=excluded.source_url,
                    fetched_at=excluded.fetched_at
                """,
                (
                    video["id"],
                    video["title"],
                    video["channel"],
                    video["channel_id"],
                    video["upload_date"],
                    video["subtitle_type"],
                    video["subtitle_language"],
                    video["source_url"],
                    video["fetched_at"],
                ),
            )
            conn.execute(
                "DELETE FROM transcript_segments WHERE video_id = ?", (video["id"],)
            )
            conn.executemany(
                """
                INSERT INTO transcript_segments (video_id, start_ms, end_ms, text)
                VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        video["id"],
                        segment["start_ms"],
                        segment["end_ms"],
                        segment["text"],
                    )
                    for segment in segments
                ),
            )
        conn.close()

    def get_videos(self) -> list[dict]:
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT id, title, channel, channel_id, upload_date,
                   subtitle_type, subtitle_language, source_url, fetched_at
            FROM videos
            ORDER BY title
            """
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_transcript(self, video_id: str) -> list[dict]:
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT start_ms, end_ms, text
            FROM transcript_segments
            WHERE video_id = ?
            ORDER BY start_ms
            """,
            (video_id,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_segments(self, query: str) -> list[dict]:
        if not query.strip():
            return []
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT s.video_id, s.start_ms, s.end_ms, s.text,
                   v.title, v.channel, v.source_url
            FROM transcript_segments s
            JOIN videos v ON v.id = s.video_id
            WHERE lower(s.text) LIKE ?
            ORDER BY v.title, s.start_ms
            """,
            (f"%{query.lower()}%",),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_missing_subtitles(self) -> list[dict]:
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT id, title, channel, channel_id, source_url
            FROM videos
            WHERE subtitle_type = 'none'
            ORDER BY title
            """
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def delete_video(self, video_id: str) -> None:
        conn = self._connect()
        with conn:
            conn.execute("DELETE FROM transcript_segments WHERE video_id = ?", (video_id,))
            conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.close()

    def delete_all_videos(self) -> None:
        conn = self._connect()
        with conn:
            conn.execute("DELETE FROM transcript_segments")
            conn.execute("DELETE FROM videos")
        conn.close()

    def get_setting(self, key: str) -> str:
        conn = self._connect()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row["value"] if row else ""

    def set_setting(self, key: str, value: str) -> None:
        conn = self._connect()
        with conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )
        conn.close()


class Api:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or (Path(__file__).resolve().parent / "data")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._store = CaptionStore(self._data_dir / "captions.db")
        self._window = None
        self._serializable = False
        self._ytdlp = str(get_ytdlp_path())

    def set_window(self, window) -> None:
        self._window = window

    def select_cookies_file(self) -> dict:
        if not self._window:
            return {"ok": False, "error": "Window is not ready."}
        files = self._window.create_file_dialog(
            file_types=("Cookies (*.txt;*.cookies;*.json)", "All files (*.*)")
        )
        if not files:
            return {"ok": True, "path": ""}
        return {"ok": True, "path": self._normalize_path(files[0])}

    def get_settings(self) -> dict:
        return {
            "ok": True,
            "settings": {
                "cookies_path": self._store.get_setting("cookies_path"),
                "cookies_browser": self._store.get_setting("cookies_browser"),
            },
        }

    def save_settings(self, cookies_path: str, cookies_browser: str) -> dict:
        normalized_path = self._normalize_path(cookies_path)
        self._store.set_setting("cookies_path", normalized_path)
        self._store.set_setting("cookies_browser", (cookies_browser or "").strip())
        return {"ok": True}

    def ingest_urls(
        self,
        input_text: str,
        cookies_path: str | None = None,
        cookies_browser: str | None = None,
    ) -> dict:
        urls = parse_input_urls(input_text)
        if not urls:
            return {"ok": False, "error": "Provide at least one URL."}
        cookies_path = self._normalize_path(cookies_path or "")
        cookies_browser = (cookies_browser or "").strip() or None
        self._store.set_setting("cookies_path", cookies_path or "")
        self._store.set_setting("cookies_browser", cookies_browser or "")
        if cookies_path and not Path(cookies_path).exists():
            return {"ok": False, "error": f"Cookies file not found: {cookies_path}"}
        try:
            expanded_urls = self._expand_urls(urls, cookies_path, cookies_browser)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)}
        processed: list[dict] = []
        missing: list[dict] = []
        errors: list[dict] = []
        seen: set[str] = set()
        for url in expanded_urls:
            if url in seen:
                continue
            seen.add(url)
            try:
                video = self._process_video(url, cookies_path, cookies_browser)
            except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError, ValueError) as exc:
                errors.append({"url": url, "error": str(exc)})
                continue
            processed.append(video)
            if video["subtitle_type"] == "none":
                missing.append(video)
        return {"ok": True, "processed": processed, "missing": missing, "errors": errors}

    def get_videos(self) -> dict:
        return {"ok": True, "videos": self._store.get_videos()}

    def get_transcript(self, video_id: str) -> dict:
        return {"ok": True, "segments": self._store.get_transcript(video_id)}

    def search_transcripts(self, query: str) -> dict:
        return {"ok": True, "results": self._store.search_segments(query)}

    def get_missing_subtitles(self) -> dict:
        return {"ok": True, "videos": self._store.get_missing_subtitles()}

    def delete_video(self, video_id: str) -> dict:
        self._store.delete_video(video_id)
        return {"ok": True}

    def delete_all_videos(self) -> dict:
        self._store.delete_all_videos()
        return {"ok": True}

    def _base_ytdlp_args(
        self, cookies_path: Optional[str], cookies_browser: Optional[str]
    ) -> list[str]:
        args = [self._ytdlp, "--no-warnings", "-q"]
        if cookies_path:
            args.extend(["--cookies", cookies_path])
        if cookies_browser:
            args.extend(["--cookies-from-browser", cookies_browser])
        return args

    def _normalize_path(self, raw_path: str) -> str:
        if not raw_path:
            return ""
        path = raw_path.strip().strip('"').strip("'")
        if not path:
            return ""
        has_unc_prefix = path.startswith("\\\\")
        if has_unc_prefix:
            path = "__UNC__" + path[2:]
        path = path.replace("\\\\", "\\")
        if has_unc_prefix:
            path = path.replace("__UNC__", "\\\\", 1)
        path = os.path.expandvars(os.path.expanduser(path))
        return os.path.normpath(path)

    def _expand_urls(
        self,
        urls: Iterable[str],
        cookies_path: Optional[str],
        cookies_browser: Optional[str],
    ) -> list[str]:
        expanded: list[str] = []
        base_args = self._base_ytdlp_args(cookies_path, cookies_browser)
        for url in urls:
            args = base_args + ["--flat-playlist", "-J", url]
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=120, creationflags=_SUBPROCESS_FLAGS
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr or f"yt-dlp failed for {url}")
            info = json.loads(result.stdout)
            if info.get("_type") in {"playlist", "multi_video"}:
                entries = info.get("entries") or []
                for entry in entries:
                    entry_url = self._entry_to_url(entry)
                    if entry_url:
                        expanded.append(entry_url)
            else:
                expanded.append(info.get("webpage_url") or url)
        return expanded

    def _entry_to_url(self, entry: dict) -> Optional[str]:
        entry_url = entry.get("webpage_url") or entry.get("url")
        if entry_url:
            if entry_url.startswith("http"):
                return entry_url
            ie_key = (entry.get("ie_key") or entry.get("extractor_key") or "").lower()
            if "youtube" in ie_key:
                return f"https://www.youtube.com/watch?v={entry_url}"
        entry_id = entry.get("id")
        if entry_id:
            return f"https://www.youtube.com/watch?v={entry_id}"
        return None

    def _process_video(
        self, url: str, cookies_path: Optional[str], cookies_browser: Optional[str]
    ) -> dict:
        info = self._extract_video_info(url, cookies_path, cookies_browser)
        video_id = info.get("id")
        if not video_id:
            raise ValueError("Missing video ID from yt-dlp info.")
        subtitles = info.get("subtitles") or {}
        automatic = info.get("automatic_captions") or {}
        subtitle_type = "none"
        language: Optional[str] = None
        if subtitles:
            subtitle_type = "manual"
            language = select_caption_language(subtitles)
        elif automatic:
            subtitle_type = "auto"
            language = select_caption_language(automatic)
        if subtitle_type != "none" and not language:
            subtitle_type = "none"
        segments: list[dict] = []
        if subtitle_type != "none" and language:
            vtt_content = self._download_subtitles(
                url, video_id, subtitle_type, language, cookies_path, cookies_browser
            )
            segments = parse_vtt(vtt_content)
        video = {
            "id": video_id,
            "title": info.get("title") or "",
            "channel": info.get("channel") or info.get("uploader") or "",
            "channel_id": info.get("channel_id") or info.get("uploader_id") or "",
            "upload_date": info.get("upload_date") or "",
            "subtitle_type": subtitle_type,
            "subtitle_language": language or "",
            "source_url": info.get("webpage_url") or url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store.upsert_video(video, segments)
        video["segment_count"] = len(segments)
        return video

    def _extract_video_info(
        self, url: str, cookies_path: Optional[str], cookies_browser: Optional[str]
    ) -> dict:
        args = self._base_ytdlp_args(cookies_path, cookies_browser) + [
            "--skip-download", "-J", url
        ]
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=120, creationflags=_SUBPROCESS_FLAGS
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or f"yt-dlp failed for {url}")
        return json.loads(result.stdout)

    def _download_subtitles(
        self,
        url: str,
        video_id: str,
        subtitle_type: str,
        language: str,
        cookies_path: Optional[str],
        cookies_browser: Optional[str],
    ) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            outtmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")
            args = self._base_ytdlp_args(cookies_path, cookies_browser) + [
                "--skip-download",
                "--sub-lang", language,
                "--sub-format", "vtt",
                "-o", outtmpl,
            ]
            if subtitle_type == "manual":
                args.append("--write-sub")
            else:
                args.append("--write-auto-sub")
            args.append(url)
            
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=120, creationflags=_SUBPROCESS_FLAGS
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr or f"yt-dlp subtitle download failed for {url}")
            
            candidates = glob.glob(os.path.join(temp_dir, f"{video_id}*.vtt"))
            if not candidates:
                raise FileNotFoundError(f"Subtitle file not found for {video_id}.")
            with open(candidates[0], "r", encoding="utf-8") as handle:
                return handle.read()
