<script>
  import { ChevronDown, ChevronRight } from 'lucide-svelte';

  let {
    settings = {},
    busy = false,
    onfetch,
    onsettingchange,
  } = $props();

  let urlsInput = $state('');
  let optionsOpen = $state(false);

  const TAB_LABELS = {
    videos: 'Videos',
    shorts: 'Shorts',
    streams: 'Live',
  };

  const selectedTabs = $derived(
    String(settings.channel_tabs || 'videos')
      .split(',')
      .map((tab) => tab.trim())
      .filter(Boolean)
  );

  function toggleTab(tab) {
    const next = selectedTabs.includes(tab)
      ? selectedTabs.filter((item) => item !== tab)
      : [...selectedTabs, tab];
    // An empty tab list would silently enumerate nothing.
    onsettingchange?.({ channel_tabs: (next.length ? next : [tab]).join(',') });
  }

  function setSetting(key, value) {
    onsettingchange?.({ [key]: value });
  }

  function submit() {
    if (!urlsInput.trim() || busy) return;
    onfetch?.(urlsInput);
  }

  function handleKeydown(event) {
    // Ctrl/Cmd+Enter submits; plain Enter keeps making new lines.
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      submit();
    }
  }
</script>

<div class="ingest">
  <textarea
    bind:value={urlsInput}
    onkeydown={handleKeydown}
    placeholder="Channel, playlist, or video URLs — one per line&#10;e.g. youtube.com/@3blue1brown"
    rows="3"
  ></textarea>

  <button class="primary" onclick={submit} disabled={busy || !urlsInput.trim()}>
    {busy ? 'Fetching...' : 'Fetch captions'}
  </button>

  <button class="disclosure" type="button" onclick={() => (optionsOpen = !optionsOpen)}>
    {#if optionsOpen}<ChevronDown size={13} />{:else}<ChevronRight size={13} />{/if}
    Options
  </button>

  {#if optionsOpen}
    <div class="options">
      <div class="field">
        <span class="field-label">Channel tabs</span>
        <div class="chips">
          {#each Object.entries(TAB_LABELS) as [tab, label]}
            <button
              type="button"
              class="chip"
              class:on={selectedTabs.includes(tab)}
              onclick={() => toggleTab(tab)}
            >{label}</button>
          {/each}
        </div>
      </div>

      <div class="field">
        <label class="field-label" for="langs">Preferred languages</label>
        <input
          id="langs"
          type="text"
          value={settings.preferred_languages || 'en'}
          placeholder="en, ja"
          onchange={(e) => setSetting('preferred_languages', e.currentTarget.value)}
        />
      </div>

      <label class="check">
        <input
          type="checkbox"
          checked={settings.allow_auto !== '0'}
          onchange={(e) => setSetting('allow_auto', e.currentTarget.checked ? '1' : '0')}
        />
        Use auto-generated captions when there is no manual track
      </label>

      <label class="check">
        <input
          type="checkbox"
          checked={settings.allow_other_languages !== '0'}
          onchange={(e) =>
            setSetting('allow_other_languages', e.currentTarget.checked ? '1' : '0')}
        />
        Fall back to other languages
      </label>

      <label class="check">
        <input
          type="checkbox"
          checked={settings.skip_existing !== '0'}
          onchange={(e) => setSetting('skip_existing', e.currentTarget.checked ? '1' : '0')}
        />
        Skip videos already stored
      </label>

      <div class="row">
        <div class="field">
          <label class="field-label" for="concurrency">Parallel</label>
          <input
            id="concurrency"
            type="number"
            min="1"
            max="16"
            value={settings.concurrency || '6'}
            onchange={(e) => setSetting('concurrency', e.currentTarget.value)}
          />
        </div>
        <div class="field">
          <label class="field-label" for="maxvideos">Limit (0 = all)</label>
          <input
            id="maxvideos"
            type="number"
            min="0"
            value={settings.max_videos || '0'}
            onchange={(e) => setSetting('max_videos', e.currentTarget.value)}
          />
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .ingest {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  textarea {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 10px 12px;
    border-radius: 8px;
    resize: vertical;
    font-size: 13px;
    line-height: 1.4;
    font-family: inherit;
  }

  textarea::placeholder {
    color: var(--text-muted);
  }

  .primary {
    background: var(--accent);
    border: none;
    color: white;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
  }

  .primary:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .primary:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .disclosure {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    padding: 2px 0;
    align-self: flex-start;
  }

  .disclosure:hover {
    color: var(--text);
  }

  .options {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 0;
  }

  .field-label {
    font-size: 11px;
    color: var(--text-muted);
  }

  .field input {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 12px;
  }

  .row {
    display: flex;
    gap: 8px;
  }

  .chips {
    display: flex;
    gap: 6px;
  }

  .chip {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text-muted);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    cursor: pointer;
  }

  .chip.on {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
  }

  .check {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
    line-height: 1.35;
  }

  .check input {
    margin: 1px 0 0;
    flex-shrink: 0;
  }
</style>
