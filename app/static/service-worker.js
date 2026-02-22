/*
 * Legacy static service worker file left in place for backwards compatibility
 * (some clients or deployments might have cached it).  The actual script used
 * by the application is generated dynamically via a Flask view at
 * /service-worker.js.  This placeholder ensures that if the browser requests
 * the old URL directly it at least receives a no‑op file instead of 404.
 */

console.warn('Deprecated static service-worker.js loaded; dynamic version should be used.');
self.addEventListener('fetch', () => { });
