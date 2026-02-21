// This is a tiny node script used by our Python test to exercise queue logic.
// We'll import the JS module, create a queue, enqueue some fake requests and
// flush (mock fetch).

const OfflineQueue = require('../app/static/js/pwa-queue.js').default;

(global.fetch) = async (url, options) => {
    // simulate a successful request
    return { ok: true, status: 200 };
};

async function run() {
    const q = new OfflineQueue('test-queue', 'requests');
    await q.enqueueRequest('/foo', { method: 'POST', body: 'x' });
    await q.enqueueRequest('/bar', { method: 'GET' });
    const all = await q.getAll();
    console.log('enqueued items', all.length);
    const res = await q.flush();
    console.log('flush result', res);
    const leftover = await q.getAll();
    console.log('leftovers', leftover.length);
}

run().catch(e => console.error(e));