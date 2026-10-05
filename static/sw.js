// Service Worker para la PWA de Nexum ID (Soporte Offline Completo)
const NOMBRE_CACHE = 'nexum-cache-v3';
const RECURSOS_ESTATICOS = [
  '/',
  '/static/theme.css',
  '/static/manifest.json',
  '/static/vendor/fontawesome/css/all.min.css',
  '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
  '/static/vendor/fontawesome/webfonts/fa-regular-400.woff2',
  '/static/vendor/chartjs/chart.umd.min.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(NOMBRE_CACHE).then(cache => {
      return cache.addAll(RECURSOS_ESTATICOS).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== NOMBRE_CACHE).map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Peticiones de API y navegación no se cachean agresivamente
  if (event.request.url.includes('/api/') || event.request.method !== 'GET') {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});
