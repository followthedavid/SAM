# Warp_Open Diagnostic & Recovery Tools

This directory contains several scripts to help diagnose and fix issues with the Warp_Open Electron app, especially when the window closes unexpectedly or blocks aren't recording properly.

## 🚀 Quick Launch Scripts

### `./quick_launch.sh`
Launch with verbose logging and enter-heuristic blocks enabled:
```bash
./quick_launch.sh
```
- Sets `ELECTRON_ENABLE_LOGGING=1` and `ELECTRON_ENABLE_STACK_DUMPING=1`  
- Forces `WARP_OPEN_BLOCKS_MODE=enter` for easy block generation
- Launches the GUI with all debug features enabled

### Manual Quick Launch (copy-paste)
```bash
export APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
cd "$APP"
export ELECTRON_ENABLE_LOGGING=1
export ELECTRON_ENABLE_STACK_DUMPING=1
export WARP_OPEN_ENABLE_BLOCKS=1
export WARP_OPEN_BLOCKS_MODE=enter
./scripts/dev_enter_blocks.sh
```

## 🔍 Proof Collection

### `./quick_proof.sh`
Verify that blocks and inputs are being recorded:
```bash
./quick_proof.sh
```
Shows:
- Latest session file path
- Block events (`block:start`, `block:exec`, `block:end`)
- Recent input events with `\r` indicators

### Manual Proof Collection (copy-paste)
```bash
LOG="$(ls -t "$HOME/.warp_open/sessions"/session-*.jsonl | head -1)"
echo "Latest session: $LOG"
grep -nE 'block:(start|exec|end)|cwd:update' "$LOG" || echo "No block events found"
grep -n 'pty:input' "$LOG" | tail -20 | sed -n l
```

## 🔧 Quick Fixes

### `./quick_fixes.sh`
Interactive menu for common fixes:
```bash
./quick_fixes.sh
```
Options:
1. **Rebuild ABI** - Fixes runtime version mismatches
2. **Kill stuck processes** - Cleans up hung Electron processes  
3. **Show diagnostics** - App config and recent logs
4. **Run smoke test** - Quick health check
5. **Exit**

### Manual Common Fixes (copy-paste)

**ABI Rebuild:**
```bash
cd "$HOME/ReverseLab/Warp_Open/app/gui-electron"
npm run rebuild
./scripts/dev_enter_blocks.sh
```

**Kill stuck processes:**
```bash
pkill -f "Electron.app/Contents/MacOS/Electron" || true
```

**Show diagnostics:**
```bash
cd "$HOME/ReverseLab/Warp_Open/app/gui-electron"
node -e 'const pkg=require("./package.json"); console.log({electron:pkg.devDependencies?.electron, xterm:pkg.dependencies?.xterm, node_pty:pkg.dependencies?.["node-pty"]})'
log show --predicate 'process == "Electron"' --last 5m --info --debug --style syslog | tail -20
```

## 📋 Complete Diagnostic Workflow

### `./diagnostic_workflow.sh`
Step-by-step interactive diagnostic process:
```bash
./diagnostic_workflow.sh
```
Walks through:
1. **Launch Setup** - Configure verbose environment
2. **Proof Collection** - Verify block/input recording
3. **Diagnostics** - Capture system information
4. **Common Fixes** - Apply standard solutions
5. **UI Verification** - Test interface features

## ✅ What "Good" Looks Like

**Session Log Events:**
- `block:start`, `block:exec`, `block:end` lines for commands
- `pty:input` lines include `\r` when Enter was pressed
- `cwd:update` events when changing directories

**UI Features Working:**
- **Cmd+B**: Toggle Blocks panel (or click 📋)
- **Cmd+Opt+B**: Print block summary in DevTools console
- **💾 Flush**: Click button, see toast + `[session.flush] { ok: true }`

**DevTools Console:**
```
[blocks] total=3 running=0 done=3 failed=0 last="ls"
```

## 🧪 Health Checks

**Quick smoke test:**
```bash
cd ~/ReverseLab/Warp_Open/app/gui-electron
npm run smoke:once  # Should show "[main] Smoke test initiated"
```

**Session summary:**
```bash
cd ~/ReverseLab/Warp_Open/app/gui-electron  
scripts/smoke_summary.sh
```

## 🔧 Troubleshooting

**Window closes immediately:**
1. Check for JavaScript errors in DevTools Console
2. Rebuild ABI: `npm run rebuild`
3. Check for stuck processes: `pkill -f Electron`

**No blocks recorded:**
1. Verify `WARP_OPEN_BLOCKS_MODE=enter` is set
2. Check session log for `pty:input` with `\r`
3. Look for renderer exceptions in DevTools

**DevTools debugging:**
- Open DevTools: View → Toggle DevTools  
- Reload window: Cmd+R
- Check Console tab for errors
- Network tab for failed requests

## 📁 Files Created

- `diagnostic_workflow.sh` - Complete interactive workflow
- `quick_launch.sh` - Fast launch with debugging  
- `quick_proof.sh` - Session verification
- `quick_fixes.sh` - Common fixes menu
- `warp_open_demo_helpers.sh` - Original demo helper installer
- `app/gui-electron/scripts/dev_enter_blocks.sh` - Launch with blocks enabled

All scripts are executable and can be run from the Warp_Open root directory.
