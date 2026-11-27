<script>
  import { ExternalLink, Copy, Check, ScrollText } from 'lucide-svelte';
  import TranscriptPanel from './TranscriptPanel.svelte';
  import { formatTime, formatDuration, formatUploadDate, timestampUrl, copyText, splitHit } from '../format.js';
  import { t } from '../i18n/index.js';

  let { video, onengage } = $props();

  const PREVIEW_HITS = 3;

  let expanded = $state(false);
  let transcriptOpen = $state(false);
  let focusId = $state(null);
  let copiedId = $state(null);

  const shownHits = $derived(expanded ? video.hits : video.hits.slice(0, PREVIEW_HITS));
  const hiddenHits = $derived(video.hits.length - shownHits.length);
  const hitIds = $derived(video.hits.map((hit) => hit.id));
  const meta = $derived(
    [video.channel, formatUploadDate(video.upload_date), formatDuration(video.duration)].filter(Boolean)
  );

  function open(hit) {
    onengage?.();
    window.open(timestampUrl(video.id, hit.start_ms), '_blank');
  }

  async function copyLink(hit) {
    onengage?.();
    await copyText(timestampUrl(video.id, hit.start_ms));
    copiedId = hit.id;
    setTimeout(() => {
      if (copiedId === hit.id) copiedId = null;
    }, 1200);
  }

  function showInTranscript(hit) {
    focusId = hit.id;
    transcriptOpen = true;
  }

  function toggleTranscript() {
    transcriptOpen = !transcriptOpen;
    if (transcriptOpen && focusId == null) focusId = video.hits[0]?.id ?? null;
  }
</script>

<article class="card">
  <header>
    <div class="title-row">
      <a class="title" href={timestampUrl(video.id, 0)} target="_blank" rel="noreferrer" title={video.title}>
        {video.title || video.id}
      </a>
      <span class="count">{t('results.hitCount', video.hit_count)}</span>
    </div>
    <div class="meta">
      {#each meta as bit, i}{#if i > 0}<span class="dot">·</span>{/if}<span>{bit}</span>{/each}
      {#if video.subtitle_type === 'auto'}<span class="tag">{t('results.autoCaptions')}</span>{/if}
    </div>
  </header>

  <ul class="hits">
    {#each shownHits as hit (hit.id)}
      <li>
        <button class="time" type="button" title={t('common.openAtTime')} onclick={() => open(hit)}>
          {formatTime(hit.start_ms)}
        </button>
        <p class="text">
          {#if hit.before}<span class="before">{hit.before} </span>{/if}
          {#each splitHit(hit.highlight, hit.cue_length) as part}{#if part.match}<mark class:soft={part.trailing}>{part.text}</mark>{:else if part.trailing}<span class="after">{part.text}</span>{:else}{part.text}{/if}{/each}
        </p>
        <div class="actions">
          <button type="button" title={t('results.showInTranscript')} onclick={() => showInTranscript(hit)}>
            <ScrollText size={13} />
          </button>
          <button type="button" title={t('common.openInBrowser')} onclick={() => open(hit)}>
            <ExternalLink size={13} />
          </button>
          <button type="button" title={t('common.copyLink')} onclick={() => copyLink(hit)}>
            {#if copiedId === hit.id}<Check size={13} />{:else}<Copy size={13} />{/if}
          </button>
        </div>
      </li>
    {/each}
  </ul>

  <footer>
    {#if hiddenHits > 0}
      <button class="link" type="button" onclick={() => (expanded = true)}>
        {t('results.showMoreHits', hiddenHits)}
      </button>
    {:else if expanded && video.hits.length > PREVIEW_HITS}
      <button class="link" type="button" onclick={() => (expanded = false)}>{t('results.showFewerHits')}</button>
    {/if}
    <button class="link" type="button" onclick={toggleTranscript}>
      {transcriptOpen ? t('results.hideTranscript') : t('results.showTranscript')}
    </button>
  </footer>

  {#if transcriptOpen}
    <div class="transcript">
      <TranscriptPanel videoId={video.id} {hitIds} {focusId} />
    </div>
  {/if}
</article>

<style>
  .card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  header {
    padding: 12px 16px 10px;
    border-bottom: 1px solid var(--border);
  }

  .title-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  .title {
    flex: 1;
    min-width: 0;
    color: var(--text);
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .title:hover {
    text-decoration: underline;
  }

  .count {
    font-size: 12px;
    color: var(--text-secondary);
    white-space: nowrap;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: 3px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .tag {
    font-size: 10px;
    background: var(--border-input);
    color: var(--text-secondary);
    padding: 1px 5px;
    border-radius: 4px;
  }

  .hits {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .hits li {
    display: grid;
    grid-template-columns: 56px 1fr auto;
    gap: 12px;
    align-items: start;
    padding: 10px 16px;
  }

  .hits li + li {
    border-top: 1px solid var(--border);
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
    margin: 0;
    color: var(--text);
    font-size: 14px;
    line-height: 1.6;
  }

  .before,
  .after {
    color: var(--text-muted);
  }

  mark {
    background: var(--mark-bg);
    color: var(--mark-text);
    border-radius: 3px;
    padding: 1px 2px;
  }

  mark.soft {
    background: transparent;
    color: var(--text-secondary);
    text-decoration: underline;
    text-decoration-color: var(--mark-bg);
    text-underline-offset: 3px;
  }

  .actions {
    display: flex;
    gap: 4px;
    opacity: 0;
  }

  .hits li:hover .actions,
  .actions:focus-within {
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
    color: var(--text);
  }

  footer {
    display: flex;
    gap: 16px;
    padding: 8px 16px 10px;
    border-top: 1px solid var(--border);
  }

  .link {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
    padding: 0;
  }

  .link:hover {
    color: var(--text);
  }

  .transcript {
    padding: 0 16px 14px;
  }
</style>
