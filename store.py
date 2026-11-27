"""SQLite persistence with full-text search.

A single channel is easily 150 videos x ~500 caption cues = 75k rows, and the
app is built to hold several channels at once. ``LIKE '%term%'`` scans every
row on every keystroke at that size, so segment text lives in an FTS5 index and
searches run against that.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Optional

SCHEMA_VERSION = 4

# Terms are quoted before being handed to FTS5, so the only characters that
# still need stripping are the ones that break tokenisation entirely.
_FTS_STRIP_RE = re.compile(r'["\x00]')
_PHRASE_RE = re.compile(r'"([^"]*)"')

SEARCH_MODES = ("phrase", "all")
SEARCH_SORTS = {
    "relevance": "best ASC, hit_count DESC",
    "hits": "hit_count DESC, best ASC",
    "newest": "v.upload_date DESC, best ASC",
    "oldest": "v.upload_date = '', v.upload_date ASC, best ASC",
}

# A hit is reported at the cue its match starts in. Matching runs against
# windows of three consecutive cues, so a sentence YouTube split across cues is
# still found; the same match then also shows up in the window(s) before it.
# A window keeps the hit if its first cue matches on its own, or if the window
# one cue later does not match (so the match must begin in this first cue).
_HITS_CTE = """
WITH single AS MATERIALIZED (
    SELECT rowid AS id FROM segments_fts WHERE segments_fts MATCH :q
),
windowed AS MATERIALIZED (
    SELECT rowid AS id, rank AS score
    FROM windows_fts WHERE windows_fts MATCH :q
),
hits AS (
    SELECT w.id, w.score FROM windowed w
    WHERE w.id IN (SELECT id FROM single)
       OR w.id + 1 NOT IN (SELECT id FROM windowed)
)
"""


class SearchSyntaxError(ValueError):
    """Raised when a query cannot be turned into a valid FTS5 expression."""


def _clean_tokens(text: str) -> list[str]:
    tokens = [_FTS_STRIP_RE.sub("", token) for token in text.split()]
    return [token for token in tokens if token]


def build_fts_query(query: str, mode: str = "phrase", whole_words: bool = True) -> str:
    """Turn user input into an FTS5 MATCH expression.

    ``phrase`` matches the words in order, as typed. ``all`` matches every word
    anywhere in the same stretch of captions, keeping double-quoted runs as
    phrases. With ``whole_words`` off, words also match as prefixes (only the
    last word in phrase mode). Every term is quoted before it reaches FTS5, so
    operators the user happens to type (``AND``, ``*``, ``-``, ``NEAR``) are
    searched for literally -- this is a caption search box, not a query
    language.
    """
    query = (query or "").strip()
    if not query:
        raise SearchSyntaxError("Empty query")
    star = "" if whole_words else "*"

    if mode == "phrase":
        tokens = _clean_tokens(query)
        if not tokens:
            raise SearchSyntaxError("Query has no searchable terms")
        return '"{}"{}'.format(" ".join(tokens), star)

    parts: list[str] = []

    def add_terms(text: str) -> None:
        parts.extend(f'"{token}"{star}' for token in _clean_tokens(text))

    cursor = 0
    for match in _PHRASE_RE.finditer(query):
        add_terms(query[cursor : match.start()])
        tokens = _clean_tokens(match.group(1))
        if tokens:
            parts.append('"{}"'.format(" ".join(tokens)))
        cursor = match.end()
    add_terms(query[cursor:])

    if not parts:
        raise SearchSyntaxError("Query has no searchable terms")
    return " ".join(parts)


class CaptionStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # Ingest runs on a worker pool while the UI reads on the main thread.
        self._write_lock = threading.Lock()
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    # ---------------------------------------------------------------- plumbing

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            # An in-memory database dies with its connection, so tests need the
            # same handle handed back every time.
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _close(self, conn: sqlite3.Connection) -> None:
        if conn is not self._memory_conn:
            conn.close()

    def _ensure_db(self) -> None:
        conn = self._connect()
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            # Databases written before this app tracked a schema version report
            # 0, which is also what a brand-new file reports. Migrating both is
            # correct: on an empty database every migration step is a no-op.
            needs_migration = version < SCHEMA_VERSION
            with conn:
                self._create_schema(conn)
                if needs_migration:
                    self._migrate(conn, version)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        finally:
            self._close(conn)

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            -- video_count is deliberately not stored; it is derived from
            -- video_sources so it cannot drift out of date.
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                title TEXT,
                url TEXT,
                added_at TEXT,
                last_synced_at TEXT
            );

            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT,
                channel TEXT,
                channel_id TEXT,
                upload_date TEXT,
                duration INTEGER,
                subtitle_type TEXT,
                subtitle_language TEXT,
                source_url TEXT,
                fetched_at TEXT,
                segment_count INTEGER DEFAULT 0,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS video_sources (
                video_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                PRIMARY KEY (video_id, source_id)
            );

            CREATE TABLE IF NOT EXISTS transcript_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                start_ms INTEGER,
                end_ms INTEGER,
                text TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_segments_video
                ON transcript_segments(video_id, start_ms);
            CREATE INDEX IF NOT EXISTS idx_video_sources_source
                ON video_sources(source_id);
            CREATE INDEX IF NOT EXISTS idx_videos_channel
                ON videos(channel_id);

            CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
                text,
                content='transcript_segments',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );

            CREATE TRIGGER IF NOT EXISTS segments_ai
            AFTER INSERT ON transcript_segments BEGIN
                INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
            END;

            CREATE TRIGGER IF NOT EXISTS segments_ad
            AFTER DELETE ON transcript_segments BEGIN
                INSERT INTO segments_fts(segments_fts, rowid, text)
                VALUES ('delete', old.id, old.text);
            END;

            CREATE TRIGGER IF NOT EXISTS segments_au
            AFTER UPDATE ON transcript_segments BEGIN
                INSERT INTO segments_fts(segments_fts, rowid, text)
                VALUES ('delete', old.id, old.text);
                INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
            END;

            -- Each cue joined with the next two from the same video. A video's
            -- cues are inserted in one go and in time order, so their ids are
            -- consecutive and id + 1 is the next cue. Being a view, the window
            -- text is never stored twice; only its index is.
            CREATE VIEW IF NOT EXISTS segment_windows AS
            SELECT s.id, s.video_id,
                   s.text || COALESCE(' ' || n1.text, '') || COALESCE(' ' || n2.text, '') AS text
            FROM transcript_segments s
            LEFT JOIN transcript_segments n1 ON n1.id = s.id + 1 AND n1.video_id = s.video_id
            LEFT JOIN transcript_segments n2 ON n2.id = s.id + 2 AND n2.video_id = s.video_id;

            -- Kept in step by hand (_index_windows/_unindex_windows): a trigger
            -- on one cue cannot see the neighbours its windows depend on.
            CREATE VIRTUAL TABLE IF NOT EXISTS windows_fts USING fts5(
                text,
                content='segment_windows',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );
            """
        )

    def _index_windows(self, conn: sqlite3.Connection, video_id: str) -> None:
        conn.execute(
            "INSERT INTO windows_fts(rowid, text) SELECT id, text FROM segment_windows WHERE video_id = ?",
            (video_id,),
        )

    def _unindex_windows(self, conn: sqlite3.Connection, video_filter: str, params: tuple) -> None:
        """Drop windows from the index; must run while their cues still exist.

        External-content FTS5 deletes need the exact text that was indexed,
        which the view can only reproduce before the cues are gone.
        """
        conn.execute(
            f"""
            INSERT INTO windows_fts(windows_fts, rowid, text)
            SELECT 'delete', id, text FROM segment_windows WHERE video_id {video_filter}
            """,
            params,
        )

    def _migrate(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Bring a pre-FTS database up to the current schema.

        Version 0/1 databases predate ``user_version`` being set, so they are
        detected by their missing columns instead.
        """
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(videos)")}
        for column, ddl in (
            ("duration", "INTEGER"),
            ("segment_count", "INTEGER DEFAULT 0"),
            ("error", "TEXT"),
        ):
            if column not in columns:
                conn.execute(f"ALTER TABLE videos ADD COLUMN {column} {ddl}")

        # Backfill segment counts for rows written before the column existed.
        conn.execute(
            """
            UPDATE videos SET segment_count = (
                SELECT COUNT(*) FROM transcript_segments s WHERE s.video_id = videos.id
            )
            WHERE segment_count IS NULL OR segment_count = 0
            """
        )
        # Segments written before the FTS index existed are invisible to it,
        # and the index cannot be inspected to find out: COUNT(*) on an
        # external-content FTS5 table reads the content table, so it always
        # matches. Rebuilding unconditionally is the only reliable option --
        # and this runs once per schema bump, not per launch.
        conn.execute("INSERT INTO segments_fts(segments_fts) VALUES ('rebuild')")
        conn.execute("INSERT INTO windows_fts(windows_fts) VALUES ('rebuild')")

    # ------------------------------------------------------------------ videos

    def upsert_video(
        self,
        video: dict,
        segments: Iterable[dict],
        source_ids: Iterable[str] = (),
    ) -> int:
        # Time order matters: segment_windows treats id + 1 as the next cue.
        segment_rows = [
            (video["id"], seg["start_ms"], seg["end_ms"], seg["text"])
            for seg in sorted(segments, key=lambda seg: seg["start_ms"])
        ]
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO videos (
                            id, title, channel, channel_id, upload_date, duration,
                            subtitle_type, subtitle_language, source_url,
                            fetched_at, segment_count, error
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            title=excluded.title,
                            channel=excluded.channel,
                            channel_id=excluded.channel_id,
                            upload_date=excluded.upload_date,
                            duration=excluded.duration,
                            subtitle_type=excluded.subtitle_type,
                            subtitle_language=excluded.subtitle_language,
                            source_url=excluded.source_url,
                            fetched_at=excluded.fetched_at,
                            segment_count=excluded.segment_count,
                            error=excluded.error
                        """,
                        (
                            video["id"],
                            video.get("title") or "",
                            video.get("channel") or "",
                            video.get("channel_id") or "",
                            video.get("upload_date") or "",
                            video.get("duration") or 0,
                            video.get("subtitle_type") or "none",
                            video.get("subtitle_language") or "",
                            video.get("source_url") or "",
                            video.get("fetched_at") or "",
                            len(segment_rows),
                            video.get("error") or None,
                        ),
                    )
                    # DELETE fires the FTS delete trigger, keeping the index in
                    # step when a video is refetched.
                    self._unindex_windows(conn, "= ?", (video["id"],))
                    conn.execute(
                        "DELETE FROM transcript_segments WHERE video_id = ?",
                        (video["id"],),
                    )
                    conn.executemany(
                        """
                        INSERT INTO transcript_segments (video_id, start_ms, end_ms, text)
                        VALUES (?, ?, ?, ?)
                        """,
                        segment_rows,
                    )
                    self._index_windows(conn, video["id"])
                    for source_id in source_ids:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO video_sources (video_id, source_id)
                            VALUES (?, ?)
                            """,
                            (video["id"], source_id),
                        )
            finally:
                self._close(conn)
        return len(segment_rows)

    def link_videos_to_source(self, video_ids: Iterable[str], source_id: str) -> None:
        """Attach stored videos to a source without touching their transcripts.

        Re-syncing a channel finds mostly videos we already have. Routing that
        through upsert_video would rewrite every caption row (and reindex it)
        purely to add a link row.
        """
        if not source_id:
            return
        rows = [(video_id, source_id) for video_id in video_ids if video_id]
        if not rows:
            return
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.executemany(
                        "INSERT OR IGNORE INTO video_sources (video_id, source_id) VALUES (?, ?)",
                        rows,
                    )
            finally:
                self._close(conn)

    def get_videos(self, source_id: str = "") -> list[dict]:
        conn = self._connect()
        try:
            if source_id:
                rows = conn.execute(
                    """
                    SELECT v.* FROM videos v
                    JOIN video_sources vs ON vs.video_id = v.id
                    WHERE vs.source_id = ?
                    ORDER BY v.upload_date DESC, v.title
                    """,
                    (source_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM videos ORDER BY upload_date DESC, title"
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close(conn)

    def get_existing_video_ids(self) -> set[str]:
        """IDs already stored with usable captions.

        Videos recorded with ``subtitle_type = 'none'`` are deliberately left
        out: a channel may have published captions since the last sync, so they
        are worth retrying.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id FROM videos WHERE subtitle_type != 'none' AND segment_count > 0"
            ).fetchall()
            return {row["id"] for row in rows}
        finally:
            self._close(conn)

    def get_video(self, video_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            self._close(conn)

    def get_transcript(self, video_id: str) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, start_ms, end_ms, text FROM transcript_segments
                WHERE video_id = ? ORDER BY start_ms
                """,
                (video_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close(conn)

    def get_missing_subtitles(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, title, channel, channel_id, source_url, error
                FROM videos WHERE subtitle_type = 'none' ORDER BY title
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close(conn)

    def delete_video(self, video_id: str) -> None:
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    self._unindex_windows(conn, "= ?", (video_id,))
                    conn.execute(
                        "DELETE FROM transcript_segments WHERE video_id = ?", (video_id,)
                    )
                    conn.execute(
                        "DELETE FROM video_sources WHERE video_id = ?", (video_id,)
                    )
                    conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            finally:
                self._close(conn)

    def delete_all_videos(self) -> None:
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute("DELETE FROM transcript_segments")
                    conn.execute("DELETE FROM video_sources")
                    conn.execute("DELETE FROM videos")
                    conn.execute("DELETE FROM sources")
                    conn.execute("INSERT INTO segments_fts(segments_fts) VALUES ('rebuild')")
                    conn.execute("INSERT INTO windows_fts(windows_fts) VALUES ('rebuild')")
            finally:
                self._close(conn)

    # ----------------------------------------------------------------- sources

    def upsert_source(self, source: dict) -> None:
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO sources (id, kind, title, url, added_at, last_synced_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            kind=excluded.kind,
                            title=COALESCE(NULLIF(excluded.title, ''), sources.title),
                            url=excluded.url,
                            last_synced_at=excluded.last_synced_at
                        """,
                        (
                            source["id"],
                            source["kind"],
                            source.get("title") or "",
                            source.get("url") or "",
                            source.get("added_at") or "",
                            source.get("last_synced_at") or "",
                        ),
                    )
            finally:
                self._close(conn)

    def get_sources(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT s.id, s.kind, s.title, s.url, s.added_at, s.last_synced_at, (
                    SELECT COUNT(*) FROM video_sources vs WHERE vs.source_id = s.id
                ) AS video_count
                FROM sources s ORDER BY s.title, s.id
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close(conn)

    def get_source(self, source_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            self._close(conn)

    def delete_source(self, source_id: str, delete_videos: bool = False) -> None:
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    if delete_videos:
                        # Only drop videos this source is the sole owner of.
                        sole_owned = """
                            IN (
                                SELECT vs.video_id FROM video_sources vs
                                WHERE vs.source_id = ?
                                AND NOT EXISTS (
                                    SELECT 1 FROM video_sources o
                                    WHERE o.video_id = vs.video_id AND o.source_id != ?
                                )
                            )
                        """
                        params = (source_id, source_id)
                        self._unindex_windows(conn, sole_owned, params)
                        conn.execute(
                            f"DELETE FROM transcript_segments WHERE video_id {sole_owned}", params
                        )
                        conn.execute(f"DELETE FROM videos WHERE id {sole_owned}", params)
                    conn.execute(
                        "DELETE FROM video_sources WHERE source_id = ?", (source_id,)
                    )
                    conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            finally:
                self._close(conn)

    # ------------------------------------------------------------------ search

    def search(
        self,
        query: str,
        *,
        mode: str = "phrase",
        whole_words: bool = True,
        source_id: str = "",
        subtitle_type: str = "",
        date_from: str = "",
        date_to: str = "",
        sort: str = "relevance",
        limit: Optional[int] = 25,
        offset: int = 0,
    ) -> dict:
        """Full-text search over captions, grouped by video.

        Returns ``{"videos", "total_videos", "total_hits", "has_more"}``. Only
        the ``limit`` videos from ``offset`` carry their hits (``limit=None``
        means all of them). Each hit's ``highlight`` is its three-cue window
        with matched terms wrapped in ``\\x02``/``\\x03`` sentinels, which the
        UI turns into markup without having to trust any of it as HTML.
        """
        empty = {"videos": [], "total_videos": 0, "total_hits": 0, "has_more": False}
        try:
            match_expr = build_fts_query(
                query, mode if mode in SEARCH_MODES else "phrase", whole_words
            )
        except SearchSyntaxError:
            return empty

        where = []
        params: dict = {"q": match_expr}
        if source_id:
            where.append(
                "EXISTS (SELECT 1 FROM video_sources vs "
                "WHERE vs.video_id = v.id AND vs.source_id = :source_id)"
            )
            params["source_id"] = source_id
        if subtitle_type:
            where.append("v.subtitle_type = :subtitle_type")
            params["subtitle_type"] = subtitle_type
        # upload_date is YYYYMMDD, so plain string comparison orders it.
        if date_from:
            where.append("v.upload_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where.append("v.upload_date != '' AND v.upload_date <= :date_to")
            params["date_to"] = date_to
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        order_sql = SEARCH_SORTS.get(sort, SEARCH_SORTS["relevance"])

        conn = self._connect()
        try:
            videos = [
                dict(row)
                for row in conn.execute(
                    f"""
                    {_HITS_CTE}
                    SELECT v.id, v.title, v.channel, v.upload_date, v.duration,
                           v.subtitle_type, v.subtitle_language,
                           COUNT(*) AS hit_count, MIN(h.score) AS best
                    FROM hits h
                    JOIN transcript_segments s ON s.id = h.id
                    JOIN videos v ON v.id = s.video_id
                    {where_sql}
                    GROUP BY v.id
                    ORDER BY {order_sql}
                    """,
                    params,
                )
            ]
            page = videos[offset:] if limit is None else videos[offset : offset + limit]
            hits_by_video = self._hits_for(conn, match_expr, [v["id"] for v in page])
        except sqlite3.OperationalError as exc:
            raise SearchSyntaxError(str(exc)) from exc
        finally:
            self._close(conn)

        for video in page:
            video.pop("best")
            video["hits"] = hits_by_video.get(video["id"], [])
        return {
            "videos": page,
            "total_videos": len(videos),
            "total_hits": sum(video["hit_count"] for video in videos),
            "has_more": offset + len(page) < len(videos),
        }

    def _hits_for(self, conn: sqlite3.Connection, match_expr: str, video_ids: list[str]) -> dict:
        hits: dict[str, list[dict]] = {}
        # Chunked to stay under SQLite's bound-parameter limit when exporting.
        for start in range(0, len(video_ids), 500):
            chunk = video_ids[start : start + 500]
            params = {"q": match_expr, **{f"v{i}": vid for i, vid in enumerate(chunk)}}
            placeholders = ", ".join(f":v{i}" for i in range(len(chunk)))
            rows = conn.execute(
                f"""
                {_HITS_CTE}
                SELECT s.id, s.video_id, s.start_ms, length(s.text) AS cue_length,
                       highlight(windows_fts, 0, char(2), char(3)) AS highlight,
                       b.text AS before
                FROM windows_fts
                JOIN transcript_segments s ON s.id = windows_fts.rowid
                LEFT JOIN transcript_segments b ON b.id = s.id - 1 AND b.video_id = s.video_id
                WHERE windows_fts MATCH :q
                  AND s.video_id IN ({placeholders})
                  AND s.id IN (SELECT id FROM hits)
                ORDER BY s.start_ms
                """,
                params,
            )
            for row in rows:
                hit = dict(row)
                hits.setdefault(hit.pop("video_id"), []).append(hit)
        return hits

    def get_stats(self) -> dict:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM videos) AS videos,
                    (SELECT COUNT(*) FROM videos WHERE subtitle_type = 'manual') AS manual,
                    (SELECT COUNT(*) FROM videos WHERE subtitle_type = 'auto') AS auto,
                    (SELECT COUNT(*) FROM videos WHERE subtitle_type = 'none') AS missing,
                    (SELECT COUNT(*) FROM transcript_segments) AS segments,
                    (SELECT COUNT(*) FROM sources) AS sources
                """
            ).fetchone()
            return dict(row)
        finally:
            self._close(conn)

    # ---------------------------------------------------------------- settings

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default
        finally:
            self._close(conn)

    def set_setting(self, key: str, value: str) -> None:
        with self._write_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO settings (key, value) VALUES (?, ?)
                        ON CONFLICT(key) DO UPDATE SET value=excluded.value
                        """,
                        (key, value),
                    )
            finally:
                self._close(conn)
