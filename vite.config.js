import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'node:path';

export default defineConfig({
  root: 'src',
  base: './',
  plugins: [svelte()],
  build: {
    outDir: '../ui',
    emptyOutDir: true,
    assetsDir: '.',
    cssCodeSplit: false,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
