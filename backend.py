"""pywebview JS bridge.

Every method here is callable from the UI. Ingest work is deliberately *not*
done inline: a channel takes tens of seconds, and the pywebview bridge is
synchronous, so running it on the calling thread would freeze the window. Jobs
run on a worker thread and report progress by pushing events into the page.
"""

from __future__ import annotations

import json
import os
import re
import threading
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from ingest import Ingestor, IngestOptions, build_targets
from store import CaptionStore, SearchSyntaxError
from ytdlp_manager import ensure_ytdlp, get_data_dir, get_local_version, resolve_ytdlp
from ytdlp_url import CHANNEL_TABS, Target

SETTING_KEYS = (
    "cookies_path",
    "cookies_browser",
    "preferred_languages",
    "allow_auto",
    "allow_other_languages",
    "channel_tabs",
    "concurrency",
    "skip_existing",
    "max_videos",
)

DEFAULT_SETTINGS = {
    "cookies_path": "",
    "cookies_browser": "",
    "preferred_languages": "en",
    "allow_auto": "1",
    "allow_other_languages": "1",
    "channel_tabs": "videos",
    "concurrency": "6",
    "skip_existing": "1",
    "max_videos": "0",
}


class Job:
    """State of one ingest run, shared between the worker and the UI."""

    def __init__(self, job_id: str, kind: str, label: str) -> None:
        self.id = job_id
        self.kind = kind
        self.label = label
        self.status = "running"
        self.phase = "starting"
        self.message = ""
        self.current = ""
        self.found = 0
        self.total = 0
        self.completed = 0
        self.ok = 0
        self.missing = 0
        self.failed = 0
        self.added = 0
        self.skipped = 0
        self.errors: list[dict] = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at = ""
        self.cancel_event = threading.Event()
        self.ingestor: Optional[Ingestor] = None

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "phase": self.phase,
            "message": self.message,
            "current": self.current,
            "found": self.found,
            "total": self.total,
            "completed": self.completed,
            "ok": self.ok,
            "missing": self.missing,
            "failed": self.failed,
            "added": self.added,
            "skipped": self.skipped,
            # The full list can run to thousands on a bad night; the UI only
            # ever shows a handful, so cap what crosses the bridge.
            "errors": self.errors[:50],
            "error_count": len(self.errors),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


_EXTRACTOR_TAG_RE = re.compile(r"^\[[^\]]+\]\s*")


def _summarize_error(message: str) -> str:
    """Turn a raw yt-dlp stderr line into something worth showing a user."""
    text = (message or "").strip()
    text = text.removeprefix("ERROR:").strip()
    text = _EXTRACTOR_TAG_RE.sub("", text)
    if "404" in text or "not found" in text.lower():
        text += (
            " - that URL does not resolve. YouTube retired many /c/ and /user/"
            " links; try the channel's @handle URL instead."
        )
    return text


def _ok(**payload) -> dict:
    return {"ok": True, **payload}


def _err(message: str) -> dict:
    return {"ok": False, "error": message}


