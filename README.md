# Caption Search

Youtube caption fetcher + searcher...

## Prereqs

- FFmpeg must be in your PATH
- yt-dlp is downloaded on first run 


You'll need to provide cookies to yt-dlp, see https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
In the app's ui you can browse for a cookies file or grab cookies from a browser

If you use VRCVideoCacher or another program that already stores cookies in this way you can just use that same file

-----

## build from src

- **Python 3.10+**
- **Deno 2.0+**
- **FFmpeg** in PATH

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