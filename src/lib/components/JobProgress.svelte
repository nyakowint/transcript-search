<script>
  import { X } from 'lucide-svelte';

  let { job = null, oncancel } = $props();

  const running = $derived(job?.status === 'running');
  const percent = $derived.by(() => {
    if (!job) return 0;
    if (job.phase === 'expanding') return 0;
    if (!job.total) return job.status === 'running' ? 0 : 100;
    return Math.min(100, Math.round((job.completed / job.total) * 100));
  });

  const headline = $derived.by(() => {
    if (!job) return '';
    if (job.status === 'error') return job.message || 'Fetch failed';
    if (job.status === 'cancelled') return 'Cancelled';
    if (job.status === 'done') {
      if (job.message) return job.message;
      const bits = [`${job.ok} fetched`];
      if (job.skipped) bits.push(`${job.skipped} already stored`);
      if (job.missing) bits.push(`${job.missing} without captions`);
      if (job.failed) bits.push(`${job.failed} failed`);
      return bits.join(' · ');
    }
    if (job.phase === 'expanding') {
      return job.message || 'Finding videos...';
    }
    return `${job.completed} / ${job.total} · ${job.current || 'working...'}`;
  });
</script>

{#if job}
  <div class="job" class:error={job.status === 'error'} class:done={job.status === 'done'}>
    <div class="job-top">
      <span class="job-label">{job.label}</span>
      {#if running}
        <button class="cancel" type="button" title="Cancel" onclick={() => oncancel?.()}>
          <X size={14} />
        </button>
      {/if}
    </div>

    <div class="bar" class:indeterminate={running && job.phase === 'expanding'}>
      <div class="fill" style:width="{percent}%"></div>
    </div>

    <div class="job-status">{headline}</div>

    {#if job.error_count > 0}
      <details class="errors">
        <summary>{job.error_count} error{job.error_count === 1 ? '' : 's'}</summary>
        <ul>
          {#each job.errors as item}
            <li>{item.video_id || item.url || ''} {item.error}</li>
          {/each}
        </ul>
      </details>
    {/if}
  </div>
{/if}

<style>
  .job {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  .job.error {
    border-color: var(--error);
  }

  .job-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .job-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cancel {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 2px;
    display: flex;
    flex-shrink: 0;
  }

  .cancel:hover {
    color: var(--error);
  }

  .bar {
    height: 4px;
    border-radius: 2px;
    background: var(--border);
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: var(--accent);
    transition: width 0.2s ease;
  }

  .job.done .fill {
    background: var(--success);
  }

  .job.error .fill {
    background: var(--error);
  }

  /* Enumeration has no known total, so the bar sweeps instead of filling. */
  .bar.indeterminate .fill {
    width: 35% !important;
    animation: sweep 1.1s ease-in-out infinite;
  }

  @keyframes sweep {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(340%); }
  }

  .job-status {
    font-size: 11px;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .errors {
    font-size: 11px;
    color: var(--error);
  }

  .errors summary {
    cursor: pointer;
  }

  .errors ul {
    margin: 6px 0 0;
    padding-left: 16px;
    max-height: 120px;
    overflow-y: auto;
  }

  .errors li {
    color: var(--text-muted);
    margin-bottom: 3px;
    word-break: break-word;
  }
</style>
