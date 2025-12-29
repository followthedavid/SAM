const { ipcMain } = require('electron');
const fs = require('fs');
const os = require('os');
const path = require('path');

const SESS_DIR = path.join(os.homedir(), '.warp_open', 'sessions');

function safeListSessions(limit = 100) {
  try {
    if (!fs.existsSync(SESS_DIR)) return [];
    const files = fs.readdirSync(SESS_DIR)
      .filter(f => f.startsWith('session-') && f.endsWith('.jsonl'))
      .map(f => {
        const p = path.join(SESS_DIR, f);
        const st = fs.statSync(p);
        return { file: f, path: p, mtimeMs: st.mtimeMs, size: st.size };
      })
      .sort((a,b) => b.mtimeMs - a.mtimeMs)
      .slice(0, limit);
    return files;
  } catch (e) {
    return [];
  }
}

function readJsonl(filepath, maxBytes = 5_000_000) {
  // cap to 5MB by default; large sessions can be heavy in renderer
  const st = fs.statSync(filepath);
  let start = 0;
  if (st.size > maxBytes) start = st.size - maxBytes;
  const fd = fs.openSync(filepath, 'r');
  const buf = Buffer.alloc(st.size - start);
  fs.readSync(fd, buf, 0, buf.length, start);
  fs.closeSync(fd);
  const text = buf.toString('utf8');
  // ensure we start on a new line
  const firstNl = text.indexOf('\n');
  const trimmed = start ? text.slice(firstNl + 1) : text;
  const lines = trimmed.split('\n').filter(Boolean);
  const events = [];
  for (const ln of lines) {
    try { events.push(JSON.parse(ln)); } catch {}
  }
  return events;
}

function wireReplayIpc() {
  ipcMain.handle('replay:list-sessions', (_e, limit = 200) => safeListSessions(limit));
  ipcMain.handle('replay:read-session', (_e, fullpath) => {
    if (!fullpath || typeof fullpath !== 'string') return { events: [] };
    try { return { events: readJsonl(fullpath) }; }
    catch (e) { return { events: [] }; }
  });
}

module.exports = { wireReplayIpc };