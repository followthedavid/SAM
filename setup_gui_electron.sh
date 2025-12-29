# ~/ReverseLab/Warp_Open/setup_gui_electron.sh
set -euo pipefail

FORCE=0
if [[ "${1:-}" == "--force" ]]; then FORCE=1; fi

APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
mkdir -p "$APP/src"

write_if_missing () {
  local path="$1"
  local tag="$2"
  if [[ -f "$path" && $FORCE -eq 0 ]]; then
    echo "• Skipping existing $path (use --force to overwrite)"
    return 0
  fi
  mkdir -p "$(dirname "$path")"
  /usr/bin/env bash -c "cat > \"$path\" <<'$tag'
$3
$tag"
  echo "• Wrote $path"
}

# Check Node
if ! command -v node >/dev/null 2>&1; then
  echo "Node not found. Install first, e.g.:  brew install node"
  exit 1
fi

# package.json
write_if_missing "$APP/package.json" JSON "$(cat <<'JSON'
{
  "name": "warp-open-electron",
  "version": "0.1.0",
  "description": "Minimal clean-room terminal (Electron + xterm.js) for Warp_Open",
  "main": "src/main.js",
  "type": "commonjs",
  "scripts": {
    "dev": "electron .",
    "build": "echo 'Add electron-builder later'",
    "postinstall": "patch -p0 < /dev/null || true"
  },
  "dependencies": {
    "electron": "^31.0.0",
    "node-pty": "^1.0.0",
    "xterm": "^5.5.0",
    "xterm-addon-fit": "^0.9.0",
    "xterm-addon-web-links": "^0.9.0"
  }
}
JSON
)"

# src/main.js
write_if_missing "$APP/src/main.js" JS "$(cat <<'JS'
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const pty = require('node-pty');

let win;
function createWindow() {
  win = new BrowserWindow({
    width: 1080,
    height: 720,
    backgroundColor: '#0b0f14',
    title: 'Warp_Open — Terminal',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false
    }
  });
  win.loadFile(path.join(__dirname, 'index.html'));
  if (!app.isPackaged) win.webContents.openDevTools({ mode: 'detach' });
}
app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

let term;
ipcMain.handle('pty:start', (_event, opts) => {
  const shellPath = process.env.SHELL || (process.platform === 'win32' ? 'pwsh.exe' : '/bin/zsh');
  const env = { ...process.env, TERM:'xterm-256color', COLORTERM:'truecolor',
    WARP_OPEN_SESSION: process.env.WARP_OPEN_SESSION || `${Date.now()}-${Math.floor(Math.random()*1e6)}`
  };
  term = pty.spawn(shellPath, ['-l'], {
    name: 'xterm-256color',
    cols: (opts && opts.cols) || 120,
    rows: (opts && opts.rows) || 32,
    cwd: process.env.HOME,
    env
  });
  term.onData(d => win && win.webContents.send('pty:data', d));
  term.onExit(e => win && win.webContents.send('pty:exit', e));
  return { ok: true };
});
ipcMain.on('pty:input', (_e, d) => { if (term) term.write(d); });
ipcMain.on('pty:resize', (_e, { cols, rows }) => { if (term) term.resize(cols, rows); });
ipcMain.on('open:external', (_e, href) => { if (typeof href === 'string' && href.startsWith('http')) shell.openExternal(href); });
JS
)"

# src/preload.js
write_if_missing "$APP/src/preload.js" JS "$(cat <<'JS'
const { contextBridge, ipcRenderer, clipboard } = require('electron');
contextBridge.exposeInMainWorld('bridge', {
  startPTY: (opts) => ipcRenderer.invoke('pty:start', opts),
  sendInput: (data) => ipcRenderer.send('pty:input', data),
  resizePTY: (cols, rows) => ipcRenderer.send('pty:resize', { cols, rows }),
  onData: (cb) => ipcRenderer.on('pty:data', (_e, d) => cb(d)),
  onExit: (cb) => ipcRenderer.on('pty:exit', (_e, info) => cb(info)),
  copy: (text) => clipboard.writeText(text || ''),
  openExternal: (href) => ipcRenderer.send('open:external', href)
});
JS
)"

