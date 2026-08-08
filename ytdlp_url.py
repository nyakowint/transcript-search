"""Recognise what a pasted YouTube URL actually refers to.

Kept apart from the ingest engine so it stays trivially testable -- no network,
no subprocesses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")

# Tabs a channel can be enumerated from. "videos" is long-form uploads,
# "streams" is past live broadcasts, "shorts" is vertical short-form.
CHANNEL_TABS = ("videos", "shorts", "streams")
_KNOWN_TABS = {*CHANNEL_TABS, "playlists", "community", "featured", "about", "search"}

# Single-segment paths that are YouTube's own, not somebody's custom URL.
# Everything else at the top level is treated as a legacy custom channel URL.
RESERVED_PATHS = {
    "about", "account", "ads", "attribution_link", "channel", "c", "clip",
    "creators", "embed", "error", "feed", "gaming", "hashtag", "howyoutubeworks",
    "live", "logout", "movies", "music", "new", "oauth", "playlist", "post",
    "premium", "redirect", "reporthistory", "results", "robots.txt", "shorts",
    "signin", "source", "supported_browsers", "sw.js", "t", "upload", "user",
    "v", "watch", "watch_videos",
}


@dataclass
class Target:
    """One thing to ingest."""

    kind: str  # "video" | "playlist" | "channel"
    url: str
    # Stable identity used as the sources-table primary key. For a channel this
    # is the handle or UC id; for a playlist the PL id; empty for a lone video.
    source_id: str = ""
    title: str = ""
    # Channel targets fan out to one enumeration URL per selected tab.
    tabs: tuple[str, ...] = field(default_factory=tuple)
    # Alternate base URLs to retry when the primary one 404s. Only ever other
    # spellings of the *same* namespace: "/c/name" and a bare "/name" are two
    # forms of one legacy custom URL, so swapping them is safe. "@name" is a
    # separate namespace that may belong to a different channel entirely, so it
    # is never guessed at.
    fallback_urls: tuple[str, ...] = field(default_factory=tuple)
    # Filled in during enumeration from yt-dlp's playlist metadata. A handle can
    # be renamed, so the canonical "UC..." id is what a source is finally keyed
    # on -- that way "@foo" and "/channel/UC..." collapse to one source.
    resolved_id: str = ""
    resolved_title: str = ""

    @property
    def key(self) -> str:
        return self.resolved_id or self.source_id

    @property
    def label(self) -> str:
        return self.resolved_title or self.title or self.source_id or self.url

    def tab_urls(self, base: str = "") -> list[str]:
        if self.kind != "channel":
            return [self.url]
        base = (base or self.url).rstrip("/")
        return [f"{base}/{tab}" for tab in self.tabs] or [base]

    def candidate_bases(self) -> list[str]:
        """Base URLs to try in order. The user's own URL always goes first."""
        return [self.url, *self.fallback_urls]


def parse_input_urls(input_text: str) -> list[str]:
    tokens = re.split(r"[\s,]+", (input_text or "").strip())
    return [token for token in tokens if token]


def _strip_tab(path_parts: list[str]) -> tuple[list[str], Optional[str]]:
    if path_parts and path_parts[-1].lower() in _KNOWN_TABS:
        return path_parts[:-1], path_parts[-1].lower()
    return path_parts, None


