<script>
  import CookiesPanel from './components/CookiesPanel.svelte';
  import IngestPanel from './components/IngestPanel.svelte';
  import JobProgress from './components/JobProgress.svelte';
  import SearchPanel from './components/SearchPanel.svelte';
  import SourcesPanel from './components/SourcesPanel.svelte';
  import TranscriptPanel from './components/TranscriptPanel.svelte';
  import VideoListPanel from './components/VideoListPanel.svelte';
  import { apiClient, onBackendEvent } from './services/api.js';
  import { FileText, Sun, Moon, X, Settings } from 'lucide-svelte';

  let status = $state('');
  let statusError = $state(false);
  let settings = $state({});
  let sources = $state([]);
  let videos = $state([]);
  let missing = $state([]);
  let stats = $state({});
  let activeSourceId = $state('');

  let transcript = $state([]);
  let selectedVideo = $state(null);
  let selectedVideoId = $state('');
  let transcriptOpen = $state(false);

  let searchResults = $state([]);
  let searchTotal = $state(0);
  let searchTruncated = $state(false);
  let searching = $state(false);
  let lastQuery = $state('');

  let job = $state(null);
  let ytdlpStatus = $state('');
  let darkMode = $state(true);
  let settingsOpen = $state(false);
  let confirmModal = $state(null);

  const busy = $derived(job?.status === 'running');
  const activeSource = $derived(sources.find((source) => source.id === activeSourceId));
  const scopeLabel = $derived(activeSource ? activeSource.title || activeSource.id : 'everything');
  const hasContent = $derived((stats.segments || 0) > 0);

  $effect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  });

  function setStatus(message, isError = false) {
    status = message;
    statusError = isError;
  }

  // ---------------------------------------------------------------- data load

  async function refreshLists() {
    const [videoResponse, sourceResponse, missingResponse, statsResponse] = await Promise.all([
      apiClient.getVideos(activeSourceId),
      apiClient.getSources(),
      apiClient.getMissing(),
      apiClient.getStats(),
    ]);
    if (videoResponse.ok) videos = videoResponse.videos;
    if (sourceResponse.ok) sources = sourceResponse.sources;
    if (missingResponse.ok) missing = missingResponse.videos;
    if (statsResponse.ok) stats = statsResponse.stats;
  }

  async function selectSource(sourceId) {
    activeSourceId = sourceId;
    await refreshLists();
    if (lastQuery) await runSearch(lastQuery);
  }

  // ------------------------------------------------------------------ ingest

  async function handleFetch(input) {
    const response = await apiClient.startIngest(input);
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    job = response.job;
    setStatus('');
  }

  async function handleSync(sourceId, force) {
    const response = await apiClient.syncSource(sourceId, force);
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    job = response.job;
  }

  async function handleRefetch(videoId) {
    const response = await apiClient.refetchVideos([videoId]);
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    job = response.job;
  }

  function confirmRefetchAll() {
    confirmModal = {
      title: `Refetch all ${videos.length} videos?`,
      body: 'Captions are downloaded again and existing transcripts are replaced. Nothing is deleted if a fetch fails.',
      confirmLabel: 'Refetch all',
      danger: false,
      action: async () => {
        const response = await apiClient.refetchAll('all');
        if (!response.ok) setStatus(response.error, true);
        else job = response.job;
      },
    };
  }

  async function retryMissing() {
    const response = await apiClient.refetchAll('missing');
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    job = response.job;
  }

  async function cancelJob() {
    await apiClient.cancelJob(job?.id || '');
  }

  // ------------------------------------------------------------------ search

  async function runSearch(query) {
    lastQuery = query;
    if (!query.trim()) {
      searchResults = [];
      searchTotal = 0;
      searchTruncated = false;
      return;
    }
    searching = true;
    const response = await apiClient.searchTranscripts(query, { sourceId: activeSourceId });
    searching = false;
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    searchResults = response.results;
    searchTotal = response.total;
    searchTruncated = response.truncated;
  }

  // -------------------------------------------------------------- transcript

  async function loadTranscript(videoId) {
    const response = await apiClient.getTranscript(videoId);
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    transcript = response.segments;
    selectedVideo = response.video;
    selectedVideoId = videoId;
    transcriptOpen = true;
  }

  // ------------------------------------------------------------------ delete

  async function deleteVideo(videoId) {
    const response = await apiClient.deleteVideo(videoId);
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    if (selectedVideoId === videoId) {
      transcript = [];
      selectedVideoId = '';
      selectedVideo = null;
    }
    await refreshLists();
    if (lastQuery) await runSearch(lastQuery);
  }

  function confirmDeleteAll() {
    confirmModal = {
      title: 'Clear the whole library?',
      body: `This removes all ${stats.videos || 0} videos, ${stats.sources || 0} sources, and their transcripts. It cannot be undone.`,
      confirmLabel: 'Clear everything',
      danger: true,
      action: async () => {
        await apiClient.deleteAllVideos();
        transcript = [];
        selectedVideoId = '';
        selectedVideo = null;
        searchResults = [];
        searchTotal = 0;
        activeSourceId = '';
        transcriptOpen = false;
        await refreshLists();
        setStatus('Library cleared.');
      },
    };
  }

  function confirmDeleteSource(source) {
    confirmModal = {
      title: `Remove ${source.title || source.id}?`,
      body: `Also delete the ${source.video_count} videos that came from it? Videos that also belong to another source are kept either way.`,
      confirmLabel: 'Remove source only',
      extraLabel: 'Remove source and videos',
      danger: true,
      action: async () => {
        await apiClient.deleteSource(source.id, false);
        if (activeSourceId === source.id) activeSourceId = '';
        await refreshLists();
      },
      extraAction: async () => {
        await apiClient.deleteSource(source.id, true);
        if (activeSourceId === source.id) activeSourceId = '';
        await refreshLists();
        if (lastQuery) await runSearch(lastQuery);
      },
    };
  }

  async function runConfirm(which) {
    const modal = confirmModal;
    confirmModal = null;
    if (!modal) return;
    await (which === 'extra' ? modal.extraAction?.() : modal.action?.());
  }

  // ---------------------------------------------------------------- settings

  async function updateSettings(patch) {
    const response = await apiClient.saveSettings(patch);
    if (response.ok) settings = response.settings;
  }

  async function browseCookies() {
    const response = await apiClient.selectCookiesFile();
    if (!response.ok) {
      setStatus(response.error, true);
      return;
    }
    if (response.path) await updateSettings({ cookies_path: response.path });
  }

  // -------------------------------------------------------------- lifecycle

  onBackendEvent((event) => {
    if (event.type === 'job') {
      job = event.job;
      if (event.job.status !== 'running') {
        refreshLists().then(() => lastQuery && runSearch(lastQuery));
      }
    } else if (event.type === 'ytdlp') {
      ytdlpStatus = event.message || '';
      if (event.error) setStatus(event.message, true);
    }
  });

  async function init() {
    const response = await apiClient.getSettings();
    if (response.ok) settings = response.settings;
    await refreshLists();
    // A job can outlive a page reload; pick it back up.
    const jobResponse = await apiClient.getJob();
    if (jobResponse.ok && jobResponse.job) job = jobResponse.job;
  }

  apiClient.onReady(init);
