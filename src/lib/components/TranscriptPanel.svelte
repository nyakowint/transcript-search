<script>
  let { transcript = [] } = $props();

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
          <span>{segment.text}</span>
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
    grid-template-columns: 60px 1fr;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid #1f232b;
  }

  .time {
    color: #7aa2ff;
  }

  .empty {
    color: #8c92a2;
  }
</style>