class Api:
    def __init__(self, data_dir: Path | None = None) -> None:
        # Shared with the yt-dlp manager rather than derived from __file__: in a
        # frozen build __file__ points inside the bundle, which is a temporary
        # directory under one-file and would throw the database away on exit.
        self._data_dir = data_dir or get_data_dir()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._store = CaptionStore(self._data_dir / "captions.db")
        self._window = None
        self._jobs: dict[str, Job] = {}
        self._jobs_lock = threading.Lock()
        self._active_job_id = ""

    def set_window(self, window) -> None:
        self._window = window

    # ------------------------------------------------------------ UI plumbing

    def _push(self, event: dict) -> None:
        """Send an event to the page.

        pywebview has no server push, so this evaluates a call to a hook the
        frontend installs. Failures are swallowed: the window may be closing,
        and a dropped progress tick must never break an ingest.
        """
        if not self._window:
            return
        try:
            payload = json.dumps(event)
            self._window.evaluate_js(
                f"window.__captionSearchEvent && window.__captionSearchEvent({payload})"
            )
        except Exception:
            pass

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

    def select_cookies_file(self) -> dict:
        if not self._window:
            return _err("Window is not ready.")
        files = self._window.create_file_dialog(
            file_types=("Cookies (*.txt;*.cookies;*.json)", "All files (*.*)")
        )
        if not files:
            return _ok(path="")
        return _ok(path=self._normalize_path(files[0]))

    # -------------------------------------------------------------- settings

    def get_settings(self) -> dict:
        settings = {
            key: self._store.get_setting(key, DEFAULT_SETTINGS[key])
            for key in SETTING_KEYS
        }
        return _ok(
            settings=settings,
            channel_tab_options=list(CHANNEL_TABS),
            ytdlp_version=get_local_version() or "",
        )

    def save_settings(self, settings: dict) -> dict:
        settings = settings or {}
        for key in SETTING_KEYS:
            if key not in settings:
                continue
            value = settings[key]
            if isinstance(value, bool):
                value = "1" if value else "0"
            elif isinstance(value, (list, tuple)):
                value = ",".join(str(item) for item in value)
            else:
                value = str(value)
            if key == "cookies_path":
                value = self._normalize_path(value)
            self._store.set_setting(key, value)
        return self.get_settings()

    def _options_from_settings(self, overrides: dict | None = None) -> IngestOptions:
        raw = {
            key: self._store.get_setting(key, DEFAULT_SETTINGS[key])
            for key in SETTING_KEYS
        }
        raw.update(overrides or {})

        def as_bool(value) -> bool:
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}

        def as_list(value) -> list[str]:
            if isinstance(value, (list, tuple)):
                return [str(item).strip() for item in value if str(item).strip()]
            return [part.strip() for part in str(value).split(",") if part.strip()]

        def as_int(value, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        return IngestOptions(
            preferred_languages=as_list(raw["preferred_languages"]) or ["en"],
            allow_auto=as_bool(raw["allow_auto"]),
            allow_other_languages=as_bool(raw["allow_other_languages"]),
            channel_tabs=as_list(raw["channel_tabs"]) or list(CHANNEL_TABS),
            concurrency=as_int(raw["concurrency"], 6),
            skip_existing=as_bool(raw["skip_existing"]),
            max_videos=as_int(raw["max_videos"], 0),
            cookies_path=self._normalize_path(str(raw["cookies_path"])),
            cookies_browser=str(raw["cookies_browser"]).strip(),
        )

    # ------------------------------------------------------------------ jobs

    def _start_job(
        self,
        kind: str,
        label: str,
        worker: Callable[[Job, Ingestor, IngestOptions], None],
        options: IngestOptions,
    ) -> dict:
        with self._jobs_lock:
            active = self._jobs.get(self._active_job_id)
            if active and active.status == "running":
                return _err("A fetch is already running. Cancel it first.")
            job = Job(uuid.uuid4().hex[:12], kind, label)
            self._jobs[job.id] = job
            self._active_job_id = job.id

        ytdlp = resolve_ytdlp()
        if not Path(ytdlp).exists():
            job.status = "error"
            job.message = f"yt-dlp not found at {ytdlp}"
            return _err(job.message)

        def on_event(event: dict) -> None:
            job.phase = event.get("phase", job.phase)
            for key in ("message", "current", "found", "total", "completed", "ok", "missing", "failed"):
                if key in event:
                    setattr(job, key, event[key])
            self._push({"type": "job", "job": job.snapshot()})

        job.ingestor = Ingestor(ytdlp, options, job.cancel_event, on_event)

        def run() -> None:
            try:
                worker(job, job.ingestor, options)
                job.status = "cancelled" if job.cancel_event.is_set() else "done"
                job.phase = job.status
            except Exception as exc:  # noqa: BLE001 - surface any worker crash to the UI
                job.status = "error"
                job.phase = "error"
                job.message = str(exc)
                job.errors.append({"error": traceback.format_exc(limit=3)})
            finally:
                job.finished_at = datetime.now(timezone.utc).isoformat()
                self._push({"type": "job", "job": job.snapshot()})

        threading.Thread(target=run, daemon=True, name=f"ingest-{job.id}").start()
        return _ok(job=job.snapshot())

    def _run_targets(
        self,
        job: Job,
        ingestor: Ingestor,
        options: IngestOptions,
        targets: list[Target],
        force_ids: Optional[set[str]] = None,
    ) -> None:
        """Enumerate targets, drop what we already have, then fetch the rest."""
        stubs, enumerate_errors = ingestor.enumerate_targets(targets)
        job.errors.extend(enumerate_errors)
        job.found = len(stubs)

        # Listing nothing *and* failing is a failure, not an empty result.
        # Reporting "nothing new to fetch" here would dress a dead URL up as
        # an up-to-date library.
        if not stubs and enumerate_errors:
            raise RuntimeError(_summarize_error(enumerate_errors[0]["error"]))

        now = datetime.now(timezone.utc).isoformat()
        for target in targets:
            if target.kind in {"channel", "playlist"} and target.key:
                self._store.upsert_source(
                    {
                        "id": target.key,
                        "kind": target.kind,
                        "title": target.label,
                        "url": target.url,
                        "added_at": now,
                        "last_synced_at": now,
                    }
                )

        if options.skip_existing:
            existing = self._store.get_existing_video_ids() - (force_ids or set())
            kept = [stub for stub in stubs if stub["id"] not in existing]
            job.skipped = len(stubs) - len(kept)
            # A video already stored can still be new to *this* source, so
            # record the link even when its captions are not refetched.
            links: dict[str, list[str]] = {}
            for stub in stubs:
                if stub["id"] not in existing:
                    continue
                for source_id in stub.get("source_ids", []):
                    links.setdefault(source_id, []).append(stub["id"])
            for source_id, video_ids in links.items():
                self._store.link_videos_to_source(video_ids, source_id)
            stubs = kept

        job.total = len(stubs)
        job.added = len(stubs)
        if not stubs:
            job.phase = "done"
            job.message = "Nothing new to fetch."
            return

        result = ingestor.fetch_videos(
            stubs,
            lambda video, segments, source_ids: self._store.upsert_video(
                video, segments, source_ids
            ),
        )
        job.errors.extend(result["errors"])
        counters = result["counters"]
        job.completed = counters["completed"]
        job.ok = counters["ok"]
        job.missing = counters["missing"]
        job.failed = counters["failed"]

    # ---------------------------------------------------------------- ingest

    def start_ingest(self, input_text: str, overrides: dict | None = None) -> dict:
        options = self._options_from_settings(overrides)
        targets, target_errors = build_targets(input_text, options)
        if not targets:
            message = target_errors[0]["error"] if target_errors else "Provide at least one URL."
            return _err(message)
        if options.cookies_path and not Path(options.cookies_path).exists():
            return _err(f"Cookies file not found: {options.cookies_path}")

        label = ", ".join(t.title or t.source_id or t.url for t in targets)[:80]

        def worker(job: Job, ingestor: Ingestor, opts: IngestOptions) -> None:
            job.errors.extend(target_errors)
            self._run_targets(job, ingestor, opts, targets)

        return self._start_job("ingest", label, worker, options)

    def refetch_videos(self, video_ids: list[str], overrides: dict | None = None) -> dict:
        """Re-download captions for specific videos, ignoring skip-existing."""
        video_ids = [vid for vid in (video_ids or []) if vid]
        if not video_ids:
            return _err("No videos selected.")
        options = self._options_from_settings(overrides)
        options.skip_existing = False

        def worker(job: Job, ingestor: Ingestor, opts: IngestOptions) -> None:
            stubs = []
            for video_id in video_ids:
                video = self._store.get_video(video_id)
                stubs.append(
                    {
                        "id": video_id,
                        "title": (video or {}).get("title", ""),
                        "duration": (video or {}).get("duration", 0),
                        "source_ids": [],
                    }
                )
            job.found = job.total = len(stubs)
            result = ingestor.fetch_videos(
                stubs,
                lambda video, segments, source_ids: self._store.upsert_video(
                    video, segments, source_ids
                ),
            )
            job.errors.extend(result["errors"])
            counters = result["counters"]
            job.completed, job.ok = counters["completed"], counters["ok"]
            job.missing, job.failed = counters["missing"], counters["failed"]

        label = video_ids[0] if len(video_ids) == 1 else f"{len(video_ids)} videos"
        return self._start_job("refetch", label, worker, options)

    def sync_source(self, source_id: str, force: bool = False) -> dict:
        """Re-scan a channel or playlist: pull in new uploads, optionally redo the rest."""
        source = self._store.get_source(source_id)
        if not source:
            return _err(f"Unknown source: {source_id}")
        options = self._options_from_settings()
        options.skip_existing = not force
        target = Target(
            kind=source["kind"],
            url=source["url"],
            source_id=source["id"],
            title=source.get("title") or source["id"],
            tabs=options.channel_tabs if source["kind"] == "channel" else (),
        )

        def worker(job: Job, ingestor: Ingestor, opts: IngestOptions) -> None:
            self._run_targets(job, ingestor, opts, [target])

        return self._start_job("sync", target.title, worker, options)

    def refetch_all(self, scope: str = "all", older_than_days: int = 0) -> dict:
        """Refetch stored videos.

        ``scope`` is ``all``, ``missing`` (only videos that had no captions --
        uploaders add them after the fact), or ``stale`` (fetched longer ago
        than ``older_than_days``).
        """
        videos = self._store.get_videos()
        if scope == "missing":
            videos = [v for v in videos if v.get("subtitle_type") == "none"]
        elif scope == "stale":
            cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, older_than_days))
            kept = []
            for video in videos:
                try:
                    fetched = datetime.fromisoformat(video.get("fetched_at") or "")
                except ValueError:
                    kept.append(video)
                    continue
                if fetched.tzinfo is None:
                    fetched = fetched.replace(tzinfo=timezone.utc)
                if fetched < cutoff:
                    kept.append(video)
            videos = kept

        if not videos:
            return _err("Nothing matches that refetch scope.")
        return self.refetch_videos([video["id"] for video in videos])

    def cancel_job(self, job_id: str = "") -> dict:
        with self._jobs_lock:
            job = self._jobs.get(job_id or self._active_job_id)
        if not job:
            return _err("No such job.")
        if job.status != "running":
            return _ok(job=job.snapshot())
        job.cancel_event.set()
        if job.ingestor:
            job.ingestor.cancel()
        job.message = "Cancelling..."
        return _ok(job=job.snapshot())

    def get_job(self, job_id: str = "") -> dict:
        with self._jobs_lock:
            job = self._jobs.get(job_id or self._active_job_id)
        return _ok(job=job.snapshot() if job else None)

    # ----------------------------------------------------------------- reads

    def get_videos(self, source_id: str = "") -> dict:
        return _ok(videos=self._store.get_videos(source_id))

    def get_sources(self) -> dict:
        return _ok(sources=self._store.get_sources())

    def get_transcript(self, video_id: str) -> dict:
        return _ok(
            segments=self._store.get_transcript(video_id),
            video=self._store.get_video(video_id),
        )

    def search_transcripts(
        self,
        query: str,
        source_id: str = "",
        video_id: str = "",
        limit: int = 300,
        offset: int = 0,
    ) -> dict:
        try:
            result = self._store.search_segments(
                query, source_id=source_id, video_id=video_id, limit=limit, offset=offset
            )
        except SearchSyntaxError as exc:
            return _err(str(exc))
        return _ok(**result)

    def get_missing_subtitles(self) -> dict:
        return _ok(videos=self._store.get_missing_subtitles())

    def get_stats(self) -> dict:
        return _ok(stats=self._store.get_stats())

    # --------------------------------------------------------------- deletes

    def delete_video(self, video_id: str) -> dict:
        self._store.delete_video(video_id)
        return _ok()

    def delete_all_videos(self) -> dict:
        self._store.delete_all_videos()
        return _ok()

    def delete_source(self, source_id: str, delete_videos: bool = False) -> dict:
        self._store.delete_source(source_id, delete_videos)
        return _ok()

    # ------------------------------------------------------------- lifecycle

    def prepare_ytdlp(self) -> dict:
        """Download or update yt-dlp in the background, reporting to the UI."""

        def run() -> None:
            try:
                ensure_ytdlp(
                    lambda message: self._push({"type": "ytdlp", "message": message})
                )
                self._push(
                    {
                        "type": "ytdlp",
                        "message": "",
                        "ready": True,
                        "version": get_local_version() or "",
                    }
                )
            except Exception as exc:  # noqa: BLE001 - reported, not raised into the UI thread
                self._push({"type": "ytdlp", "message": str(exc), "error": True})

        threading.Thread(target=run, daemon=True, name="ytdlp-update").start()
        return _ok()
