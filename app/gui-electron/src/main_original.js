const { app, BrowserWindow, ipcMain, shell, Menu, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const pty = require('node-pty');

// WARP_OPEN_SMOKE_MARKER
try {
  const { maybeRunSmoke } = require("./smoke");
  if (maybeRunSmoke(require("electron").app)) {
    // headless smoke handled; main process will continue but won't create UI
    module.exports = {};
    return; // Don't exit immediately, let the smoke test complete
  }
} catch (e) { /* smoke not fatal */ }
// WARP_OPEN_SMOKE_MARKER
let win;
let pendingSessionPath = null;
function scheduleSessionLoad(p) {
  try {
    if (typeof p !== 'string' || !p.toLowerCase().endsWith('.json')) return;
    if (win && !win.isDestroyed()) {
      win.webContents.send('menu:session-load-path', p);
      pendingSessionPath = null;
    } else {
      pendingSessionPath = p;
    }
  } catch {}
}
function createWindow() {
  const cfg = readConfig();
  win = new BrowserWindow({
    x: (cfg.window && Number.isFinite(cfg.window.x)) ? cfg.window.x : undefined,
    y: (cfg.window && Number.isFinite(cfg.window.y)) ? cfg.window.y : undefined,
    width: (cfg.window && cfg.window.width) ? cfg.window.width : 1080,
    height: (cfg.window && cfg.window.height) ? cfg.window.height : 720,
    backgroundColor: '#0b0f14',
    title: 'Warp_Open — Terminal',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false
    }
  });
  if (cfg.window && cfg.window.maximized) try { win.maximize(); } catch {}
  win.loadFile(path.join(__dirname, 'index.html'));
  try { const c = readConfig(); if (c && c.openDevToolsOnStart) win.webContents.openDevTools({ mode: 'detach' }); } catch {}
  setAppMenu();
  // Structured app start log
  try { logEvent({ type: 'app_start', version: app.getVersion(), electron: process.versions.electron, node: process.versions.node }); } catch {}
  // If a session file was queued before window creation, load it now
  if (pendingSessionPath) { try { scheduleSessionLoad(pendingSessionPath); } catch {} }
  // Persist window size/pos/state
  try {
    const writeWinState = (overrides = {}) => {
      const [w,h] = win.getSize();
      const [x,y] = win.getPosition();
      const maximized = win.isMaximized();
      writeConfig({ window: Object.assign({ x, y, width: w, height: h, maximized }, overrides) });
    };
    win.on('maximize', () => { writeWinState({ maximized: true }); });
    win.on('unmaximize', () => { writeWinState({ maximized: false }); });
    win.on('resize', () => { if (!win.isMaximized()) writeWinState({ maximized: false }); });
    win.on('move', () => { if (!win.isMaximized()) writeWinState({ maximized: false }); });
  } catch {}
}

