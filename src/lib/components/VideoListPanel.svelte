<script>
  import { createEventDispatcher } from 'svelte';

  let { videos = [], missing = [] } = $props();

  const dispatch = createEventDispatcher();

  function handleSelect(videoId) {
    dispatch('select', videoId);
  }

  function handleDelete(event, videoId) {
    event.stopPropagation();
    dispatch('delete', videoId);
  }

  function handleDeleteAll() {
    dispatch('deleteAll');
  }
</script>

<div class="panel">
  <div class="panel-header">
    <h2>Videos</h2>
    <div class="header-actions">
      <span>{videos.length} loaded</span>
      {#if videos.length > 0}
        <button class="btn-danger-sm" type="button" on:click={handleDeleteAll} title="Remove all videos">
          Clear all
        </button>
      {/if}
    </div>
  </div>
  <ul>
    {#if videos.length === 0}
      <li class="empty">No videos loaded yet.</li>
    {:else}
      {#each videos as video}
        <li>
          <button type="button" class="video-btn" on:click={() => handleSelect(video.id)}>
            <strong>{video.title || video.id}</strong>
            <span>{video.channel || 'Unknown'}</span>
            <span class="pill">{video.subtitle_type}</span>
          </button>
          <button
            type="button"
            class="btn-delete"
            on:click={(e) => handleDelete(e, video.id)}
            title="Remove video"
          >
            ✕
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

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-actions span {
    color: #b5b9c5;
    font-size: 12px;
  }

  .btn-danger-sm {
    background: #3a2a2a;
    border: 1px solid #5a3a3a;
    color: #ff8a8a;
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 6px;
    cursor: pointer;
  }

  .btn-danger-sm:hover {
    background: #4a3030;
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
    align-items: flex-start;
    gap: 8px;
  }

  li .video-btn {
    flex: 1;
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

  li .video-btn:hover strong {
    color: #7aa2ff;
  }

  .btn-delete {
    background: transparent;
    border: none;
    color: #6a6e7a;
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .btn-delete:hover {
    background: #3a2a2a;
    color: #ff8a8a;
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