</script>

<div class="app">
  <aside class="sidebar left">
    <div class="sidebar-header">
      <span class="sidebar-title">Library</span>
      <button
        class="icon-btn-sm"
        title="Settings"
        aria-label="Settings"
        onclick={() => (settingsOpen = !settingsOpen)}
      >
        <Settings size={15} />
      </button>
    </div>

    <div class="sidebar-content">
      <IngestPanel
        {settings}
        {busy}
        onfetch={handleFetch}
        onsettingchange={updateSettings}
      />

      {#if settingsOpen}
        <div class="settings-block">
          <CookiesPanel
            cookiesPath={settings.cookies_path || ''}
            cookiesBrowser={settings.cookies_browser || ''}
            onchange={updateSettings}
            onbrowse={browseCookies}
          />
        </div>
      {/if}

      {#if job}
        <JobProgress {job} oncancel={cancelJob} />
      {/if}

      <SourcesPanel
        {sources}
        {activeSourceId}
        {busy}
        onselect={selectSource}
        onsync={handleSync}
        ondelete={confirmDeleteSource}
      />

      <VideoListPanel
        {videos}
        {missing}
        {selectedVideoId}
        {busy}
        onselect={loadTranscript}
        ondelete={deleteVideo}
        onrefetch={handleRefetch}
        ondeleteAll={confirmDeleteAll}
        onrefetchAll={confirmRefetchAll}
        onretryMissing={retryMissing}
      />
    </div>

    {#if status || ytdlpStatus}
      <div class="sidebar-footer" class:error={statusError}>{status || ytdlpStatus}</div>
    {/if}
  </aside>

  <main class="main">
    <div class="top-bar">
      <button
        class="icon-btn"
        class:active={transcriptOpen}
        title="Transcript"
        aria-label="Toggle transcript"
        onclick={() => (transcriptOpen = !transcriptOpen)}
      >
        <FileText size={18} />
      </button>
      <button
        class="icon-btn"
        title={darkMode ? 'Light mode' : 'Dark mode'}
        aria-label="Toggle theme"
        onclick={() => (darkMode = !darkMode)}
      >
        {#if darkMode}<Sun size={18} />{:else}<Moon size={18} />{/if}
      </button>
    </div>

    <section class="hero">
      <div class="hero-head">
        <h1>Transcript Search</h1>
        {#if hasContent}
          <p class="subtitle">
            {stats.videos} videos · {stats.segments.toLocaleString()} lines
            {#if stats.missing}· {stats.missing} without captions{/if}
          </p>
        {/if}
      </div>
      <SearchPanel
        results={searchResults}
        total={searchTotal}
        truncated={searchTruncated}
        {searching}
        {scopeLabel}
        {hasContent}
        query={lastQuery}
        onsearch={runSearch}
        onopenVideo={loadTranscript}
      />
    </section>
  </main>

  <aside class="sidebar right" class:open={transcriptOpen}>
    <div class="sidebar-header">
      <span class="sidebar-title" title={selectedVideo?.title || ''}>
        {selectedVideo?.title || 'Transcript'}
      </span>
      <button class="icon-btn-sm" aria-label="Close transcript" onclick={() => (transcriptOpen = false)}>
        <X size={16} />
      </button>
    </div>
    <div class="sidebar-content">
      <TranscriptPanel {transcript} video={selectedVideo} videoId={selectedVideoId} />
    </div>
  </aside>

  {#if confirmModal}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      tabindex="-1"
      onclick={() => (confirmModal = null)}
      onkeydown={(event) => event.key === 'Escape' && (confirmModal = null)}
    >
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="modal" onclick={(event) => event.stopPropagation()} onkeydown={(event) => event.stopPropagation()}>
        <h3 id="modal-title">{confirmModal.title}</h3>
        <p>{confirmModal.body}</p>
        <div class="modal-actions">
          <button class="secondary" onclick={() => (confirmModal = null)}>Cancel</button>
          {#if confirmModal.extraLabel}
            <button class="danger" onclick={() => runConfirm('extra')}>{confirmModal.extraLabel}</button>
          {/if}
          <button class={confirmModal.danger ? 'danger' : 'primary'} onclick={() => runConfirm('main')}>
            {confirmModal.confirmLabel}
          </button>
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
    --accent-subtle: #17203a;
    --success: #4ade80;
    --success-subtle: #14301f;
    --error: #ff8a8a;
    --error-subtle: #3a1c1c;
    --mark-bg: #3b6cff;
    --mark-text: #ffffff;
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
    --border: #e3e5e9;
    --border-input: #c5c9d0;
    --text: #1f2937;
    --text-muted: #6b7280;
    --text-secondary: #4b5563;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --accent-subtle: #e6edfd;
    --success: #15803d;
    --success-subtle: #dcfce7;
    --error: #dc2626;
    --error-subtle: #fee2e2;
    --mark-bg: #fde68a;
    --mark-text: #1f2937;
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
    background: transparent;
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

  .sidebar {
    width: var(--sidebar-width);
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
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
    gap: 8px;
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
    min-height: 0;
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

  .settings-block {
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
  }

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
    gap: 8px;
    z-index: 10;
  }

  .icon-btn {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
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
    flex-shrink: 0;
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
    padding: 72px 24px 28px;
    overflow: hidden;
  }

  .hero-head {
    text-align: center;
    flex-shrink: 0;
    margin-bottom: 22px;
  }

  .hero h1 {
    font-size: 28px;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.5px;
  }

  .subtitle {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .hero :global(.search-panel) {
    width: 100%;
    max-width: 720px;
    flex: 1;
    min-height: 0;
  }

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
    max-width: 460px;
    width: 90%;
  }

  .modal h3 {
    margin: 0 0 12px;
    font-size: 16px;
  }

  .modal p {
    margin: 0 0 20px;
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .modal-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  @media (max-width: 900px) {
    :global(:root) {
      --sidebar-width: 300px;
    }
  }
</style>
