/**
 * PWA Manager - Handles Progressive Web App functionality
 * Features:
 * - Service Worker registration
 * - Online/Offline detection
 * - Install prompt handling
 * - Cache management
 */

class PWAManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.deferredPrompt = null;
        this.swRegistration = null;
        this.init();
    }

    async init() {
        console.log('[PWA] Initializing PWA Manager');

        // Check if Service Worker is supported and we're on secure context
        if ('serviceWorker' in navigator) {
            if (window.isSecureContext) {
                this.registerServiceWorker();
            } else {
                console.warn('[PWA] Service Worker requires HTTPS. Offline features disabled.');
                console.warn('[PWA] Use localhost or enable HTTPS for full PWA support.');
            }
        } else {
            console.warn('[PWA] Service Worker not supported in this browser');
        }

        // Online/Offline event listeners
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());

        // Install prompt event listener
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallPrompt();
        });

        // App installed listener
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed');
            this.deferredPrompt = null;
            this.hideInstallPrompt();
        });

        // Update status on load
        this.updateOnlineStatus();
    }

    /**
     * Register Service Worker
     */
    async registerServiceWorker() {
        try {
            this.swRegistration = await navigator.serviceWorker.register('/static/service-worker.js', {
                scope: '/'
            });
            console.log('[PWA] Service Worker registered:', this.swRegistration);

            // Check for updates immediately on page load
            this.swRegistration.update().then(() => {
                console.log('[PWA] Checked for Service Worker updates');
            });

            // Pre-cache important pages when online and logged in
            if (navigator.onLine && document.body.hasAttribute('data-user-logged-in')) {
                this.preCachePages();
            }

            // Check for updates periodically every 60 seconds when online
            if (navigator.onLine) {
                setInterval(() => {
                    this.swRegistration.update();
                }, 60000);
            }

            // Listen for updates
            this.swRegistration.addEventListener('updatefound', () => {
                const newWorker = this.swRegistration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'activated') {
                        console.log('[PWA] New Service Worker activated');
                        this.notifyUpdate();
                    }
                });
            });
        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
        }
    }

    /**
     * Pre-cache important pages for offline use
     */
    async preCachePages() {
        // Correct URLs for the application
        const pagesToCache = [
            '/',                    // Home page (book list)
            '/loans/',              // Loans list
            '/libraries/',          // Libraries list
            '/users/',              // Users list
            '/notifications/',      // Notifications
            '/user/settings',       // User settings
            '/offline'              // Offline page (with translations)
        ];
        console.log('[PWA] Pre-caching pages...');

        const cache = await caches.open('libriya-v13');

        for (const page of pagesToCache) {
            try {
                const fullUrl = new URL(page, location.origin).href;
                const response = await fetch(page, { credentials: 'same-origin' });
                if (response.ok) {
                    // Cache with full URL as key (same format as service worker uses)
                    await cache.put(fullUrl, response.clone());
                    console.log('[PWA] Pre-cached:', fullUrl);

                    // Also cache without trailing slash variant
                    const altUrl = fullUrl.endsWith('/') ? fullUrl.slice(0, -1) : fullUrl + '/';
                    await cache.put(altUrl, response.clone());
                }
            } catch (e) {
                console.log('[PWA] Failed to pre-cache:', page, e);
            }
        }
        console.log('[PWA] Pre-caching complete');
    }

    /**
     * Handle online status change
     */
    handleOnline() {
        this.isOnline = true;
        console.log('[PWA] Device is online');
        this.updateOnlineStatus();
        this.hideOfflineWarning();
    }

    /**
     * Handle offline status change
     */
    handleOffline() {
        this.isOnline = false;
        console.log('[PWA] Device is offline');
        this.updateOnlineStatus();
        this.showOfflineWarning();
    }

    /**
     * Update UI based on online status
     */
    updateOnlineStatus() {
        const statusElement = document.getElementById('online-status-badge');

        if (!statusElement) {
            console.warn('[PWA] Online status badge element not found');
            return;
        }

        if (this.isOnline) {
            statusElement.innerHTML = '<span class="badge bg-success"><i class="bx bx-wifi"></i> Online</span>';
            statusElement.classList.remove('offline');
        } else {
            statusElement.innerHTML = '<span class="badge bg-warning"><i class="bx bx-wifi-0"></i> Offline</span>';
            statusElement.classList.add('offline');
        }
    }

    /**
     * Show offline warning banner
     */
    showOfflineWarning() {
        const banner = document.getElementById('offline-warning');
        if (banner) {
            banner.style.display = 'flex';
            banner.classList.add('show');
        }
    }

    /**
     * Hide offline warning banner
     */
    hideOfflineWarning() {
        const banner = document.getElementById('offline-warning');
        if (banner) {
            banner.classList.remove('show');
            setTimeout(() => {
                banner.style.display = 'none';
            }, 300);
        }
    }

    /**
     * Show install prompt
     */
    showInstallPrompt() {
        const installBtn = document.getElementById('install-app-btn');
        if (installBtn) {
            installBtn.style.display = 'inline-block';
            console.log('[PWA] Install prompt available');
        }
    }

    /**
     * Hide install prompt
     */
    hideInstallPrompt() {
        const installBtn = document.getElementById('install-app-btn');
        if (installBtn) {
            installBtn.style.display = 'none';
        }
    }

    /**
     * Handle install button click
     */
    installApp() {
        if (!this.deferredPrompt) {
            console.warn('[PWA] Install prompt not available');
            return;
        }

        this.deferredPrompt.prompt();
        this.deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('[PWA] User accepted install prompt');
            } else {
                console.log('[PWA] User dismissed install prompt');
            }
            this.deferredPrompt = null;
        });
    }

    /**
     * Notify user about app update
     */
    notifyUpdate() {
        const banner = document.getElementById('update-banner');
        if (banner) {
            banner.style.display = 'flex';
            banner.classList.add('show');

            const reloadBtn = document.getElementById('reload-app-btn');
            if (reloadBtn) {
                reloadBtn.addEventListener('click', () => {
                    window.location.reload();
                });
            }
        }
    }

    /**
     * Clear thumbnail cache manually
     */
    async clearThumbnailCache() {
        if ('serviceWorker' in navigator && 'controller' in navigator.serviceWorker) {
            navigator.serviceWorker.controller.postMessage({
                type: 'CLEAR_THUMBNAILS'
            });
            console.log('[PWA] Thumbnail cache clear requested');

            // Also try to delete from caches API
            const cacheNames = await caches.keys();
            const thumbnailCache = cacheNames.find(name => name.includes('thumbnail'));
            if (thumbnailCache) {
                await caches.delete(thumbnailCache);
                console.log('[PWA] Thumbnail cache deleted');
            }
        }
    }

    /**
     * Get cache info (for debugging)
     */
    async getCacheInfo() {
        const cacheNames = await caches.keys();
        const cacheInfo = {};

        for (const name of cacheNames) {
            const cache = await caches.open(name);
            const keys = await cache.keys();
            cacheInfo[name] = {
                count: keys.length,
                urls: keys.map(req => req.url)
            };
        }

        console.log('[PWA] Cache Info:', cacheInfo);
        return cacheInfo;
    }

    /**
     * Check if specific resource is cached
     */
    async isCached(url) {
        const cacheNames = await caches.keys();

        for (const name of cacheNames) {
            const cache = await caches.open(name);
            const response = await cache.match(url);
            if (response) {
                return true;
            }
        }

        return false;
    }

    /**
     * Pre-cache all books data and micro-thumbnails for offline use
     * Called after login or manually from settings
     */
    async preCacheOfflineData(showProgress = false) {
        if (!navigator.onLine) {
            console.log('[PWA] Cannot pre-cache offline data - device is offline');
            return { success: false, reason: 'offline' };
        }

        console.log('[PWA] Starting offline data pre-cache...');

        const progressEl = showProgress ? document.getElementById('offline-cache-progress') : null;
        const updateProgress = (text) => {
            if (progressEl) progressEl.textContent = text;
            console.log('[PWA]', text);
        };

        try {
            // 1. Fetch all books data
            updateProgress('Pobieranie danych książek...');
            const response = await fetch('/api/offline/books', { credentials: 'same-origin' });

            if (!response.ok) {
                throw new Error(`Failed to fetch books data: ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Unknown error');
            }

            const books = data.books;
            console.log(`[PWA] Got ${books.length} books for offline caching`);

            // 2. Cache the books JSON data
            const dataCache = await caches.open('libriya-data-v1');
            await dataCache.put(
                new URL('/api/offline/books', location.origin).href,
                new Response(JSON.stringify(data), {
                    headers: { 'Content-Type': 'application/json' }
                })
            );
            updateProgress(`Zapisano dane ${books.length} książek`);

            // 3. Cache micro-thumbnails for offline use
            const microCache = await caches.open('libriya-micro-v1');
            let cachedCovers = 0;
            let failedCovers = 0;

            for (const book of books) {
                if (book.micro_cover_url) {
                    try {
                        const coverResponse = await fetch(book.micro_cover_url);
                        if (coverResponse.ok) {
                            await microCache.put(
                                new URL(book.micro_cover_url, location.origin).href,
                                coverResponse.clone()
                            );
                            cachedCovers++;
                        } else {
                            failedCovers++;
                        }
                    } catch (e) {
                        failedCovers++;
                    }

                    // Update progress every 10 books
                    if ((cachedCovers + failedCovers) % 10 === 0) {
                        updateProgress(`Pobieranie okładek: ${cachedCovers}/${books.filter(b => b.micro_cover_url).length}`);
                    }
                }
            }

            // 4. Cache individual book detail pages
            updateProgress('Zapisywanie stron szczegółów...');
            const mainCache = await caches.open('libriya-v13');
            let cachedPages = 0;

            for (const book of books) {
                try {
                    const pageResponse = await fetch(book.detail_url, { credentials: 'same-origin' });
                    if (pageResponse.ok) {
                        await mainCache.put(
                            new URL(book.detail_url, location.origin).href,
                            pageResponse.clone()
                        );
                        cachedPages++;
                    }
                } catch (e) {
                    // Skip failed pages
                }

                // Update progress every 10 books
                if (cachedPages % 10 === 0) {
                    updateProgress(`Zapisywanie stron: ${cachedPages}/${books.length}`);
                }
            }

            const result = {
                success: true,
                booksCount: books.length,
                coversCount: cachedCovers,
                pagesCount: cachedPages,
                timestamp: new Date().toISOString()
            };

            // Save cache metadata to localStorage
            localStorage.setItem('offlineCacheInfo', JSON.stringify(result));

            updateProgress(`Gotowe! ${books.length} książek, ${cachedCovers} okładek`);
            console.log('[PWA] Offline data pre-cache complete:', result);

            return result;

        } catch (error) {
            console.error('[PWA] Error pre-caching offline data:', error);
            updateProgress(`Błąd: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get offline cache status info
     */
    async getOfflineCacheStatus() {
        const stored = localStorage.getItem('offlineCacheInfo');
        const cacheInfo = stored ? JSON.parse(stored) : null;

        // Get actual cache sizes
        const sizes = {};
        const cacheNames = ['libriya-v13', 'libriya-micro-v1', 'libriya-data-v1', 'libriya-thumbnails-v1'];

        for (const name of cacheNames) {
            try {
                const cache = await caches.open(name);
                const keys = await cache.keys();
                sizes[name] = keys.length;
            } catch (e) {
                sizes[name] = 0;
            }
        }

        return {
            lastCache: cacheInfo,
            currentSizes: sizes
        };
    }

    /**
     * Clear all offline book data
     */
    async clearOfflineData() {
        const cachesToClear = ['libriya-micro-v1', 'libriya-data-v1'];

        for (const name of cachesToClear) {
            try {
                await caches.delete(name);
                console.log(`[PWA] Cleared cache: ${name}`);
            } catch (e) {
                console.error(`[PWA] Failed to clear cache ${name}:`, e);
            }
        }

        localStorage.removeItem('offlineCacheInfo');
        console.log('[PWA] Offline data cleared');
    }
}

// Initialize PWA Manager on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaManager = new PWAManager();
    });
} else {
    window.pwaManager = new PWAManager();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PWAManager;
}
