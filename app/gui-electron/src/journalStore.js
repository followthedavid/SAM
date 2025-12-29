/**
 * journalStore - persistent JSON journal for AI actions with simple undo-last.
 * Stores to: ~/.warp_open/warp_history.json
 */
const fs = require('fs').promises;
const path = require('path');
const os = require('os');
const { makeId } = require('./fsOps');

const BASE_DIR = path.join(os.homedir(), '.warp_open');
const STORE_FILE = path.join(BASE_DIR, 'warp_history.json');

async function ensureStore() {
  await fs.mkdir(BASE_DIR, { recursive: true });
  try {
    await fs.access(STORE_FILE);
  } catch {
    await fs.writeFile(STORE_FILE, JSON.stringify({ entries: [] }, null, 2), 'utf8');
  }
}

async function loadStore() {
  await ensureStore();
  const txt = await fs.readFile(STORE_FILE, 'utf8');
  return JSON.parse(txt || '{"entries": []}');
}

async function saveStore(store) {
  await ensureStore();
  await fs.writeFile(STORE_FILE, JSON.stringify(store, null, 2), 'utf8');
}

async function logAction({ type, summary, payload = {} } = {}) {
  const store = await loadStore();
  const entry = {
    id: makeId('action'),
    timestamp: new Date().toISOString(),
    type,
    summary,
    payload
  };
  store.entries.unshift(entry); // newest first
  await saveStore(store);
  return entry;
}

async function getEntries({ offset = 0, limit = 100 } = {}) {
  const store = await loadStore();
  return store.entries.slice(offset, offset + limit);
}

async function undoLast() {
  const store = await loadStore();
  if (!store.entries || store.entries.length === 0) {
    return { ok: false, error: 'no-actions' };
  }
  const last = store.entries.shift();
  await saveStore(store);
  return { ok: true, undone: last };
}

module.exports = {
  logAction,
  getEntries,
  undoLast,
  STORE_FILE
};
