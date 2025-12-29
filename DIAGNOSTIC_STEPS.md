# Warp_Open Diagnostic Steps

## Current Issue: Blank screen, can't type

### Step 1: Open Browser DevTools

Since Tauri uses a webview, we can inspect it like a browser:

**On macOS:**
1. With the Warp_Open window focused
2. Right-click anywhere in the window
3. Select **"Inspect Element"** (if available)

**Alternative - Use Safari Web Inspector:**
1. Open Safari
2. Safari menu → Preferences → Advanced
3. Check "Show Develop menu in menu bar"
4. Run your Tauri app
5. Develop menu → Your computer name → Warp_Open Terminal

### Step 2: Check Console for Errors

Once DevTools are open:
1. Click the **Console** tab
2. Look for red error messages
3. Look for our debug logs:
   - "Creating new tab..."
   - "Invoking spawn_pty..."
   - "PTY spawned successfully:"
   - "TerminalWindow mounted for PTY:"

**Take a screenshot or copy all console output**

### Step 3: Check Network Tab

1. Click the **Network** tab
2. Refresh the page (Cmd+R)
3. Look for failed requests (red)
4. Check if `xterm.css` loaded
5. Check if all JavaScript files loaded

### Step 4: Check Elements Tab

1. Click the **Elements** (or **DOM**) tab  
2. Expand the `<body>` tag
3. Look for `<div id="app">`
4. Expand it and look for:
   - `.top-bar`
   - `.terminal-container`
   - `.terminal-window`
   - Canvas elements from xterm

**Is anything missing?**

### Step 5: Manual Test in Browser

Open http://localhost:5173/ in your regular browser (Chrome/Safari/Firefox)

Does it work there? This helps isolate if it's a Tauri issue or code issue.

### Step 6: Check Rust Backend Logs

In the terminal where you ran `npm run tauri:dev`:

Look for:
- Rust compilation errors
- Runtime errors
- PTY spawn failures
- Permission errors

### Step 7: Test PTY Commands Manually

Add this to your browser console:

```javascript
// Test if Tauri is available
console.log('Tauri:', window.__TAURI__)

// Test spawn_pty
window.__TAURI__.invoke('spawn_pty', { shell: null })
  .then(result => console.log('spawn_pty result:', result))
  .catch(err => console.error('spawn_pty error:', err))
```

### Step 8: Common Issues

#### Issue: "invoke is not defined"
**Cause:** Tauri API not available
**Fix:** Check `tauri.conf.json` has `"withGlobalTauri": true`

#### Issue: "command spawn_pty not found"
**Cause:** Command not registered in Rust
**Fix:** Check `src-tauri/src/main.rs` has `spawn_pty` in `invoke_handler`

#### Issue: PTY spawn fails silently
**Cause:** Permission error or shell not found
**Fix:** Check Rust logs for "Failed to spawn PTY"

#### Issue: xterm.css not loaded
**Cause:** Build issue
**Fix:** Run `npm install xterm` and restart

### Step 9: Simplified Test

Let's create a minimal test. Replace App.vue temporarily with:

```vue
<template>
  <div style="padding: 20px; color: white;">
    <h1>Diagnostic Test</h1>
    <button @click="testPty">Test PTY Spawn</button>
    <pre>{{ status }}</pre>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

const status = ref('Click button to test')

async function testPty() {
  status.value = 'Testing...'
  try {
    const result = await invoke('spawn_pty', { shell: null })
    status.value = 'SUCCESS: ' + JSON.stringify(result, null, 2)
  } catch (error) {
    status.value = 'ERROR: ' + error
  }
}
</script>
```

If this works, the problem is in the UI. If not, it's the backend.

### Step 10: Report Findings

Please provide:
1. Console errors (screenshots or text)
2. Network tab screenshot
3. Elements tab - what do you see under `#app`?
4. Does http://localhost:5173/ work in browser?
5. What does the simplified test show?
6. Any Rust errors in terminal?

---

## Quick Fixes to Try

### Fix 1: Restart Everything
```bash
# Kill any running processes
pkill -f tauri
pkill -f vite

# Clear and reinstall
cd warp_tauri
rm -rf node_modules dist
npm install
npm run tauri:dev
```

### Fix 2: Check xterm is installed
```bash
cd warp_tauri
npm list xterm
# Should show: xterm@5.x.x

# If not:
npm install xterm xterm-addon-fit xterm-addon-web-links
```

### Fix 3: Verify Rust compilation
```bash
cd warp_tauri/src-tauri
cargo build
# Should complete without errors
```

### Fix 4: Test PTY directly
```bash
cd warp_core
cargo test test_pty_spawn -- --nocapture
# Should show PTY working
```

---

## Expected Console Output (Good)

```
Creating new tab...
Invoking spawn_pty...
PTY spawned successfully: {id: 1}
Tab created: {id: 1, ptyId: 1, name: "Terminal 1"}
TerminalWindow mounted for PTY: 1 Tab: 1
Opening xterm terminal...
Terminal opened and focused
Starting output polling for PTY: 1
Received output: bash-3.2$ ...
```

## Bad Console Output (Errors)

```
Failed to create new tab: Error: command spawn_pty not found
```
OR
```
Failed to read PTY output: PTY 1 not found
```
OR
```
Uncaught TypeError: Cannot read property 'invoke' of undefined
```

---

Let me know what you find!
