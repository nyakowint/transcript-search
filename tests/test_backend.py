"""Offline tests: no network, no yt-dlp, no webview."""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from captions import parse_json3, parse_vtt, select_track  # noqa: E402
from ingest import IngestOptions, build_targets  # noqa: E402
from store import CaptionStore, SearchSyntaxError, build_fts_query  # noqa: E402
from ytdlp_url import classify_url, parse_input_urls  # noqa: E402


def track(*languages):
    return {lang: [{"ext": "json3", "url": f"https://example.test/{lang}"}] for lang in languages}


class TrackSelectionTests(unittest.TestCase):
    def test_prefers_manual_in_preferred_language(self):
        chosen = select_track(track("en", "es"), track("en", "fr"), ("en",))
        self.assertEqual((chosen["language"], chosen["kind"]), ("en", "manual"))

    def test_preferred_language_beats_manual_in_wrong_language(self):
        """A hand-written Spanish track does not answer an English query."""
        chosen = select_track(track("es", "ar"), track("en", "fr"), ("en",))
        self.assertEqual((chosen["language"], chosen["kind"]), ("en", "auto"))

    def test_falls_back_to_auto_when_no_manual_exists(self):
        chosen = select_track({}, track("en"), ("en",))
        self.assertEqual((chosen["language"], chosen["kind"]), ("en", "auto"))

    def test_matches_language_variants(self):
        chosen = select_track(track("en-GB"), {}, ("en",))
        self.assertEqual(chosen["language"], "en-GB")

    def test_exact_tag_beats_variant(self):
        chosen = select_track(track("en-GB", "en"), {}, ("en",))
        self.assertEqual(chosen["language"], "en")

    def test_original_language_breaks_ties_among_leftovers(self):
        chosen = select_track(track("es", "ar"), {}, ("en",), original_language="es")
        self.assertEqual(chosen["language"], "es")

    def test_allow_auto_false_skips_auto_tracks(self):
        self.assertIsNone(select_track({}, track("en"), ("en",), allow_auto=False))

    def test_allow_other_languages_false_is_strict(self):
        self.assertIsNone(
            select_track(track("es"), track("fr"), ("en",), allow_other_languages=False)
        )

    def test_returns_none_without_any_track(self):
        self.assertIsNone(select_track({}, {}, ("en",)))

    def test_prefers_json3_over_vtt(self):
        subtitles = {
            "en": [
                {"ext": "vtt", "url": "https://example.test/en.vtt"},
                {"ext": "json3", "url": "https://example.test/en.json3"},
            ]
        }
        self.assertEqual(select_track(subtitles, {}, ("en",))["ext"], "json3")


class Json3ParsingTests(unittest.TestCase):
    def test_parses_events(self):
        payload = json.dumps(
            {
                "events": [
                    {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
                ]
            }
        )
        segments = parse_json3(payload)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], {"start_ms": 1000, "end_ms": 3000, "text": "Hello world"})

    def test_drops_rolling_placeholder_events(self):
        """Auto-caption tracks interleave duration-less blanking events."""
        payload = json.dumps(
            {
                "events": [
                    {"tStartMs": 4390, "segs": [{"utf8": " "}]},
                    {"tStartMs": 4400, "dDurationMs": 4159, "segs": [{"utf8": "This is a three."}]},
                    {"tStartMs": 6869, "dDurationMs": 1690, "segs": [{"utf8": "  \n "}]},
                ]
            }
        )
        segments = parse_json3(payload)
        self.assertEqual([seg["text"] for seg in segments], ["This is a three."])

    def test_merges_repeated_adjacent_cues(self):
        payload = json.dumps(
            {
                "events": [
                    {"tStartMs": 0, "dDurationMs": 1000, "segs": [{"utf8": "same"}]},
                    {"tStartMs": 1000, "dDurationMs": 1000, "segs": [{"utf8": "same"}]},
                ]
            }
        )
        segments = parse_json3(payload)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["end_ms"], 2000)

    def test_unescapes_entities_and_strips_tags(self):
        payload = json.dumps(
            {"events": [{"tStartMs": 0, "dDurationMs": 10, "segs": [{"utf8": "<i>caf&#233;</i> bar"}]}]}
        )
        self.assertEqual(parse_json3(payload)[0]["text"], "café bar")


class VttParsingTests(unittest.TestCase):
    def test_parses_single_cue(self):
        content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello world\n\n"
        segments = parse_vtt(content)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "Hello world")

    def test_dedupes_overlapping_cues(self):
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
            segments[0]["text"], "Look at that beautiful sunset. Isn't it vibrant?"
        )


