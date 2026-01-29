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

        // Register Service Worker
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
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

            // Check for updates periodically
            setInterval(() => {
                this.swRegistration.update();
            }, 60000); // Every minute

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
