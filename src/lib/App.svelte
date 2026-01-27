<script>
  import CookiesPanel from './components/CookiesPanel.svelte';
  import TranscriptPanel from './components/TranscriptPanel.svelte';
  import SearchPanel from './components/SearchPanel.svelte';
  import VideoListPanel from './components/VideoListPanel.svelte';
  import { apiClient } from './services/api.js';

  let status = $state('');
  let statusError = $state(false);
  let urlsInput = $state('');
  let cookiesPath = $state('');
  let cookiesBrowser = $state('');
  let videos = $state([]);
  let missing = $state([]);
  let transcript = $state([]);
  let searchResults = $state([]);
  let selectedVideoId = $state('');

  function setStatus(message, isError = false) {
    status = message;
    statusError = isError;
  }

  async function refreshLists() {
    const videoResponse = await apiClient.safe(() => apiClient.getVideos());
    if (videoResponse.ok) {
      videos = videoResponse.videos;
    }
    const missingResponse = await apiClient.safe(() => apiClient.getMissing());
    if (missingResponse.ok) {
      missing = missingResponse.videos;
    }
  }

  async function loadTranscript(videoId) {
    const response = await apiClient.safe(() => apiClient.getTranscript(videoId));
    if (!response.ok) {
      setStatus(response.error || 'Failed to load transcript', true);
      return;
    }
    transcript = response.segments;
    selectedVideoId = videoId;
  }

  async function deleteVideo(videoId) {
    const response = await apiClient.safe(() => apiClient.deleteVideo(videoId));
    if (!response.ok) {
      setStatus(response.error || 'Failed to delete video', true);
      return;
    }
    if (selectedVideoId === videoId) {
      transcript = [];
      selectedVideoId = '';
    }
    await refreshLists();
    setStatus('Video removed.');
  }

  async function deleteAllVideos() {
    const response = await apiClient.safe(() => apiClient.deleteAllVideos());
    if (!response.ok) {
      setStatus(response.error || 'Failed to delete videos', true);
      return;
    }
    transcript = [];
    selectedVideoId = '';
    searchResults = [];
    await refreshLists();
    setStatus('All videos removed.');
  }

  async function ingestUrls() {
    if (!urlsInput.trim()) {
      setStatus('Enter at least one URL.', true);
      return;
    }
    setStatus('Fetching subtitles...');
    const response = await apiClient.safe(() =>
      apiClient.ingestUrls(urlsInput, cookiesPath, cookiesBrowser)
    );
    if (!response.ok) {
      setStatus(response.error || 'Failed to ingest URLs', true);
      return;
    }
    if (response.errors?.length) {
      setStatus(`Completed with ${response.errors.length} errors.`, true);
    } else {
      setStatus(`Processed ${response.processed.length} videos.`);
    }
    await refreshLists();
  }

  async function searchTranscripts(query) {
    if (!query.trim()) {
      setStatus('Enter a search phrase.', true);
      return;
    }
    const response = await apiClient.safe(() => apiClient.searchTranscripts(query));
    if (!response.ok) {
      setStatus(response.error || 'Search failed', true);
      return;
    }
    searchResults = response.results;
  }

  async function handleCookiesChange(event) {
    cookiesPath = event.detail.cookiesPath;
    cookiesBrowser = event.detail.cookiesBrowser;
    await apiClient.safe(() => apiClient.saveSettings(cookiesPath, cookiesBrowser));
  }

  async function handleBrowseRequest() {
    const response = await apiClient.safe(() => apiClient.selectCookiesFile());
    if (!response.ok) {
      setStatus(response.error || 'Failed to select cookies file.', true);
      return;
    }
    if (response.path) {
      cookiesPath = response.path;
      await apiClient.safe(() => apiClient.saveSettings(cookiesPath, cookiesBrowser));
    }
  }

  async function init() {
    const response = await apiClient.safe(() => apiClient.getSettings());
    if (response.ok) {
      cookiesPath = response.settings.cookies_path || '';
      cookiesBrowser = response.settings.cookies_browser || '';
    }
    await refreshLists();
  }

  apiClient.onReady(init);
</script>

<div class="app">
  <header>
    <div>
      <h1>Caption Search</h1>
      <p>Fetch and search YouTube transcripts for editing.</p>
    </div>
    <div class="status" class:error={statusError}>{status}</div>
  </header>

  <section class="panel">
    <div class="panel-header">
      <h2>Ingest videos or playlists</h2>
      <button class="primary" on:click={ingestUrls}>Fetch subtitles</button>
    </div>
    <textarea
      bind:value={urlsInput}
      placeholder="Paste YouTube video URLs or playlist URLs (separate with spaces or new lines)."
    ></textarea>
    <CookiesPanel
      {cookiesPath}
      {cookiesBrowser}
      on:change={handleCookiesChange}
      on:browse={handleBrowseRequest}
    />
  </section>

  <section class="grid">
    <VideoListPanel
      {videos}
      {missing}
      on:select={(event) => loadTranscript(event.detail)}
      on:delete={(event) => deleteVideo(event.detail)}
      on:deleteAll={deleteAllVideos}
    />
    <div class="stack">
      <TranscriptPanel {transcript} videoId={selectedVideoId} />
      <SearchPanel {searchResults} on:search={(event) => searchTranscripts(event.detail)} />
    </div>
  </section>
</div>

<style>
  :global(body) {
    margin: 0;
    font-family: "Segoe UI", system-ui, sans-serif;
    background: #0f1115;
    color: #f2f2f2;
  }

  .app {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  header p {
    margin: 4px 0 0;
    color: #b5b9c5;
  }

  .status {
    font-size: 14px;
    color: #cfd4e6;
  }

  .status.error {
    color: #ff8a8a;
  }

  .panel {
    background: #171a21;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    display: grid;
    gap: 12px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  textarea {
    width: 100%;
    min-height: 120px;
    background: #0f1115;
    border: 1px solid #2a2f3a;
    color: #f2f2f2;
    padding: 12px;
    border-radius: 8px;
    resize: vertical;
  }

  .primary {
    background: #4c7dff;
    border: none;
    color: white;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
  }

  .primary:hover {
    background: #3d6af0;
  }

  .grid {
    display: grid;
    grid-template-columns: 1fr 1.4fr;
    gap: 16px;
  }

  .stack {
    display: grid;
    gap: 16px;
  }

  @media (max-width: 960px) {
    header {
      flex-direction: column;
      align-items: flex-start;
    }

    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
