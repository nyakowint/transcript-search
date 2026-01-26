const statusEl = document.getElementById("status");
const videoList = document.getElementById("video-list");
const missingList = document.getElementById("missing-list");
const transcriptEl = document.getElementById("transcript");
const searchResultsEl = document.getElementById("search-results");
const cookiesPathInput = document.getElementById("cookies-path");
const cookiesBrowserSelect = document.getElementById("cookies-browser");
const cookiesBrowseButton = document.getElementById("cookies-browse");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "status error" : "status";
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const padded = (value) => String(value).padStart(2, "0");
  if (hours > 0) {
    return `${hours}:${padded(minutes)}:${padded(seconds)}`;
  }
  return `${minutes}:${padded(seconds)}`;
}

function renderList(container, items, emptyMessage) {
  container.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = emptyMessage;
    li.className = "empty";
    container.appendChild(li);
    return;
  }
  items.forEach((item) => container.appendChild(item));
}

function getApi() {
  return window.pywebview?.api;
}

async function refreshVideos() {
  const api = getApi();
  if (!api) {
    return;
  }
  const response = await api.get_videos();
  if (!response.ok) {
    setStatus(response.error || "Failed to load videos", true);
    return;
  }
  const items = response.videos.map((video) => {
    const li = document.createElement("li");
    li.className = "video-item";
    li.textContent = `${video.title || video.id} · ${video.channel || "Unknown"} (${video.subtitle_type})`;
    li.addEventListener("click", () => loadTranscript(video.id));
    return li;
  });
  renderList(videoList, items, "No videos loaded yet.");
}

async function refreshMissing() {
  const api = getApi();
  if (!api) {
    return;
  }
  const response = await api.get_missing_subtitles();
  if (!response.ok) {
    setStatus(response.error || "Failed to load missing subtitles", true);
    return;
  }
  const items = response.videos.map((video) => {
    const li = document.createElement("li");
    li.textContent = `${video.title || video.id} · ${video.channel || "Unknown"}`;
    return li;
  });
  renderList(missingList, items, "All videos have subtitles.");
}

async function loadTranscript(videoId) {
  const api = getApi();
  if (!api) {
    return;
  }
  const response = await api.get_transcript(videoId);
  if (!response.ok) {
    setStatus(response.error || "Failed to load transcript", true);
    return;
  }
  transcriptEl.innerHTML = "";
  if (!response.segments.length) {
    transcriptEl.textContent = "No transcript loaded.";
    return;
  }
  response.segments.forEach((segment) => {
    const row = document.createElement("div");
    row.className = "segment";
    row.innerHTML = `<span class="time">${formatTime(segment.start_ms)}</span><span>${segment.text}</span>`;
    transcriptEl.appendChild(row);
  });
}

async function ingestUrls() {
  const input = document.getElementById("url-input").value;
  if (!input.trim()) {
    setStatus("Enter at least one URL.", true);
    return;
  }
  const api = getApi();
  if (!api) {
    setStatus("App is not ready yet.", true);
    return;
  }
  setStatus("Fetching subtitles...");
  const response = await api.ingest_urls(
    input,
    cookiesPathInput.value,
    cookiesBrowserSelect.value
  );
  if (!response.ok) {
    setStatus(response.error || "Failed to ingest URLs", true);
    return;
  }
  if (response.errors && response.errors.length) {
    setStatus(`Completed with ${response.errors.length} errors.`, true);
  } else {
    setStatus(`Processed ${response.processed.length} videos.`);
  }
  await refreshVideos();
  await refreshMissing();
}

async function searchTranscripts() {
  const query = document.getElementById("search-input").value.trim();
  if (!query) {
    setStatus("Enter a search phrase.", true);
    return;
  }
  const api = getApi();
  if (!api) {
    setStatus("App is not ready yet.", true);
    return;
  }
  const response = await api.search_transcripts(query);
  if (!response.ok) {
    setStatus(response.error || "Search failed", true);
    return;
  }
  searchResultsEl.innerHTML = "";
  if (!response.results.length) {
    searchResultsEl.textContent = "No matches found.";
    return;
  }
  response.results.forEach((result) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.innerHTML = `
      <div class="result-meta">${result.title || result.video_id} · ${result.channel || "Unknown"}</div>
      <div class="result-text"><span class="time">${formatTime(result.start_ms)}</span>${result.text}</div>
    `;
    searchResultsEl.appendChild(card);
  });
}

async function loadSettings() {
  const api = getApi();
  if (!api) {
    return;
  }
  const response = await api.get_settings();
  if (!response.ok) {
    return;
  }
  const settings = response.settings || {};
  if (settings.cookies_path) {
    cookiesPathInput.value = settings.cookies_path;
  }
  if (settings.cookies_browser) {
    cookiesBrowserSelect.value = settings.cookies_browser;
  }
}

async function saveSettings() {
  const api = getApi();
  if (!api) {
    return;
  }
  await api.save_settings(cookiesPathInput.value, cookiesBrowserSelect.value);
}

function initApp() {
  document.getElementById("ingest-button").addEventListener("click", ingestUrls);
  document.getElementById("search-button").addEventListener("click", searchTranscripts);
  cookiesBrowseButton.addEventListener("click", async () => {
    const api = getApi();
    if (!api) {
      setStatus("App is not ready yet.", true);
      return;
    }
    const response = await api.select_cookies_file();
    if (!response.ok) {
      setStatus(response.error || "Failed to select cookies file.", true);
      return;
    }
    if (response.path) {
      cookiesPathInput.value = response.path;
      await saveSettings();
    }
  });
  cookiesPathInput.addEventListener("change", saveSettings);
  cookiesBrowserSelect.addEventListener("change", saveSettings);
  loadSettings().then(() => {
    refreshVideos();
    refreshMissing();
  });
}

if (window.pywebview) {
  initApp();
} else {
  window.addEventListener("pywebviewready", initApp);
}
