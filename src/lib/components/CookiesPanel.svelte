<script>
  import { createEventDispatcher } from 'svelte';

  export let cookiesPath = '';
  export let cookiesBrowser = '';

  const dispatch = createEventDispatcher();

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
    dispatch('change', { cookiesPath, cookiesBrowser });
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
        on:change={handleChange}
        placeholder="Paste cookies file path or browse..."
      />
      <button class="secondary" type="button" on:click={() => dispatch('browse')}>
        Browse
      </button>
    </div>
  </div>
  <div class="field">
    <label for="cookies-browser">Cookies from browser (optional)</label>
    <select id="cookies-browser" bind:value={cookiesBrowser} on:change={handleChange}>
      {#each browsers as browser}
        <option value={browser.value}>{browser.label}</option>
      {/each}
    </select>
  </div>
</div>

<style>
  .cookies {
    display: grid;
    grid-template-columns: 1fr 220px;
    gap: 12px;
  }

  .field label {
    display: block;
    font-size: 12px;
    color: #b5b9c5;
    margin-bottom: 6px;
  }

  .field input,
  .field select {
    width: 100%;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid #2a2f3a;
    background: #0f1115;
    color: #f2f2f2;
  }

  .input-group {
    display: flex;
    gap: 8px;
  }

  .input-group input {
    flex: 1;
  }

  .secondary {
    background: #2a2f3a;
    border: none;
    color: #f2f2f2;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
  }

  .secondary:hover {
    background: #3a4050;
  }

  @media (max-width: 960px) {
    .cookies {
      grid-template-columns: 1fr;
    }
  }
</style>