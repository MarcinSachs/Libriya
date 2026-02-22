/**
 * Offline Data Manager - Displays cached books when offline
 * Loads books from caches, displays them with covers and details
 */

class OfflineDataManager {
    constructor() {
        this.books = [];
        this.caches = {};
        this.cacheVersion = (window.pwaConfig && window.pwaConfig.cacheVersion) || 'v1';
        this.cacheNames = {
            main: `libriya-${this.cacheVersion}`,
            thumbnail: `libriya-thumbnails-${this.cacheVersion}`,
            micro: `libriya-micro-${this.cacheVersion}`,
            data: `libriya-data-${this.cacheVersion}`
        };
        console.log('[OfflineDataManager] Initialized with cache version:', this.cacheVersion);
        console.log('[OfflineDataManager] Cache names:', this.cacheNames);
    }

    /**
     * Load all cached books data from caches
     */
    async loadCachedBooks() {
        try {
            console.log('[OfflineDataManager] Attempting to load cached books...');

            // First check if cache exists at all
            const cacheNames = await caches.keys();
            const dataCacheExists = cacheNames.includes(this.cacheNames.data);
            console.log('[OfflineDataManager] Data cache exists?', dataCacheExists, '- looking for:', this.cacheNames.data);

            if (!dataCacheExists) {
                console.log('[OfflineDataManager] Data cache does not exist');
                return [];
            }

            // 1. Load books JSON data from cache with timeout
            const dataCache = await caches.open(this.cacheNames.data);
            const cacheUrl = new URL('/api/offline/books', location.origin).href;
            console.log('[OfflineDataManager] Looking for cache URL:', cacheUrl);

            // Use Promise.race with timeout
            const cacheMatch = Promise.race([
                dataCache.match(cacheUrl),
                new Promise((resolve) => setTimeout(() => resolve(null), 2000))
            ]);

            const response = await cacheMatch;

            if (!response) {
                console.log('[OfflineDataManager] No cached books data found or cache lookup timed out');
                return [];
            }

            const data = await response.json();
            this.books = data.books || [];
            console.log('[OfflineDataManager] Successfully loaded', this.books.length, 'books from cache');
            return this.books;

        } catch (e) {
            console.error('[OfflineDataManager] Error loading cached books:', e);
            return [];
        }
    }

    /**
     * Get a cached book by ID
     */
    getBook(bookId) {
        return this.books.find(b => b.id === parseInt(bookId));
    }

