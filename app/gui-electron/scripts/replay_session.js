#!/usr/bin/env node
const fs = require('fs');
const file = process.argv[2];
if (!file){ console.error('usage: replay_session.js <session.jsonl>'); process.exit(2); }
const out = [];
for (const ln of fs.readFileSync(file,'utf8').split('\n')) {
  if (!ln.trim()) continue;
  try { const ev = JSON.parse(ln); if (ev.type==='pty:data' && typeof ev.sample==='string') out.push(ev.sample); } catch {}
}
process.stdout.write(out.join(''));
