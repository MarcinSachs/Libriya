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
        console.log('[PWA] Secure context:', window.isSecureContext);
        console.log('[PWA] Protocol:', window.location.protocol);
        console.log('[PWA] Hostname:', window.location.hostname);
        console.log('[PWA] User agent:', navigator.userAgent);

        // Hide install buttons if running as standalone/PWA
        if (this.isRunningStandalone()) {
            this.hideInstallPrompt();
        }

        // Check if Service Worker is supported
        if ('serviceWorker' in navigator) {
            // Allow Service Worker on:
            // 1. Secure context (HTTPS)
            // 2. localhost (development)
            // 3. Local network IPs (development on LAN)
            const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const isLocalIP = (
                window.location.hostname.startsWith('192.168.') ||
                window.location.hostname.startsWith('10.') ||
                window.location.hostname.startsWith('172.')
            );
            const canUseServiceWorker = window.isSecureContext || isLocalhost || isLocalIP;

            if (canUseServiceWorker) {
                this.registerServiceWorker();
            } else {
                console.warn('[PWA] Not in secure context and not on local network. Service Worker disabled.');
                console.warn('[PWA] Showing fallback install method for HTTP access.');
                this.showInstallPromptFallback();
            }
        } else {
            console.warn('[PWA] Service Worker not supported in this browser');
        }

        // Online/Offline event listeners
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());

        // Install prompt event listener
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('[PWA] beforeinstallprompt event triggered');
            e.preventDefault();
            this.deferredPrompt = e;
            // Only show if not running as standalone
            if (!this.isRunningStandalone()) {
                this.showInstallPrompt();
            }
        });

        // App installed listener
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed successfully');
            this.deferredPrompt = null;
            this.hideInstallPrompt();
        });

        // Update status on load
        this.updateOnlineStatus();
    }

    /**
     * Returns true if app is running as standalone (PWA)
     */
    isRunningStandalone() {
        return (
            window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true ||
            document.referrer.startsWith('android-app://')
        );
    }

    /**
     * Show install prompt fallback for non-secure contexts
     */
    showInstallPromptFallback() {
        // On non-secure contexts (HTTP), still show the button with external install link
        const mobileInstallBtn = document.getElementById('mobile-install-app-btn');

        // Delay to ensure DOM is ready
        setTimeout(() => {
            if (mobileInstallBtn) {
                mobileInstallBtn.style.display = 'inline-flex';
                mobileInstallBtn.style.alignItems = 'center';
                console.log('[PWA] Fallback install button shown for non-secure context');

                if (navigator.userAgent.includes('Android')) {
                    // For Android, change onclick to show instructions
                    mobileInstallBtn.onclick = () => {
                        alert('To install this app on Android:\n\n1. Tap the menu (⋮) in Chrome\n2. Tap "Install app"\n3. Confirm installation');
                    };
                    console.log('[PWA] Android fallback method configured');
                } else if (navigator.userAgent.includes('iPhone') || navigator.userAgent.includes('iPad')) {
                    // For iOS
                    mobileInstallBtn.onclick = () => {
                        alert('To install on iOS:\n\n1. Tap Share button (Up arrow)\n2. Tap "Add to Home Screen"\n3. Tap "Add"');
                    };
                    console.log('[PWA] iOS fallback method configured');
                }
            }
        }, 100);
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

        const cache = await caches.open('libriya-v14');

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
        const mobileInstallBtn = document.getElementById('mobile-install-app-btn');

        if (installBtn) {
            installBtn.style.display = 'inline-block';
        }
        if (mobileInstallBtn) {
            mobileInstallBtn.style.display = 'inline-flex';
            mobileInstallBtn.style.alignItems = 'center';
        }
        console.log('[PWA] Install prompt shown');
    }

    /**
     * Hide install prompt
     */
    hideInstallPrompt() {
        const installBtn = document.getElementById('install-app-btn');
        const mobileInstallBtn = document.getElementById('mobile-install-app-btn');

        if (installBtn) {
            installBtn.style.display = 'none';
        }
        if (mobileInstallBtn) {
            mobileInstallBtn.style.display = 'none';
        }
    }

    /**
     * Handle install button click
     */
    installApp() {
        if (!this.deferredPrompt) {
            console.warn('[PWA] Install prompt not available - showing manual instructions');

            // Fallback: Show manual installation instructions
            if (navigator.userAgent.includes('Android')) {
                alert('To install this app:\n\n1. Tap the menu (⋮) in Chrome\n2. Tap "Install app"\n3. Confirm installation\n\nOr:\n1. Tap Share (↗️)\n2. Tap "Add to Home Screen"');
            } else if (navigator.userAgent.includes('iPhone') || navigator.userAgent.includes('iPad')) {
                alert('To install on iOS:\n\n1. Tap Share button (Up arrow ↗️)\n2. Scroll and tap "Add to Home Screen"\n3. Tap "Add" button');
            } else {
                alert('To install this app:\n\n1. Look for an install prompt in the address bar\n2. Or use your browser menu to "Install app"');
            }
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

        let totalBytes = 0; // Track total size

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
            const jsonString = JSON.stringify(data);
            totalBytes += jsonString.length;
            await dataCache.put(
                new URL('/api/offline/books', location.origin).href,
                new Response(jsonString, {
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
                            const blob = await coverResponse.clone().blob();
                            totalBytes += blob.size;
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
                        const blob = await pageResponse.clone().blob();
                        totalBytes += blob.size;
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
                totalBytes: totalBytes,
                totalFormatted: this.formatBytes(totalBytes),
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

        // Use stored size from last download
        const totalBytes = cacheInfo?.totalBytes || 0;
        const totalFormatted = cacheInfo?.totalFormatted || this.formatBytes(totalBytes);

        return {
            lastCache: cacheInfo,
            totalBytes: totalBytes,
            totalFormatted: totalFormatted
        };
    }

    /**
     * Format bytes to human readable string
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
