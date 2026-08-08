"""Caption track selection and subtitle parsing.

YouTube exposes every caption track as a set of format URLs inside the yt-dlp
info JSON. We pick one track, fetch that URL over plain HTTP, and parse it --
no second yt-dlp invocation and no media download.

``json3`` is preferred over ``vtt``: it is YouTube's native timedtext format and
auto-generated tracks come back as clean, non-overlapping events. The rolling
duplicate text that plagues auto-generated WebVTT is an artifact of the VTT
serialisation, not of the underlying data.
"""

from __future__ import annotations

import html
import json
import re
from typing import Iterable, Optional

TIME_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")

# Ordered by how cheap and lossless they are to parse.
FORMAT_PREFERENCE = ("json3", "vtt", "srv3", "srv1", "ttml")


def normalize_language(code: str) -> str:
    """Reduce ``en-US``/``en-orig`` style codes to their base language."""
    if not code:
        return ""
    base = code.split("-", 1)[0]
    return base.lower()


def _rank_language(code: str, preferred: Iterable[str]) -> Optional[int]:
    """Position of ``code`` in ``preferred``, or None when it does not match."""
    base = normalize_language(code)
    for index, want in enumerate(preferred):
        want_base = normalize_language(want)
        if base == want_base:
            # Exact tag match sorts ahead of a mere base-language match so that
            # "en" beats "en-GB" when the user asked for "en".
            return index * 2 + (0 if code.lower() == want.lower() else 1)
    return None


def _best_format(formats: list[dict]) -> Optional[dict]:
    by_ext = {}
    for fmt in formats or []:
        ext = (fmt.get("ext") or "").lower()
        if ext and ext not in by_ext and fmt.get("url"):
            by_ext[ext] = fmt
    for ext in FORMAT_PREFERENCE:
        if ext in by_ext:
            return {"ext": ext, "url": by_ext[ext]["url"]}
    for ext, fmt in by_ext.items():
        return {"ext": ext, "url": fmt["url"]}
    return None


def _candidates(
    tracks: dict, kind: str, preferred: list[str], original_language: str = ""
) -> list[tuple]:
    """Build a sortable candidate list from a subtitles/automatic_captions dict.

    Sort key is ``(missed_preference, preference_rank, not_original, language)``.
    Anything outside the preference list sorts last -- for auto-generated tracks
    that tail is ~160 machine translations of the same ASR output, none of which
    carry more information than the source track. Among those leftovers the
    video's own declared language wins, so a fallback lands on what was actually
    spoken rather than on whichever translation sorts first alphabetically.
    """
    original = normalize_language(original_language)
    out: list[tuple] = []
    for lang, formats in (tracks or {}).items():
        fmt = _best_format(formats)
        if not fmt:
            continue
        rank = _rank_language(lang, preferred)
        out.append(
            (
                0 if rank is not None else 1,
                rank if rank is not None else 0,
                0 if original and normalize_language(lang) == original else 1,
                lang,
                {"language": lang, "kind": kind, "ext": fmt["ext"], "url": fmt["url"]},
            )
        )
    return out


def select_track(
    subtitles: dict | None,
    automatic_captions: dict | None,
    preferred_languages: Iterable[str] = ("en",),
    allow_auto: bool = True,
    allow_other_languages: bool = True,
    original_language: str = "",
) -> Optional[dict]:
    """Choose one caption track.

    Preference order, strongest first:

    1. uploader-submitted (manual) track in a preferred language
    2. auto-generated track in a preferred language
    3. uploader-submitted track in any other language
    4. auto-generated track in any other language

    Manual captions beat auto-generated ones, but only within the same
    language. Language match is the stronger signal because this is a search
    tool: an English ASR transcript answers an English query, while a
    hand-written Spanish translation of the same video does not. Popular
    channels routinely carry community-contributed translations without an
    English manual track, so ranking manual first outright would silently
    index the wrong language.

    Returns ``None`` when nothing is usable.
    """
    preferred = [code for code in preferred_languages if code] or ["en"]

    manual = _candidates(subtitles or {}, "manual", preferred, original_language)
    auto = (
        _candidates(automatic_captions or {}, "auto", preferred, original_language)
        if allow_auto
        else []
    )

    def matching(candidates: list[tuple]) -> list[tuple]:
        return [c for c in candidates if c[0] == 0]

    def other(candidates: list[tuple]) -> list[tuple]:
        return [] if not allow_other_languages else [c for c in candidates if c[0] != 0]

    tiers = (matching(manual), matching(auto), other(manual), other(auto))
    for group in tiers:
        if not group:
            continue
        group.sort(key=lambda item: item[:4])
        return group[0][4]
    return None


