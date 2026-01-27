<script>
  import CookiesPanel from './components/CookiesPanel.svelte';
  import TranscriptPanel from './components/TranscriptPanel.svelte';
  import SearchPanel from './components/SearchPanel.svelte';
  import VideoListPanel from './components/VideoListPanel.svelte';
  import { apiClient } from './services/api.js';
  import { FileText, Sun, Moon, X } from 'lucide-svelte';

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
  let selectedVideoTitle = $state('');
  let transcriptSidebarOpen = $state(false);
  let darkMode = $state(true);
  let confirmModalOpen = $state(false);

  $effect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  });

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
    const video = videos.find(v => v.id === videoId);
    selectedVideoTitle = video?.title || videoId;
    transcriptSidebarOpen = true;
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
    confirmModalOpen = false;
    const response = await apiClient.safe(() => apiClient.deleteAllVideos());
    if (!response.ok) {
      setStatus(response.error || 'Failed to delete videos', true);
      return;
    }
    transcript = [];
    selectedVideoId = '';
    selectedVideoTitle = '';
    searchResults = [];
    transcriptSidebarOpen = false;
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
  <!-- Left Sidebar: Library (always visible) -->
  <aside class="sidebar left">
    <div class="sidebar-header">
      <span class="sidebar-title">Library</span>
    </div>
    <div class="sidebar-content">
      <div class="ingest-section">
        <textarea
          bind:value={urlsInput}
          placeholder="Paste YouTube URLs or playlist links..."
          rows="2"
        ></textarea>
        <CookiesPanel
          {cookiesPath}
          {cookiesBrowser}
          onchange={handleCookiesChange}
          onbrowse={handleBrowseRequest}
        />
        <button class="primary" onclick={ingestUrls}>Fetch subtitles</button>
      </div>
      <VideoListPanel
        {videos}
        {missing}
        onselect={(event) => loadTranscript(event.detail)}
        ondelete={(event) => deleteVideo(event.detail)}
        ondeleteAll={() => confirmModalOpen = true}
      />
    </div>
    {#if status}
      <div class="sidebar-footer" class:error={statusError}>{status}</div>
    {/if}
  </aside>

  <!-- Main Content -->
  <main class="main">
    <div class="top-bar">
      <div class="top-bar-right">
        <button class="icon-btn" class:active={transcriptSidebarOpen} title="Transcript" onclick={() => transcriptSidebarOpen = !transcriptSidebarOpen}>
          <FileText size={18} />
        </button>
        <button class="icon-btn" title={darkMode ? 'Light mode' : 'Dark mode'} onclick={() => darkMode = !darkMode}>
          {#if darkMode}
            <Sun size={18} />
          {:else}
            <Moon size={18} />
          {/if}
        </button>
      </div>
    </div>

    <section class="hero">
      <h1>Caption Search</h1>
      <SearchPanel {searchResults} onsearch={(event) => searchTranscripts(event.detail)} />
    </section>
  </main>

  <!-- Right Sidebar: Transcript -->
  <aside class="sidebar right" class:open={transcriptSidebarOpen}>
    <div class="sidebar-header">
      <span class="sidebar-title" title={selectedVideoTitle}>{selectedVideoTitle || 'Transcript'}</span>
      <button class="icon-btn-sm" aria-label="Close transcript" onclick={() => transcriptSidebarOpen = false}>
        <X size={16} />
      </button>
    </div>
    <div class="sidebar-content">
      <TranscriptPanel {transcript} videoId={selectedVideoId} />
    </div>
  </aside>

  <!-- Confirmation Modal -->
  {#if confirmModalOpen}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1" onclick={() => confirmModalOpen = false} onkeydown={(e) => e.key === 'Escape' && (confirmModalOpen = false)}>
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <div class="modal" role="document" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
        <h3 id="modal-title">Clear all videos?</h3>
        <p>This will remove all {videos.length} videos and their transcripts. This cannot be undone.</p>
        <div class="modal-actions">
          <button class="secondary" onclick={() => confirmModalOpen = false}>Cancel</button>
          <button class="danger" onclick={deleteAllVideos}>Clear all</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  :global(:root) {
    --bg-base: #0a0c0f;
    --bg-elevated: #12151a;
    --bg-panel: #12151a;
    --bg-input: #12151a;
    --bg-sidebar: #0d0f13;
    --border: #1f242d;
    --border-input: #252a35;
    --text: #f2f2f2;
    --text-muted: #6b7280;
    --text-secondary: #9ca3af;
    --accent: #3b6cff;
    --accent-hover: #2d5bef;
    --error: #ff8a8a;
    --scrollbar-track: transparent;
    --scrollbar-thumb: #3a3f4a;
    --scrollbar-thumb-hover: #4a5060;
    --sidebar-width: 360px;
  }

  :global([data-theme="light"]) {
    --bg-base: #f5f5f7;
    --bg-elevated: #ffffff;
    --bg-panel: #ffffff;
    --bg-input: #f0f0f2;
    --bg-sidebar: #ffffff;
    --border: #d1d5db;
    --border-input: #c5c9d0;
    --text: #1f2937;
    --text-muted: #6b7280;
    --text-secondary: #4b5563;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --error: #dc2626;
    --scrollbar-track: transparent;
    --scrollbar-thumb: #c5c9d0;
    --scrollbar-thumb-hover: #9ca3af;
  }

  :global(body) {
    margin: 0;
    font-family: "Segoe UI", system-ui, sans-serif;
    background: var(--bg-base);
    color: var(--text);
  }

  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(*::-webkit-scrollbar) {
    width: 8px;
    height: 8px;
  }

  :global(*::-webkit-scrollbar-track) {
    background: var(--scrollbar-track);
  }

  :global(*::-webkit-scrollbar-thumb) {
    background: var(--scrollbar-thumb);
    border-radius: 4px;
  }

  :global(*::-webkit-scrollbar-thumb:hover) {
    background: var(--scrollbar-thumb-hover);
  }

  .app {
    height: 100vh;
    display: flex;
    overflow: hidden;
  }

  /* Sidebars */
  .sidebar {
    width: var(--sidebar-width);
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .sidebar.left {
    position: relative;
  }

  .sidebar.right {
    position: fixed;
    top: 0;
    bottom: 0;
    right: 0;
    border-right: none;
    border-left: 1px solid var(--border);
    transform: translateX(100%);
    transition: transform 0.2s ease;
    z-index: 20;
  }

  .sidebar.right.open {
    transform: translateX(0);
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .sidebar-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .sidebar-footer {
    padding: 10px 16px;
    font-size: 12px;
    color: var(--text-secondary);
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }

  .sidebar-footer.error {
    color: var(--error);
  }

  .ingest-section {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .ingest-section textarea {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 10px 12px;
    border-radius: 8px;
    resize: none;
    font-size: 13px;
    line-height: 1.4;
  }

  .ingest-section textarea::placeholder {
    color: var(--text-muted);
  }

  /* Main content */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    position: relative;
  }

  .top-bar {
    position: absolute;
    top: 12px;
    right: 16px;
    display: flex;
    justify-content: flex-end;
    z-index: 10;
  }

  .top-bar-right {
    display: flex;
    gap: 8px;
  }

  .icon-btn {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .icon-btn:hover {
    color: var(--text);
    border-color: var(--border-input);
  }

  .icon-btn.active {
    color: var(--accent);
    border-color: var(--accent);
  }

  .icon-btn-sm {
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 4px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .icon-btn-sm:hover {
    color: var(--text);
    background: var(--border);
  }

  .hero {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding: 80px 24px 32px;
    overflow: hidden;
  }

  .hero h1 {
    font-size: 28px;
    font-weight: 600;
    margin: 0 0 24px;
    color: var(--text);
    letter-spacing: -0.5px;
    flex-shrink: 0;
  }

  .hero :global(.search-panel) {
    width: 100%;
    max-width: 700px;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  /* Buttons */
  .primary {
    background: var(--accent);
    border: none;
    color: white;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
  }

  .primary:hover {
    background: var(--accent-hover);
  }

  .secondary {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
  }

  .secondary:hover {
    background: var(--border);
  }

  .danger {
    background: #dc2626;
    border: none;
    color: white;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
  }

  .danger:hover {
    background: #b91c1c;
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .modal {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    max-width: 400px;
    width: 90%;
  }

  .modal h3 {
    margin: 0 0 12px;
    font-size: 16px;
    color: var(--text);
  }

  .modal p {
    margin: 0 0 20px;
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .modal-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }

  @media (max-width: 600px) {
    .sidebar {
      width: 100%;
    }
  }
</style>
