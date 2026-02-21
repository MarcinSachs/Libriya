// debug helpers - log early and catch uncaught errors
console.log('[SW] start');
self.addEventListener('error', e => {
    console.error('[SW] uncaught error', e.message, e.filename, e.lineno, e.colno);
});
self.addEventListener('unhandledrejection', e => {
    console.error('[SW] unhandled promise rejection', e.reason);
});

importScripts('https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js');

// use backend-supplied version to control cache names
workbox.core.setCacheNameDetails({
    prefix: 'libriya',
    suffix: '{{ PWA_CACHE_VERSION }}'
});

// Precache a small set of public pages on install.  Do **not** include
// authenticated endpoints (libraries, loans, etc.) – those are fetched when the
// user explicitly asks to cache offline data via the UI and stored manually.
// precacheAndRoute will automatically serve cached responses for matched URLs
// even when the network is available, so including protected pages leads to
// stale login screens being shown after a user signs in.
//
// The list below is derived from the backend value but filtered strictly to
// safe URLs.  Only the landing page ("/") and the offline fallback are
// precached by default.
const PRECACHE_URLS = {{ PWA_PRECACHE_PAGES| tojson }}
    .filter(u => u === '/' || u === '/offline');

workbox.precaching.precacheAndRoute(
    PRECACHE_URLS.map(p => ({ url: p, revision: '{{ PWA_CACHE_VERSION }}' }))
);

// App shell caching for navigation requests (except settings)
// leave settings page network-only to avoid stale login page being served
// Only cache successful (200/opaque) responses; do not persist redirects or
// errors because those are typically login pages or server faults that would
// be misleading when the user is subsequently authenticated.
workbox.routing.registerRoute(
    ({url, request}) => request.mode === 'navigate' && !url.pathname.startsWith('/user/settings'),
    new workbox.strategies.NetworkFirst({
        cacheName: `libriya-shell-{{ PWA_CACHE_VERSION }}`,
        networkTimeoutSeconds: 3,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 50,
                maxAgeSeconds: 7 * 24 * 60 * 60,
            }),
            new workbox.cacheableResponse.CacheableResponsePlugin({
                statuses: [0, 200]
            })
        ]
    })
);

// Network-only route for settings (no caching)
workbox.routing.registerRoute(
    ({url}) => url.pathname.startsWith('/user/settings'),
    new workbox.strategies.NetworkOnly()
);

// Cache images (covers, uploads) with a cache-first strategy
workbox.routing.registerRoute(
    /\/(static\/uploads|cover)\//,
    new workbox.strategies.CacheFirst({
        cacheName: `libriya-images-{{ PWA_CACHE_VERSION }}`,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 200,
                maxAgeSeconds: 30 * 24 * 60 * 60,
            })
        ]
    })
);

// API responses: network-first with cache fallback
workbox.routing.registerRoute(
    /\/api\//,
    new workbox.strategies.NetworkFirst({
        cacheName: `libriya-api-{{ PWA_CACHE_VERSION }}`,
        networkTimeoutSeconds: 5,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 100,
                maxAgeSeconds: 24 * 60 * 60,
            })
        ]
    })
);

// fallback to offline page
workbox.routing.setCatchHandler(async ({ event }) => {
    if (event.request.destination === 'document') {
        return caches.match('/offline');
    }
    return Response.error();
});

// When activating the new service worker, delete any old caches that use a
// different version string.  This mirrors the cleanup logic in the page
// script and ensures clients update automatically when ``PWA_CACHE_VERSION``
// is bumped.
self.addEventListener('activate', (event) => {
    const expected = [
        `libriya-shell-{{ PWA_CACHE_VERSION }}`,
        `libriya-images-{{ PWA_CACHE_VERSION }}`,
        `libriya-api-{{ PWA_CACHE_VERSION }}`
    ];
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k.startsWith('libriya-') && !expected.includes(k))
                    .map(k => caches.delete(k))
            )
        )
    );
});

// listen for messages from client
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