class UrlClassificationTests(unittest.TestCase):
    def test_video_forms(self):
        for raw in (
            "https://www.youtube.com/watch?v=aircAruvnKk",
            "https://youtu.be/aircAruvnKk?t=30",
            "https://www.youtube.com/shorts/aircAruvnKk",
            "aircAruvnKk",
        ):
            target = classify_url(raw)
            self.assertEqual(target.kind, "video", raw)
            self.assertIn("aircAruvnKk", target.url)

    def test_channel_forms(self):
        for raw in ("@3blue1brown", "https://www.youtube.com/@3blue1brown", "youtube.com/@3blue1brown"):
            self.assertEqual(classify_url(raw).kind, "channel", raw)

    def test_channel_fans_out_to_selected_tabs(self):
        target = classify_url(
            "https://www.youtube.com/@3blue1brown", tabs=("videos", "shorts")
        )
        self.assertEqual(
            target.tab_urls(),
            [
                "https://www.youtube.com/@3blue1brown/videos",
                "https://www.youtube.com/@3blue1brown/shorts",
            ],
        )

    def test_explicit_tab_in_url_overrides_defaults(self):
        target = classify_url(
            "https://www.youtube.com/@3blue1brown/shorts", tabs=("videos", "shorts", "streams")
        )
        self.assertEqual(target.tab_urls(), ["https://www.youtube.com/@3blue1brown/shorts"])

    def test_playlist_wins_over_video_when_both_present(self):
        target = classify_url("https://www.youtube.com/watch?v=abc&list=PL123")
        self.assertEqual(target.kind, "playlist")
        self.assertEqual(target.source_id, "PL123")

    def test_radio_mix_is_treated_as_a_single_video(self):
        """RD lists are generated per request and effectively infinite."""
        target = classify_url("https://www.youtube.com/watch?v=aircAruvnKk&list=RDaircAruvnKk")
        self.assertEqual(target.kind, "video")

    def test_resolved_identity_wins_over_provisional(self):
        target = classify_url("@3blue1brown")
        self.assertEqual(target.key, "@3blue1brown")
        target.resolved_id = "UCYO_jab_esuFRV4b17AJtAw"
        target.resolved_title = "3Blue1Brown"
        self.assertEqual(target.key, "UCYO_jab_esuFRV4b17AJtAw")
        self.assertEqual(target.label, "3Blue1Brown")

    def test_bare_custom_url_is_a_channel(self):
        """youtube.com/name is the same custom URL as youtube.com/c/name."""
        target = classify_url("https://www.youtube.com/thatmumbojumbo", tabs=("videos",))
        self.assertEqual(target.kind, "channel")
        self.assertEqual(
            target.tab_urls(), ["https://www.youtube.com/thatmumbojumbo/videos"]
        )

    def test_custom_url_spellings_share_one_source_id(self):
        self.assertEqual(
            classify_url("https://www.youtube.com/c/Foo").source_id,
            classify_url("https://www.youtube.com/Foo").source_id,
        )

    def test_dead_vanity_path_falls_back_within_its_namespace(self):
        """YouTube retired many /c/ links while the bare form still resolves."""
        target = classify_url("https://www.youtube.com/c/thatmumbojumbo", tabs=("videos",))
        self.assertEqual(
            target.candidate_bases(),
            [
                "https://www.youtube.com/c/thatmumbojumbo",
                "https://www.youtube.com/thatmumbojumbo",
            ],
        )

    def test_never_guesses_a_handle_for_a_custom_url(self):
        """@name is a different namespace and may be a different channel."""
        for raw in ("https://www.youtube.com/c/foo", "https://www.youtube.com/user/foo"):
            bases = classify_url(raw).candidate_bases()
            self.assertFalse(
                any("@" in base for base in bases), f"{raw} guessed a handle: {bases}"
            )

    def test_canonical_channel_id_url_has_no_fallback(self):
        target = classify_url("https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw")
        self.assertEqual(len(target.candidate_bases()), 1)

    def test_rejects_reserved_youtube_paths(self):
        for raw in (
            "https://www.youtube.com/feed/subscriptions",
            "https://www.youtube.com/results?search_query=x",
            "https://www.youtube.com/account",
        ):
            with self.assertRaises(ValueError, msg=raw):
                classify_url(raw)

    def test_rejects_a_bare_word(self):
        with self.assertRaises(ValueError):
            classify_url("notaurl")

    def test_parse_input_urls_splits_on_whitespace_and_commas(self):
        self.assertEqual(parse_input_urls(" a,b\n c  "), ["a", "b", "c"])

    def test_build_targets_reports_bad_lines_without_dropping_good_ones(self):
        targets, errors = build_targets(
            "https://www.youtube.com/watch?v=aircAruvnKk\nhttps://www.youtube.com/feed/subscriptions",
            IngestOptions(),
        )
        self.assertEqual(len(targets), 1)
        self.assertEqual(len(errors), 1)


