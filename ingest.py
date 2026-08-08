"""Caption ingestion: enumerate videos, fetch metadata, download caption text.

Two things dominate the cost of ingesting a channel, and both are addressed
here:

* **Process spawns.** yt-dlp costs ~2.5s for the first URL in an invocation but
  only ~0.5s for each additional one, because it reuses its HTTP session. So
  URLs are handed to it in batches, and several batches run concurrently.
* **Round trips per video.** The info JSON already contains a direct, signed URL
  for every caption track. Fetching that URL over plain HTTP avoids a second
  yt-dlp invocation per video, and no media is ever downloaded.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Iterable, Iterator, Optional

from captions import parse_caption_payload, select_track
from ytdlp_url import CHANNEL_TABS, Target, classify_url, parse_input_urls

# Hide console windows on Windows when spawning yt-dlp.
_SUBPROCESS_FLAGS = (
    getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
)

# Fields pulled from yt-dlp per video. Requesting a subset instead of full -J
# keeps the JSON we have to parse down to what we actually use.
_INFO_FIELDS = (
    "id,title,channel,uploader,channel_id,uploader_id,upload_date,duration,"
    "webpage_url,subtitles,automatic_captions,language,live_status,availability"
)
_INFO_PRINT = f"%(.{{{_INFO_FIELDS}}})j"
_FLAT_PRINT = (
    "%(.{id,title,duration,live_status,playlist_id,playlist_title,playlist_channel})j"
)

_CAPTION_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

ENUMERATE_TIMEOUT = 300
BATCH_TIMEOUT = 600
CAPTION_TIMEOUT = 45


class Cancelled(Exception):
    """Raised inside a worker when the job has been cancelled."""


class IngestOptions:
    """Everything the UI can tune about a run."""

    def __init__(
        self,
        preferred_languages: Iterable[str] = ("en",),
        allow_auto: bool = True,
        allow_other_languages: bool = True,
        channel_tabs: Iterable[str] = CHANNEL_TABS,
        concurrency: int = 6,
        batch_size: int = 10,
        skip_existing: bool = True,
        max_videos: int = 0,
        cookies_path: str = "",
        cookies_browser: str = "",
    ) -> None:
        self.preferred_languages = [
            code.strip() for code in preferred_languages if str(code).strip()
        ] or ["en"]
        self.allow_auto = allow_auto
        self.allow_other_languages = allow_other_languages
        self.channel_tabs = tuple(
            tab for tab in channel_tabs if tab in CHANNEL_TABS
        ) or CHANNEL_TABS
        self.concurrency = max(1, min(16, int(concurrency)))
        self.batch_size = max(1, min(50, int(batch_size)))
        self.skip_existing = skip_existing
        self.max_videos = max(0, int(max_videos))
        self.cookies_path = cookies_path or ""
        self.cookies_browser = cookies_browser or ""

    @classmethod
    def from_dict(cls, data: dict | None) -> "IngestOptions":
        data = data or {}
        langs = data.get("preferred_languages")
        if isinstance(langs, str):
            langs = [part for part in langs.replace(";", ",").split(",")]
        return cls(
            preferred_languages=langs or ("en",),
            allow_auto=bool(data.get("allow_auto", True)),
            allow_other_languages=bool(data.get("allow_other_languages", True)),
            channel_tabs=data.get("channel_tabs") or CHANNEL_TABS,
            concurrency=data.get("concurrency", 6),
            batch_size=data.get("batch_size", 10),
            skip_existing=bool(data.get("skip_existing", True)),
            max_videos=data.get("max_videos", 0),
            cookies_path=data.get("cookies_path", ""),
            cookies_browser=data.get("cookies_browser", ""),
        )

    def to_dict(self) -> dict:
        return {
            "preferred_languages": self.preferred_languages,
            "allow_auto": self.allow_auto,
            "allow_other_languages": self.allow_other_languages,
            "channel_tabs": list(self.channel_tabs),
            "concurrency": self.concurrency,
            "batch_size": self.batch_size,
            "skip_existing": self.skip_existing,
            "max_videos": self.max_videos,
        }


class Ingestor:
    """Runs one ingest job. Not reusable across jobs -- create one per run."""

    def __init__(
        self,
        ytdlp_path: str,
        options: IngestOptions,
        cancel_event: Optional[threading.Event] = None,
        on_event: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._ytdlp = ytdlp_path
        self.options = options
        self._cancel = cancel_event or threading.Event()
        self._on_event = on_event or (lambda event: None)
        self._processes: set[subprocess.Popen] = set()
        self._proc_lock = threading.Lock()

    # ------------------------------------------------------------- lifecycle

    def cancel(self) -> None:
        self._cancel.set()
        with self._proc_lock:
            processes = list(self._processes)
        for proc in processes:
            try:
                proc.kill()
            except OSError:
                pass

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def _check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise Cancelled()

    def _emit(self, **event) -> None:
        try:
            self._on_event(event)
        except Exception:
            # A failing progress listener must never abort an ingest.
            pass

    # ------------------------------------------------------------- yt-dlp I/O

    def _base_args(self) -> list[str]:
        args = [self._ytdlp, "--no-warnings", "--ignore-config", "--no-progress"]
        if self.options.cookies_path:
            args += ["--cookies", self.options.cookies_path]
        if self.options.cookies_browser:
            args += ["--cookies-from-browser", self.options.cookies_browser]
        return args

    def _stream_json_lines(
        self, args: list[str], timeout: int
    ) -> Iterator[tuple[Optional[dict], Optional[str]]]:
        """Run yt-dlp and yield ``(record, error)`` as its stdout arrives.

        Streaming rather than buffering matters for channels: a 1000-video
        enumeration reports progress as it goes instead of after a two-minute
        silence, and cancelling kills the process mid-flight.
        """
        self._check_cancelled()
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_SUBPROCESS_FLAGS,
        )
        with self._proc_lock:
            self._processes.add(proc)

        stderr_lines: list[str] = []

        def drain_stderr() -> None:
            assert proc.stderr is not None
            for line in proc.stderr:
                line = line.strip()
                if line:
                    stderr_lines.append(line)

        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stderr_thread.start()

        timer = threading.Timer(timeout, proc.kill)
        timer.start()
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                if self._cancel.is_set():
                    proc.kill()
                    raise Cancelled()
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    yield json.loads(line), None
                except json.JSONDecodeError:
                    continue
            proc.wait()
        finally:
            timer.cancel()
            stderr_thread.join(timeout=2)
            with self._proc_lock:
                self._processes.discard(proc)
            try:
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
            except OSError:
                pass

        self._check_cancelled()
        if proc.returncode not in (0, None):
            for message in stderr_lines:
                if message.startswith("ERROR:"):
                    yield None, message
            if not any(m.startswith("ERROR:") for m in stderr_lines):
                yield None, (
                    stderr_lines[-1]
                    if stderr_lines
                    else f"yt-dlp exited with code {proc.returncode}"
                )

    # ----------------------------------------------------------- enumeration

    def enumerate_targets(self, targets: list[Target]) -> tuple[list[dict], list[dict]]:
        """Expand targets into a de-duplicated list of video stubs.

        Returns ``(videos, errors)``. Each stub is
        ``{"id", "title", "duration", "source_ids"}``.
        """
        seen: dict[str, dict] = {}
        errors: list[dict] = []

        for target in targets:
            self._check_cancelled()
            if target.kind == "video":
                video_id = target.url.rsplit("=", 1)[-1]
                stub = seen.setdefault(
                    video_id, {"id": video_id, "title": "", "duration": 0, "source_ids": []}
                )
                if target.source_id and target.source_id not in stub["source_ids"]:
                    stub["source_ids"].append(target.source_id)
                self._emit(phase="expanding", message=f"Queued {video_id}", found=len(seen))
                continue

            count_before = len(seen)
            target_errors: list[dict] = []

            # Try each candidate base until one lists something. A retired
            # vanity path 404s on every tab, so there is no point continuing
            # with it once the handle form works.
            for base in target.candidate_bases():
                self._check_cancelled()
                base_errors: list[dict] = []
                found_before_base = len(seen)

                for list_url in target.tab_urls(base):
                    self._check_cancelled()
                    self._emit(
                        phase="expanding",
                        message=f"Listing {target.label}...",
                        found=len(seen),
                    )
                    try:
                        self._enumerate_one(target, list_url, seen, base_errors)
                    except Cancelled:
                        raise
                    except OSError as exc:
                        base_errors.append({"url": list_url, "error": str(exc)})

                if len(seen) > found_before_base:
                    # This base worked; drop the earlier bases' failures.
                    target_errors = base_errors
                    break
                target_errors = base_errors

            errors.extend(target_errors)
            self._emit(
                phase="expanding",
                message=f"{target.label}: {len(seen) - count_before} videos",
                found=len(seen),
            )

        self._remap_source_ids(targets, seen.values())
        videos = list(seen.values())
        if self.options.max_videos:
            videos = videos[: self.options.max_videos]
        return videos, errors

    def _enumerate_one(
        self, target: Target, list_url: str, seen: dict[str, dict], errors: list[dict]
    ) -> None:
        """Stream one playlist/tab listing into ``seen``."""
        args = self._base_args() + [
            "--flat-playlist",
            "--ignore-errors",
            # Without this, a user with cookies loaded gets an "authentication"
            # error whenever the channel webpage fails to download -- which
            # hides the real cause (a 404, a rate limit) behind a misleading
            # message. We only ever list public content.
            "--extractor-args",
            "youtubetab:skip=authcheck",
            "--print",
            _FLAT_PRINT,
        ]
        if self.options.max_videos:
            args += ["--playlist-end", str(self.options.max_videos)]
        args.append(list_url)

        for record, error in self._stream_json_lines(args, ENUMERATE_TIMEOUT):
            if error:
                # A channel with no Shorts tab 404s; normal for a fan-out.
                if "does not have a" in error or "This channel does not have" in error:
                    continue
                errors.append({"url": list_url, "error": error})
                continue
            video_id = record.get("id")
            if not video_id:
                continue
            self._resolve_target(target, record)
            stub = seen.setdefault(
                video_id,
                {
                    "id": video_id,
                    "title": record.get("title") or "",
                    "duration": record.get("duration") or 0,
                    "source_ids": [],
                },
            )
            if target.source_id and target.source_id not in stub["source_ids"]:
                stub["source_ids"].append(target.source_id)
            if len(seen) % 25 == 0:
                self._emit(
                    phase="expanding",
                    message=f"Listing {target.label}... {len(seen)} found",
                    found=len(seen),
                )

    @staticmethod
    def _resolve_target(target: Target, record: dict) -> None:
        """Learn a target's real identity from the first enumerated entry."""
        if target.resolved_id and target.resolved_title:
            return
        if not target.resolved_id:
            playlist_id = record.get("playlist_id") or ""
            if playlist_id:
                target.resolved_id = playlist_id
        if not target.resolved_title:
            if target.kind == "channel":
                title = record.get("playlist_channel") or ""
            else:
                title = record.get("playlist_title") or ""
            if title:
                target.resolved_title = title

    @staticmethod
    def _remap_source_ids(targets: list[Target], stubs: Iterable[dict]) -> None:
        """Rewrite provisional source ids to the canonical ones enumeration found."""
        remap = {
            target.source_id: target.key
            for target in targets
            if target.source_id and target.key != target.source_id
        }
        if not remap:
            return
        for stub in stubs:
            seen_ids: list[str] = []
            for source_id in stub["source_ids"]:
                mapped = remap.get(source_id, source_id)
                if mapped not in seen_ids:
                    seen_ids.append(mapped)
            stub["source_ids"] = seen_ids

    # ------------------------------------------------------- metadata + text

    def _fetch_captions(self, track: dict) -> list[dict]:
        request = urllib.request.Request(
            track["url"],
            headers={"User-Agent": _CAPTION_UA, "Accept-Language": "en-US,en;q=0.9"},
        )
        with urllib.request.urlopen(request, timeout=CAPTION_TIMEOUT) as response:
            payload = response.read()
        return parse_caption_payload(payload, track["ext"])

    def _build_video(self, info: dict) -> tuple[dict, list[dict]]:
        video_id = info.get("id") or ""
        track = select_track(
            info.get("subtitles"),
            info.get("automatic_captions"),
            preferred_languages=self.options.preferred_languages,
            allow_auto=self.options.allow_auto,
            allow_other_languages=self.options.allow_other_languages,
            original_language=info.get("language") or "",
        )
        video = {
            "id": video_id,
            "title": info.get("title") or "",
            "channel": info.get("channel") or info.get("uploader") or "",
            "channel_id": info.get("channel_id") or info.get("uploader_id") or "",
            "upload_date": info.get("upload_date") or "",
            "duration": int(info.get("duration") or 0),
            "subtitle_type": "none",
            "subtitle_language": "",
            "source_url": info.get("webpage_url")
            or f"https://www.youtube.com/watch?v={video_id}",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
        segments: list[dict] = []
        if track:
            try:
                segments = self._fetch_captions(track)
            except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
                video["error"] = f"Caption download failed: {exc}"
            else:
                if segments:
                    video["subtitle_type"] = track["kind"]
                    video["subtitle_language"] = track["language"]
                else:
                    video["error"] = "Caption track was empty"
        else:
            video["error"] = "No caption track available"
        return video, segments

    def _batch_args(self, urls: list[str]) -> list[str]:
        return (
            self._base_args()
            + ["--skip-download", "--ignore-errors", "--print", _INFO_PRINT]
            + urls
        )

    def fetch_videos(
        self,
        stubs: list[dict],
        on_video: Callable[[dict, list[dict], list[str]], None],
    ) -> dict:
        """Fetch metadata and captions for every stub, concurrently.

        ``on_video(video, segments, source_ids)`` is called once per video from
        a worker thread; it is expected to persist the result.
        """
        total = len(stubs)
        counters = {"completed": 0, "ok": 0, "missing": 0, "failed": 0}
        errors: list[dict] = []
        lock = threading.Lock()
        by_id = {stub["id"]: stub for stub in stubs}

        def report(video_title: str) -> None:
            self._emit(
                phase="fetching",
                total=total,
                current=video_title,
                message="",
                **counters,
            )

        def record(video: dict, segments: list[dict], source_ids: list[str]) -> None:
            with lock:
                counters["completed"] += 1
                if video["subtitle_type"] == "none":
                    counters["missing"] += 1
                else:
                    counters["ok"] += 1
            on_video(video, segments, source_ids)
            report(video.get("title") or video["id"])

        def record_failure(video_id: str, message: str) -> None:
            with lock:
                counters["completed"] += 1
                counters["failed"] += 1
                errors.append({"video_id": video_id, "error": message})
            report(video_id)

        def run_batch(batch: list[dict]) -> None:
            urls = [f"https://www.youtube.com/watch?v={stub['id']}" for stub in batch]
            handled: set[str] = set()
            batch_errors: list[str] = []
            try:
                for info, error in self._stream_json_lines(
                    self._batch_args(urls), BATCH_TIMEOUT
                ):
                    if error:
                        batch_errors.append(error)
                        continue
                    video_id = info.get("id")
                    if not video_id:
                        continue
                    handled.add(video_id)
                    stub = by_id.get(video_id, {})
                    try:
                        video, segments = self._build_video(info)
                    except Cancelled:
                        raise
                    except Exception as exc:  # noqa: BLE001 - one bad video must not kill the run
                        record_failure(video_id, str(exc))
                        continue
                    record(video, segments, stub.get("source_ids", []))
            except Cancelled:
                raise
            except OSError as exc:
                batch_errors.append(str(exc))

            # Anything yt-dlp never printed a line for failed. Match it to the
            # error mentioning its id so the user sees the real reason.
            for stub in batch:
                if stub["id"] in handled or self._cancel.is_set():
                    continue
                message = next(
                    (err for err in batch_errors if stub["id"] in err),
                    batch_errors[0] if batch_errors else "yt-dlp returned no data",
                )
                record_failure(stub["id"], message)

        batch_size = self._effective_batch_size(total)
        batches = [stubs[i : i + batch_size] for i in range(0, total, batch_size)]
        report("")

        try:
            with ThreadPoolExecutor(max_workers=self.options.concurrency) as pool:
                list(pool.map(run_batch, batches))
        except Cancelled:
            pass

        return {"counters": counters, "errors": errors, "cancelled": self.cancelled}

    def _effective_batch_size(self, total: int) -> int:
        """Keep every worker busy on small jobs instead of loading up one batch."""
        if total <= 0:
            return 1
        fair_share = max(1, total // self.options.concurrency)
        return max(1, min(self.options.batch_size, fair_share))


def build_targets(input_text: str, options: IngestOptions) -> tuple[list[Target], list[dict]]:
    """Classify each pasted line, collecting per-line errors rather than failing."""
    targets: list[Target] = []
    errors: list[dict] = []
    for raw in parse_input_urls(input_text):
        try:
            targets.append(classify_url(raw, tabs=options.channel_tabs))
        except ValueError as exc:
            errors.append({"url": raw, "error": str(exc)})
    return targets, errors
