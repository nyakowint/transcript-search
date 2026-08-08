export function formatTime(ms) {
  const totalSeconds = Math.floor((ms || 0) / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (value) => String(value).padStart(2, '0');
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(seconds)}`
    : `${minutes}:${pad(seconds)}`;
}

export function formatDuration(totalSeconds) {
  if (!totalSeconds) return '';
  return formatTime(totalSeconds * 1000);
}

/** yt-dlp reports upload dates as YYYYMMDD. */
export function formatUploadDate(raw) {
  if (!raw || raw.length !== 8) return '';
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
}

export function timestampUrl(videoId, ms) {
  return `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor((ms || 0) / 1000)}s`;
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // The embedded webview denies clipboard access in some configurations.
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.select();
    const copied = document.execCommand('copy');
    document.body.removeChild(textArea);
    return copied;
  }
}

// SQLite's highlight() wraps matches in these sentinels instead of markup, so
// matched text stays data and never has to be trusted as HTML.
const MARK_OPEN = String.fromCharCode(2);
const MARK_CLOSE = String.fromCharCode(3);
const MARK_RE = new RegExp(`${MARK_OPEN}([^${MARK_CLOSE}]*)${MARK_CLOSE}`, 'g');

/** Split an FTS5 highlight string into alternating plain and matched runs. */
export function splitHighlights(highlight, fallback = '') {
  const source = highlight || fallback || '';
  if (!source.includes(MARK_OPEN)) return [{ text: source, match: false }];

  const parts = [];
  let cursor = 0;
  MARK_RE.lastIndex = 0;
  let match;
  while ((match = MARK_RE.exec(source)) !== null) {
    if (match.index > cursor) {
      parts.push({ text: source.slice(cursor, match.index), match: false });
    }
    parts.push({ text: match[1], match: true });
    cursor = MARK_RE.lastIndex;
  }
  if (cursor < source.length) {
    parts.push({ text: source.slice(cursor), match: false });
  }
  return parts;
}
