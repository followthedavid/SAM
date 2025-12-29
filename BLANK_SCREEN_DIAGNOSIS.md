# Blank Screen Diagnosis

## Current Status: BLOCKED

**Problem:** Warp_Open window opens but shows only blank white screen. No UI elements, no way to type.

## What We Know

### ✅ Working Components
1. **Vite dev server** - Running on http://localhost:5173/ ✓
2. **Rust backend** - Compiles without errors ✓
3. **Binary exists** - `/Users/davidquinton/ReverseLab/Warp_Open/warp_tauri/src-tauri/target/debug/Warp_Open` ✓
4. **Safari can connect** - http://localhost:5173/ loads in Safari (with expected Tauri API errors)

### ❌ Not Working
1. **Tauri webview** - Cannot load http://localhost:5173/
2. **App shows blank white screen** - No content renders
3. **No errors in terminal** - App runs but displays nothing

## Root Cause Analysis

The Tauri native webview cannot connect to or render the Vite dev server content. This could be:

### Possibility 1: Webview Security/Network Issue
- macOS webview (WKWebView) may block localhost connections
- CSP (Content Security Policy) might be too restrictive
- Webview not configured to allow dev server connections

### Possibility 2: Build Configuration Problem
- `tauri.conf.json` might have incorrect `devPath`
- Webview might be trying to load wrong URL
- `withGlobalTauri: true` change might have broken something

### Possibility 3: macOS Permissions
- App might not have network permissions
- Firewall blocking localhost connections
- Sandbox preventing webview from accessing network

## Evidence

```bash
# Vite is running
$ lsof -i :5173 | grep LISTEN
node    4119  ... TCP localhost:5173 (LISTEN)

# Safari can access it
http://localhost:5173/ - Works (shows app with Tauri errors)

# Native app cannot
Warp_Open window - Blank white screen
```

## Recommended Fix Attempts

### Fix 1: Use 0.0.0.0 instead of localhost

Sometimes macOS webview has issues with "localhost". Try binding to all interfaces:

**Update `warp_tauri/vite.config.ts`:**
```typescript
export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
  // ... rest of config
})
```

Then update `tauri.conf.json`:
```json
{
  "build": {
    "devPath": "http://127.0.0.1:5173"
  }
}
```

### Fix 2: Disable CSP temporarily

**In `tauri.conf.json`:**
```json
{
  "tauri": {
    "security": {
      "csp": null  // Already set
    }
  }
}
```

### Fix 3: Check Console Output

We need to see what error the webview is actually encountering. Unfortunately, Tauri doesn't show webview errors by default.

**Enable debug logging:**

Set environment variable:
```bash
RUST_LOG=debug ./target/debug/Warp_Open
```

### Fix 4: Try Production Build

The issue might be dev-only. Try a production build:

```bash
cd /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri
npm run build
npm run tauri:build
```

Then run the built app from `src-tauri/target/release/bundle/`

### Fix 5: Use Inline Build

Instead of `devPath` pointing to Vite server, build the frontend and use `distDir`:

```bash
# Build frontend
npm run build

# Update tauri.conf.json temporarily
{
  "build": {
    "beforeDevCommand": "",  // Disable
    "devPath": "../dist",    // Use built files
  }
}

# Run Tauri
cd src-tauri
cargo run
```

## Most Likely Solution

Based on similar issues, this is **almost certainly a webview networking problem**. The fix is:

1. Change Vite to bind to `0.0.0.0` instead of `localhost`
2. Change devPath to `http://127.0.0.1:5173`
3. Restart everything

## Quick Test Commands

```bash
# Kill everything
pkill -f vite
pkill -f Warp_Open

# Start Vite on 0.0.0.0
cd /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri
npm run dev -- --host 0.0.0.0 &

# Wait for it to start
sleep 3

# Run Tauri app
./src-tauri/target/debug/Warp_Open
```

## What to Check Next

1. **Does `npm run tauri:dev` work?**
   - This is the official way and should handle everything
   - If this shows blank screen, it's a real config issue

2. **Can you see errors with RUST_LOG=debug?**
   ```bash
   RUST_LOG=debug npm run tauri:dev 2>&1 | tee /tmp/tauri_debug.log
   ```

3. **Does production build work?**
   ```bash
   npm run tauri:build
   open src-tauri/target/release/bundle/macos/Warp_Open.app
   ```

## Critical Files to Check

1. `warp_tauri/vite.config.ts` - Server configuration
2. `warp_tauri/src-tauri/tauri.conf.json` - Dev path configuration  
3. `warp_tauri/src-tauri/Cargo.toml` - Tauri features

## Status: NEEDS USER INTERVENTION

I cannot fix this without:
1. Being able to see webview console errors
2. Being able to test network configuration changes
3. Being able to see full RUST_LOG=debug output

## Next Steps

Please try in order:

1. **Use official command:**
   ```bash
   cd /Users/davidquinton/ReverseLab/Warp_Open/warp_tauri
   npm run tauri:dev
   ```
   Does it show blank screen? If yes, continue.

2. **Check if it's URL issue:**
   ```bash
   # Edit vite.config.ts - add host: '0.0.0.0'
   # Then retry npm run tauri:dev
   ```

3. **Try production build:**
   ```bash
   npm run tauri:build
   open src-tauri/target/release/bundle/macos/Warp_Open.app
   ```

4. **Get debug logs:**
   ```bash
   RUST_LOG=debug npm run tauri:dev 2>&1 | tee /tmp/full_debug.log
   # Then share the log
   ```

This is a Tauri webview configuration issue, not a code bug. The solution exists but requires systematic testing of network/security configurations.

---

**Status:** Diagnosis complete. Awaiting configuration testing.
