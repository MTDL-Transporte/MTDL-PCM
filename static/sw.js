/*
  Service Worker leve para MTDL-PCM
  - Cache de assets estáticos
  - Fallback offline para navegação
  - Estratégias simples para /static e /api GET
*/

const VERSION = 'v2';
const STATIC_CACHE = `mtdl-static-${VERSION}`;
const DYNAMIC_CACHE = `mtdl-dynamic-${VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/css/style.css',
  '/static/css/custom-styles.css',
  '/static/js/app.js',
  '/static/js/offline-queue.js',
  '/static/img/favicon.svg',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => ![STATIC_CACHE, DYNAMIC_CACHE].includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  // Navegação: network-first com fallback offline
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, copy)).catch(() => {});
          return response;
        })
        .catch(() => caches.match('/offline').then(r => r || caches.match('/')))
    );
    return;
  }

  // Assets estáticos locais: cache-first
  if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request)
          .then(response => {
            const copy = response.clone();
            caches.open(STATIC_CACHE).then(cache => cache.put(request, copy)).catch(() => {});
            return response;
          })
          .catch(() => cached);
      })
    );
    return;
  }

  // API GET: stale-while-revalidate simples
  if (url.origin === self.location.origin && url.pathname.startsWith('/api/') && request.method === 'GET') {
    event.respondWith(
      caches.match(request).then(cached => {
        const fetchPromise = fetch(request)
          .then(response => {
            const copy = response.clone();
            caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, copy)).catch(() => {});
            return response;
          })
          .catch(() => cached);
        return cached ? Promise.resolve(cached).then(() => fetchPromise) : fetchPromise;
      })
    );
    return;
  }
});