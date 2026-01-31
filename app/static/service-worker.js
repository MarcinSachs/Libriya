const CACHE_NAME = 'libriya-v14';
const THUMBNAIL_CACHE = 'libriya-thumbnails-v1';
const MICRO_CACHE = 'libriya-micro-v1';
const DATA_CACHE = 'libriya-data-v1';

// Static assets to cache during install
const STATIC_ASSETS = [
    '/offline',
    '/static/css/style.css',
    '/static/js/pwa-manager.js',
    '/static/manifest.json',
    '/static/images/logo.svg'
];

// Pages that should NEVER be cached (forms with CSRF)
const NO_CACHE_PAGES = ['/login', '/register', '/invitation'];

// Install event
self.addEventListener('install', (event) => {
    console.log('[SW] Installing v13');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.log('[SW] Install failed:', err);
            });
        })
    );
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating v11');
    event.waitUntil(
        caches.keys().then((names) => {
            return Promise.all(
                names.map((name) => {
                    // Delete old main caches but keep thumbnails and data
                    if (name.startsWith('libriya-v') && name !== CACHE_NAME) {
                        console.log('[SW] Deleting old cache:', name);
                        return caches.delete(name);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Helper: Should cache this page?
function shouldCache(pathname) {
    return !NO_CACHE_PAGES.some(p => pathname.includes(p));
}

// Helper: Cache with URL string as key (not Request object!)
async function cacheByUrl(cacheName, urlString, response) {
    try {
        const cache = await caches.open(cacheName);
        await cache.put(urlString, response);
        console.log('[SW] Cached:', urlString);
    } catch (e) {
        console.log('[SW] Cache error:', e);
    }
}

// Helper: Get from any cache by URL string (tries multiple variants)
async function getCached(urlString) {
    const urlsToTry = [
        urlString,
        urlString.endsWith('/') ? urlString.slice(0, -1) : urlString + '/'
    ];

    for (const name of [CACHE_NAME, DATA_CACHE, THUMBNAIL_CACHE, MICRO_CACHE]) {
        try {
            const cache = await caches.open(name);
            for (const url of urlsToTry) {
                const response = await cache.match(url);
                if (response) {
                    console.log('[SW] Cache HIT:', url, 'in', name);
                    return response;
                }
            }
        } catch (e) {
            console.log('[SW] Cache error:', e);
        }
    }
    console.log('[SW] Cache MISS:', urlString);
    return null;
}

// Fetch event
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    const urlString = url.href;
    const pathname = url.pathname;


    // Only GET requests
    if (request.method !== 'GET') return;

    // Only same origin
    if (url.origin !== location.origin) return;

    // === IGNORE language switch route ===
    if (pathname.startsWith('/set_language/')) {
        // Do not intercept, let browser handle
        return;
    }

    // === UPLOADS & THUMBNAILS - Cache first ===
    if (pathname.includes('/static/uploads/') || pathname.includes('/cover/thumbnail') || pathname.includes('/cover/micro')) {
        event.respondWith(
            getCached(urlString).then(cached => {
                if (cached) return cached;

                return fetch(request).then(response => {
                    if (response.ok) {
                        // Use appropriate cache for micro vs regular thumbnails
                        const targetCache = pathname.includes('/cover/micro') ? MICRO_CACHE : THUMBNAIL_CACHE;
                        cacheByUrl(targetCache, urlString, response.clone());
                    }
                    return response;
                }).catch(() => new Response('', { status: 404 }));
            })
        );
        return;
    }

    // === API - Network first ===
    if (pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request).then(response => {
                if (response.ok) {
                    cacheByUrl(DATA_CACHE, urlString, response.clone());
                }
                return response;
            }).catch(() => {
                return getCached(urlString).then(cached => {
                    return cached || new Response(JSON.stringify({ error: 'Offline' }), {
                        status: 503,
                        headers: { 'Content-Type': 'application/json' }
                    });
                });
            })
        );
        return;
    }

    // === HTML PAGES - Network first, cache fallback ===
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request, { credentials: 'same-origin' }).then(response => {
                if (response.ok && shouldCache(pathname)) {
                    // Cache with full URL
                    cacheByUrl(CACHE_NAME, urlString, response.clone());
                    // Also cache alternate URL (with/without slash)
                    const altUrl = urlString.endsWith('/') ? urlString.slice(0, -1) : urlString + '/';
                    cacheByUrl(CACHE_NAME, altUrl, response.clone());
                }
                return response;
            }).catch(async () => {
                console.log('[SW] OFFLINE - looking for:', urlString);

                // Try to get from cache
                const cached = await getCached(urlString);
                if (cached) {
                    console.log('[SW] Returning cached page');
                    return cached;
                }

                // Fallback to offline page (dynamic with translations)
                console.log('[SW] No cache found, showing /offline');
                const offlinePage = await getCached(location.origin + '/offline');
                return offlinePage || new Response('Offline', { status: 503 });
            })
        );
        return;
    }

    // === STATIC ASSETS - Cache first ===
    event.respondWith(
        getCached(urlString).then(cached => {
            if (cached) return cached;

            return fetch(request).then(response => {
                if (response.ok) {
                    cacheByUrl(CACHE_NAME, urlString, response.clone());
                }
                return response;
            }).catch(() => new Response('Not found', { status: 404 }));
        })
    );
});

// Message handler
self.addEventListener('message', (event) => {
    if (event.data?.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    if (event.data?.type === 'CLEAR_THUMBNAILS') {
        caches.delete(THUMBNAIL_CACHE);
    }
    if (event.data?.type === 'CACHE_PAGES') {
        // Pre-cache pages
        const pages = ['/', '/books/', '/loans/', '/libraries/'];
        caches.open(CACHE_NAME).then(cache => {
            pages.forEach(page => {
                fetch(page, { credentials: 'same-origin' })
                    .then(res => res.ok && cache.put(location.origin + page, res))
                    .catch(() => { });
            });
        });
    }
});
