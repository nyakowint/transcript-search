const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const getApi = () => window.pywebview?.api;

async function waitForApi(timeoutMs = 15000) {
  const start = Date.now();
  while (!getApi()) {
    if (Date.now() - start > timeoutMs) return null;
    await wait(100);
  }
  return getApi();
}

/**
 * Backend push channel.
 *
 * pywebview cannot push to the page on its own, so Python calls
 * `window.__captionSearchEvent(payload)`. Installing the hook here at module
 * load means no progress tick is dropped while components are still mounting.
 */
const listeners = new Set();

window.__captionSearchEvent = (event) => {
  for (const listener of listeners) {
    try {
      listener(event);
    } catch (error) {
      console.error('event listener failed', error);
    }
  }
};

export function onBackendEvent(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

async function call(method, ...args) {
  const api = await waitForApi();
  if (!api) return { ok: false, error: 'Backend is not ready yet.' };
  if (typeof api[method] !== 'function') {
    return { ok: false, error: `Backend has no method "${method}".` };
  }
  try {
    const result = await api[method](...args);
    return result ?? { ok: false, error: 'Backend returned nothing.' };
  } catch (error) {
    return { ok: false, error: error?.message || String(error) };
  }
}

export const apiClient = {
  onReady(callback) {
    if (window.pywebview?.api) {
      callback();
      return;
    }
    window.addEventListener('pywebviewready', () => {
      if (window.pywebview?.api) callback();
    });
  },

  // settings
  getSettings: () => call('get_settings'),
  saveSettings: (settings) => call('save_settings', settings),
  selectCookiesFile: () => call('select_cookies_file'),

  // ingest + jobs
  startIngest: (inputText, overrides) => call('start_ingest', inputText, overrides ?? null),
  syncSource: (sourceId, force = false) => call('sync_source', sourceId, force),
  refetchVideos: (videoIds) => call('refetch_videos', videoIds),
  refetchAll: (scope = 'all', olderThanDays = 0) =>
    call('refetch_all', scope, olderThanDays),
  cancelJob: (jobId = '') => call('cancel_job', jobId),
  getJob: (jobId = '') => call('get_job', jobId),

  // reads
  getVideos: (sourceId = '') => call('get_videos', sourceId),
  getSources: () => call('get_sources'),
  getTranscript: (videoId) => call('get_transcript', videoId),
  getMissing: () => call('get_missing_subtitles'),
  getStats: () => call('get_stats'),
  searchTranscripts: (query, options = {}) =>
    call(
      'search_transcripts',
      query,
      options.sourceId ?? '',
      options.videoId ?? '',
      options.limit ?? 300,
      options.offset ?? 0
    ),

  // deletes
  deleteVideo: (videoId) => call('delete_video', videoId),
  deleteAllVideos: () => call('delete_all_videos'),
  deleteSource: (sourceId, deleteVideos = false) =>
    call('delete_source', sourceId, deleteVideos),
};