    /**
     * Render books list for offline page
     */
    async renderBooksList(containerId) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn('[OfflineDataManager] Container not found:', containerId);
            return;
        }

        console.log('[OfflineDataManager] Rendering books list in', containerId);

        // Set timeout for loading books
        const loadTimeout = setTimeout(() => {
            console.warn('[OfflineDataManager] renderBooksList timeout - showing empty state');
            container.innerHTML = `
                <div class="text-center py-8">
                    <p class="text-gray-600 mb-4">No books downloaded for offline access</p>
                    <p class="text-sm text-gray-500">Go online and visit Settings → Download to cache books</p>
                </div>
            `;
        }, 3000);

        try {
            const books = await this.loadCachedBooks();
            clearTimeout(loadTimeout); // Clear timeout since we got books

            if (books.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-8">
                        <p class="text-gray-600 mb-4">No books downloaded for offline access</p>
                        <p class="text-sm text-gray-500">Go online and visit Settings → Download to cache books</p>
                    </div>
                `;
                return;
            }

            // Create grid of books
            const grid = document.createElement('div');
            grid.className = 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4';

            for (const book of books) {
                const bookCard = document.createElement('a');
                bookCard.href = book.detail_url;
                bookCard.className = 'offline-book-card group cursor-pointer';
                bookCard.innerHTML = `
                    <div class="bg-white rounded-lg shadow-sm hover:shadow-md transition overflow-hidden h-full flex flex-col">
                        <div class="relative overflow-hidden h-48 bg-gray-200">
                            ${book.micro_cover_url
                        ? `<img src="${book.micro_cover_url}" alt="${book.title}" class="w-full h-full object-cover group-hover:scale-105 transition">`
                        : `<div class="w-full h-full flex items-center justify-center bg-gray-300"><i class="bx bx-image-alt text-gray-500 text-3xl"></i></div>`
                    }
                        </div>
                        <div class="p-3 flex-1 flex flex-col">
                            <h3 class="text-sm font-semibold text-gray-800 line-clamp-2 mb-1">${book.title}</h3>
                            <p class="text-xs text-gray-600 mb-2">
                                ${book.authors && book.authors.length > 0 ? book.authors[0].name : 'Unknown author'}
                            </p>
                            <div class="mt-auto">
                                <p class="text-xs text-gray-500">Library: ${book.library_name || 'Unknown'}</p>
                            </div>
                        </div>
                    </div>
                `;
                grid.appendChild(bookCard);
            }

            container.innerHTML = '';
            container.appendChild(grid);
            console.log('[OfflineDataManager] Rendered', books.length, 'books');
        } catch (e) {
            clearTimeout(loadTimeout);
            console.error('[OfflineDataManager] Error rendering books:', e);
            container.innerHTML = `
                <div class="text-center py-8">
                    <p class="text-red-600 mb-4">Error loading offline books: ${e.message}</p>
                    <p class="text-sm text-gray-500">Go online to reload</p>
                </div>
            `;
        }
    }

    /**
     * Display book details in offline mode
     */
    async displayBookDetail(bookId, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const books = await this.loadCachedBooks();
        const book = books.find(b => b.id === parseInt(bookId));

        if (!book) {
            container.innerHTML = '<p class="text-red-600">Book not found in offline cache</p>';
            return;
        }

        const authorsHtml = book.authors && book.authors.length > 0
            ? `<p class="mb-2"><strong>Authors:</strong> ${book.authors.map(a => a.name).join(', ')}</p>`
            : '';

        container.innerHTML = `
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="grid md:grid-cols-3 gap-6">
                    <div class="md:col-span-1">
                        ${book.micro_cover_url
                ? `<img src="${book.micro_cover_url}" alt="${book.title}" class="w-full rounded-lg shadow-md">`
                : `<div class="w-full h-64 bg-gray-300 rounded-lg flex items-center justify-center"><i class="bx bx-image-alt text-gray-500 text-5xl"></i></div>`
            }
                    </div>
                    <div class="md:col-span-2">
                        <h1 class="text-3xl font-bold mb-2">${book.title}</h1>
                        ${authorsHtml}
                        <p class="mb-2"><strong>ISBN:</strong> ${book.isbn || 'N/A'}</p>
                        <p class="mb-2"><strong>Year:</strong> ${book.year || 'N/A'}</p>
                        <p class="mb-4"><strong>Library:</strong> ${book.library_name}</p>
                        <div class="bg-blue-50 border-l-4 border-blue-500 p-4">
                            <p class="text-blue-800"><i class="bx bx-info-circle"></i> This book is displayed from offline cache. Full details will load when you go online.</p>
                        </div>
                        <div class="mt-4">
                            <a href="/" class="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Back to offline library</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Check if we have cached books
     */
    async hasCachedBooks() {
        const books = await this.loadCachedBooks();
        return books.length > 0;
    }

    /**
     * Get cache statistics
     */
    async getCacheStats() {
        try {
            const newBooks = await this.loadCachedBooks();

            // Count covers
            const microCache = await caches.open(this.cacheNames.micro);
            const microKeys = await microCache.keys();

            // Count book pages
            const mainCache = await caches.open(this.cacheNames.main);
            const mainKeys = await mainCache.keys();
            const bookPages = mainKeys.filter(req =>
                req.url.includes('/book/') && !req.url.includes('/api/')
            ).length;

            return {
                booksCount: newBooks.length,
                coversCount: microKeys.length,
                pagesCount: bookPages
            };
        } catch (e) {
            console.error('[OfflineDataManager] Error getting cache stats:', e);
            return { booksCount: 0, coversCount: 0, pagesCount: 0 };
        }
    }
}

// Export for use as module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OfflineDataManager;
}

// Create global instance
const offlineDataManager = new OfflineDataManager();
console.log('[OfflineDataManager] Global instance created');
