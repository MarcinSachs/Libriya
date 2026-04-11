// Caching disabled � this service worker immediately unregisters itself and
// clears all libriya caches.  Offline mode is not yet functional so caching
// only caused stale-UI bugs (e.g. favourites state not updating after toggle).
console.log('[SW] caching disabled � unregistering');

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys.filter(k => k.startsWith('libriya-')).map(k => caches.delete(k))
            ))
            .then(() => self.registration.unregister())
            .then(() => self.clients.matchAll())
            .then(clients => clients.forEach(c => c.navigate && c.navigate(c.url)))
    );
});
