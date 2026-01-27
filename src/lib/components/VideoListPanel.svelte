<script>
  let { videos = [], missing = [], onselect, ondelete, ondeleteAll } = $props();

  function handleSelect(videoId) {
    onselect?.({ detail: videoId });
  }

  function handleDelete(event, videoId) {
    event.stopPropagation();
    ondelete?.({ detail: videoId });
  }

  function handleDeleteAll() {
    ondeleteAll?.();
  }
</script>

<div class="video-list">
  <div class="list-header">
    <span class="label">Videos ({videos.length})</span>
    {#if videos.length > 0}
      <button class="btn-clear" type="button" onclick={handleDeleteAll}>Clear all</button>
    {/if}
  </div>
  <ul class="video-items">
    {#if videos.length === 0}
      <li class="empty">No videos loaded.</li>
    {:else}
      {#each videos as video}
        <li>
          <button type="button" class="video-btn" onclick={() => handleSelect(video.id)}>
            <span class="video-title">{video.title || video.id}</span>
            <span class="video-meta">
              {video.channel || ''}
              <span class="pill">{video.subtitle_type}</span>
            </span>
          </button>
          <button
            type="button"
            class="btn-delete"
            onclick={(e) => handleDelete(e, video.id)}
          >✕</button>
        </li>
      {/each}
    {/if}
  </ul>

  {#if missing.length > 0}
    <div class="missing-section">
      <span class="label">Missing subtitles ({missing.length})</span>
      <ul class="missing-items">
        {#each missing as video}
          <li>{video.title || video.id}</li>
        {/each}
      </ul>
    </div>
  {/if}
</div>

<style>
  .video-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
    min-height: 0;
  }

  .list-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }

  .label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .btn-clear {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    padding: 2px 6px;
  }

  .btn-clear:hover {
    color: var(--error);
  }

  .video-items {
    list-style: none;
    padding: 0;
    margin: 0;
    overflow-y: auto;
    flex: 1;
  }

  .video-items li {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 6px;
    border-radius: 6px;
  }

  .video-items li:hover {
    background: var(--border);
  }

  .video-btn {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text);
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 2px;
    cursor: pointer;
    padding: 0;
    min-width: 0;
  }

  .video-title {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .video-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .pill {
    background: var(--border-input);
    color: var(--text-secondary);
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 4px;
  }

  .btn-delete {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
    padding: 2px 4px;
    opacity: 0;
  }

  li:hover .btn-delete {
    opacity: 1;
  }

  .btn-delete:hover {
    color: var(--error);
  }

  .empty {
    color: var(--text-muted);
    font-size: 12px;
    padding: 8px 4px;
  }

  .missing-section {
    border-top: 1px solid var(--border);
    padding-top: 12px;
    margin-top: 8px;
    flex-shrink: 0;
  }

  .missing-items {
    list-style: none;
    padding: 0;
    margin: 6px 0 0;
    max-height: 120px;
    overflow-y: auto;
  }

  .missing-items li {
    font-size: 12px;
    color: var(--text-muted);
    padding: 3px 4px;
  }
</style>
