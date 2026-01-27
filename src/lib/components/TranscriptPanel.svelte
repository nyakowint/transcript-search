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

<div class="panel">
  <div class="panel-header">
    <h2>Transcript</h2>
    <span>{transcript.length} lines</span>
  </div>
  <div class="transcript">
    {#if transcript.length === 0}
      <p class="empty">Select a video to see its transcript.</p>
    {:else}
      {#each transcript as segment}
        <div class="segment">
          <span class="time">{formatTime(segment.start_ms)}</span>
          <span class="text">{segment.text}</span>
          <div class="actions">
            <button type="button" title="Open in browser" on:click={() => openInBrowser(segment.start_ms)}>
              ↗
            </button>
            <button type="button" title="Copy link" on:click={() => copyLink(segment.start_ms)}>
              📋
            </button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .panel {
    background: #171a21;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .panel-header span {
    color: #b5b9c5;
    font-size: 12px;
  }

  .transcript {
    max-height: 320px;
    overflow: auto;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    padding: 8px;
    background: #0f1115;
  }

  .segment {
    display: grid;
    grid-template-columns: 60px 1fr auto;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid #1f232b;
    align-items: start;
  }

  .time {
    color: #7aa2ff;
  }

  .text {
    color: #f2f2f2;
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
    background: #2a2f3a;
    border: none;
    color: #b5b9c5;
    font-size: 12px;
    padding: 4px 6px;
    border-radius: 4px;
    cursor: pointer;
  }

  .actions button:hover {
    background: #3a4050;
    color: #f2f2f2;
  }

  .empty {
    color: #8c92a2;
  }
</style>
