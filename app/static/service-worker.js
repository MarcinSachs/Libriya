const CACHE_NAME = 'libriya-v4'; // Increment version to force cache update
const THUMBNAIL_CACHE = 'libriya-thumbnails-v1';
const FULLSIZE_CACHE = 'libriya-covers-v1';

// Only cache offline page during install
const STATIC_ASSETS = [
    '/static/offline.html'
];

// Install event - cache essential files
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(() => {
                console.log('Install cache failed, will cache on-demand');
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
                    if (cacheName !== CACHE_NAME && cacheName !== THUMBNAIL_CACHE && cacheName !== FULLSIZE_CACHE) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch event - intelligent caching strategy based on request type
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Strategy 1: THUMBNAILS - Cache first (offline priority)
    if (url.pathname.includes('/cover/thumbnail')) {
        event.respondWith(
            caches.match(request).then(response => {
                if (response) {
                    return response; // Return cached immediately
                }

                // Not in cache, fetch from network
                return fetch(request)
                    .then(response => {
                        if (response.status === 200) {
                            // Cache the thumbnail for offline use
                            const responseToCache = response.clone();
                            caches.open(THUMBNAIL_CACHE).then(cache => {
                                cache.put(request, responseToCache);
                            });
                        }
                        return response;
                    })
                    .catch(() => {
                        // If thumbnail not cached and offline, return placeholder
                        return caches.match('/');
                    });
            })
        );
    }
    // Strategy 2: FULL-SIZE COVERS - Network first (quality priority)
    else if (url.pathname.includes('/api/books/') && url.pathname.includes('/cover')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    if (response.status === 200) {
                        // Cache full-size cover for offline viewing
                        const responseToCache = response.clone();
                        caches.open(FULLSIZE_CACHE).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Fall back to cached version if offline
                    return caches.match(request).then(response => {
                        return response || caches.match('/'); // Return fallback
                    });
                })
        );
    }
    // Strategy 3: API CALLS - Network first, fallback to cache
    else if (url.pathname.startsWith('/api/')) {
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
                        return new Response(JSON.stringify({ error: 'Offline - data not cached' }), {
                            status: 503,
                            statusText: 'Service Unavailable',
                            headers: new Headers({
                                'Content-Type': 'application/json'
                            })
                        });
                    });
                })
        );
    }
    // Strategy 4: HTML PAGES - Network first, but cache is priority when offline
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
                    // Try to get cached version first
                    return caches.match(request).then(cachedResponse => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // Try to return cached home page
                        return caches.match('/').then(homeResponse => {
                            if (homeResponse) {
                                return homeResponse;
                            }
                            // Last resort: return offline page
                            return caches.match('/static/offline.html');
                        });
                    });
                })
        );
    }
    // Strategy 5: STATIC ASSETS - Cache first (css, js, images, fonts)
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
                    // Return offline page as fallback for HTML requests
                    if (request.headers.get('accept')?.includes('text/html')) {
                        return caches.match('/static/offline.html');
                    }
                    // For other assets, return error
                    return new Response('Not found', { status: 404 });
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

// Message handler for cache size management
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_THUMBNAILS') {
        caches.delete(THUMBNAIL_CACHE).then(() => {
            console.log('Thumbnail cache cleared');
        });
    }
});
