<script>
  import { RefreshCw, Trash2, Radio, ListVideo } from 'lucide-svelte';
  import { t } from '../i18n/index.js';

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
  <section class="sources">
    <h2>{t('sources.label')}</h2>
    <div class="chips">
      <button class="chip" class:active={activeSourceId === ''} type="button" onclick={() => onselect?.('')}>
        {t('sources.allSources')}
      </button>
      {#each sources as source (source.id)}
        <div class="chip" class:active={activeSourceId === source.id}>
          <button class="pick" type="button" title={source.url} onclick={() => onselect?.(source.id)}>
            {#if source.kind === 'channel'}<Radio size={13} />{:else}<ListVideo size={13} />{/if}
            <span class="name">{source.title || source.id}</span>
            <span class="count">{source.video_count}</span>
          </button>
          <button
            class="icon"
            type="button"
            title={t('sources.checkForNew')}
            disabled={busy}
            onclick={() => onsync?.(source.id, false)}
          >
            <RefreshCw size={12} />
          </button>
          <button class="icon" type="button" title={t('sources.removeSource')} onclick={() => ondelete?.(source)}>
            <Trash2 size={12} />
          </button>
        </div>
      {/each}
    </div>
  </section>
{/if}

<style>
  .sources {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  h2 {
    margin: 0;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    display: flex;
    align-items: center;
    gap: 2px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 13px;
    padding: 0 4px 0 0;
    max-width: 100%;
  }

  button.chip {
    padding: 6px 12px;
    cursor: pointer;
  }

  .chip:hover {
    border-color: var(--border-input);
  }

  .chip.active {
    border-color: var(--accent);
    background: var(--accent-subtle);
  }

  .pick {
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
    background: none;
    border: none;
    color: inherit;
    font-size: 13px;
    padding: 6px 6px 6px 10px;
    cursor: pointer;
  }

  .pick :global(svg) {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 260px;
  }

  .count {
    font-size: 11px;
    color: var(--text-muted);
  }

  .icon {
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 4px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
  }

  .icon:hover:not(:disabled) {
    color: var(--text);
    background: var(--border);
  }

  .icon:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
