<script>
  import CookiesPanel from './components/CookiesPanel.svelte';
  import IngestPanel from './components/IngestPanel.svelte';
  import JobChip from './components/JobChip.svelte';
  import Modal from './components/Modal.svelte';
  import SearchBox from './components/SearchBox.svelte';
  import SearchFilters from './components/SearchFilters.svelte';
  import SearchResults from './components/SearchResults.svelte';
  import SourcesPanel from './components/SourcesPanel.svelte';
  import VideoListPanel from './components/VideoListPanel.svelte';
  import { apiClient, onBackendEvent } from './services/api.js';
  import { t } from './i18n/index.js';
  import { Sun, Moon, Settings, Plus, ArrowUp, X } from 'lucide-svelte';

  const PAGE_SIZE = 25;
  const EMPTY_RESULT = { videos: [], total_videos: 0, total_hits: 0, has_more: false };

  let settings = $state({});
  let ytdlpVersion = $state('');
  let sources = $state([]);
  let videos = $state([]);
  let stats = $state({});
  let loaded = $state(false);

  let query = $state('');
  let options = $state({
    mode: 'phrase',
    whole_words: true,
    source_id: '',
    subtitle_type: '',
    date_from: '',
    date_to: '',
    sort: 'relevance',
  });
  let result = $state(EMPTY_RESULT);
  let searching = $state(false);
  let loadingMore = $state(false);
  let recent = $state([]);
  let searchInput = $state();
  let searchSeq = 0;
  let searchTimer;

  let job = $state(null);
  let toast = $state(null);
  let toastTimer;
  let darkMode = $state(true);
  let addOpen = $state(false);
  let settingsOpen = $state(false);
  let confirmModal = $state(null);

  let scroller = $state();
  let showTop = $state(false);

  const busy = $derived(job?.status === 'running');
  const searchActive = $derived(query.trim() !== '');
  const activeSource = $derived(sources.find((source) => source.id === options.source_id));
  const scopeLabel = $derived(activeSource ? activeSource.title || activeSource.id : t('app.everything'));
  const hasContent = $derived((stats.segments || 0) > 0);
  const libraryEmpty = $derived(loaded && !videos.length && !sources.length && !options.source_id);

  $effect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  });

  // Typing and filter changes both re-run the search after a short pause.
  $effect(() => {
    const text = query;
    const opts = { ...options };
    clearTimeout(searchTimer);
    if (!text.trim()) {
      searchSeq++;
      result = EMPTY_RESULT;
      searching = false;
      return;
    }
    searchTimer = setTimeout(() => runSearch(text, opts), 200);
  });

  function notify(message, isError = false) {
    clearTimeout(toastTimer);
    toast = { message, isError };
    if (!isError) toastTimer = setTimeout(() => (toast = null), 4000);
  }

  // ---------------------------------------------------------------- data load

  async function refreshLists() {
    const [videoResponse, sourceResponse, statsResponse] = await Promise.all([
      apiClient.getVideos(options.source_id),
      apiClient.getSources(),
      apiClient.getStats(),
    ]);
    if (videoResponse.ok) videos = videoResponse.videos;
    if (sourceResponse.ok) sources = sourceResponse.sources;
    if (statsResponse.ok) stats = statsResponse.stats;
    loaded = true;
  }

  function selectSource(sourceId) {
    options.source_id = sourceId;
    refreshLists();
  }

  function setOptions(next) {
    const sourceChanged = next.source_id !== options.source_id;
    options = next;
    if (sourceChanged) refreshLists();
  }

  // ------------------------------------------------------------------ search

  async function runSearch(text, opts, offset = 0) {
    const seq = ++searchSeq;
    if (offset) loadingMore = true;
    else searching = true;
    const response = await apiClient.searchTranscripts(text, { ...opts, limit: PAGE_SIZE, offset });
    if (seq !== searchSeq) return;
    searching = false;
    loadingMore = false;
    if (!response.ok) {
      notify(response.error, true);
      return;
    }
    const { ok, ...page } = response;
    result = offset ? { ...page, videos: [...result.videos, ...page.videos] } : page;
  }

  function rerunSearch() {
    if (searchActive) runSearch(query, { ...options });
  }

  function loadMore() {
    runSearch(query, { ...options }, result.videos.length);
  }

  async function rememberSearch(text = query) {
    if (!text.trim()) return;
    const response = await apiClient.addRecentSearch(text);
    if (response.ok) recent = response.searches;
  }

  async function clearRecent() {
    const response = await apiClient.clearRecentSearches();
    if (response.ok) recent = response.searches;
  }

  async function exportResults(format) {
    rememberSearch();
    const response = await apiClient.exportSearch(query, { ...options }, format);
    if (!response.ok) notify(response.error, true);
    else if (response.path) notify(t('results.exported', response.path));
  }

  // ------------------------------------------------------------------ ingest

  async function startJob(request) {
    const response = await request;
    if (!response.ok) {
      notify(response.error, true);
      return false;
    }
    job = response.job;
    return true;
  }

  async function handleFetch(input) {
    if (await startJob(apiClient.startIngest(input))) addOpen = false;
  }

  function confirmRefetchAll() {
    confirmModal = {
      title: t('app.confirmRefetchAllTitle', videos.length),
      body: t('app.confirmRefetchAllBody'),
      confirmLabel: t('app.confirmRefetchAllLabel'),
      danger: false,
      action: () => startJob(apiClient.refetchAll('all')),
    };
  }

  // ------------------------------------------------------------------ delete

  async function deleteVideo(videoId) {
    const response = await apiClient.deleteVideo(videoId);
    if (!response.ok) {
      notify(response.error, true);
      return;
    }
    await refreshLists();
    rerunSearch();
  }

  function confirmDeleteAll() {
    confirmModal = {
      title: t('app.confirmClearTitle'),
      body: t('app.confirmClearBody', { videos: stats.videos || 0, sources: stats.sources || 0 }),
      confirmLabel: t('app.confirmClearLabel'),
      danger: true,
      action: async () => {
        await apiClient.deleteAllVideos();
        query = '';
        options.source_id = '';
        await refreshLists();
        notify(t('app.libraryCleared'));
      },
    };
  }

  function confirmDeleteSource(source) {
    const remove = async (withVideos) => {
      await apiClient.deleteSource(source.id, withVideos);
      if (options.source_id === source.id) options.source_id = '';
      await refreshLists();
      rerunSearch();
    };
    confirmModal = {
      title: t('app.confirmRemoveSourceTitle', source.title || source.id),
      body: t('app.confirmRemoveSourceBody', source.video_count),
      confirmLabel: t('app.confirmRemoveSourceOnly'),
      extraLabel: t('app.confirmRemoveSourceAndVideos'),
      danger: true,
      action: () => remove(false),
      extraAction: () => remove(true),
    };
  }

  async function runConfirm(which) {
    const modal = confirmModal;
    confirmModal = null;
    await (which === 'extra' ? modal?.extraAction?.() : modal?.action?.());
  }

  // ---------------------------------------------------------------- settings

  async function updateSettings(patch) {
    const response = await apiClient.saveSettings(patch);
    if (response.ok) settings = response.settings;
  }

  async function browseCookies() {
    const response = await apiClient.selectCookiesFile();
    if (!response.ok) notify(response.error, true);
    else if (response.path) await updateSettings({ cookies_path: response.path });
  }

  // -------------------------------------------------------------- lifecycle

  function handleGlobalKeydown(event) {
    if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target;
    if (target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
    event.preventDefault();
    searchInput?.focus();
  }

  onBackendEvent((event) => {
    if (event.type === 'job') {
      job = event.job;
      if (event.job.status !== 'running') refreshLists().then(rerunSearch);
    } else if (event.type === 'ytdlp') {
      if (event.version) ytdlpVersion = event.version;
      if (event.message) notify(event.message, !!event.error);
    }
  });

  async function init() {
    const [settingsResponse, recentResponse, jobResponse] = await Promise.all([
      apiClient.getSettings(),
      apiClient.getRecentSearches(),
      // A job can outlive a page reload; pick it back up.
      apiClient.getJob(),
    ]);
    if (settingsResponse.ok) {
      settings = settingsResponse.settings;
      ytdlpVersion = settingsResponse.ytdlp_version;
    }
    if (recentResponse.ok) recent = recentResponse.searches;
    if (jobResponse.ok && jobResponse.job) job = jobResponse.job;
    await refreshLists();
  }

  apiClient.onReady(init);
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<div class="app">
  <header>
    <div class="bar">
      <span class="brand">{t('app.title')}</span>
      <div class="search">
        <SearchBox
          bind:value={query}
          bind:input={searchInput}
          {recent}
          placeholder={hasContent ? t('search.placeholder', scopeLabel) : t('search.fetchFirst')}
          onsubmit={(text) => rememberSearch(text)}
          onclearRecent={clearRecent}
        />
      </div>
      <div class="tools">
        {#if job}
          <JobChip {job} oncancel={() => apiClient.cancelJob(job?.id || '')} ondismiss={() => (job = null)} />
        {/if}
        <button class="tool" type="button" title={t('app.addTooltip')} onclick={() => (addOpen = true)}>
          <Plus size={16} />
          <span>{t('app.add')}</span>
        </button>
        <button
          class="icon-btn"
          type="button"
          title={t('app.settingsTooltip')}
          aria-label={t('app.settingsTooltip')}
          onclick={() => (settingsOpen = true)}
        >
          <Settings size={16} />
        </button>
        <button
          class="icon-btn"
          type="button"
          title={darkMode ? t('app.lightMode') : t('app.darkMode')}
          aria-label={t('app.toggleTheme')}
          onclick={() => (darkMode = !darkMode)}
        >
          {#if darkMode}<Sun size={16} />{:else}<Moon size={16} />{/if}
        </button>
      </div>
    </div>
    {#if searchActive}
      <div class="filters-row">
        <SearchFilters {options} {sources} onchange={setOptions} />
      </div>
    {/if}
    <div class="progress" class:on={searching}></div>
  </header>

  <main bind:this={scroller} onscroll={() => (showTop = scroller.scrollTop > 500)}>
    <div class="column">
      {#if searchActive}
        <div class:stale={searching}>
          <SearchResults
            {result}
            {query}
            sort={options.sort}
            onsort={(sort) => (options.sort = sort)}
            loading={searching}
            {loadingMore}
            onloadMore={loadMore}
            onexport={exportResults}
            onengage={() => rememberSearch()}
          />
        </div>
      {:else if libraryEmpty}
        <div class="empty-state">
          <h1>{t('app.emptyTitle')}</h1>
          <p>{t('app.emptyBody')}</p>
          <button class="primary" type="button" onclick={() => (addOpen = true)}>{t('app.emptyAction')}</button>
        </div>
      {:else if loaded}
        {#if hasContent}
          <p class="stats">
            {t('app.stats', { videos: stats.videos, segments: stats.segments, missing: stats.missing })}
          </p>
        {/if}
        <SourcesPanel
          {sources}
          activeSourceId={options.source_id}
          {busy}
          onselect={selectSource}
          onsync={(sourceId, force) => startJob(apiClient.syncSource(sourceId, force))}
          ondelete={confirmDeleteSource}
        />
        <VideoListPanel
          {videos}
          missingCount={stats.missing || 0}
          {busy}
          ondelete={deleteVideo}
          onrefetch={(videoId) => startJob(apiClient.refetchVideos([videoId]))}
          ondeleteAll={confirmDeleteAll}
          onrefetchAll={confirmRefetchAll}
          onretryMissing={() => startJob(apiClient.refetchAll('missing'))}
        />
      {/if}
    </div>
  </main>

  {#if showTop}
    <button
      class="to-top"
      type="button"
      title={t('app.backToTop')}
      aria-label={t('app.backToTop')}
      onclick={() => scroller.scrollTo({ top: 0, behavior: 'smooth' })}
    >
      <ArrowUp size={18} />
    </button>
  {/if}

  {#if toast}
    <div class="toast" class:error={toast.isError} role="status">
      <span>{toast.message}</span>
      <button type="button" aria-label={t('app.dismiss')} onclick={() => (toast = null)}><X size={14} /></button>
    </div>
  {/if}

  {#if addOpen}
    <Modal title={t('app.addTitle')} width={560} onclose={() => (addOpen = false)}>
      <IngestPanel {settings} {busy} onfetch={handleFetch} onsettingchange={updateSettings} />
    </Modal>
  {/if}

  {#if settingsOpen}
    <Modal title={t('app.settingsTitle')} onclose={() => (settingsOpen = false)}>
      <CookiesPanel
        cookiesPath={settings.cookies_path || ''}
        onchange={updateSettings}
        onbrowse={browseCookies}
      />
      {#if ytdlpVersion}<p class="version">{t('app.ytdlpVersion', ytdlpVersion)}</p>{/if}
    </Modal>
  {/if}

  {#if confirmModal}
    <Modal title={confirmModal.title} onclose={() => (confirmModal = null)}>
      <p class="confirm-body">{confirmModal.body}</p>
      <div class="modal-actions">
        <button class="secondary" type="button" onclick={() => (confirmModal = null)}>{t('common.cancel')}</button>
        {#if confirmModal.extraLabel}
          <button class="danger" type="button" onclick={() => runConfirm('extra')}>{confirmModal.extraLabel}</button>
        {/if}
        <button class={confirmModal.danger ? 'danger' : 'primary'} type="button" onclick={() => runConfirm('main')}>
          {confirmModal.confirmLabel}
        </button>
      </div>
    </Modal>
  {/if}
</div>

<style>
  :global(:root) {
    --bg-base: #0a0c0f;
    --bg-elevated: #12151a;
    --bg-panel: #12151a;
    --bg-input: #12151a;
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
    --column: 920px;
    color-scheme: dark;
  }

  :global([data-theme="light"]) {
    --bg-base: #f5f5f7;
    --bg-elevated: #ffffff;
    --bg-panel: #ffffff;
    --bg-input: #f0f0f2;
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
    color-scheme: light;
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

  :global(.primary) {
    background: var(--accent);
    border: none;
    color: white;
    padding: 9px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
  }

  :global(.primary:hover:not(:disabled)) {
    background: var(--accent-hover);
  }

  :global(.primary:disabled) {
    opacity: 0.5;
    cursor: default;
  }

  .app {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    position: relative;
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
    background: var(--bg-base);
  }

  .bar,
  .filters-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 24px;
  }

  .filters-row {
    padding-top: 0;
    max-width: calc(var(--column) + 48px);
    margin: 0 auto;
  }

  .brand {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    flex: 1;
    flex-basis: 0;
  }

  .search {
    flex: 0 1 var(--column);
    min-width: 0;
  }

  .tools {
    flex: 1;
    flex-basis: 0;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
  }

  .tool,
  .icon-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text-secondary);
    padding: 7px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
  }

  .tool {
    padding: 6px 12px 6px 9px;
  }

  .tool:hover,
  .icon-btn:hover {
    color: var(--text);
  }

  /* Thin bar under the header while a search is in flight. */
  .progress {
    position: absolute;
    left: 0;
    right: 0;
    bottom: -1px;
    height: 2px;
    overflow: hidden;
  }

  .progress.on::after {
    content: '';
    position: absolute;
    inset: 0 auto 0 0;
    width: 30%;
    background: var(--accent);
    animation: sweep 0.9s ease-in-out infinite;
  }

  @keyframes sweep {
    from { transform: translateX(-100%); }
    to { transform: translateX(340%); }
  }

  main {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .column {
    max-width: var(--column);
    margin: 0 auto;
    padding: 20px 24px 48px;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .stale {
    opacity: 0.6;
    transition: opacity 0.15s;
  }

  .stats {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .empty-state {
    text-align: center;
    margin-top: 14vh;
  }

  .empty-state h1 {
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 8px;
  }

  .empty-state p {
    margin: 0 auto 20px;
    max-width: 420px;
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-secondary);
  }

  .to-top {
    position: fixed;
    right: 24px;
    bottom: 24px;
    display: flex;
    padding: 10px;
    border-radius: 50%;
    background: var(--bg-elevated);
    border: 1px solid var(--border-input);
    color: var(--text-secondary);
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    z-index: 50;
  }

  .to-top:hover {
    color: var(--text);
  }

  .toast {
    position: fixed;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 12px;
    max-width: min(640px, calc(100vw - 48px));
    padding: 10px 12px 10px 16px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-input);
    border-radius: 10px;
    font-size: 13px;
    color: var(--text);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    z-index: 90;
  }

  .toast.error {
    border-color: var(--error);
    color: var(--error);
  }

  .toast span {
    word-break: break-word;
  }

  .toast button {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    padding: 2px;
  }

  .version {
    margin: 14px 0 0;
    font-size: 11px;
    color: var(--text-muted);
  }

  .confirm-body {
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

  .secondary {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 9px 16px;
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
    padding: 9px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
  }

  .danger:hover {
    background: #b91c1c;
  }

  @media (max-width: 980px) {
    .brand {
      display: none;
    }

    .search {
      flex: 1;
    }
  }
</style>
