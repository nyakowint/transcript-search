const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const getApi = () => window.pywebview?.api;

async function waitForApi(timeoutMs = 10000) {
  const start = Date.now();
  while (!getApi()) {
    if (Date.now() - start > timeoutMs) {
      return null;
    }
    await wait(100);
  }
  return getApi();
}

export const apiClient = {
  onReady(callback) {
    if (window.pywebview && window.pywebview.api) {
      callback();
      return;
    }
    window.addEventListener('pywebviewready', () => {
      if (window.pywebview?.api) {
        callback();
      }
    });
  },
  async safe(fn) {
    const api = await waitForApi();
    if (!api) {
      return { ok: false, error: 'App is not ready yet.' };
    }
    try {
      return await fn(api);
    } catch (error) {
      return { ok: false, error: error?.message || 'Unexpected error' };
    }
  },
  async getVideos() {
    const api = await waitForApi();
    return api.get_videos();
  },
  async getMissing() {
    const api = await waitForApi();
    return api.get_missing_subtitles();
  },
  async getTranscript(videoId) {
    const api = await waitForApi();
    return api.get_transcript(videoId);
  },
  async ingestUrls(inputText, cookiesPath, cookiesBrowser) {
    const api = await waitForApi();
    return api.ingest_urls(inputText, cookiesPath, cookiesBrowser);
  },
  async searchTranscripts(query) {
    const api = await waitForApi();
    return api.search_transcripts(query);
  },
  async getSettings() {
    const api = await waitForApi();
    return api.get_settings();
  },
  async saveSettings(cookiesPath, cookiesBrowser) {
    const api = await waitForApi();
    return api.save_settings(cookiesPath, cookiesBrowser);
  },
  async selectCookiesFile() {
    const api = await waitForApi();
    return api.select_cookies_file();
  },
};
