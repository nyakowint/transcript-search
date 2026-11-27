import { mount } from 'svelte';
import App from './lib/App.svelte';

function start() {
  const target = document.getElementById('app');
  if (!target) {
    throw new Error('App mount point not found.');
  }
  try {
    mount(App, { target });
  } catch (error) {
    // Without this a startup crash is just an empty window.
    target.style.cssText = 'padding:24px;font:13px monospace;white-space:pre-wrap;color:#ff8a8a';
    target.textContent = `The UI failed to start:\n\n${error?.stack || error}`;
    throw error;
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start);
} else {
  start();
}
