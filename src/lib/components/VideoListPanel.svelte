<script>
  import { RefreshCw, X } from 'lucide-svelte';
  import { formatDuration, formatUploadDate } from '../format.js';

  let {
    videos = [],
    missing = [],
    selectedVideoId = '',
    busy = false,
    onselect,
    ondelete,
    onrefetch,
    ondeleteAll,
    onrefetchAll,
    onretryMissing,
  } = $props();

  let filter = $state('');

  const filtered = $derived.by(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return videos;
    return videos.filter(
      (video) =>
        (video.title || '').toLowerCase().includes(needle) ||
        (video.channel || '').toLowerCase().includes(needle)
    );
  });

  // A big channel can hold thousands of rows; render a window of them and let
  // the filter box reach the rest rather than paying for every node up front.
  const RENDER_CAP = 300;
  const visible = $derived(filtered.slice(0, RENDER_CAP));
  const hiddenCount = $derived(Math.max(0, filtered.length - visible.length));
</script>

<div class="video-list">
  <div class="list-header">
    <span class="label">Videos ({videos.length})</span>
    {#if videos.length > 0}
      <div class="header-actions">
        <button
          class="link"
          type="button"
          disabled={busy}
          title="Refetch every stored video"
          onclick={() => onrefetchAll?.()}
        >Refetch all</button>
        <button class="link danger" type="button" onclick={() => ondeleteAll?.()}>Clear</button>
      </div>
    {/if}
  </div>

  {#if videos.length > 8}
    <input class="filter" type="text" bind:value={filter} placeholder="Filter videos..." />
  {/if}

  <ul class="video-items">
    {#if videos.length === 0}
      <li class="empty">No videos yet. Paste a channel or playlist above.</li>
    {:else if filtered.length === 0}
      <li class="empty">Nothing matches "{filter}".</li>
    {:else}
      {#each visible as video (video.id)}
        <li class:active={video.id === selectedVideoId}>
          <button type="button" class="video-btn" onclick={() => onselect?.(video.id)}>
            <span class="video-title" title={video.title || video.id}>
              {video.title || video.id}
            </span>
            <span class="video-meta">
              <span class="pill" class:auto={video.subtitle_type === 'auto'} class:none={video.subtitle_type === 'none'}>
                {video.subtitle_type === 'none'
                  ? 'no captions'
                  : `${video.subtitle_type} · ${video.subtitle_language}`}
              </span>
              {#if video.duration}<span>{formatDuration(video.duration)}</span>{/if}
              {#if video.upload_date}<span>{formatUploadDate(video.upload_date)}</span>{/if}
            </span>
          </button>
          <div class="row-actions">
            <button
              type="button"
              title="Refetch captions"
              disabled={busy}
              onclick={() => onrefetch?.(video.id)}
            >
              <RefreshCw size={12} />
            </button>
            <button type="button" title="Remove" onclick={() => ondelete?.(video.id)}>
              <X size={13} />
            </button>
          </div>
        </li>
      {/each}
      {#if hiddenCount > 0}
        <li class="more">+{hiddenCount} more — use the filter to narrow down</li>
      {/if}
    {/if}
  </ul>

  {#if missing.length > 0}
    <div class="missing-section">
      <div class="list-header">
        <span class="label">No captions ({missing.length})</span>
        <button
          class="link"
          type="button"
          disabled={busy}
          title="Uploaders sometimes add captions later"
          onclick={() => onretryMissing?.()}
        >Retry</button>
      </div>
      <ul class="missing-items">
        {#each missing.slice(0, 50) as video}
          <li title={video.error || ''}>{video.title || video.id}</li>
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
    gap: 8px;
    flex-shrink: 0;
  }

  .label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }

  .link {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    padding: 2px 0;
  }

  .link:hover:not(:disabled) {
    color: var(--text);
  }

  .link.danger:hover {
    color: var(--error);
  }

  .link:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .filter {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
    flex-shrink: 0;
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
    padding: 7px 6px;
    border-radius: 6px;
  }

  .video-items li:hover {
    background: var(--border);
  }

  .video-items li.active {
    background: var(--accent-subtle);
  }

  .video-btn {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text);
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 3px;
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
    font-size: 10px;
    color: var(--text-muted);
  }

  .pill {
    background: var(--success-subtle);
    color: var(--success);
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 4px;
  }

  .pill.auto {
    background: var(--border-input);
    color: var(--text-secondary);
  }

  .pill.none {
    background: var(--error-subtle);
    color: var(--error);
  }

  .row-actions {
    display: flex;
    gap: 1px;
    opacity: 0;
    flex-shrink: 0;
  }

  li:hover .row-actions {
    opacity: 1;
  }

  .row-actions button {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 3px;
    border-radius: 4px;
    display: flex;
  }

  .row-actions button:hover:not(:disabled) {
    color: var(--text);
    background: var(--bg-input);
  }

  .row-actions button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .empty,
  .more {
    color: var(--text-muted);
    font-size: 12px;
    padding: 8px 4px;
  }

  .missing-section {
    border-top: 1px solid var(--border);
    padding-top: 10px;
    margin-top: 4px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .missing-items {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 110px;
    overflow-y: auto;
  }

  .missing-items li {
    font-size: 11px;
    color: var(--text-muted);
    padding: 2px 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
