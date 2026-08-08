<script>
  import { ExternalLink, Copy, Check } from 'lucide-svelte';
  import { formatTime, timestampUrl, copyText } from '../format.js';

  let { transcript = [], video = null, videoId = '' } = $props();

  let filter = $state('');
  let copiedMs = $state(-1);

  const id = $derived(videoId || video?.id || '');

  const filtered = $derived.by(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return transcript;
    return transcript.filter((segment) => segment.text.toLowerCase().includes(needle));
  });

  async function copyLink(ms) {
    await copyText(timestampUrl(id, ms));
    copiedMs = ms;
    setTimeout(() => {
      if (copiedMs === ms) copiedMs = -1;
    }, 1200);
  }

  function open(ms) {
    window.open(timestampUrl(id, ms), '_blank');
  }

  async function copyAll() {
    await copyText(
      filtered.map((segment) => `[${formatTime(segment.start_ms)}] ${segment.text}`).join('\n')
    );
    copiedMs = -2;
    setTimeout(() => {
      if (copiedMs === -2) copiedMs = -1;
    }, 1200);
  }
</script>

<div class="transcript-panel">
  {#if transcript.length > 0}
    <div class="panel-header">
      <span class="count">
        {filtered.length}{filter.trim() ? ` / ${transcript.length}` : ''} lines
        {#if video?.subtitle_type}
          · {video.subtitle_type} {video.subtitle_language}
        {/if}
      </span>
      <button class="link" type="button" onclick={copyAll}>
        {copiedMs === -2 ? 'Copied' : 'Copy all'}
      </button>
    </div>
    <input class="filter" type="text" bind:value={filter} placeholder="Filter this transcript..." />
  {/if}

  <div class="transcript-list">
    {#if transcript.length === 0}
      <p class="empty">Select a video to read its transcript.</p>
    {:else if filtered.length === 0}
      <p class="empty">No lines match "{filter}".</p>
    {:else}
      {#each filtered as segment (segment.start_ms)}
        <div class="segment">
          <button class="time" type="button" onclick={() => open(segment.start_ms)}>
            {formatTime(segment.start_ms)}
          </button>
          <span class="text">{segment.text}</span>
          <div class="actions">
            <button type="button" title="Open" onclick={() => open(segment.start_ms)}>
              <ExternalLink size={12} />
            </button>
            <button type="button" title="Copy link" onclick={() => copyLink(segment.start_ms)}>
              {#if copiedMs === segment.start_ms}<Check size={12} />{:else}<Copy size={12} />{/if}
            </button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .transcript-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 8px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-shrink: 0;
  }

  .count {
    font-size: 11px;
    color: var(--text-muted);
  }

  .link {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    padding: 0;
  }

  .link:hover {
    color: var(--text);
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

  .transcript-list {
    flex: 1;
    overflow-y: auto;
  }

  .segment {
    display: grid;
    grid-template-columns: 52px 1fr auto;
    gap: 10px;
    padding: 7px 4px;
    border-radius: 6px;
    align-items: start;
  }

  .segment:hover {
    background: var(--border);
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
  }

  .time:hover {
    text-decoration: underline;
  }

  .text {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.45;
  }

  .actions {
    display: flex;
    gap: 3px;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .segment:hover .actions {
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
    background: var(--border);
    color: var(--text);
  }

  .empty {
    color: var(--text-muted);
    font-size: 13px;
    margin: 0;
  }
</style>