# src/index.html
write_if_missing "$APP/src/index.html" HTML "$(cat <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Warp_Open — Terminal</title>
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline';"/>
  <link rel="stylesheet" href="./styles.css"/>
</head>
<body>
  <header id="titlebar">
    <div class="title">Warp_Open — Terminal (clean room)</div>
    <div class="actions">
      <button id="copy">Copy</button>
      <button id="clear">Clear</button>
    </div>
  </header>
  <div id="terminal"></div>
  <script src="./renderer.js"></script>
</body>
</html>
HTML
)"

# src/renderer.js
write_if_missing "$APP/src/renderer.js" JS "$(cat <<'JS'
const { Terminal } = require('xterm');
const { FitAddon } = require('xterm-addon-fit');
const { WebLinksAddon } = require('xterm-addon-web-links');

const termEl = document.getElementById('terminal');
const copyBtn = document.getElementById('copy');
const clearBtn = document.getElementById('clear');

const term = new Terminal({
  fontFamily: 'ui-monospace, Menlo, Monaco, "Cascadia Mono", monospace',
  fontSize: 13,
  theme: { background: '#0b0f14', foreground: '#e6edf3', cursor: '#a6da95', selection: '#204a72' },
  allowProposedApi: true,
  scrollback: 5000,
  convertEol: false
});
const fit = new FitAddon();
term.loadAddon(fit);
term.loadAddon(new WebLinksAddon((e, uri) => window.bridge.openExternal(uri)));

term.open(termEl);
fit.fit();
window.bridge.startPTY({ cols: term.cols, rows: term.rows });
window.bridge.onData((data) => term.write(data));
window.bridge.onExit((info) => term.write(`\r\n\x1b[31m[process exited: code=${info.exitCode}]\x1b[0m\r\n`));
term.onData(d => window.bridge.sendInput(d));

const resize = () => { fit.fit(); window.bridge.resizePTY(term.cols, term.rows); };
window.addEventListener('resize', resize);

copyBtn.addEventListener('click', () => { const sel = term.getSelection(); if (sel) window.bridge.copy(sel); });
clearBtn.addEventListener('click', () => term.clear());

term.write('\x1b[38;5;111mWelcome to Warp_Open (clean-room).\x1b[0m\r\n');
term.write('• OSC 8 links supported.\r\n');
term.write('• Try: echo -e "\\e]8;;https://example.com\\e\\\\link\\e]8;;\\e\\\\"\r\n');
JS
)"

# src/styles.css
write_if_missing "$APP/src/styles.css" CSS "$(cat <<'CSS'
html, body { height: 100%; margin: 0; background: #0b0f14; color: #e6edf3; }
#titlebar { height: 36px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 12px; background: #0f141b; border-bottom: 1px solid #121a22;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
#titlebar .actions button { background: #182230; color: #dbe6f0; border: 1px solid #2a3a4a;
  padding: 6px 10px; border-radius: 8px; cursor: pointer; margin-left: 6px; }
#titlebar .actions button:hover { background: #1d2a3a; }
#terminal { position: absolute; top: 36px; left: 0; right: 0; bottom: 0; }
CSS
)"

# .npmrc to avoid peer resolution issues
write_if_missing "$APP/.npmrc" NPMRC "$(cat <<'NPMRC'
legacy-peer-deps=true
NPMRC
)"

# Install dependencies (clean)
cd "$APP"
rm -rf node_modules package-lock.json
npm install

# Sanity checks
node -e "JSON.parse(require('fs').readFileSync('package.json','utf8')); console.log('package.json ✓')"
node -e "require('vm').runInNewContext(require('fs').readFileSync('src/main.js','utf8'),{}, {filename:'main.js'}); console.log('main.js ✓')"
node -e "require('vm').runInNewContext(require('fs').readFileSync('src/preload.js','utf8'),{}, {filename:'preload.js'}); console.log('preload.js ✓')"
node -e "require('vm').runInNewContext(require('fs').readFileSync('src/renderer.js','utf8'),{}, {filename:'renderer.js'}); console.log('renderer.js ✓')"

echo
echo "✅ Electron app ready at: $APP"
echo "➡️  To launch:  cd \"$APP\" && npm run dev"