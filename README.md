# Transcript Search

YouTube caption fetcher + searcher. Point it at a channel, a playlist, or a
handful of videos; it pulls the captions and gives you full-text search with
timestamped links back to the exact moment.

No YouTube Data API key. No video downloads.

## What it does

- **Whole channels** — paste `youtube.com/@somechannel` and it enumerates the
  Videos, Shorts and Live tabs (pick which ones in Options).
- **Playlists** — paste any playlist URL, or a `watch?v=...&list=...` link.
- **Individual videos** — URLs, `youtu.be` links, or bare video IDs.
- **Manual captions preferred** — uploader-submitted captions win over
  auto-generated ones, but only within your preferred language. An English ASR
  track beats a hand-written Spanish translation when you're searching English,
  which is what popular channels with community translations actually have.
- **Full-text search** — SQLite FTS5 with match highlighting, scoped to
  everything or to one channel/playlist.
- **Refetch** — per video, per source ("check for new uploads"), everything, or
  just the ones that had no captions last time.

## Usage

- yt-dlp is downloaded on first run and update-checked once every 24 hours.
- Cookies are optional. You only need them for age-restricted, members-only, or
  rate-limited fetches — see
  [the yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).
  You can browse for a cookies file or pull them from an installed browser. If
  you use VRCVideoCacher or something similar that already keeps a cookies file,
  point it at that same file.

For Windows grab the build artifact (needs sign-in) or the latest release.

For macOS/Linux build it yourself, it's simple.

## How it fetches

Two things make a channel-sized fetch fast enough to sit through:

1. **One yt-dlp call per batch, not per video.** yt-dlp costs ~2.5s for the
   first URL in an invocation but only ~0.5s for each one after, because it
   reuses its HTTP session. URLs go in batches, and batches run in parallel.
2. **One round trip per video.** The info JSON already contains a direct signed
   URL for every caption track, so the captions are fetched over plain HTTP
   instead of paying for a second yt-dlp invocation. Media is never downloaded.

Captions are parsed from YouTube's native `json3` timedtext format rather than
WebVTT. Auto-generated VTT is served as an overlapping rolling window that
duplicates every line two or three times; `json3` has clean event boundaries, so
search hits do not come back triplicated.

Roughly: a 150-video channel takes about a minute, versus about 13 minutes for
the same work done serially at two yt-dlp calls per video.

## Stack

Python + Svelte, and it should stay that way.

The interesting question is whether the Python half earns its keep, since the
frontend is just a webview. It does — because yt-dlp *is* the product, and yt-dlp
is Python. Any other runtime talks to it as a subprocess exactly the way this
does, so a rewrite buys nothing and gives up the option of importing it in-process
later. The parts that were actually slow were architectural (two subprocess spawns
per video, serial execution, `LIKE '%term%'` over every caption row), not the
language.

yt-dlp stays a runtime-downloaded binary rather than a bundled dependency on
purpose: YouTube breaks extractors often enough that a pinned copy goes stale in
weeks, and self-updating a binary beats rebuilding and redistributing the app.

- `ytdlp_url.py` — URL classification (no network, no subprocess)
- `captions.py` — track selection and `json3`/WebVTT parsing
- `store.py` — SQLite + FTS5, schema migrations
- `ingest.py` — enumeration, batching, concurrency, cancellation
- `backend.py` — the pywebview JS bridge and job manager
- `src/` — Svelte 5 UI

## Build from source

- **Python 3.10+**
- **Deno 2.0+**

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Build the UI:
   ```
   deno task build
   ```

3. Run the app:
   ```
   python app.py
   ```

Run the tests (offline — no network, no yt-dlp, no webview):

```
python -m unittest discover -s tests
```

Set `CAPTION_SEARCH_YTDLP` to point at an existing yt-dlp binary if you don't
want the app managing its own copy.

latest webslop made for myself!

And if u dont need it... go do something else what are u even doing here? lmao
