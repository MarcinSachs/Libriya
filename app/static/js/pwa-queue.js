// Simple IndexedDB-backed queue for offline network requests.
// Example:
//   const q = new OfflineQueue();
//   await q.enqueueRequest('/book_delete/5', {method:'POST', headers:{}, body:'...'});
//   await q.flush();

class OfflineQueue {
    constructor(dbName = 'offline-queue', storeName = 'requests') {
        this.dbName = dbName;
        this.storeName = storeName;
        this.dbPromise = this.openDB(dbName, 1, (db) => {
            if (!db.objectStoreNames.contains(storeName)) {
                db.createObjectStore(storeName, { keyPath: 'id', autoIncrement: true });
            }
        });
    }

    openDB(name, version, upgradeCallback) {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(name, version);
            request.onupgradeneeded = (event) => {
                upgradeCallback(event.target.result);
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async _withStore(mode, callback) {
        const db = await this.dbPromise;
        const tx = db.transaction(this.storeName, mode);
        const store = tx.objectStore(this.storeName);
        // execute callback, capture its result
        const result = await callback(store);
        // wait for transaction to finish before returning the result
        await (tx.complete ? tx.complete : new Promise((res) => tx.oncomplete = res));
        return result;
    }

    /**
     * Store a request to be replayed later.
     * `options` should be serializable (no functions/streams).
     */
    async enqueueRequest(url, options = {}) {
        return this._withStore('readwrite', (store) => {
            const item = {
                url,
                options,
                timestamp: Date.now()
            };
            store.add(item);
        });
    }

    async getAll() {
        return this._withStore('readonly', (store) => {
            return new Promise((resolve, reject) => {
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
        });
    }

    async clear() {
        return this._withStore('readwrite', (store) => store.clear());
    }

    async flush() {
        const items = await this.getAll();
        const results = [];
        for (const item of items) {
            try {
                const response = await fetch(item.url, item.options);
                results.push({ item, status: response.status });
                if (response.ok) {
                    await this._withStore('readwrite', store => store.delete(item.id));
                }
            } catch (e) {
                console.error('[OfflineQueue] flush error', e);
                // stop on first failure to try later
                break;
            }
        }
        return results;
    }
}

export default OfflineQueue;