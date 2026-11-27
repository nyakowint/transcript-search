<script>
  import { LoaderCircle, CircleCheck, CircleAlert, X } from 'lucide-svelte';
  import JobProgress from './JobProgress.svelte';
  import { t } from '../i18n/index.js';

  let { job, oncancel, ondismiss } = $props();

  let open = $state(false);
  const running = $derived(job.status === 'running');
  const failed = $derived(job.status === 'error');

  const label = $derived.by(() => {
    if (running) {
      return job.total ? `${job.completed} / ${job.total}` : t('job.findingVideos');
    }
    if (failed) return t('job.fetchFailed');
    if (job.status === 'cancelled') return t('job.cancelled');
    return t('job.done');
  });
</script>

<svelte:window onclick={() => (open = false)} />

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="wrap" onclick={(event) => event.stopPropagation()}>
  <button class="chip" class:failed type="button" onclick={() => (open = !open)}>
    {#if running}
      <span class="spin"><LoaderCircle size={14} /></span>
    {:else if failed}
      <CircleAlert size={14} />
    {:else}
      <CircleCheck size={14} />
    {/if}
    <span>{label}</span>
  </button>
  {#if !running}
    <button class="dismiss" type="button" aria-label={t('job.dismiss')} onclick={() => ondismiss?.()}>
      <X size={13} />
    </button>
  {/if}

  {#if open}
    <div class="popover">
      <JobProgress {job} {oncancel} />
    </div>
  {/if}
</div>

<style>
  .wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .chip {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text-secondary);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
  }

  .chip:hover {
    color: var(--text);
  }

  .chip.failed {
    color: var(--error);
  }

  .spin {
    display: flex;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .dismiss {
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 4px;
    cursor: pointer;
    display: flex;
  }

  .dismiss:hover {
    color: var(--text);
  }

  .popover {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    width: 340px;
    z-index: 40;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    border-radius: 8px;
  }
</style>
