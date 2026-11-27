<script>
  import { Download } from 'lucide-svelte';
  import ResultCard from './ResultCard.svelte';
  import { t } from '../i18n/index.js';

  let { result, query, sort, onsort, loading = false, loadingMore = false, onloadMore, onexport, onengage } = $props();

  const remaining = $derived(result.total_videos - result.videos.length);
</script>

<section class="results">
  {#if result.total_videos === 0}
    {#if !loading}
      <p class="empty">{t('results.none', query.trim())}</p>
    {/if}
  {:else}
    <div class="summary">
      <span>{t('results.summary', result.total_hits, result.total_videos)}</span>
      <select value={sort} onchange={(e) => onsort?.(e.currentTarget.value)} aria-label={t('filters.sort')}>
        <option value="relevance">{t('filters.sortRelevance')}</option>
        <option value="hits">{t('filters.sortHits')}</option>
        <option value="newest">{t('filters.sortNewest')}</option>
        <option value="oldest">{t('filters.sortOldest')}</option>
      </select>
      <div class="export" title={t('results.exportTooltip')}>
        <Download size={13} />
        <button type="button" onclick={() => onexport?.('csv')}>{t('results.exportCsv')}</button>
        <button type="button" onclick={() => onexport?.('md')}>{t('results.exportMarkdown')}</button>
      </div>
    </div>

    {#each result.videos as video (video.id)}
      <ResultCard {video} {onengage} />
    {/each}

    {#if result.has_more}
      <button class="more" type="button" disabled={loadingMore} onclick={() => onloadMore?.()}>
        {loadingMore ? t('results.loading') : t('results.loadMore', remaining)}
      </button>
    {/if}
  {/if}
</section>

<style>
  .results {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .summary {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: var(--text-muted);
  }

  select {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text-secondary);
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 12px;
    font-family: inherit;
  }

  .export {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .export button {
    background: none;
    border: none;
    padding: 0;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
  }

  .export button:hover {
    color: var(--text);
    text-decoration: underline;
  }

  .empty {
    margin: 32px 0;
    text-align: center;
    font-size: 13px;
    color: var(--text-muted);
  }

  .more {
    align-self: center;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
  }

  .more:hover:not(:disabled) {
    background: var(--border);
  }

  .more:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
