#!/usr/bin/env node
// Replay a session JSONL file, printing concatenated PTY output for a given ptyId (optional)
// Usage: node replay_session.js <path-to-jsonl> [ptyId]
const fs = require('fs');

function main() {
  const fp = process.argv[2];
  const targetId = process.argv[3] || null;
  if (!fp) {
    console.error('Usage: replay_session.js <path> [ptyId]');
    process.exit(2);
  }
  const rs = fs.createReadStream(fp, { encoding: 'utf8' });
  let buf = '';
  rs.on('data', chunk => {
    buf += chunk;
    let idx;
    while ((idx = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, idx); buf = buf.slice(idx + 1);
      if (!line.trim()) continue;
      try {
        const obj = JSON.parse(line);
        if (obj.type === 'pty_data' && (!targetId || obj.ptyId === targetId)) {
          process.stdout.write(obj.data);
        }
      } catch {}
    }
  });
  rs.on('end', () => { if (buf.trim()) { try { const o = JSON.parse(buf); if (o.type === 'pty_data' && (!targetId || o.ptyId === targetId)) process.stdout.write(o.data); } catch {} } });
}

if (require.main === module) main();
