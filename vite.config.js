import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Folds the built JS and CSS into index.html so the UI is one file. There are
// no hashed asset files beside it that can go stale, half-copy or get lost.
function inlineAssets() {
  return {
    name: 'inline-assets',
    enforce: 'post',
    generateBundle(_, bundle) {
      const html = bundle['index.html'];
      let source = String(html.source);
      for (const [fileName, output] of Object.entries(bundle)) {
        const ref = new RegExp(`<(script|link)[^>]*\\./${fileName.replace(/[.]/g, '\\.')}"[^>]*>(</script>)?`);
        if (output.type === 'chunk') {
          // A literal "</script" inside the code would end the inline tag early.
          const code = output.code.replace(/<\/script/gi, '<\\/script');
          source = source.replace(ref, () => `<script type="module">${code}</script>`);
        } else if (fileName.endsWith('.css')) {
          source = source.replace(ref, () => `<style>${output.source}</style>`);
        } else {
          continue;
        }
        delete bundle[fileName];
      }
      html.source = source;
    },
  };
}

export default defineConfig({
  root: 'src',
  base: './',
  publicDir: false,
  plugins: [svelte(), inlineAssets()],
  build: {
    outDir: '../build/ui',
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: () => true,
    modulePreload: false,
    rollupOptions: {
      output: { inlineDynamicImports: true },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
