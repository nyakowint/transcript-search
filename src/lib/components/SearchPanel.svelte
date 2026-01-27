<script>
  import { Search } from 'lucide-svelte';

  let { searchResults = [], onsearch } = $props();

  let query = $state('');

  function submit() {
    onsearch?.({ detail: query });
  }

  function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const padded = (value) => String(value).padStart(2, '0');
    if (hours > 0) {
      return `${hours}:${padded(minutes)}:${padded(seconds)}`;
    }
    return `${minutes}:${padded(seconds)}`;
  }

  function getTimestampUrl(videoId, ms) {
    const seconds = Math.floor(ms / 1000);
    return `https://www.youtube.com/watch?v=${videoId}&t=${seconds}s`;
  }

  function openInBrowser(videoId, ms) {
    window.open(getTimestampUrl(videoId, ms), '_blank');
  }

  async function copyLink(videoId, ms) {
    try {
      await navigator.clipboard.writeText(getTimestampUrl(videoId, ms));
    } catch {
      const url = getTimestampUrl(videoId, ms);
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }
</script>

<div class="search-panel">
  <div class="search-bar">
    <input
      type="text"
      bind:value={query}
      placeholder="Search all transcripts..."
      onkeydown={(event) => event.key === 'Enter' && submit()}
    />
    <button class="search-btn" type="button" aria-label="Search" onclick={submit}>
      <Search size={18} />
    </button>
  </div>

  {#if searchResults.length > 0}
    <div class="results">
      <div class="results-header">{searchResults.length} match{searchResults.length === 1 ? '' : 'es'}</div>
      {#each searchResults as result}
        <div class="result-card">
          <div class="result-source">
            <span class="source-title">{result.title || result.video_id}</span>
            <span class="source-channel">{result.channel || ''}</span>
          </div>
          <div class="result-row">
            <span class="time">{formatTime(result.start_ms)}</span>
            <span class="text">{result.text}</span>
            <div class="actions">
              <button type="button" title="Open in browser" onclick={() => openInBrowser(result.video_id, result.start_ms)}>
                ↗
              </button>
              <button type="button" title="Copy link" onclick={() => copyLink(result.video_id, result.start_ms)}>
                📋
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .search-panel {
    width: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }

  .search-bar {
    display: flex;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.15s;
    flex-shrink: 0;
  }

  .search-bar:focus-within {
    border-color: var(--accent);
  }

  .search-bar input {
    flex: 1;
    padding: 14px 18px;
    border: none;
    background: transparent;
    color: var(--text);
    font-size: 15px;
    outline: none;
  }

  .search-bar input::placeholder {
    color: var(--text-muted);
  }

  .search-btn {
    padding: 14px 18px;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
  }

  .search-btn:hover {
    color: var(--text);
  }

  .results {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .results-header {
    font-size: 12px;
    color: var(--text-muted);
    padding: 0 4px 8px;
  }

  .result-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    transition: border-color 0.15s;
  }

  .result-card:hover {
    border-color: var(--border-input);
  }

  .result-source {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 6px;
  }

  .source-title {
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
  }

  .source-channel {
    color: var(--text-muted);
    font-size: 11px;
  }

  .result-row {
    display: grid;
    grid-template-columns: 52px 1fr auto;
    gap: 10px;
    align-items: start;
  }

  .time {
    color: var(--accent);
    font-size: 12px;
    font-family: "SF Mono", "Consolas", monospace;
  }

  .text {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.5;
  }

  .actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .result-card:hover .actions {
    opacity: 1;
  }

  .actions button {
    background: var(--border-input);
    border: none;
    color: var(--text-secondary);
    font-size: 11px;
    padding: 4px 6px;
    border-radius: 4px;
    cursor: pointer;
  }

  .actions button:hover {
    background: var(--border);
    color: var(--text);
  }
</style>
