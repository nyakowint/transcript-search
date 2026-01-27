<script>
  let { transcript = [], videoId = '', sourceUrl = '' } = $props();

  function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const padded = (value) => String(value).padStart(2, '0');
    if (hours > 0) {
      return `${hours}:${padded(minutes)}:${padded(seconds)}`;
    }
    return `${minutes}:${padded(seconds)}`;
  }

  function getTimestampUrl(ms) {
    const seconds = Math.floor(ms / 1000);
    return `https://www.youtube.com/watch?v=${videoId}&t=${seconds}s`;
  }

  function openInBrowser(ms) {
    window.open(getTimestampUrl(ms), '_blank');
  }

  async function copyLink(ms) {
    try {
      await navigator.clipboard.writeText(getTimestampUrl(ms));
    } catch {
      // Fallback for older browsers
      const url = getTimestampUrl(ms);
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }
</script>

<div class="transcript-panel">
  {#if transcript.length > 0}
    <div class="panel-header">
      <span class="count">{transcript.length} lines</span>
    </div>
  {/if}
  <div class="transcript-list">
    {#if transcript.length === 0}
      <p class="empty">Select a video to view its transcript.</p>
    {:else}
      {#each transcript as segment}
        <div class="segment">
          <span class="time">{formatTime(segment.start_ms)}</span>
          <span class="text">{segment.text}</span>
          <div class="actions">
            <button type="button" title="Open" onclick={() => openInBrowser(segment.start_ms)}>↗</button>
            <button type="button" title="Copy" onclick={() => copyLink(segment.start_ms)}>📋</button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .transcript-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-bottom: 8px;
    flex-shrink: 0;
  }

  .count {
    font-size: 11px;
    color: var(--text-muted);
  }

  .transcript-list {
    flex: 1;
    overflow-y: auto;
  }

  .segment {
    display: grid;
    grid-template-columns: 50px 1fr auto;
    gap: 10px;
    padding: 8px 4px;
    border-radius: 6px;
    align-items: start;
  }

  .segment:hover {
    background: var(--border);
  }

  .time {
    color: var(--accent);
    font-size: 11px;
    font-family: "SF Mono", "Consolas", monospace;
  }

  .text {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.4;
  }

  .actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .segment:hover .actions {
    opacity: 1;
  }

  .actions button {
    background: var(--border-input);
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    padding: 3px 5px;
    border-radius: 4px;
    cursor: pointer;
  }

  .actions button:hover {
    background: var(--border);
    color: var(--text);
  }

  .empty {
    color: var(--text-muted);
    font-size: 13px;
    margin: 0;
  }
</style>