def classify_url(raw: str, tabs: tuple[str, ...] = CHANNEL_TABS) -> Target:
    """Map one user-supplied string to a :class:`Target`.

    Accepts full URLs, ``@handle`` shorthand, and bare 11-character video IDs.
    Unrecognised input is passed through as a generic target and left for
    yt-dlp to interpret -- it supports far more sites than we can enumerate.
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Empty URL")

    # Shorthands that are not URLs at all.
    if raw.startswith("@") and "/" not in raw:
        handle = raw
        return Target(
            kind="channel",
            url=f"https://www.youtube.com/{handle}",
            source_id=handle.lower(),
            title=handle,
            tabs=tabs,
        )
    if VIDEO_ID_RE.match(raw):
        return Target(kind="video", url=f"https://www.youtube.com/watch?v={raw}")
    if CHANNEL_ID_RE.match(raw):
        return Target(
            kind="channel",
            url=f"https://www.youtube.com/channel/{raw}",
            source_id=raw,
            title=raw,
            tabs=tabs,
        )

    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    query = parse_qs(parsed.query)
    parts = [p for p in parsed.path.split("/") if p]

    if host not in {"youtube.com", "youtu.be", "music.youtube.com"}:
        # A bare word is not a URL. Without this, stray input like "hello" gets
        # read as the host "hello" and costs a DNS lookup to reject.
        if "." not in host:
            raise ValueError(f"Unrecognised URL: {raw}")
        # Some other extractor's URL. yt-dlp decides; treat as a playlist so a
        # multi-item result is still expanded.
        return Target(kind="playlist", url=candidate, source_id=candidate, title=candidate)

    if host == "youtu.be":
        video_id = parts[0] if parts else ""
        return Target(kind="video", url=f"https://www.youtube.com/watch?v={video_id}")

    list_id = (query.get("list") or [""])[0]
    video_id = (query.get("v") or [""])[0]

    # "RD"-prefixed lists are autogenerated radio mixes: effectively infinite
    # and different on every request, so the video the user pasted wins.
    if list_id and not list_id.startswith("RD"):
        return Target(
            kind="playlist",
            url=f"https://www.youtube.com/playlist?list={list_id}",
            source_id=list_id,
            title=list_id,
        )
    if video_id:
        return Target(kind="video", url=f"https://www.youtube.com/watch?v={video_id}")

    if parts and parts[0] in {"shorts", "live", "embed", "v"} and len(parts) > 1:
        return Target(kind="video", url=f"https://www.youtube.com/watch?v={parts[1]}")

    if parts and parts[0] == "playlist":
        return Target(kind="playlist", url=candidate, source_id=list_id or candidate)

    base_parts, explicit_tab = _strip_tab(parts)
    # A URL that names a tab ("/@foo/shorts") is an explicit request for just
    # that tab, and overrides the caller's default selection.
    if explicit_tab in CHANNEL_TABS:
        tabs = (explicit_tab,)

    if base_parts and base_parts[0].startswith("@"):
        handle = base_parts[0]
        return Target(
            kind="channel",
            url=f"https://www.youtube.com/{handle}",
            source_id=handle.lower(),
            title=handle,
            tabs=tabs,
        )
    if len(base_parts) >= 2 and base_parts[0] in {"channel", "c", "user"}:
        prefix, ident = base_parts[0], base_parts[1]
        return _custom_channel(prefix, ident, tabs)

    # A bare "/name" is the same legacy custom URL as "/c/name" -- YouTube
    # accepts both, and these days it is often the "/c/" spelling that 404s.
    if len(base_parts) == 1 and base_parts[0].lower() not in RESERVED_PATHS:
        return _custom_channel("", base_parts[0], tabs)

    raise ValueError(f"Unrecognised YouTube URL: {raw}")


def _custom_channel(prefix: str, ident: str, tabs: tuple[str, ...]) -> Target:
    """Build a channel target, preferring the spelling the user gave us."""
    bare = f"https://www.youtube.com/{ident}"
    prefixed = f"https://www.youtube.com/{prefix}/{ident}" if prefix else bare

    if prefix == "channel":
        # "/channel/UC..." is canonical; nothing to fall back to.
        return Target(
            kind="channel", url=prefixed, source_id=ident, title=ident, tabs=tabs
        )
    if prefix == "user":
        # The username namespace is distinct, but a bare custom URL of the same
        # name is the usual migration target, so it is worth a second attempt.
        return Target(
            kind="channel",
            url=prefixed,
            source_id=f"user/{ident}",
            title=ident,
            tabs=tabs,
            fallback_urls=(bare,),
        )

    primary, fallback = (prefixed, bare) if prefix else (bare, f"https://www.youtube.com/c/{ident}")
    return Target(
        kind="channel",
        url=primary,
        source_id=f"custom/{ident.lower()}",
        title=ident,
        tabs=tabs,
        fallback_urls=(fallback,),
    )
