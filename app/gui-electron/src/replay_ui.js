/* Minimal Replay Timeline UI
 * - Toggle via button with id="btn-replay" (added below)
 * - Panel #replay-panel with:
 *   left: sessions list + search
 *   right: blocks timeline + output replay
 */

function h(tag, attrs={}, ...children){
  const el = document.createElement(tag);
  for (const [k,v] of Object.entries(attrs||{})){
    if (k === 'class') el.className = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else el.setAttribute(k, v);
  }
  for (const ch of children){
    if (ch == null) continue;
    if (typeof ch === 'string') el.appendChild(document.createTextNode(ch));
    else el.appendChild(ch);
  }
  return el;
}

const state = {
  sessions: [],
  selected: null,
  events: [],
  blocks: [],
  output: '',
};

function fmtDuration(ms){
  if (ms == null) return '—';
  if (ms < 1000) return `${ms} ms`;
  const s = (ms/1000).toFixed(2);
  return `${s}s`;
}

function parseBlocks(events){
  // Build simple blocks from block:start/block:end and collect pty:data between them
  const blocks = [];
  const byId = new Map();
  for (const ev of events){
    if (ev.type === 'block:start'){
      byId.set(ev.id, { id: ev.id, cmd: ev.cmd || ev.command || '', start: ev.t, end: null, cwd: ev.cwd, exit: null, durationMs: null, _dataIdx: [] });
    } else if (ev.type === 'block:end'){
      const b = byId.get(ev.id);
      if (b){
        b.end = ev.t;
        b.exit = ev.exit;
        b.durationMs = ev.durationMs ?? ev.duration_ms ?? null;
        blocks.push(b);
      }
    }
  }
  // attach output by time window (best-effort)
  // build an index of pty:data with timestamps (monotonic order assumed)
  // If evs lack timestamps suitable for interpolate, just concatenate all pty:data for simplicity.
  const allData = events.filter(e => e.type === 'pty:data').map(e => e.data).join('');
  for (const b of blocks){ b.output = allData; } // simple, deterministic replay
  return blocks;
}

function renderSessions(){
  const list = document.getElementById('replay-sessions');
  list.innerHTML = '';
  for (const s of state.sessions){
    const row = h('div', { class: 'sess-row', onclick: async ()=>{
      state.selected = s;
      const { events } = await window.bridge.readSession(s.path);
      state.events = events || [];
      state.blocks = parseBlocks(state.events);
      renderBlocks();
    }},
    h('div', { class:'name' }, s.file),
    h('div', { class:'meta' }, new Date(s.mtimeMs).toLocaleString(), ' · ', `${(s.size/1024).toFixed(1)} KB`)
    );
    if (state.selected && state.selected.path === s.path) row.classList.add('active');
    list.appendChild(row);
  }
}

function renderBlocks(){
  const tl = document.getElementById('replay-timeline');
  const out = document.getElementById('replay-output');
  tl.innerHTML = '';
  out.textContent = '';
  for (const b of state.blocks){
    const statusClass = (b.exit === 0) ? 'ok' : (b.exit == null ? 'run' : 'err');
    const row = h('div', { class: `blk-row ${statusClass}`, onclick: ()=>{
      out.textContent = b.output || '';
    }},
      h('div', { class:'cmd' }, b.cmd || b.command || '(unknown)'),
      h('div', { class:'meta' },
        `exit: ${b.exit ?? '—'} · `,
        `dur: ${fmtDuration(b.durationMs)} · `,
        `cwd: ${b.cwd || '—'}`
      ),
    );
    tl.appendChild(row);
  }
}

async function refreshSessions(){
  const q = document.getElementById('replay-search').value.trim().toLowerCase();
  const all = await window.bridge.listSessions(200);
  state.sessions = (q ? all.filter(s => s.file.toLowerCase().includes(q)) : all);
  renderSessions();
}

function toggleReplay(){
  const panel = document.getElementById('replay-panel');
  panel.classList.toggle('open');
  if (panel.classList.contains('open')) refreshSessions();
}

function bootReplayUI(){
  const btn = document.getElementById('btn-replay');
  if (btn){ btn.addEventListener('click', toggleReplay); }
  document.addEventListener('keydown', (e)=>{
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase()==='r' && e.shiftKey){
      // Cmd/Ctrl+Shift+R → open replay
      e.preventDefault(); toggleReplay();
    }
  });
  const srch = document.getElementById('replay-search');
  if (srch) srch.addEventListener('input', ()=>refreshSessions());
}

document.addEventListener('DOMContentLoaded', bootReplayUI);