<script>
  import { Search, ExternalLink, Copy, Check } from 'lucide-svelte';
  import { formatTime, timestampUrl, copyText, splitHighlights } from '../format.js';

  let {
    results = [],
    total = 0,
    truncated = false,
    searching = false,
    query = '',
    scopeLabel = 'everything',
    hasContent = true,
    onsearch,
    onopenVideo,
  } = $props();

  let input = $state('');
  let copiedKey = $state('');
  let debounceTimer;

  $effect(() => {
    // Keep the box in step when a scope change re-runs the last query.
    if (query && !input) input = query;
  });

  function submit() {
    clearTimeout(debounceTimer);
    onsearch?.(input);
  }

  function handleInput() {
    clearTimeout(debounceTimer);
    const value = input;
    // Search is local SQLite, so typing straight into it is cheap; a short
    // debounce just avoids a query per keystroke on very large libraries.
    debounceTimer = setTimeout(() => onsearch?.(value), 220);
  }

  async function copyLink(result) {
    const key = `${result.video_id}-${result.start_ms}`;
    await copyText(timestampUrl(result.video_id, result.start_ms));
    copiedKey = key;
    setTimeout(() => {
      if (copiedKey === key) copiedKey = '';
    }, 1200);
  }

  function open(result) {
    window.open(timestampUrl(result.video_id, result.start_ms), '_blank');
  }

  // Consecutive hits in the same video share one header instead of repeating it.
  const grouped = $derived.by(() => {
    const groups = [];
    for (const result of results) {
      const last = groups[groups.length - 1];
      if (last && last.videoId === result.video_id) {
        last.hits.push(result);
      } else {
        groups.push({
          videoId: result.video_id,
          title: result.title,
          channel: result.channel,
          subtitleType: result.subtitle_type,
          hits: [result],
        });
      }
    }
    return groups;
  });
</script>

<div class="search-panel">
  <div class="search-bar">
    <input
      type="text"
      bind:value={input}
      oninput={handleInput}
      placeholder={hasContent ? `Search ${scopeLabel}...` : 'Fetch some captions first'}
      onkeydown={(event) => event.key === 'Enter' && submit()}
    />
    <button class="search-btn" type="button" aria-label="Search" onclick={submit}>
      <Search size={18} />
    </button>
  </div>

  {#if input.trim() && !searching && total === 0}
    <p class="no-results">No matches for "{input.trim()}" in {scopeLabel}.</p>
  {/if}

  {#if results.length > 0}
    <div class="results">
      <div class="results-header">
        {total} match{total === 1 ? '' : 'es'} in {scopeLabel}
        {#if truncated}<span class="muted"> · showing first {results.length}</span>{/if}
      </div>

      {#each grouped as group}
        <div class="group">
          <button class="group-head" type="button" onclick={() => onopenVideo?.(group.videoId)}>
            <span class="group-title">{group.title || group.videoId}</span>
            <span class="group-channel">{group.channel || ''}</span>
            {#if group.subtitleType === 'auto'}<span class="auto-tag">auto</span>{/if}
          </button>

          {#each group.hits as hit}
            <div class="hit">
              <button class="time" type="button" title="Open at this time" onclick={() => open(hit)}>
                {formatTime(hit.start_ms)}
              </button>
              <span class="text">
                {#each splitHighlights(hit.highlight, hit.text) as part}
                  {#if part.match}<mark>{part.text}</mark>{:else}{part.text}{/if}
                {/each}
              </span>
              <div class="actions">
                <button type="button" title="Open in browser" onclick={() => open(hit)}>
                  <ExternalLink size={12} />
                </button>
                <button type="button" title="Copy timestamped link" onclick={() => copyLink(hit)}>
                  {#if copiedKey === `${hit.video_id}-${hit.start_ms}`}
                    <Check size={12} />
                  {:else}
                    <Copy size={12} />
                  {/if}
                </button>
              </div>
            </div>
          {/each}
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
    min-width: 0;
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

  .no-results {
    margin: 24px 0 0;
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
  }

  .results {
    margin-top: 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 4px;
  }

  .results-header {
    font-size: 12px;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .muted {
    color: var(--text-muted);
    opacity: 0.75;
  }

  .group {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    /* The results list is a flex column, so without this every card shrinks to
       share the visible height and clips its own hits instead of scrolling. */
    flex-shrink: 0;
  }

  .group-head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    width: 100%;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--border);
    padding: 10px 14px;
    cursor: pointer;
    text-align: left;
  }

  .group-head:hover {
    background: var(--bg-input);
  }

  .group-title {
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .group-channel {
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
  }

  .auto-tag {
    margin-left: auto;
    font-size: 10px;
    color: var(--text-muted);
    background: var(--border-input);
    padding: 1px 5px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .hit {
    display: grid;
    grid-template-columns: 56px 1fr auto;
    gap: 12px;
    align-items: start;
    padding: 12px 14px;
  }

  /* Hairline between hits so a wrapped line never reads as the next result. */
  .hit + .hit {
    border-top: 1px solid var(--border);
  }

  .hit:hover {
    background: var(--bg-input);
  }

  .time {
    color: var(--accent);
    font-size: 12px;
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
    color: var(--text);
    font-size: 14px;
    line-height: 1.6;
  }

  mark {
    background: var(--mark-bg);
    color: var(--mark-text);
    border-radius: 3px;
    padding: 1px 3px;
    font-weight: 600;
  }

  .actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .hit:hover .actions {
    opacity: 1;
  }

  .actions button {
    background: var(--border-input);
    border: none;
    color: var(--text-secondary);
    padding: 4px 5px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
  }

  .actions button:hover {
    background: var(--border);
    color: var(--text);
  }
</style>
