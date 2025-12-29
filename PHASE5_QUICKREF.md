# Phase 5 Terminal — Quick Reference Card

## 📁 Files Created

```
app/gui-electron/src/
├─ terminal/
│  ├─ ptyManager.js       ✅ Multi-PTY management (243 lines)
│  ├─ blockManager.js     ✅ Block orchestration (243 lines)
│  ├─ ui.js               ✅ DOM rendering (203 lines)
│  ├─ terminal.scss       ✅ Styles source
│  ├─ terminal.css        ✅ Compiled styles
│  └─ terminal_ipc.js     ✅ Main process IPC (129 lines)
├─ terminal.html           ✅ Phase 5 UI (158 lines)
└─ terminal_renderer.js    ✅ Renderer logic (270 lines)

Total: ~1,246 lines
```

## 🚀 Integration Steps

### 1. Update main.js

```javascript
const { TerminalIPC } = require('./src/terminal/terminal_ipc');

app.whenReady().then(() => {
  const terminalIPC = new TerminalIPC();
  terminalIPC.setup();
  
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'src', 'preload.js'),
      contextIsolation: true,
    },
  });
  
  win.loadFile('src/terminal.html');
});
```

### 2. Update preload.js

```javascript
contextBridge.exposeInMainWorld('terminalBridge', {
  createTab: (name, shell, cwd) => 
    ipcRenderer.invoke('terminal:createTab', name, shell, cwd),
  runCommand: (cmd) => 
    ipcRenderer.invoke('terminal:runCommand', cmd),
  switchTab: (id) => 
    ipcRenderer.invoke('terminal:switchTab', id),
  getTabs: () => 
    ipcRenderer.invoke('terminal:getTabs'),
  closeTab: (id) => 
    ipcRenderer.invoke('terminal:closeTab', id),
  onBlock: (callback) => 
    ipcRenderer.on('terminal:block', (_, block) => callback(block)),
});
```

### 3. Run

```bash
cd app/gui-electron
npm run dev
```

## 🎮 Usage

### Shell Commands
```bash
ls -la                 # Regular command
cd src                 # Change directory
pwd                    # Show current directory
```

### AI Commands
```bash
/ask <question>        # Ask AI anything
/explain               # Explain last command
/fix <error>           # Fix command error
```

### Tab Management
- **New tab:** Click `+` button
- **Switch tab:** Click tab name
- **Close tab:** Click `×`
- **Rename tab:** Double-click name

### Block Actions (hover over blocks)
- 📋 **Copy** — Copy to clipboard
- 💡 **Explain** — Ask AI to explain
- 🔧 **Fix** — Ask AI to fix (errors only)

## 🔌 API Reference

### window.ai2 (from preload.js)

```javascript
// AI
await window.ai2.askAI(prompt)

// Journal
await window.ai2.logAction(type, summary, payload)
await window.ai2.getEntries(offset, limit)
await window.ai2.undoLast()

// Files
await window.ai2.writeFile(path, content)
await window.ai2.readFile(path)
await window.ai2.patchFile(path, diff)

// Context
await window.ai2.cd(path)
await window.ai2.getContextPack()
```

### window.terminalBridge

```javascript
// Tabs
const tabId = await window.terminalBridge.createTab('Main')
await window.terminalBridge.switchTab(tabId)
const tabs = await window.terminalBridge.getTabs()
await window.terminalBridge.closeTab(tabId)

// Commands
const block = await window.terminalBridge.runCommand('ls -la')

// Events
window.terminalBridge.onBlock((block) => {
  console.log('New block:', block)
})
```

## 🎨 Block Structure

```javascript
{
  id: 'action-uuid',
  type: 'input' | 'output' | 'error' | 'ai',
  content: 'command or output text',
  timestamp: '2024-11-09T06:30:00.000Z',
  terminalId: 'terminal-uuid',
  status: 'running' | 'complete',
  context: { /* optional metadata */ }
}
```

## 🧪 Testing

### Placeholder Mode (no node-pty)
Open `terminal.html` directly in browser or Electron:
- Simulates command execution
- AI commands work
- No real PTY required

### With PTY
Requires node-pty:
```bash
npm run rebuild
npm run dev
```

## 🐛 Troubleshooting

### "node-pty not found"
```bash
cd app/gui-electron
npm install node-pty
npm run rebuild
```

### "window.ai2 not available"
- Check preload.js exposes window.ai2
- Check ai2-main.js is initialized
- Verify contextIsolation is true

### "Blocks not appearing"
- Check terminal_ipc is set up in main.js
- Verify terminalBridge is exposed in preload
- Check console for IPC errors

### "AI commands not working"
- Ensure window.ai2 is available
- Check AI backend is running (Ollama/OpenAI)
- Verify askAI() function works

## 📊 Performance Tips

1. **Limit block history** — Keep only last 1000 blocks
2. **Buffer output** — Don't create block per character
3. **Lazy render** — Use intersection observer for scrolling
4. **Debounce PTY output** — Reduce IPC overhead

## 🔒 Security Notes

- PTY runs in main process (secure)
- Renderer can't access filesystem directly
- All operations go through IPC
- CSP enabled in terminal.html

## 📚 Next Steps

1. ✅ **Phase 5.1:** Full PTY integration
2. 📋 **Phase 5.2:** Enhanced block features
3. 🤖 **Phase 5.3:** Context-aware AI
4. 🎨 **Phase 5.4:** Advanced terminal features
5. ⚡ **Phase 5.5:** Rust backend migration

## 🎯 Key Files to Know

| File | Purpose | Lines |
|------|---------|-------|
| `ptyManager.js` | PTY lifecycle | 243 |
| `blockManager.js` | High-level logic | 243 |
| `ui.js` | DOM helpers | 203 |
| `terminal_ipc.js` | IPC bridge | 129 |
| `terminal_renderer.js` | Renderer UI | 270 |
| `terminal.html` | UI layout | 158 |

**Total:** ~1,246 lines of production code

## ✅ Status

- [x] Core infrastructure complete
- [x] Block-based UI working
- [x] AI commands implemented
- [x] Journal integration ready
- [x] Multi-tab PTY functional
- [x] Placeholder mode tested
- [x] Documentation complete

**Ready for production integration!** 🚀

---

**Full docs:** `PHASE5_TERMINAL_SCAFFOLD.md`  
**Rust backend:** `warp_core/PHASE5_SUMMARY.md`  
**API reference:** `warp_core/API_REFERENCE.md`
