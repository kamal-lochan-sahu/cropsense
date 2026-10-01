// CropSense service worker. The cache name includes an asset hash that changes on every
// deploy, so stale files are never served after an update.
const VERSION = '{{ asset_version }}';
const CACHE = `cropsense-${VERSION}`;
const SHELL = [
  '/',
  `/static/css/style.css?v=${VERSION}`,
  `/static/js/translations.js?v=${VERSION}`,
  `/static/js/app.js?v=${VERSION}`,
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key.startsWith('cropsense-') && key !== CACHE).map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

// Pages: network first so users always get the latest HTML, cached copy when offline.
async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok && new URL(request.url).pathname === '/') cache.put('/', response.clone());
    return response;
  } catch {
    const cached = await cache.match('/');
    if (cached) return cached;
    return new Response('You are offline.', { status: 503, headers: { 'Content-Type': 'text/plain' } });
  }
}

// Static files: serve from cache, refresh in the background.
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const refresh = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);
  return cached || refresh;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request));
  } else if (url.pathname.startsWith('/static/')) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
