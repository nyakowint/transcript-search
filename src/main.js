import { mount } from 'svelte';
import App from './lib/App.svelte';

function start() {
  const target = document.getElementById('app');
  if (!target) {
    throw new Error('App mount point not found.');
  }
  mount(App, { target });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start);
} else {
  start();
}
