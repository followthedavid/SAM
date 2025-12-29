(function () {
  const state = { items: [], filtered: [], open: false, sel: 0, home: '' };

  function h(sel, attrs={}, ...children) {
    const el = document.createElement(sel);
    for (const [k,v] of Object.entries(attrs||{})) {
      if (k === 'class') el.className = v;
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
      else el.setAttribute(k, v);
    }
    for (const c of children) el.append(c.nodeType ? c : document.createTextNode(c));
    return el;
  }

  function fuzzy(q, item) {
    // simple subsequence match on name + command
    q = q.trim().toLowerCase();
    if (!q) return true;
    const hay = ((item.name||'') + ' ' + (item.command||'')).toLowerCase();
    let i=0;
    for (const ch of q) { i = hay.indexOf(ch, i); if (i < 0) return false; i++; }
    return true;
  }

  function render() {
    const root = document.getElementById('palette-root');
    if (!root) return;
    root.innerHTML = '';
    if (!state.open) { root.style.display = 'none'; return; }
    root.style.display = 'block';

    const onInput = (e) => {
      const q = e.target.value;
      state.filtered = state.items.filter(it => fuzzy(q, it)).slice(0, 200);
      state.sel = 0;
      render();
    };

    const input = h('input', { class: 'pal-input', placeholder: 'Type to search…' });
    input.value = window.localStorage.getItem('palette:lastQuery') || '';
    input.addEventListener('input', onInput);

    const list = h('div', { class: 'pal-list' });
    const src = state.filtered.length || input.value ? state.filtered : state.items.slice(0, 200);

    src.forEach((it, idx) => {
      const row = h('div', { class: 'pal-row' + (idx===state.sel ? ' active' : '') });
      row.append(
        h('div', { class: 'pal-name' }, it.name || '(unnamed)'),
        h('div', { class: 'pal-cmd' }, it.command || '')
      );
      row.addEventListener('mouseenter', () => { state.sel = idx; render(); });
      row.addEventListener('dblclick', () => runSelected(false));
      list.append(row);
    });

    const footer = h('div', { class: 'pal-footer' },
      'Enter: Run   •   Shift+Enter: New Tab   •   Esc: Close'
    );

    root.append(h('div', { class: 'pal-panel' }, input, list, footer));
    input.focus(); input.selectionStart = input.value.length; input.selectionEnd = input.value.length;
  }

  function runSelected(newTab) {
    const arr = state.filtered.length ? state.filtered : state.items.slice(0, 200);
    const it = arr[state.sel];
    if (!it) return;
    const base = (it.base_cwd || state.home || '~');
    const cmd = it.command || '';
    const line = (base ? `cd ${JSON.stringify(base)} && ` : '') + cmd + '\r';

    if (newTab && window.newTab) {
      window.newTab({ cwd: base });
      setTimeout(() => window.bridge.sendInput(line), 60);
    } else {
      window.bridge.sendInput(line);
    }
    // remember last query
    const input = document.querySelector('#palette-root .pal-input');
    if (input) window.localStorage.setItem('palette:lastQuery', input.value || '');
    toggle(false);
  }

  function loadWorkflows() {
    try {
      state.home = (window.files && window.files.getHomeDir) ? window.files.getHomeDir() : '';
      const wfPath = (state.home ? `${state.home}/.warp_open/workflows.json` : '');
      const txt = (window.files && window.files.readTextFile && wfPath) ? window.files.readTextFile(wfPath) : null;
      if (txt) {
        const raw = JSON.parse(txt);
        state.items = Array.isArray(raw) ? raw : [];
      } else {
        state.items = [];
      }
      state.filtered = [];
      state.sel = 0;
    } catch { state.items = []; }
  }

  function toggle(force) {
    if (typeof force === 'boolean') state.open = force;
    else state.open = !state.open;
    if (state.open) loadWorkflows();
    render();
  }

  // Keyboard bindings (Cmd/Ctrl+P, arrows, enter/esc)
  window.addEventListener('keydown', (e) => {
    const isMac = navigator.platform.toLowerCase().includes('mac');
    const mod = isMac ? e.metaKey : e.ctrlKey;

    if (mod && e.key.toLowerCase() === 'p') {
      e.preventDefault();
      toggle(true);
      return;
    }
    if (!state.open) return;

    if (e.key === 'Escape') { e.preventDefault(); toggle(false); }
    if (e.key === 'ArrowDown') { e.preventDefault(); state.sel = Math.min(state.sel+1, (state.filtered.length||state.items.length)-1); render(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); state.sel = Math.max(state.sel-1, 0); render(); }
    if (e.key === 'Enter') {
      e.preventDefault();
      runSelected(e.shiftKey); // Shift+Enter → new tab
    }
  });

  // Expose for buttons/menus if needed
  window.palette = { open: () => toggle(true), close: () => toggle(false), toggle };

  // Initial DOM
  const root = document.createElement('div');
  root.id = 'palette-root';
  document.body.appendChild(root);
  render();
})();