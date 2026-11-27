<script>
  import { RefreshCw, X, ChevronRight, ChevronDown } from 'lucide-svelte';
  import TranscriptPanel from './TranscriptPanel.svelte';
  import { formatDuration, formatUploadDate } from '../format.js';
  import { t } from '../i18n/index.js';

  let {
    videos = [],
    missingCount = 0,
    busy = false,
    ondelete,
    onrefetch,
    ondeleteAll,
    onrefetchAll,
    onretryMissing,
  } = $props();

  let filter = $state('');
  let openId = $state('');

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

<section class="video-list">
  <div class="list-header">
    <h2>{t('videoList.videosLabel', videos.length)}</h2>
    {#if videos.length > 0}
      <div class="header-actions">
        {#if missingCount > 0}
          <button
            class="link"
            type="button"
            disabled={busy}
            title={t('videoList.retryMissingTooltip')}
            onclick={() => onretryMissing?.()}
          >{t('videoList.retryMissing', missingCount)}</button>
        {/if}
        <button
          class="link"
          type="button"
          disabled={busy}
          title={t('videoList.refetchAllTooltip')}
          onclick={() => onrefetchAll?.()}
        >{t('videoList.refetchAll')}</button>
        <button class="link danger" type="button" onclick={() => ondeleteAll?.()}>{t('videoList.clear')}</button>
      </div>
    {/if}
  </div>

  {#if videos.length > 8}
    <input class="filter" type="text" bind:value={filter} placeholder={t('videoList.filterPlaceholder')} />
  {/if}

  <ul class="video-items">
    {#if videos.length === 0}
      <li class="empty">{t('videoList.noVideosYet')}</li>
    {:else if filtered.length === 0}
      <li class="empty">{t('videoList.nothingMatches', filter)}</li>
    {:else}
      {#each visible as video (video.id)}
        <li class:open={video.id === openId}>
          <div class="row">
            <button
              type="button"
              class="video-btn"
              disabled={video.subtitle_type === 'none'}
              title={video.subtitle_type === 'none' ? video.error || '' : ''}
              onclick={() => (openId = openId === video.id ? '' : video.id)}
            >
              <span class="chevron">
                {#if video.id === openId}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
              </span>
              <span class="video-title">{video.title || video.id}</span>
              <span class="video-meta">
                <span class="pill" class:auto={video.subtitle_type === 'auto'} class:none={video.subtitle_type === 'none'}>
                  {video.subtitle_type === 'none'
                    ? t('videoList.noCaptions')
                    : t('videoList.subtitleInfo', video.subtitle_type, video.subtitle_language)}
                </span>
                {#if video.duration}<span>{formatDuration(video.duration)}</span>{/if}
                {#if video.upload_date}<span>{formatUploadDate(video.upload_date)}</span>{/if}
              </span>
            </button>
            <div class="row-actions">
              <button
                type="button"
                title={t('videoList.refetchCaptions')}
                disabled={busy}
                onclick={() => onrefetch?.(video.id)}
              >
                <RefreshCw size={13} />
              </button>
              <button type="button" title={t('videoList.remove')} onclick={() => ondelete?.(video.id)}>
                <X size={14} />
              </button>
            </div>
          </div>
          {#if video.id === openId}
            <div class="transcript">
              <TranscriptPanel videoId={video.id} />
            </div>
          {/if}
        </li>
      {/each}
      {#if hiddenCount > 0}
        <li class="more">{t('videoList.moreHidden', hiddenCount)}</li>
      {/if}
    {/if}
  </ul>
</section>

<style>
  .video-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .list-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  h2 {
    margin: 0;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .header-actions {
    display: flex;
    gap: 14px;
  }

  .link {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
    padding: 0;
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
    padding: 7px 10px;
    border-radius: 7px;
    font-size: 13px;
  }

  .video-items {
    list-style: none;
    padding: 0;
    margin: 0;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--bg-panel);
  }

  .video-items > li + li {
    border-top: 1px solid var(--border);
  }

  .row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 0 10px 0 0;
  }

  .row:hover {
    background: var(--bg-input);
  }

  li:first-child .row {
    border-radius: 10px 10px 0 0;
  }

  .video-btn {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    background: transparent;
    border: none;
    color: var(--text);
    text-align: left;
    cursor: pointer;
    padding: 10px 0 10px 10px;
    min-width: 0;
  }

  .video-btn:disabled {
    cursor: default;
    color: var(--text-muted);
  }

  .video-btn:disabled .chevron {
    visibility: hidden;
  }

  .chevron {
    display: flex;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .video-title {
    flex: 1;
    min-width: 0;
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .video-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 11px;
    color: var(--text-muted);
    flex-shrink: 0;
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
    gap: 2px;
    opacity: 0;
    flex-shrink: 0;
  }

  .row:hover .row-actions,
  .row-actions:focus-within {
    opacity: 1;
  }

  .row-actions button {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
  }

  .row-actions button:hover:not(:disabled) {
    color: var(--text);
    background: var(--border);
  }

  .row-actions button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .transcript {
    padding: 4px 14px 14px 34px;
  }

  .empty,
  .more {
    color: var(--text-muted);
    font-size: 13px;
    padding: 14px;
  }
</style>
