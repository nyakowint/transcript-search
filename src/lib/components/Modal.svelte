<script>
  import { X } from 'lucide-svelte';
  import { t } from '../i18n/index.js';

  let { title = '', width = 460, onclose, children } = $props();
</script>

<div
  class="overlay"
  role="presentation"
  onclick={() => onclose?.()}
  onkeydown={(event) => event.key === 'Escape' && onclose?.()}
>
  <div
    class="modal"
    role="dialog"
    aria-modal="true"
    aria-label={title}
    tabindex="-1"
    style:max-width="{width}px"
    onclick={(event) => event.stopPropagation()}
    onkeydown={(event) => event.key === 'Escape' && onclose?.()}
  >
    <div class="head">
      <h3>{title}</h3>
      <button class="close" type="button" aria-label={t('common.close')} onclick={() => onclose?.()}>
        <X size={16} />
      </button>
    </div>
    {@render children()}
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 10vh 16px 16px;
    z-index: 100;
  }

  .modal {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px 20px;
    width: 100%;
    max-height: 80vh;
    overflow-y: auto;
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
  }

  .close {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
  }

  .close:hover {
    color: var(--text);
    background: var(--border);
  }
</style>