class FtsQueryTests(unittest.TestCase):
    def test_bare_words_become_anded_prefixes(self):
        self.assertEqual(build_fts_query("neural network"), '"neural"* "network"*')

    def test_quoted_run_stays_a_phrase(self):
        self.assertEqual(build_fts_query('"neural network" learn'), '"neural network" "learn"*')

    def test_operators_are_searched_literally(self):
        """The search box is not a query language; AND/NEAR are just words."""
        self.assertEqual(build_fts_query("AND NEAR"), '"AND"* "NEAR"*')

    def test_empty_query_rejected(self):
        with self.assertRaises(SearchSyntaxError):
            build_fts_query("   ")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.store = CaptionStore(Path(self._temp.name) / "captions.db")

    def add_video(self, video_id="v1", texts=("hello world",), source_ids=("src1",), **overrides):
        video = {
            "id": video_id,
            "title": f"Title {video_id}",
            "channel": "Channel",
            "channel_id": "UC123",
            "upload_date": "20260101",
            "duration": 100,
            "subtitle_type": "manual",
            "subtitle_language": "en",
            "source_url": f"https://youtu.be/{video_id}",
            "fetched_at": "2026-01-01T00:00:00+00:00",
        }
        video.update(overrides)
        segments = [
            {"start_ms": i * 1000, "end_ms": i * 1000 + 900, "text": text}
            for i, text in enumerate(texts)
        ]
        return self.store.upsert_video(video, segments, source_ids)

    def test_search_finds_and_highlights(self):
        self.add_video(texts=("a neural network intro",))
        result = self.store.search_segments("neural")
        self.assertEqual(result["total"], 1)
        self.assertIn("\x02neural\x03", result["results"][0]["highlight"])

    def test_terms_must_share_a_segment(self):
        self.add_video(texts=("neural nets", "gradient descent"))
        self.assertEqual(self.store.search_segments("neural gradient")["total"], 0)
        self.assertEqual(self.store.search_segments("neural nets")["total"], 1)

    def test_search_can_be_scoped_to_a_source(self):
        self.add_video("v1", ("shared word",), ("src1",))
        self.add_video("v2", ("shared word",), ("src2",))
        self.assertEqual(self.store.search_segments("shared")["total"], 2)
        self.assertEqual(self.store.search_segments("shared", source_id="src1")["total"], 1)

    def test_refetch_replaces_segments_and_reindexes(self):
        self.add_video(texts=("original text",))
        self.add_video(texts=("replacement text",))
        self.assertEqual(self.store.search_segments("original")["total"], 0)
        self.assertEqual(self.store.search_segments("replacement")["total"], 1)

    def test_delete_video_clears_the_index(self):
        self.add_video(texts=("findable",))
        self.store.delete_video("v1")
        self.assertEqual(self.store.search_segments("findable")["total"], 0)

    def test_existing_ids_exclude_videos_without_captions(self):
        """Uploaders add captions later, so those videos stay worth retrying."""
        self.add_video("v1", ("has captions",))
        self.add_video("v2", (), subtitle_type="none")
        self.assertEqual(self.store.get_existing_video_ids(), {"v1"})

    def test_link_videos_to_source_preserves_transcripts(self):
        """Re-syncing must not rewrite caption rows just to add a link."""
        self.add_video("v1", ("keep me indexed",), ("src1",))
        self.store.link_videos_to_source(["v1"], "src2")
        self.assertEqual(self.store.search_segments("indexed", source_id="src2")["total"], 1)
        self.assertEqual(self.store.search_segments("indexed", source_id="src1")["total"], 1)
        self.assertEqual(len(self.store.get_transcript("v1")), 1)

    def test_link_videos_to_source_is_idempotent(self):
        self.add_video("v1", ("text",), ("src1",))
        self.store.link_videos_to_source(["v1"], "src1")
        self.store.upsert_source({"id": "src1", "kind": "channel", "title": "A", "url": ""})
        self.assertEqual(self.store.get_sources()[0]["video_count"], 1)

    def test_source_video_count_is_derived(self):
        self.store.upsert_source({"id": "src1", "kind": "channel", "title": "Chan", "url": "u"})
        self.add_video("v1", ("a",), ("src1",))
        self.add_video("v2", ("b",), ("src1",))
        self.assertEqual(self.store.get_sources()[0]["video_count"], 2)

    def test_delete_source_keeps_videos_shared_with_another_source(self):
        self.store.upsert_source({"id": "src1", "kind": "channel", "title": "A", "url": ""})
        self.store.upsert_source({"id": "src2", "kind": "playlist", "title": "B", "url": ""})
        self.add_video("shared", ("kept",), ("src1", "src2"))
        self.add_video("only1", ("gone",), ("src1",))
        self.store.delete_source("src1", delete_videos=True)
        self.assertEqual({v["id"] for v in self.store.get_videos()}, {"shared"})

    def test_stats(self):
        self.add_video("v1", ("a",))
        self.add_video("v2", (), subtitle_type="none")
        stats = self.store.get_stats()
        self.assertEqual((stats["videos"], stats["manual"], stats["missing"]), (2, 1, 1))

    def test_settings_round_trip(self):
        self.assertEqual(self.store.get_setting("missing", "fallback"), "fallback")
        self.store.set_setting("concurrency", "8")
        self.assertEqual(self.store.get_setting("concurrency"), "8")


