<script>
  import { createEventDispatcher } from 'svelte';

  export let videos = [];
  export let missing = [];

  const dispatch = createEventDispatcher();

  function handleSelect(videoId) {
    dispatch('select', videoId);
  }
</script>

<div class="panel">
  <div class="panel-header">
    <h2>Videos</h2>
    <span>{videos.length} loaded</span>
  </div>
  <ul>
    {#if videos.length === 0}
      <li class="empty">No videos loaded yet.</li>
    {:else}
      {#each videos as video}
        <li>
          <button type="button" on:click={() => handleSelect(video.id)}>
            <strong>{video.title || video.id}</strong>
            <span>{video.channel || 'Unknown'}</span>
            <span class="pill">{video.subtitle_type}</span>
          </button>
        </li>
      {/each}
    {/if}
  </ul>
  <h3>Missing subtitles</h3>
  <ul class="muted">
    {#if missing.length === 0}
      <li class="empty">All videos have subtitles.</li>
    {:else}
      {#each missing as video}
        <li>
          <span>{video.title || video.id}</span>
          <span>{video.channel || 'Unknown'}</span>
        </li>
      {/each}
    {/if}
  </ul>
</div>

<style>
  .panel {
    background: #171a21;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  span {
    color: #b5b9c5;
    font-size: 12px;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0 0 16px;
  }

  li {
    padding: 6px 0;
    border-bottom: 1px solid #252a33;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  li button {
    background: transparent;
    border: none;
    color: #f2f2f2;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 4px;
    cursor: pointer;
    padding: 0;
  }

  li button:hover strong {
    color: #7aa2ff;
  }

  .pill {
    background: #2a2f3a;
    color: #cfd4e6;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 999px;
    display: inline-block;
    width: fit-content;
  }

  .empty {
    color: #8c92a2;
  }

  .muted span {
    color: #c8cddc;
  }
</style>