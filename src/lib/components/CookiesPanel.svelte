<script>
  let { cookiesPath = '', cookiesBrowser = '', onchange, onbrowse } = $props();

  const browsers = [
    { label: 'None', value: '' },
    { label: 'Chrome', value: 'chrome' },
    { label: 'Edge', value: 'edge' },
    { label: 'Firefox', value: 'firefox' },
    { label: 'Brave', value: 'brave' },
    { label: 'Vivaldi', value: 'vivaldi' },
    { label: 'Opera', value: 'opera' },
  ];

  function handleChange() {
    onchange?.({ detail: { cookiesPath, cookiesBrowser } });
  }
</script>

<div class="cookies">
  <div class="field">
    <label for="cookies-path">Cookies file (optional)</label>
    <div class="input-group">
      <input
        id="cookies-path"
        type="text"
        bind:value={cookiesPath}
        onchange={handleChange}
        placeholder="Paste cookies file path or browse..."
      />
      <button class="secondary" type="button" onclick={() => onbrowse?.()}>
        Browse
      </button>
    </div>
  </div>
  <div class="field">
    <label for="cookies-browser">Or import cookies from browser</label>
    <select id="cookies-browser" bind:value={cookiesBrowser} onchange={handleChange}>
      {#each browsers as browser}
        <option value={browser.value}>{browser.label}</option>
      {/each}
    </select>
  </div>
</div>

<style>
  .cookies {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .field label {
    display: block;
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .field input,
  .field select {
    width: 100%;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--border-input);
    background: var(--bg-input);
    color: var(--text);
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .secondary {
    background: var(--border-input);
    border: none;
    color: var(--text);
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
  }

  .secondary:hover {
    background: var(--border);
  }
</style>