class MigrationTests(unittest.TestCase):
    LEGACY_SCHEMA = """
        CREATE TABLE videos (
            id TEXT PRIMARY KEY, title TEXT, channel TEXT, channel_id TEXT,
            upload_date TEXT, subtitle_type TEXT, subtitle_language TEXT,
            source_url TEXT, fetched_at TEXT
        );
        CREATE TABLE transcript_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, video_id TEXT,
            start_ms INTEGER, end_ms INTEGER, text TEXT
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO videos VALUES
            ('old1','Legacy','Chan','UC1','20200101','manual','en','u','t');
        INSERT INTO transcript_segments (video_id, start_ms, end_ms, text)
            VALUES ('old1', 0, 1000, 'legacy caption text');
        INSERT INTO settings VALUES ('cookies_path','C:/cookies.txt');
    """

    def build_legacy_db(self, user_version):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db_path = Path(temp.name) / "old.db"
        legacy = sqlite3.connect(db_path)
        with legacy:
            legacy.executescript(self.LEGACY_SCHEMA)
            legacy.execute(f"PRAGMA user_version = {user_version}")
        legacy.close()
        return db_path

    def test_upgrades_an_unversioned_database(self):
        """Databases from before schema versioning report user_version 0."""
        store = CaptionStore(self.build_legacy_db(0))
        self.assertEqual(store.search_segments("legacy")["total"], 1)
        self.assertEqual(store.get_video("old1")["segment_count"], 1)

    def test_upgrades_a_pre_fts_database(self):
        """The v1 schema had no FTS index, no duration and no segment_count."""
        db_path = self.build_legacy_db(1)
        store = CaptionStore(db_path)

        # Old rows survive and become searchable through the new index.
        self.assertEqual(store.search_segments("legacy")["total"], 1)
        self.assertEqual(store.get_setting("cookies_path"), "C:/cookies.txt")
        video = store.get_video("old1")
        self.assertEqual(video["segment_count"], 1)
        self.assertIn("duration", video)

        # And the upgraded database still accepts writes.
        store.upsert_video(
            {
                "id": "new1",
                "title": "New",
                "channel": "Chan",
                "channel_id": "UC1",
                "upload_date": "20260101",
                "duration": 5,
                "subtitle_type": "auto",
                "subtitle_language": "en",
                "source_url": "u",
                "fetched_at": "t",
            },
            [{"start_ms": 0, "end_ms": 10, "text": "brand new caption"}],
            ["src1"],
        )
        self.assertEqual(store.search_segments("brand")["total"], 1)


class IngestOptionsTests(unittest.TestCase):
    def test_clamps_concurrency_and_drops_unknown_tabs(self):
        options = IngestOptions(concurrency=999, channel_tabs=("videos", "bogus"))
        self.assertEqual(options.concurrency, 16)
        self.assertEqual(options.channel_tabs, ("videos",))

    def test_empty_tab_selection_falls_back_to_all(self):
        self.assertEqual(
            IngestOptions(channel_tabs=()).channel_tabs, ("videos", "shorts", "streams")
        )

    def test_from_dict_accepts_a_comma_separated_language_string(self):
        options = IngestOptions.from_dict({"preferred_languages": "en, ja"})
        self.assertEqual(options.preferred_languages, ["en", "ja"])


if __name__ == "__main__":
    unittest.main()
