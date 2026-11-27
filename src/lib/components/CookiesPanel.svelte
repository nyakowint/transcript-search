<script>
  import { t } from '../i18n/index.js';

  let { cookiesPath = '', cookiesBrowser = '', onchange, onbrowse } = $props();

  const browsers = [
    { label: t('cookies.browsers.none'), value: '' },
    { label: t('cookies.browsers.chrome'), value: 'chrome' },
    { label: t('cookies.browsers.edge'), value: 'edge' },
    { label: t('cookies.browsers.firefox'), value: 'firefox' },
    { label: t('cookies.browsers.brave'), value: 'brave' },
    { label: t('cookies.browsers.vivaldi'), value: 'vivaldi' },
    { label: t('cookies.browsers.opera'), value: 'opera' },
    { label: t('cookies.browsers.chromium'), value: 'chromium' },
    { label: t('cookies.browsers.safari'), value: 'safari' },
  ];

  function emit(patch) {
    onchange?.({ cookies_path: cookiesPath, cookies_browser: cookiesBrowser, ...patch });
  }
</script>

<div class="cookies">
  <p class="hint">
    {t('cookies.hint')}
  </p>
  <div class="field">
    <label for="cookies-path">{t('cookies.fileLabel')}</label>
    <div class="input-group">
      <input
        id="cookies-path"
        type="text"
        bind:value={cookiesPath}
        onchange={() => emit({ cookies_path: cookiesPath })}
        placeholder={t('cookies.filePlaceholder')}
      />
      <button class="secondary" type="button" onclick={() => onbrowse?.()}>{t('cookies.browse')}</button>
    </div>
  </div>
  <div class="field">
    <label for="cookies-browser">{t('cookies.browserLabel')}</label>
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
