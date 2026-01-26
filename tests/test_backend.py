import tempfile
import unittest
from pathlib import Path

from backend import Api, CaptionStore, parse_vtt, select_caption_language


class CaptionLanguageTests(unittest.TestCase):
    def test_selects_english(self) -> None:
        captions = {"en": {}, "es": {}}
        self.assertEqual(select_caption_language(captions), "en")

    def test_selects_english_variant(self) -> None:
        captions = {"en-US": {}, "es": {}}
        self.assertEqual(select_caption_language(captions), "en-US")

    def test_selects_first_available(self) -> None:
        captions = {"es": {}, "fr": {}}
        self.assertEqual(select_caption_language(captions), "es")


class VttParsingTests(unittest.TestCase):
    def test_parses_single_cue(self) -> None:
        content = """WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello world\n\n"""
        segments = parse_vtt(content)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "Hello world")

    def test_dedupes_overlapping_cues(self) -> None:
        content = (
            "WEBVTT\n\n"
            "00:00:02.000 --> 00:00:04.000\n"
            "Look at that beautiful sunset.\n\n"
            "00:00:02.000 --> 00:00:05.000\n"
            "Look at that beautiful sunset. Isn't it vibrant?\n\n"
        )
        segments = parse_vtt(content)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["start_ms"], 2000)
        self.assertEqual(
            segments[0]["text"],
            "Look at that beautiful sunset. Isn't it vibrant?",
        )


class SearchTests(unittest.TestCase):
    def test_search_segments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "captions.db"
            store = CaptionStore(db_path)
            video = {
                "id": "abc123",
                "title": "Test Video",
                "channel": "Test Channel",
                "channel_id": "channel123",
                "upload_date": "20260101",
                "subtitle_type": "manual",
                "subtitle_language": "en",
                "source_url": "https://example.com",
                "fetched_at": "2026-01-01T00:00:00Z",
            }
            segments = [
                {"start_ms": 0, "end_ms": 1000, "text": "Hello world"},
                {"start_ms": 2000, "end_ms": 3000, "text": "Another line"},
            ]
            store.upsert_video(video, segments)
            results = store.search_segments("world")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["video_id"], "abc123")


class PathNormalizationTests(unittest.TestCase):
    def test_normalizes_windows_path(self) -> None:
        api = Api()
        normalized = api._normalize_path(r"C:\\temp\\cookies.txt")
        self.assertEqual(normalized, r"C:\temp\cookies.txt")


if __name__ == "__main__":
    unittest.main()
