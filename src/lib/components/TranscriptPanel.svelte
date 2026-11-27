<script>
  import { ExternalLink, Copy, Check } from 'lucide-svelte';
  import { tick } from 'svelte';
  import { apiClient } from '../services/api.js';
  import { formatTime, timestampUrl, copyText } from '../format.js';
  import { t } from '../i18n/index.js';

  // hitIds marks matching lines; focusId is the line to scroll to.
  let { videoId, hitIds = [], focusId = null } = $props();

  let transcript = $state([]);
  let video = $state(null);
  let loading = $state(true);
  let error = $state('');
  let filter = $state('');
  let copiedMs = $state(-1);
  let list = $state();

  const hitSet = $derived(new Set(hitIds));

  const filtered = $derived.by(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return transcript;
    return transcript.filter((segment) => segment.text.toLowerCase().includes(needle));
  });

  $effect(() => {
    load(videoId);
  });

  $effect(() => {
    if (!loading) scrollTo(focusId);
  });

  async function load(id) {
    loading = true;
    const response = await apiClient.getTranscript(id);
    loading = false;
    if (!response.ok) {
      error = response.error;
      return;
    }
    transcript = response.segments;
    video = response.video;
  }

  async function scrollTo(id) {
    if (id == null) return;
    await tick();
    const row = list?.querySelector(`[data-id="${id}"]`);
    if (!row) return;
    // Scroll only this box; scrollIntoView would drag the whole page along.
    list.scrollTop = row.offsetTop - list.clientHeight / 3;
  }

  async function copyLink(ms) {
    await copyText(timestampUrl(videoId, ms));
    flashCopied(ms);
  }

  async function copyAll() {
    await copyText(
      filtered.map((segment) => `[${formatTime(segment.start_ms)}] ${segment.text}`).join('\n')
    );
    flashCopied(-2);
  }

  function flashCopied(key) {
    copiedMs = key;
    setTimeout(() => {
      if (copiedMs === key) copiedMs = -1;
    }, 1200);
  }

  function open(ms) {
    window.open(timestampUrl(videoId, ms), '_blank');
  }
</script>

<div class="transcript">
  {#if loading}
    <p class="empty">{t('transcript.loading')}</p>
  {:else if error}
    <p class="empty">{error}</p>
  {:else if transcript.length === 0}
    <p class="empty">{t('transcript.empty')}</p>
  {:else}
    <div class="toolbar">
      <input type="text" bind:value={filter} placeholder={t('transcript.filterPlaceholder')} />
      <span class="count">
        {t('transcript.lines', { shown: filtered.length, total: transcript.length, hasFilter: !!filter.trim() })}
        {#if video?.subtitle_type}· {video.subtitle_type} {video.subtitle_language}{/if}
      </span>
      <button class="link" type="button" onclick={copyAll}>
        {copiedMs === -2 ? t('transcript.copied') : t('transcript.copyAll')}
      </button>
    </div>

    <div class="lines" bind:this={list}>
      {#if filtered.length === 0}
        <p class="empty">{t('transcript.noLinesMatch', filter)}</p>
      {/if}
      {#each filtered as segment (segment.id)}
        <div class="line" class:hit={hitSet.has(segment.id)} class:focus={segment.id === focusId} data-id={segment.id}>
          <button class="time" type="button" title={t('common.openAtTime')} onclick={() => open(segment.start_ms)}>
            {formatTime(segment.start_ms)}
          </button>
          <span class="text">{segment.text}</span>
          <div class="actions">
            <button type="button" title={t('common.openInBrowser')} onclick={() => open(segment.start_ms)}>
              <ExternalLink size={12} />
            </button>
            <button type="button" title={t('common.copyLink')} onclick={() => copyLink(segment.start_ms)}>
              {#if copiedMs === segment.start_ms}<Check size={12} />{:else}<Copy size={12} />{/if}
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .transcript {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .toolbar input {
    flex: 1;
    min-width: 0;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
  }

  .count {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .link {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    padding: 0;
    white-space: nowrap;
  }

  .link:hover {
    color: var(--text);
  }

  .lines {
    position: relative;
    max-height: 380px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 4px;
  }

  .line {
    display: grid;
    grid-template-columns: 56px 1fr auto;
    gap: 10px;
    padding: 5px 6px;
    border-radius: 5px;
    align-items: start;
  }

  .line:hover {
    background: var(--border);
  }

  .line.hit {
    background: var(--accent-subtle);
  }

  .line.focus {
    box-shadow: inset 2px 0 0 var(--accent);
  }

  .time {
    color: var(--accent);
    font-size: 11px;
    font-family: "SF Mono", "Consolas", monospace;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    text-align: left;
    line-height: 1.6;
  }

  .time:hover {
    text-decoration: underline;
  }

  .text {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.45;
  }

  .line.hit .text {
    color: var(--text);
  }

  .actions {
    display: flex;
    gap: 3px;
    opacity: 0;
  }

  .line:hover .actions {
    opacity: 1;
  }

  .actions button {
    background: var(--border-input);
    border: none;
    color: var(--text-muted);
    padding: 3px 4px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
  }

  .actions button:hover {
    color: var(--text);
  }

  .empty {
    color: var(--text-muted);
    font-size: 12px;
    margin: 6px 2px;
  }
</style>
