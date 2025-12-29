const fs = require('fs');
const os = require('os');
const path = require('path');

const dir = path.join(os.homedir(), '.warp_open', 'sessions');
const files = fs.existsSync(dir) ? fs.readdirSync(dir).filter(f => f.startsWith('session-') && f.endsWith('.jsonl'))
  .map(f => path.join(dir, f))
  .sort((a,b)=>fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs) : [];

if (!files.length) { 
  console.error('No session logs found'); 
  process.exit(2); 
}

const f = process.argv[2] || files[0];
const lines = fs.readFileSync(f, 'utf8').trim().split(/\r?\n/).map(x=>JSON.parse(x));
const hasStart = lines.some(e => e.type === 'block:start');
const hasEnd   = lines.some(e => e.type === 'block:exec:end' || e.type === 'block:end');

console.log(`LOG: ${f}`);
console.log(`block:start = ${hasStart}, block:end = ${hasEnd}`);
if (!hasStart || !hasEnd) {
  console.error('❌ Block events missing.'); 
  process.exit(1);
}
console.log('✅ Blocks present.');