function setAppMenu() {
  const isMac = process.platform === 'darwin';
  const cfg = readConfig();
  const themeMode = cfg.themeMode || 'dark';
  const send = (channel, payload) => {
    if (win && !win.isDestroyed()) win.webContents.send(`menu:${channel}`, payload);
  };
  // Build Open Recent submenu
  const recent = Array.isArray(cfg.recentSessions) ? cfg.recentSessions : [];
  const recentExisting = recent.filter(p => { try { return p && fs.existsSync(p); } catch { return false; } });
  const recentItems = recentExisting.length
    ? recentExisting.slice(0, 10).map(p => ({ label: path.basename(p) || p, click: () => send('session-load-path', p) }))
    : [{ label: 'None', enabled: false }];
  recentItems.push({ type: 'separator' }, { label: 'Clear Recent', click: () => { try { writeConfig({ recentSessions: [] }); setAppMenu(); } catch {} } });
  const template = [
    ...(isMac ? [{
      label: app.name,
      submenu: [
{ role: 'about' },
        { type: 'separator' },
        { label: 'Preferences…', accelerator: 'CmdOrCtrl+,', click: () => send('open-prefs') },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }] : []),
    {
      label: 'File',
      submenu: [
        { label: 'New Tab', accelerator: 'CmdOrCtrl+T', click: () => send('new-tab') },
        { label: 'New Tab in Folder…', accelerator: 'CmdOrCtrl+Alt+T', click: () => send('new-tab-folder') },
        { label: 'Rename Tab', accelerator: 'CmdOrCtrl+Shift+R', click: () => send('tab-rename') },
        { label: 'Close Tab', accelerator: 'CmdOrCtrl+W', click: () => send('close-tab') },
        { label: 'Close All Tabs', accelerator: 'CmdOrCtrl+Shift+Q', click: () => send('tab-close-all') },
        { type: 'separator' },
        { label: 'Split Horizontal', accelerator: 'CmdOrCtrl+Shift+H', click: () => send('split-horizontal') },
        { label: 'Split Vertical', accelerator: 'CmdOrCtrl+Shift+V', click: () => send('split-vertical') },
        { label: 'Duplicate Pane', accelerator: 'CmdOrCtrl+Shift+D', click: () => send('duplicate-pane') },
        { label: 'Close Pane', accelerator: 'CmdOrCtrl+Shift+W', click: () => send('close-pane') },
        { type: 'separator' },
        { label: 'Export Scrollback…', click: () => send('export-scrollback') },
        { label: 'Duplicate Tab', click: () => send('tab-duplicate') },
        { type: 'separator' },
        { id: 'session-save', label: 'Save Session', accelerator: 'CmdOrCtrl+S', enabled: !!cfg.lastSessionPath, click: () => send('session-save') },
        { label: 'Save Session As…', accelerator: 'CmdOrCtrl+Shift+S', click: () => send('session-save-as') },
        { label: 'Open Recent', submenu: recentItems },
        { label: 'Load Session…', click: () => send('session-load') },
        { label: 'Load Auto-Saved Session', click: () => send('session-load-autosave') },
        ...(isMac ? [{ role: 'close' }] : [{ role: 'quit' }])
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { label: 'Copy', accelerator: 'CmdOrCtrl+C', click: () => send('copy') },
        { label: 'Copy as Quoted', click: () => send('copy-quoted') },
        { label: 'Paste', accelerator: 'CmdOrCtrl+V', click: () => send('paste') },
        { type: 'separator' },
        { label: 'Find…', accelerator: 'CmdOrCtrl+F', click: () => send('find-open') },
        { label: 'Find Next', accelerator: 'Enter', click: () => send('find-next') },
        { label: 'Find Previous', accelerator: 'Shift+Enter', click: () => send('find-prev') },
        { type: 'separator' },
        { label: 'Open Selected Path', click: () => send('open-selected-path') },
        { label: 'Reveal Selected Path', click: () => send('reveal-selected-path') },
        { label: 'CD Selected Path', click: () => send('cd-selected-path') },
        { label: 'CD Tab Folder', click: () => send('cd-tab-cwd') },
        { type: 'separator' },
        { label: 'Clear', accelerator: 'CmdOrCtrl+K', click: () => send('clear') },
        { label: 'Clear Scrollback', click: () => send('clear-scrollback') },
        { label: 'Reset', accelerator: 'CmdOrCtrl+Shift+X', click: () => send('reset') },
        { type: 'separator' },
        { id: 'copy-on-select', label: 'Copy on Selection', type: 'checkbox', checked: !!cfg.copyOnSelection, accelerator: 'CmdOrCtrl+Shift+C', click: () => send('toggle-copy-on-select') },
        { id: 'bell-sound', label: 'Bell Sound', type: 'checkbox', checked: !!cfg.bellSound, click: () => send('toggle-bell-sound') },
        { id: 'bell-toast', label: 'Bell Toast', type: 'checkbox', checked: !!cfg.bellToast, click: () => send('toggle-bell-toast') },
        { type: 'separator' },
        { label: 'Select All', accelerator: 'CmdOrCtrl+A', click: () => send('selectAll') },
        { label: 'Copy CWD', click: () => send('copy-cwd') }
      ]
    },
    {
      label: 'Navigate',
      submenu: [
        { label: 'Next Pane', accelerator: 'CmdOrCtrl+]', click: () => send('pane-next') },
        { label: 'Previous Pane', accelerator: 'CmdOrCtrl+[', click: () => send('pane-prev') },
        { type: 'separator' },
        { label: 'Grow Pane', accelerator: 'CmdOrCtrl+Shift+Right', click: () => send('pane-grow') },
        { label: 'Shrink Pane', accelerator: 'CmdOrCtrl+Shift+Left', click: () => send('pane-shrink') },
        { label: 'Equalize Panes', accelerator: 'CmdOrCtrl+Shift+0', click: () => send('panes-equal') },
        { type: 'separator' },
        { label: 'Next Tab', accelerator: 'CmdOrCtrl+Alt+Right', click: () => send('tab-next') },
        { label: 'Previous Tab', accelerator: 'CmdOrCtrl+Alt+Left', click: () => send('tab-prev') },
        { type: 'separator' },
        { label: 'Move Tab Left', accelerator: 'CmdOrCtrl+Alt+Shift+Left', click: () => send('tab-move-left') },
        { label: 'Move Tab Right', accelerator: 'CmdOrCtrl+Alt+Shift+Right', click: () => send('tab-move-right') },
        { type: 'separator' },
        { label: 'Close Others', accelerator: 'CmdOrCtrl+Alt+Shift+O', click: () => send('tab-close-others') },
        { label: 'Close Tabs to Left', accelerator: 'CmdOrCtrl+Alt+Shift+[', click: () => send('tab-close-left') },
        { label: 'Close Tabs to Right', accelerator: 'CmdOrCtrl+Alt+Shift+]', click: () => send('tab-close-right') },
        { type: 'separator' },
        { label: 'Tab 1', accelerator: 'CmdOrCtrl+1', click: () => send('tab-index', 0) },
        { label: 'Tab 2', accelerator: 'CmdOrCtrl+2', click: () => send('tab-index', 1) },
        { label: 'Tab 3', accelerator: 'CmdOrCtrl+3', click: () => send('tab-index', 2) },
        { label: 'Tab 4', accelerator: 'CmdOrCtrl+4', click: () => send('tab-index', 3) },
        { label: 'Tab 5', accelerator: 'CmdOrCtrl+5', click: () => send('tab-index', 4) },
        { label: 'Tab 6', accelerator: 'CmdOrCtrl+6', click: () => send('tab-index', 5) },
        { label: 'Tab 7', accelerator: 'CmdOrCtrl+7', click: () => send('tab-index', 6) },
        { label: 'Tab 8', accelerator: 'CmdOrCtrl+8', click: () => send('tab-index', 7) },
        { label: 'Tab 9', accelerator: 'CmdOrCtrl+9', click: () => send('tab-index', 8) }
      ]
    },
    {
      label: 'View',
      submenu: [
        { id: 'view-broadcast', label: 'Broadcast to Panes (Tab)', type: 'checkbox', click: () => send('toggle-broadcast') },
        { role: 'reload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { label: 'Default Font Size', accelerator: 'CmdOrCtrl+0', click: () => send('font-reset') },
        { label: 'Increase Font Size', accelerator: 'CmdOrCtrl+=', click: () => send('font-increase') },
        { label: 'Decrease Font Size', accelerator: 'CmdOrCtrl+-', click: () => send('font-decrease') },
        { type: 'separator' },
        { role: 'togglefullscreen' },
        { type: 'separator' },
        { label: 'Toggle Pane Zoom', accelerator: 'CmdOrCtrl+Shift+Z', click: () => send('pane-zoom') },
        { type: 'separator' },
        { label: 'Theme', submenu: [
          { id: 'theme-system', label: 'System', type: 'radio', checked: themeMode === 'system', click: () => send('theme-system') },
          { id: 'theme-dark', label: 'Dark', type: 'radio', checked: themeMode === 'dark', click: () => send('theme-dark') },
          { id: 'theme-light', label: 'Light', type: 'radio', checked: themeMode === 'light', click: () => send('theme-light') }
        ]}
      ]
    },
    { role: 'windowMenu' },
    {
      label: 'Help',
      submenu: [
        { label: 'About Warp_Open', click: () => send('about-show') },
        { label: 'Keyboard Shortcuts…', click: () => send('help-shortcuts') },
        { label: 'Run Diagnostics…', click: () => send('help-diagnostics') },
        { type: 'separator' },
        { label: 'Open Logs Folder', click: () => send('help-open-logs') },
        { label: 'Open App Data Folder', click: () => send('help-open-userdata') },
        { label: 'Open Project Folder', click: () => send('help-open-project') },
        { label: 'Reveal Autosave File', click: () => send('help-reveal-autosave') }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// Single instance lock + argv session handling
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', (_e, argv, _cwd) => {
    try {
      if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
      const cand = (argv || []).find(a => typeof a === 'string' && a.toLowerCase().endsWith('.json'));
      if (cand) scheduleSessionLoad(cand);
    } catch {}
  });
}

app.whenReady().then(() => {
  // Load session from argv if provided
  try {
    const argv = process.argv || [];
    const cand = argv.find(a => typeof a === 'string' && a.toLowerCase().endsWith('.json'));
    if (cand) pendingSessionPath = cand;
  } catch {}
  createWindow();
});
app.on('open-file', (event, path) => { try { event.preventDefault(); scheduleSessionLoad(path); } catch {} });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

// Multi-session PTY management
const sessions = new Map();
function genId() { return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`; }

// Session JSONL logging
let sessionLog = null;
function getSessionsDir() {
  try {
    const override = process.env.WARP_OPEN_LOG_DIR;
    if (override && override.trim()) {
      const p = path.resolve(override.trim());
      fs.mkdirSync(p, { recursive: true });
      return p;
    }
    const base = process.env.HOME || app.getPath('home') || process.cwd();
    const dir = path.join(base, '.warp_open', 'sessions');
    fs.mkdirSync(dir, { recursive: true });
    return dir;
  } catch {
    const dir = path.join(process.cwd(), '.warp_open_sessions');
    try { fs.mkdirSync(dir, { recursive: true }); } catch {}
    return dir;
  }
}
function getSessionLogStream() {
  if (sessionLog) return sessionLog;
  try {
    const dir = getSessionsDir();
    const sid = (process.env.WARP_OPEN_SESSION || `${Date.now()}-${Math.floor(Math.random()*1e6)}`).replace(/[^a-zA-Z0-9._-]/g,'');
    const fp = path.join(dir, `session-${sid}.jsonl`);
    sessionLog = fs.createWriteStream(fp, { flags: 'a' });
  } catch {}
  return sessionLog;
}
function logEvent(obj) {
  try {
    const ws = getSessionLogStream();
    if (!ws) return;
    const rec = Object.assign({ ts: new Date().toISOString() }, obj || {});
    ws.write(JSON.stringify(rec) + '\n');
  } catch {}
}

ipcMain.handle('pty:start', (_event, opts = {}) => {
  const id = genId();
  const cfg = readConfig();
  const shellPath = (cfg.shellPath && typeof cfg.shellPath === 'string') ? cfg.shellPath : (process.env.SHELL || '/bin/zsh');
  const env = Object.assign({}, process.env, {
    TERM: 'xterm-256color',
    COLORTERM: 'truecolor',
    WARP_OPEN_SESSION: process.env.WARP_OPEN_SESSION || `${Date.now()}-${Math.floor(Math.random()*1e6)}`
  });
  const parseArgs = (s) => {
    if (!s || typeof s !== 'string') return [];
    const m = s.match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) || [];
    return m.map(x => x.replace(/^['"]|['"]$/g, ''));
  };
  const baseArgs = [];
  if (cfg.shellLogin) baseArgs.push('-l');
  baseArgs.push(...parseArgs(cfg.shellArgs));
  const trySpawn = (sp, args) => pty.spawn(sp, args, {
    name: 'xterm-256color',
    cols: opts.cols || 120,
    rows: opts.rows || 32,
    cwd: opts.cwd || process.env.HOME,
    env
  });
  let term = null;
  try {
    term = trySpawn(shellPath, baseArgs);
  } catch (e1) {
    try {
      term = trySpawn('/bin/zsh', ['-l']);
    } catch (e2) {
      try { term = trySpawn('/bin/bash', ['-l']); } catch (e3) {
        return { ok: false, error: String(e1 && e1.message || e2 && e2.message || e3 && e3.message || 'spawn failed') };
      }
    }
  }
  sessions.set(id, term);
  // Log PTY start
  try {
    logEvent({ type: 'pty_start', ptyId: id, shell: shellPath, args: baseArgs, cols: opts.cols || 120, rows: opts.rows || 32, cwd: opts.cwd || process.env.HOME, env: { WARP_OPEN_SESSION: env.WARP_OPEN_SESSION } });
  } catch {}
  term.onData(data => { logEvent({ type: 'pty_data', ptyId: id, data }); if (win && !win.isDestroyed()) win.webContents.send('pty:data', { id, data }); });
  term.onExit(e => {
    sessions.delete(id);
    logEvent({ type: 'pty_exit', ptyId: id, exitCode: e.exitCode });
    if (win && !win.isDestroyed()) win.webContents.send('pty:exit', { id, exitCode: e.exitCode });
  });
  return { ok: true, id };
});

ipcMain.on('pty:input', (_e, { id, data }) => { logEvent({ type: 'pty_input', ptyId: id, data }); const t = sessions.get(id); if (t) t.write(data); });
ipcMain.on('pty:resize', (_e, { id, cols, rows }) => { logEvent({ type: 'pty_resize', ptyId: id, cols, rows }); const t = sessions.get(id); if (t && cols && rows) t.resize(cols, rows); });
ipcMain.on('pty:kill', (_e, { id }) => { const t = sessions.get(id); if (t) { try { t.kill(); } catch {} sessions.delete(id); logEvent({ type: 'pty_kill', ptyId: id }); } });
ipcMain.on('open:external', (_e, href) => { if (typeof href === 'string' && href.startsWith('http')) shell.openExternal(href); });

// About dialog
ipcMain.handle('about:show', async () => {
  const version = app.getVersion();
  const msg = `Warp_Open\nVersion ${version}\nElectron ${process.versions.electron} | Node ${process.versions.node}`;
  try { await dialog.showMessageBox(win, { type: 'info', buttons: ['OK'], message: msg }); } catch {}
  return true;
});

// Shortcuts help dialog
ipcMain.handle('help:shortcuts', async () => {
  const msg = [
    'Tabs & Panes:',
    '  New Tab: Cmd/Ctrl+T',
    '  Split H/V: Cmd/Ctrl+Shift+H / +Shift+V',
    '  Close Pane: Cmd/Ctrl+Shift+W',
    '  Pane Next/Prev: Cmd/Ctrl+] / Cmd/Ctrl+[',
    '  Grow/Shrink Pane: Cmd/Ctrl+Shift+Right/Left',
    '  Equalize Panes: Cmd/Ctrl+Shift+0',
    '',
    'Find:',
    '  Find: Cmd/Ctrl+F, Next: Enter, Prev: Shift+Enter',
    '',
    'Edit:',
    '  Clear: Cmd/Ctrl+K, Reset: Cmd/Ctrl+Shift+X',
    '  Select All: Cmd/Ctrl+A',
    '',
    'View:',
    '  Font +/-: Cmd/Ctrl+= / Cmd/Ctrl+-  (Reset: Cmd/Ctrl+0)',
    '  Toggle Zoom: Cmd/Ctrl+Shift+Z'
  ].join('\n');
  try { await dialog.showMessageBox(win, { type: 'info', buttons: ['OK'], message: 'Keyboard Shortcuts', detail: msg }); } catch {}
  return true;
});

// Diagnostics
ipcMain.handle('help:diagnostics', async () => {
  try {
    const cfg = readConfig();
    const paths = {
      userData: app.getPath('userData'),
      projectRoot: path.join(process.env.HOME || process.cwd(), 'ReverseLab', 'Warp_Open'),
      autosave: (function(){ try { return getAutoSessionPath(); } catch { return ''; } })(),
      lastSession: cfg.lastSessionPath || ''
    };
    const stats = [];
    try { if (paths.autosave) { const st = fs.existsSync(paths.autosave) ? fs.statSync(paths.autosave) : null; stats.push(`Autosave: ${paths.autosave} ${st?`(mtime ${new Date(st.mtimeMs).toISOString()})`:'(missing)'}`); } } catch {}
    try { if (paths.lastSession) { const st = fs.existsSync(paths.lastSession) ? fs.statSync(paths.lastSession) : null; stats.push(`Last Session: ${paths.lastSession} ${st?`(mtime ${new Date(st.mtimeMs).toISOString()})`:'(missing)'}`); } } catch {}
    const versions = `Electron ${process.versions.electron} | Node ${process.versions.node}`;
    const cfgSummary = [
      `themeMode=${cfg.themeMode}`,
      `scrollback=${cfg.scrollback}`,
      `autosaveEnabled=${cfg.autosaveEnabled}`,
      `restoreOnLaunch=${cfg.restoreSessionOnLaunch}`,
      `shellPath=${cfg.shellPath}`,
      `shellLogin=${cfg.shellLogin}`
    ].join(', ');
    const body = [
      `Warp_Open Diagnostics`,
      versions,
      '',
      `Config: ${cfgSummary}`,
      `UserData: ${paths.userData}`,
      `Project: ${paths.projectRoot}`,
      ...(stats.length?['', ...stats]:[])
    ].join('\n');
    await dialog.showMessageBox(win, { type: 'info', buttons: ['OK'], message: 'Diagnostics', detail: body });
  } catch {}
  return true;
});

// Paths helper
ipcMain.handle('env:paths', () => ({
  projectRoot: path.join(process.env.HOME || process.cwd(), 'ReverseLab', 'Warp_Open'),
  receiptsDir: path.join(process.env.HOME || process.cwd(), 'ReverseLab', 'Warp_Open', '.vg', 'receipts', 'warp_open_batch'),
  userData: app.getPath('userData')
}));

// Theme system integration
const { nativeTheme } = require('electron');
ipcMain.handle('theme:get', () => ({ shouldUseDarkColors: nativeTheme.shouldUseDarkColors }));
function broadcastThemeUpdated() {
  if (win && !win.isDestroyed()) win.webContents.send('theme:system-updated', { shouldUseDarkColors: nativeTheme.shouldUseDarkColors });
}
try { nativeTheme.on('updated', broadcastThemeUpdated); } catch {}

// Context menu for terminal panes
ipcMain.handle('menu:terminal', async (_e, _pos) => {
  const send = (ch, payload) => { if (win && !win.isDestroyed()) win.webContents.send(`menu:${ch}`, payload); };
  const template = [
    { label: 'Copy', click: () => send('copy') },
    { label: 'Paste', click: () => send('paste') },
    { type: 'separator' },
    { label: 'Find…', click: () => send('find-open') },
    { type: 'separator' },
    { label: 'Split Horizontal', click: () => send('split-horizontal') },
    { label: 'Split Vertical', click: () => send('split-vertical') },
    { label: 'Close Pane', click: () => send('close-pane') },
    { label: 'Duplicate Pane', click: () => send('duplicate-pane') },
    { type: 'separator' },
    { label: 'Open Selected Path', click: () => send('open-selected-path') },
    { label: 'Reveal Selected Path', click: () => send('reveal-selected-path') },
    { label: 'CD Selected Path', click: () => send('cd-selected-path') },
    { label: 'CD Tab Folder', click: () => send('cd-tab-cwd') },
    { type: 'separator' },
    { label: 'Clear', click: () => send('clear') },
    { label: 'Reset', click: () => send('reset') },
    { label: 'Export Scrollback…', click: () => send('export-scrollback') },
    { label: 'Open Tab Folder', click: () => send('reveal-cwd') },
    { type: 'separator' },
    { label: 'Toggle Pane Zoom', click: () => send('pane-zoom') }
  ];
  const m = Menu.buildFromTemplate(template);
  m.popup({ window: win });
  return true;
});

// Tab header context menu
ipcMain.handle('menu:tab', async (_e, { id }) => {
  const send = (ch, payload) => { if (win && !win.isDestroyed()) win.webContents.send(`menu:${ch}`, payload); };
  const template = [
    { label: 'New Tab', click: () => send('new-tab') },
    { label: 'New Tab in Folder…', click: () => send('new-tab-folder') },
    { type: 'separator' },
    { label: 'Rename', click: () => send('tab-rename') },
    { label: 'Duplicate', click: () => send('tab-duplicate') },
    { type: 'separator' },
    { label: 'Move Left', click: () => send('tab-move-left', id) },
    { label: 'Move Right', click: () => send('tab-move-right', id) },
    { type: 'separator' },
    { label: 'Close Tab', click: () => send('close-tab') },
    { label: 'Close Others', click: () => send('tab-close-others', id) },
    { label: 'Close Tabs to Left', click: () => send('tab-close-left', id) },
    { label: 'Close Tabs to Right', click: () => send('tab-close-right', id) },
    { type: 'separator' },
    { label: 'Reveal CWD', click: () => send('reveal-cwd') }
  ];
  const m = Menu.buildFromTemplate(template);
  m.popup({ window: win });
  return true;
});

// Folder picker
ipcMain.handle('pick:folder', async () => {
  const res = await dialog.showOpenDialog(win, { properties: ['openDirectory'] });
  if (res.canceled || !res.filePaths || !res.filePaths[0]) return null;
  return res.filePaths[0];
});

// Save/Open dialogs and read/write helpers
ipcMain.handle('pick:save', async (_e, suggested) => {
  const res = await dialog.showSaveDialog(win, { defaultPath: suggested || 'scrollback.txt' });
  if (res.canceled || !res.filePath) return null;
  return res.filePath;
});
ipcMain.handle('file:write', async (_e, { path: fpath, data }) => {
  try { fs.writeFileSync(fpath, data); return true; } catch { return false; }
});
ipcMain.handle('pick:open', async () => {
  const res = await dialog.showOpenDialog(win, { properties: ['openFile'], filters: [ { name: 'JSON', extensions: ['json'] }, { name: 'All Files', extensions: ['*'] } ] });
  if (res.canceled || !res.filePaths || !res.filePaths[0]) return null;
  return res.filePaths[0];
});
ipcMain.handle('file:read', async (_e, fpath) => { try { return fs.readFileSync(fpath, 'utf8'); } catch { return null; } });

// Open folder
ipcMain.handle('open:folder', async (_e, fpath) => { try { const r = await shell.openPath(fpath); return !r; } catch { return false; } });
// Open path (file or folder)
ipcMain.handle('open:path', async (_e, fpath) => { try { const r = await shell.openPath(fpath); return !r; } catch { return false; } });
// Reveal in folder
ipcMain.handle('reveal:path', async (_e, fpath) => { try { shell.showItemInFolder(fpath); return true; } catch { return false; } });
// Home dir
ipcMain.handle('env:home', () => process.env.HOME || '');

// FS helpers
ipcMain.handle('fs:stat', (_e, fpath) => {
  try { const st = fs.statSync(String(fpath)); return { exists: true, isDir: st.isDirectory(), isFile: st.isFile() }; } catch { return { exists: false }; }
});
ipcMain.handle('fs:closest', (_e, fpath) => {
  try {
    let cur = String(fpath || '');
    if (!cur) return null;
    while (cur && !fs.existsSync(cur)) {
      const next = path.dirname(cur);
      if (!next || next === cur) break;
      cur = next;
    }
    return fs.existsSync(cur) ? cur : null;
  } catch { return null; }
});

// Config management
function getConfigPath() {
  try { return path.join(app.getPath('userData'), 'config.json'); } catch { return path.join(process.env.HOME || process.cwd(), '.warp_open_config.json'); }
}
function defaultConfig() {
  return {
    theme: 'dark',
    themeMode: 'dark',
    fontSize: 13,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    copyOnSelection: false,
    scrollback: 10000,
    bellSound: true,
    bellToast: true,
    restoreSessionOnLaunch: true,
    autosaveEnabled: true,
    autoSaveIntervalSec: 30,
    recentSessions: [],
    lastSessionPath: null,
    defaultCwd: null,
    newTabUseLastCwd: false,
    openDevToolsOnStart: false,
    autosaveToast: false,
    firstRun: true,
    shellPath: process.env.SHELL || '/bin/zsh',
    shellLogin: true,
    shellArgs: '',
    confirmOnQuit: false,
    writeLastOnQuit: false,
    window: { x: undefined, y: undefined, width: 1080, height: 720, maximized: false }
  };
}
function readConfig() {
  const p = getConfigPath();
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return defaultConfig(); }
}
function writeConfig(patch) {
  const p = getConfigPath();
  let cfg = {};
  try { cfg = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { cfg = defaultConfig(); }
  cfg = Object.assign({}, cfg, patch || {});
  try { fs.mkdirSync(path.dirname(p), { recursive: true }); } catch {}
  fs.writeFileSync(p, JSON.stringify(cfg, null, 2));
  return cfg;
}

ipcMain.handle('config:get', () => readConfig());
ipcMain.handle('config:reset', () => { try { const d = defaultConfig(); fs.writeFileSync(getConfigPath(), JSON.stringify(d, null, 2)); return d; } catch { return readConfig(); } });
ipcMain.handle('config:set', (_e, patch) => {
  const newCfg = writeConfig(patch);
  try {
    const menu = Menu.getApplicationMenu();
    if (menu) {
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'bellSound')) {
        const item = menu.getMenuItemById('bell-sound'); if (item) item.checked = !!newCfg.bellSound;
      }
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'bellToast')) {
        const item = menu.getMenuItemById('bell-toast'); if (item) item.checked = !!newCfg.bellToast;
      }
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'copyOnSelection')) {
        const item = menu.getMenuItemById('copy-on-select'); if (item) item.checked = !!newCfg.copyOnSelection;
      }
      if (patch && (Object.prototype.hasOwnProperty.call(patch, 'theme') || Object.prototype.hasOwnProperty.call(patch, 'themeMode'))) {
        const sys = menu.getMenuItemById('theme-system'); const dark = menu.getMenuItemById('theme-dark'); const light = menu.getMenuItemById('theme-light');
        if (sys && dark && light) {
          sys.checked = newCfg.themeMode === 'system';
          dark.checked = newCfg.themeMode === 'dark';
          light.checked = newCfg.themeMode === 'light';
        }
      }
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'lastSessionPath')) {
        const sv = menu.getMenuItemById('session-save'); if (sv) sv.enabled = !!newCfg.lastSessionPath;
      }
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'recentSessions')) {
        try { setAppMenu(); } catch {}
      }
    }
  } catch {}
  return newCfg;
});
ipcMain.handle('config:open', () => shell.openPath(getConfigPath()));

// Structured log events from renderer
ipcMain.on('log:event', (_e, payload) => { try { if (payload && typeof payload === 'object') logEvent(payload); } catch {} });

// UI state -> menu updates
ipcMain.on('ui:broadcast', (_e, checked) => {
  try {
    const menu = Menu.getApplicationMenu();
    const item = menu && menu.getMenuItemById('view-broadcast');
    if (item) item.checked = !!checked;
  } catch {}
});

// Autosave session file helpers
function getAutoSessionPath() {
  try { return path.join(app.getPath('userData'), 'autosave-session.json'); } catch { return path.join(process.env.HOME || process.cwd(), '.warp_open_autosession.json'); }
}
async function quickSaveSessionFromRenderer() {
  try {
    if (!win || win.isDestroyed()) return false;
    const text = await win.webContents.executeJavaScript("(function(){try{return localStorage.getItem('warp_open_session')||''}catch(e){return ''}})()", true);
    if (!text) return false;
    const p = getAutoSessionPath();
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, String(text));
    return true;
  } catch { return false; }
}
ipcMain.handle('session:auto:save', (_e, text) => {
  try {
    const p = getAutoSessionPath();
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, String(text || ''));
    return true;
  } catch {
    return false;
  }
});
process.on('SIGINT', async () => { try { await quickSaveSessionFromRenderer(); } catch {} process.exit(130); });
process.on('SIGTERM', async () => { try { await quickSaveSessionFromRenderer(); } catch {} process.exit(143); });
process.on('SIGHUP', async () => { try { await quickSaveSessionFromRenderer(); } catch {} process.exit(129); });
let quitting = false;
app.on('before-quit', (e) => {
  if (quitting) return;
  try {
    const cfg = readConfig();
    const persistLast = async () => {
      try {
        if (cfg && cfg.writeLastOnQuit && cfg.lastSessionPath) {
          const text = await win.webContents.executeJavaScript("(function(){try{return localStorage.getItem('warp_open_session')||''}catch(e){return ''}})()", true);
          if (text) { fs.writeFileSync(cfg.lastSessionPath, String(text)); }
        }
      } catch {}
    };
    if (cfg && cfg.confirmOnQuit) {
      e.preventDefault();
      dialog.showMessageBox(win, { type: 'question', buttons: ['Quit', 'Cancel'], defaultId: 0, cancelId: 1, message: 'Quit Warp_Open?', detail: 'Your session will be auto-saved.' }).then(async (res) => {
        if (res.response === 0) {
          quitting = true;
          try { await quickSaveSessionFromRenderer(); } catch {}
          try { await persistLast(); } catch {}
          try { if (sessionLog) sessionLog.end(); } catch {}
          app.quit();
        }
      });
    } else {
      // No confirm, best-effort quick save
      quickSaveSessionFromRenderer();
      persistLast();
      try { if (sessionLog) sessionLog.end(); } catch {}
    }
  } catch {}
});
ipcMain.handle('session:auto:load', () => {
  try { const p = getAutoSessionPath(); return fs.readFileSync(p, 'utf8'); } catch { return null; }
});
ipcMain.handle('session:auto:stat', () => {
  try { const p = getAutoSessionPath(); const st = fs.statSync(p); return { path: p, exists: true, mtimeMs: st.mtimeMs }; } catch { return { path: getAutoSessionPath(), exists: false, mtimeMs: 0 }; }
});
ipcMain.handle('session:last:stat', () => {
  try {
    const cfg = readConfig(); const p = cfg.lastSessionPath || null;
    if (!p) return { path: null, exists: false, mtimeMs: 0 };
    const st = fs.statSync(p); return { path: p, exists: true, mtimeMs: st.mtimeMs };
  } catch {
    try { const cfg2 = readConfig(); return { path: cfg2.lastSessionPath || null, exists: false, mtimeMs: 0 }; } catch { return { path: null, exists: false, mtimeMs: 0 }; }
  }
});

// Recent sessions management
ipcMain.handle('recent:add', (_e, fpath) => {
  try {
    let cfg = readConfig();
    const list = Array.isArray(cfg.recentSessions) ? cfg.recentSessions : [];
    const updated = [String(fpath)].filter(Boolean).concat(list.filter(p => p !== fpath)).slice(0, 10);
    writeConfig({ recentSessions: updated });
    try { setAppMenu(); } catch {}
    return updated;
  } catch {
    return null;
  }
});
