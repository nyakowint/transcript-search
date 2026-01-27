# Transcript Search

Youtube captions/transcript fetcher + searcher...

## Usage

- yt-dlp gets downloaded on first run & update checked if 24hrs have passed since last run
- You will need to provide cookies to yt-dlp, see https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
  - You can browse for a cookies file or grab cookies from a browser
  - If you use VRCVideoCacher or another program that already stores cookies in this way you can just use that same file

-----

For windows grab the build artifact (need to be signed in) or the latest release

For macos/linux you should build it yourself lol its simple

## build from src

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

latest webslop made for myself! 

And if u dont need it... go do something else what are u even doing here? lmao