def _clean_text(text: str) -> str:
    cleaned = TAG_RE.sub("", html.unescape(text))
    return " ".join(cleaned.split())


def parse_json3(payload: str | bytes | dict) -> list[dict]:
    """Parse YouTube's ``json3`` timedtext format into transcript segments.

    Auto-generated tracks interleave two kinds of event: a real cue carrying
    ``dDurationMs`` and text, and a zero-width "rolling" event with no duration
    whose only job is to blank the previous line on screen. Dropping events
    without a duration or without visible text yields the same segment list
    YouTube shows in its own transcript panel.
    """
    if isinstance(payload, (str, bytes)):
        data = json.loads(payload)
    else:
        data = payload

    segments: list[dict] = []
    for event in data.get("events") or []:
        duration = event.get("dDurationMs")
        if duration is None:
            continue
        segs = event.get("segs") or []
        text = _clean_text("".join(seg.get("utf8", "") for seg in segs))
        if not text:
            continue
        start_ms = int(event.get("tStartMs") or 0)
        segments.append(
            {
                "start_ms": start_ms,
                "end_ms": start_ms + int(duration),
                "text": text,
            }
        )
    segments.sort(key=lambda seg: seg["start_ms"])
    return _merge_adjacent_duplicates(segments)


def _merge_adjacent_duplicates(segments: list[dict]) -> list[dict]:
    """Collapse identical back-to-back cues (some manual tracks repeat them)."""
    merged: list[dict] = []
    for seg in segments:
        if merged and merged[-1]["text"] == seg["text"]:
            merged[-1]["end_ms"] = max(merged[-1]["end_ms"], seg["end_ms"])
            continue
        merged.append(seg)
    return merged


def _parse_timestamp(value: str) -> int:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return int(total_seconds * 1000)


def parse_vtt(content: str) -> list[dict]:
    """Parse WebVTT. Fallback for tracks that do not offer ``json3``."""
    segments: list[dict] = []
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith(("WEBVTT", "NOTE", "STYLE")):
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
        caption_text = _clean_text(" ".join(text_lines))
        if caption_text:
            segments.append(
                {"start_ms": start_ms, "end_ms": end_ms, "text": caption_text}
            )
    return dedupe_vtt_segments(segments)


def dedupe_vtt_segments(segments: list[dict]) -> list[dict]:
    """Undo the rolling-window duplication in auto-generated WebVTT.

    YouTube serialises auto-captions as overlapping cues: a short cue holding
    only the new words, followed by a longer cue repeating the whole visible
    line. Keeping both would triple every search hit.
    """
    if not segments:
        return []

    sorted_segments = sorted(segments, key=lambda s: (s["start_ms"], s["end_ms"]))

    by_start: dict[int, dict] = {}
    for seg in sorted_segments:
        start = seg["start_ms"]
        if start not in by_start or len(seg["text"]) > len(by_start[start]["text"]):
            by_start[start] = seg

    candidates = sorted(by_start.values(), key=lambda s: s["start_ms"])

    filtered: list[dict] = []
    index = 0
    while index < len(candidates):
        current = candidates[index]
        duration = current["end_ms"] - current["start_ms"]
        if duration <= 50 and index + 1 < len(candidates):
            next_seg = candidates[index + 1]
            if (
                next_seg["start_ms"] - current["end_ms"] <= 100
                and current["text"] in next_seg["text"]
            ):
                index += 1
                continue
        filtered.append(current)
        index += 1

    def _overlap(prev_text: str, curr_text: str) -> int:
        prev_words = prev_text.split()
        curr_words = curr_text.split()
        for size in range(min(len(prev_words), len(curr_words)), 0, -1):
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
            curr_words = seg["text"].split()
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


def parse_caption_payload(payload: bytes, ext: str) -> list[dict]:
    """Parse a downloaded caption body according to its format."""
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    ext = (ext or "").lower()
    if ext == "json3":
        return parse_json3(text)
    if ext in {"vtt", "srt"}:
        return parse_vtt(text)
    raise ValueError(f"Unsupported caption format: {ext}")
