// English strings for the whole app. This is the only locale for now — see
// ./index.js for how the lookup works if more languages are ever added.
export default {
  common: {
    cancel: 'Cancel',
  },

  app: {
    sidebarTitle: 'Library',
    settingsTooltip: 'Settings',
    everything: 'everything',
    title: 'Transcript Search',
    transcriptTooltip: 'Transcript',
    toggleTranscript: 'Toggle transcript',
    lightMode: 'Light mode',
    darkMode: 'Dark mode',
    toggleTheme: 'Toggle theme',
    closeTranscript: 'Close transcript',
    transcriptFallbackTitle: 'Transcript',
    libraryCleared: 'Library cleared.',
    stats: ({ videos, segments, missing }) => {
      let text = `${videos} videos · ${segments.toLocaleString()} lines`;
      if (missing) text += ` · ${missing} without captions`;
      return text;
    },
    confirmRefetchAllTitle: (count) => `Refetch all ${count} videos?`,
    confirmRefetchAllBody:
      'Captions are downloaded again and existing transcripts are replaced. Nothing is deleted if a fetch fails.',
    confirmRefetchAllLabel: 'Refetch all',
    confirmClearTitle: 'Clear the whole library?',
    confirmClearBody: ({ videos, sources }) =>
      `This removes all ${videos} videos, ${sources} sources, and their transcripts. It cannot be undone.`,
    confirmClearLabel: 'Clear everything',
    confirmRemoveSourceTitle: (name) => `Remove ${name}?`,
    confirmRemoveSourceBody: (count) =>
      `Also delete the ${count} videos that came from it? Videos that also belong to another source are kept either way.`,
    confirmRemoveSourceOnly: 'Remove source only',
    confirmRemoveSourceAndVideos: 'Remove source and videos',
  },

  cookies: {
    browsers: {
      none: 'None',
      chrome: 'Chrome',
      edge: 'Edge',
      firefox: 'Firefox',
      brave: 'Brave',
      vivaldi: 'Vivaldi',
      opera: 'Opera',
      chromium: 'Chromium',
      safari: 'Safari',
    },
    hint: 'Only needed for age-restricted, members-only, or rate-limited fetches.',
    fileLabel: 'Cookies file',
    filePlaceholder: 'Path to cookies.txt',
    browse: 'Browse',
    browserLabel: 'Or read cookies from a browser',
  },

  ingest: {
    tabVideos: 'Videos',
    tabShorts: 'Shorts',
    tabLive: 'Live',
    urlsPlaceholder: 'Channel, playlist, or video URLs — one per line\ne.g. youtube.com/@3blue1brown',
    fetching: 'Fetching...',
    fetchCaptions: 'Fetch captions',
    options: 'Options',
    channelTabs: 'Channel tabs',
    preferredLanguages: 'Preferred languages',
    preferredLanguagesPlaceholder: 'en, ja',
    allowAuto: 'Use auto-generated captions when there is no manual track',
    allowOtherLanguages: 'Fall back to other languages',
    skipExisting: 'Skip videos already stored',
    concurrency: 'Parallel',
    maxVideos: 'Limit (0 = all)',
  },

  job: {
    fetchFailed: 'Fetch failed',
    cancelled: 'Cancelled',
    fetched: (n) => `${n} fetched`,
    alreadyStored: (n) => `${n} already stored`,
    withoutCaptions: (n) => `${n} without captions`,
    failed: (n) => `${n} failed`,
    findingVideos: 'Finding videos...',
    working: 'working...',
    progress: ({ completed, total, current }) => `${completed} / ${total} · ${current || 'working...'}`,
    cancel: 'Cancel',
    errorCount: (n) => `${n} error${n === 1 ? '' : 's'}`,
  },

  search: {
    searchScope: (scope) => `Search ${scope}...`,
    fetchFirst: 'Fetch some captions first',
    searchAria: 'Search',
    noResults: (query, scope) => `No matches for "${query}" in ${scope}.`,
    resultsHeader: (total, scope) => `${total} match${total === 1 ? '' : 'es'} in ${scope}`,
    showingFirst: (n) => `showing first ${n}`,
    auto: 'auto',
    openAtTime: 'Open at this time',
    openInBrowser: 'Open in browser',
    copyLink: 'Copy timestamped link',
  },

  sources: {
    label: 'Channels & playlists',
    allSources: 'All sources',
    checkForNew: 'Check for new videos',
    removeSource: 'Remove this source',
  },

  transcript: {
    lines: ({ shown, total, hasFilter }) => `${shown}${hasFilter ? ` / ${total}` : ''} lines`,
    copied: 'Copied',
    copyAll: 'Copy all',
    filterPlaceholder: 'Filter this transcript...',
    selectVideo: 'Select a video to read its transcript.',
    noLinesMatch: (filter) => `No lines match "${filter}".`,
    open: 'Open',
    copyLinkTooltip: 'Copy link',
  },

  videoList: {
    videosLabel: (n) => `Videos (${n})`,
    refetchAllTooltip: 'Refetch every stored video',
    refetchAll: 'Refetch all',
    clear: 'Clear',
    filterPlaceholder: 'Filter videos...',
    noVideosYet: 'No videos yet. Paste a channel or playlist above.',
    nothingMatches: (filter) => `Nothing matches "${filter}".`,
    noCaptions: 'no captions',
    subtitleInfo: (type, language) => `${type} · ${language}`,
    refetchCaptions: 'Refetch captions',
    remove: 'Remove',
    moreHidden: (n) => `+${n} more — use the filter to narrow down`,
    missingLabel: (n) => `No captions (${n})`,
    retryMissingTooltip: 'Uploaders sometimes add captions later',
    retry: 'Retry',
  },
};
