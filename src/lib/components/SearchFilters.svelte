<script>
  import { t } from '../i18n/index.js';

  let { options, sources = [], onchange } = $props();

  // <input type="date"> speaks YYYY-MM-DD; upload dates are stored as YYYYMMDD.
  const toInput = (raw) => (raw ? `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}` : '');
  const fromInput = (value) => value.replaceAll('-', '');

  function set(patch) {
    onchange?.({ ...options, ...patch });
  }
</script>

<div class="filters">
  <div class="segmented" role="group" aria-label={t('filters.match')}>
    <button type="button" class:on={options.mode === 'phrase'} onclick={() => set({ mode: 'phrase' })}>
      {t('filters.phrase')}
    </button>
    <button type="button" class:on={options.mode === 'all'} onclick={() => set({ mode: 'all' })}>
      {t('filters.allWords')}
    </button>
  </div>

  <label class="check" title={t('filters.wholeWordsTooltip')}>
    <input type="checkbox" checked={options.whole_words} onchange={(e) => set({ whole_words: e.currentTarget.checked })} />
    {t('filters.wholeWords')}
  </label>

  <span class="sep"></span>

  <select value={options.source_id} onchange={(e) => set({ source_id: e.currentTarget.value })} aria-label={t('filters.source')}>
    <option value="">{t('filters.allSources')}</option>
    {#each sources as source}
      <option value={source.id}>{source.title || source.id}</option>
    {/each}
  </select>

  <select value={options.subtitle_type} onchange={(e) => set({ subtitle_type: e.currentTarget.value })} aria-label={t('filters.captions')}>
    <option value="">{t('filters.anyCaptions')}</option>
    <option value="manual">{t('filters.manualCaptions')}</option>
    <option value="auto">{t('filters.autoCaptions')}</option>
  </select>

  <label class="date">
    {t('filters.from')}
    <input type="date" value={toInput(options.date_from)} onchange={(e) => set({ date_from: fromInput(e.currentTarget.value) })} />
  </label>
  <label class="date">
    {t('filters.to')}
    <input type="date" value={toInput(options.date_to)} onchange={(e) => set({ date_to: fromInput(e.currentTarget.value) })} />
  </label>

</div>

<style>
  .filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 10px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .segmented {
    display: flex;
    border: 1px solid var(--border-input);
    border-radius: 7px;
    overflow: hidden;
  }

  .segmented button {
    background: var(--bg-input);
    border: none;
    color: var(--text-muted);
    padding: 5px 10px;
    font-size: 12px;
    cursor: pointer;
  }

  .segmented button + button {
    border-left: 1px solid var(--border-input);
  }

  .segmented button.on {
    background: var(--accent-subtle);
    color: var(--text);
  }

  .check,
  .date {
    display: flex;
    align-items: center;
    gap: 5px;
    cursor: pointer;
  }

  .check input {
    margin: 0;
  }

  .sep {
    width: 1px;
    height: 18px;
    background: var(--border);
  }

  select,
  .date input {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    border-radius: 7px;
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
    max-width: 200px;
  }

  .date input {
    color-scheme: light dark;
  }
</style>
