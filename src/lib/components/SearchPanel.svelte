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
            <span>{result.text}</span>
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
    grid-template-columns: 60px 1fr;
    gap: 12px;
  }

  .time {
    color: #7aa2ff;
  }

  .empty {
    color: #8c92a2;
  }
</style>
