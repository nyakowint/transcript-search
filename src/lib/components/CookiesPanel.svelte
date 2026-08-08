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
    { label: 'Chromium', value: 'chromium' },
    { label: 'Safari', value: 'safari' },
  ];

  function emit(patch) {
    onchange?.({ cookies_path: cookiesPath, cookies_browser: cookiesBrowser, ...patch });
  }
</script>

<div class="cookies">
  <p class="hint">
    Only needed for age-restricted, members-only, or rate-limited fetches.
  </p>
  <div class="field">
    <label for="cookies-path">Cookies file</label>
    <div class="input-group">
      <input
        id="cookies-path"
        type="text"
        bind:value={cookiesPath}
        onchange={() => emit({ cookies_path: cookiesPath })}
        placeholder="Path to cookies.txt"
      />
      <button class="secondary" type="button" onclick={() => onbrowse?.()}>Browse</button>
    </div>
  </div>
  <div class="field">
    <label for="cookies-browser">Or read cookies from a browser</label>
    <select
      id="cookies-browser"
      bind:value={cookiesBrowser}
      onchange={() => emit({ cookies_browser: cookiesBrowser })}
    >
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

  .hint {
    margin: 0;
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
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
    font-size: 13px;
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
    font-size: 13px;
  }

  .secondary:hover {
    background: var(--border);
  }
</style>
