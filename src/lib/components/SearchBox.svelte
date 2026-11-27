<script>
  import { Search, X, History } from 'lucide-svelte';
  import { t } from '../i18n/index.js';

  // `/` anywhere outside a text field focuses the box (wired up in App).
  let { value = $bindable(''), placeholder = '', recent = [], input = $bindable(), onsubmit, onclearRecent } = $props();

  let focused = $state(false);
  const showRecent = $derived(focused && !value.trim() && recent.length > 0);

  function pick(query) {
    value = query;
    onsubmit?.(query);
    input?.blur();
  }

  function handleKeydown(event) {
    if (event.key === 'Enter') onsubmit?.(value);
    else if (event.key === 'Escape') {
      if (value) value = '';
      else input?.blur();
    }
  }
</script>

<div class="box" class:open={showRecent}>
  <Search size={16} />
  <input
    bind:this={input}
    bind:value
    type="text"
    {placeholder}
    spellcheck="false"
    onfocus={() => (focused = true)}
    onblur={() => (focused = false)}
    onkeydown={handleKeydown}
  />
  {#if value}
    <button class="clear" type="button" aria-label={t('search.clear')} onclick={() => { value = ''; input?.focus(); }}>
      <X size={15} />
    </button>
  {:else}
    <kbd title={t('search.focusHint')}>/</kbd>
  {/if}

  {#if showRecent}
    <!-- mousedown fires before the input's blur would close this list -->
    <div class="recent" role="listbox" tabindex="-1" onmousedown={(event) => event.preventDefault()}>
      <div class="recent-head">
        <span>{t('search.recent')}</span>
        <button type="button" onclick={() => onclearRecent?.()}>{t('search.clearRecent')}</button>
      </div>
      {#each recent as query}
        <button class="recent-item" type="button" role="option" aria-selected="false" onclick={() => pick(query)}>
          <History size={13} />
          <span>{query}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .box {
    position: relative;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 12px;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    border-radius: 10px;
    color: var(--text-muted);
  }

  .box:focus-within {
    border-color: var(--accent);
  }

  input {
    flex: 1;
    min-width: 0;
    padding: 10px 0;
    border: none;
    background: transparent;
    color: var(--text);
    font-size: 15px;
    outline: none;
  }

  input::placeholder {
    color: var(--text-muted);
  }

  .clear {
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 2px;
    cursor: pointer;
    display: flex;
  }

  .clear:hover {
    color: var(--text);
  }

  kbd {
    font-family: "SF Mono", "Consolas", monospace;
    font-size: 11px;
    color: var(--text-muted);
    border: 1px solid var(--border-input);
    border-radius: 4px;
    padding: 0 5px;
  }

  .recent {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    right: 0;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 6px;
    z-index: 30;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  }

  .recent-head {
    display: flex;
    justify-content: space-between;
    padding: 4px 8px 6px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .recent-head button {
    background: none;
    border: none;
    padding: 0;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
  }

  .recent-head button:hover {
    color: var(--text);
  }

  .recent-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 8px;
    background: none;
    border: none;
    border-radius: 6px;
    color: var(--text-secondary);
    font-size: 13px;
    text-align: left;
    cursor: pointer;
  }

  .recent-item:hover {
    background: var(--border);
    color: var(--text);
  }

  .recent-item span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
