<script>
  import { RefreshCw, Trash2, Radio, ListVideo } from 'lucide-svelte';

  let {
    sources = [],
    activeSourceId = '',
    busy = false,
    onselect,
    onsync,
    ondelete,
  } = $props();
</script>

{#if sources.length > 0}
  <div class="sources">
    <span class="label">Channels &amp; playlists</span>
    <ul>
      <li class:active={activeSourceId === ''}>
        <button class="pick" type="button" onclick={() => onselect?.('')}>
          <span class="name">All sources</span>
        </button>
      </li>
      {#each sources as source}
        <li class:active={activeSourceId === source.id}>
          <button class="pick" type="button" onclick={() => onselect?.(source.id)}>
            <span class="icon">
              {#if source.kind === 'channel'}
                <Radio size={13} />
              {:else}
                <ListVideo size={13} />
              {/if}
            </span>
            <span class="name" title={source.title || source.id}>
              {source.title || source.id}
            </span>
            <span class="count">{source.video_count}</span>
          </button>
          <div class="row-actions">
            <button
              type="button"
              title="Check for new videos"
              disabled={busy}
              onclick={() => onsync?.(source.id, false)}
            >
              <RefreshCw size={13} />
            </button>
            <button
              type="button"
              title="Remove this source"
              onclick={() => ondelete?.(source)}
            >
              <Trash2 size={13} />
            </button>
          </div>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .sources {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex-shrink: 0;
  }

  .label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 200px;
    overflow-y: auto;
  }

  li {
    display: flex;
    align-items: center;
    gap: 4px;
    border-radius: 6px;
    padding: 2px 4px;
  }

  li:hover {
    background: var(--border);
  }

  li.active {
    background: var(--accent-subtle);
  }

  .pick {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 7px;
    background: none;
    border: none;
    color: var(--text);
    cursor: pointer;
    padding: 5px 2px;
    min-width: 0;
    text-align: left;
  }

  .icon {
    display: flex;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  li.active .icon {
    color: var(--accent);
  }

  .name {
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .count {
    font-size: 10px;
    color: var(--text-muted);
    background: var(--border-input);
    border-radius: 10px;
    padding: 1px 6px;
    flex-shrink: 0;
  }

  .row-actions {
    display: flex;
    gap: 2px;
    opacity: 0;
    flex-shrink: 0;
  }

  li:hover .row-actions {
    opacity: 1;
  }

  .row-actions button {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
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
</style>
