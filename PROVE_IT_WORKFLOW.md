# 🚀 Warp_Open: 2-Minute Prove-It Workflow

## ⚡ Quick Prove-It Loop

### 1️⃣ Launch (30s)
```bash
cd ~/ReverseLab/Warp_Open/app/gui-electron
./scripts/dev_enter_blocks.sh
```
**In the window:** Run `echo hello`, `pwd`, `ls`, click 💾 Flush, then close.

### 2️⃣ Verify Recording (30s)  
```bash
~/ReverseLab/Warp_Open/quick_proof.sh
```
**Expected:** `block:start` / `block:exec:end` / `block:end` and `pty:input` lines with ``

### 3️⃣ If Window Closes Early (30s)
```bash
~/ReverseLab/Warp_Open/quick_fixes.sh
```
**Pick:** Rebuild ABI → Relaunch

## 📊 Health Snapshot (30s)
```bash
~/ReverseLab/Warp_Open/status.sh
```
**Expect:** Green checks for smoke, blocks toggle (Cmd+B), flush, inputs captured

## 🔒 Lock It In
```bash
cd ~/ReverseLab/Warp_Open/app/gui-electron
npm run ci              # rebuild → smoke → validate → summary
npm run pack:mac        # makes dist/Warp_Open-darwin-arm64/
```

## 🎯 UI Features to Test

| Feature | Shortcut | Action |
|---------|----------|--------|
| **Blocks Panel** | `Cmd+B` or 📋 | Toggle blocks UI |
| **Block Summary** | `Cmd+Opt+B` | Print stats in DevTools |
| **Flush Session** | Click 💾 | Force session save |
| **New Tab** | `Cmd+T` | Open new terminal tab |
| **Close Tab** | `Cmd+W` | Close current tab |
| **Replay** | Click 🕘 | Auto-load newest session |
| **Theme Toggle** | Click 🌗 or `Cmd+Shift+T` | Switch light/dark |

## ✅ What Success Looks Like

**Session Events:** `block:start`, `block:exec:end`, `block:end`, `pty:input` with \r

**UI Working:** 💾 shows toast, `Cmd+Opt+B` prints block stats, 📋 panel works

## 🛠️ Quick Fixes

**Window crashes:** `npm run rebuild`  
**No blocks:** Check `WARP_OPEN_BLOCKS_MODE=enter`  
**DevTools errors:** View → Toggle DevTools, check Console  

## 🏁 Daily-Driver Status: ~75-80%
Ready for daily use with crash guard + session restore + signed build as next steps.
