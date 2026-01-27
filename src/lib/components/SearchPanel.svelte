<script>
  import { createEventDispatcher } from 'svelte';

  let { searchResults = [] } = $props();

  const dispatch = createEventDispatcher();
  let query = $state('');

  function submit() {
    dispatch('search', query);
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

<div class="panel">
  <div class="panel-header">
    <h2>Search transcripts</h2>
  </div>
  <div class="search-row">
    <input
      type="text"
      bind:value={query}
      placeholder="Search for a phrase"
      on:keydown={(event) => event.key === 'Enter' && submit()}
    />
    <button class="primary" type="button" on:click={submit}>Search</button>
  </div>
  <div class="results">
    {#if searchResults.length === 0}
      <p class="empty">No matches yet.</p>
    {:else}
      {#each searchResults as result}
        <div class="result-card">
          <div class="result-meta">
            {result.title || result.video_id} · {result.channel || 'Unknown'}
          </div>
          <div class="result-text">
            <span class="time">{formatTime(result.start_ms)}</span>
            <span class="text">{result.text}</span>
            <div class="actions">
              <button type="button" title="Open in browser" on:click={() => openInBrowser(result.video_id, result.start_ms)}>
                ↗
              </button>
              <button type="button" title="Copy link" on:click={() => copyLink(result.video_id, result.start_ms)}>
                📋
              </button>
            </div>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .panel {
    background: #171a21;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  }

  .panel-header {
    margin-bottom: 12px;
  }

  .search-row {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .search-row input {
    flex: 1;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid #2a2f3a;
    background: #0f1115;
    color: #f2f2f2;
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

  .results {
    display: grid;
    gap: 12px;
  }

  .result-card {
    background: #0f1115;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    padding: 10px;
  }

  .result-meta {
    color: #b5b9c5;
    font-size: 12px;
    margin-bottom: 6px;
  }

  .result-text {
    display: grid;
    grid-template-columns: 60px 1fr auto;
    gap: 12px;
    align-items: start;
  }

  .text {
    color: #f2f2f2;
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
    background: #2a2f3a;
    border: none;
    color: #b5b9c5;
    font-size: 12px;
    padding: 4px 6px;
    border-radius: 4px;
    cursor: pointer;
  }

  .actions button:hover {
    background: #3a4050;
    color: #f2f2f2;
  }

  .time {
    color: #7aa2ff;
  }

  .empty {
    color: #8c92a2;
  }
</style>
