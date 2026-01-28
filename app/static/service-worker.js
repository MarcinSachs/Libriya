const CACHE_NAME = 'libriya-v3'; // Increment version to force cache update
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/images/logo.svg',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
    'https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.4/dist/html5-qrcode.min.js'
];

// Install event - cache essential files
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(() => {
                console.log('Some assets failed to cache, continuing with partial cache');
            });
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch event - network first for HTML, cache first for assets
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // For API calls - network first, fallback to cache
    if (url.pathname.startsWith('/api/v1/')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    // Cache successful API responses
                    if (response.status === 200) {
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Return cached response if offline
                    return caches.match(request).then(response => {
                        if (response) {
                            return response;
                        }
                        return new Response('Offline - data not cached', {
                            status: 503,
                            statusText: 'Service Unavailable',
                            headers: new Headers({
                                'Content-Type': 'text/plain'
                            })
                        });
                    });
                })
        );
    }
    // For HTML pages - network first (always try fresh content first)
    else if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    if (response.status === 200) {
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    return caches.match(request).then(response => {
                        if (response) {
                            return response;
                        }
                        return caches.match('/');
                    });
                })
        );
    }
    // For static assets - cache first
    else {
        event.respondWith(
            caches.match(request).then(response => {
                return response || fetch(request).then(response => {
                    // Cache new static assets
                    if (response.status === 200 && request.method === 'GET') {
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return response;
                }).catch(() => {
                    // Return offline fallback
                    return caches.match('/');
                });
            })
        );
    }
});

// Background sync for future feature (optional)
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-books') {
        event.waitUntil(
            fetch('/api/v1/sync').then(response => response.json())
        );
    }
});
