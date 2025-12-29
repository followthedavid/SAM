# UI Architecture Decision - Task 7 ✅

**Decision Date**: 2025-01-16  
**Status**: Tauri selected  
**Confidence**: High

---

## Executive Summary

After evaluating Electron and Tauri for the Warp_Open terminal UI, **Tauri** is the recommended choice due to:
- Native Rust integration with warp_core
- Smaller bundle size (~3MB vs ~150MB for Electron)
- Better performance and memory efficiency
- Modern webview integration
- Active development and community

---

## Framework Comparison

### Tauri ⭐ **SELECTED**

**Pros**:
- Native Rust backend (integrates directly with warp_core)
- Small binary size (~600KB framework + ~2-3MB app)
- Low memory footprint
- Native OS webview (WebKit on macOS, WebView2 on Windows, WebKitGTK on Linux)
- Security-first architecture
- IPC via invoke system (type-safe)
- Active development, modern tooling

**Cons**:
- Newer ecosystem (less mature than Electron)
- Platform-specific webview differences
- Requires Rust toolchain for builds

**Verdict**: ✅ Best fit for Rust-native terminal

---

### Electron

**Pros**:
- Mature ecosystem
- Extensive documentation
- Known by many developers
- Consistent Chromium across platforms
- Large plugin ecosystem

**Cons**:
- Large bundle size (~150-200MB)
- High memory usage (full Chromium per window)
- Node.js backend (would require FFI to Rust)
- Heavier resource consumption
- Security concerns (node integration)

**Verdict**: ❌ Too heavy for a terminal application

---

## Architecture Overview

### Component Hierarchy

```
Warp_Open Application
├── Tauri Backend (Rust)
│   ├── warp_core::pty (PTY management)
│   ├── warp_core::osc_parser (ANSI/OSC parsing)
│   ├── IPC handlers (commands from frontend)
│   └── State management (tabs, sessions)
│
└── Frontend (Web)
    ├── Terminal Renderer (xterm.js)
    ├── Tab Manager UI
    ├── Settings Panel
    └── Command Palette
```

### Data Flow

```
┌────────────────────────────────────┐
│       Frontend (Web/React)         │
│                                    │
│  ┌──────────────────────────────┐ │
│  │   xterm.js Terminal          │ │
│  │   (renders ANSI sequences)   │ │
│  └──────────────────────────────┘ │
│              ↕                     │
│    [Tauri IPC invoke/emit]        │
└────────────────────────────────────┘
              ↕
┌────────────────────────────────────┐
│      Tauri Backend (Rust)          │
│                                    │
│  ┌──────────────────────────────┐ │
│  │   PTY Manager                │ │
│  │   (WarpPty instances)        │ │
│  └──────────────────────────────┘ │
│              ↕                     │
│  ┌──────────────────────────────┐ │
│  │   OSC133Parser               │ │
│  │   (parse ANSI/OSC)           │ │
│  └──────────────────────────────┘ │
└────────────────────────────────────┘
              ↕
┌────────────────────────────────────┐
│       Shell Process                │
│       (/bin/zsh, /bin/bash, etc)  │
└────────────────────────────────────┘
```

---

## Technology Stack

### Backend (Rust)
- **Framework**: Tauri 2.x
- **PTY**: portable-pty (already integrated)
- **Parser**: warp_core::osc_parser (already implemented)
- **State**: tokio for async if needed
- **Serialization**: serde_json for IPC

### Frontend (Web)
- **Framework**: React 18+ (recommended) or Vanilla JS
- **Terminal Renderer**: xterm.js 5.x
- **Build Tool**: Vite
- **Styling**: Tailwind CSS or styled-components
- **State Management**: React Context or Zustand

---

## Key Features per Component

### 1. Terminal Renderer (xterm.js)
- ANSI color sequences
- OSC 133 markers visualization
- Scrollback buffer (configurable limit)
- Copy/paste support
- Link detection and click handling
- Font rendering (ligatures, emoji)

### 2. Tab Manager
- Multiple tab support
- Tab switching (Cmd/Ctrl+1-9)
- New tab (Cmd/Ctrl+T)
- Close tab (Cmd/Ctrl+W)
- Tab rename
- Tab icons/indicators

### 3. IPC Layer (Tauri Commands)
```rust
#[tauri::command]
fn spawn_pty(shell: String) -> Result<String, String>

#[tauri::command]
fn write_pty_input(pty_id: String, input: Vec<u8>) -> Result<(), String>

#[tauri::command]
fn close_pty(pty_id: String) -> Result<(), String>

// Events from backend to frontend
emit("pty_output", { pty_id, data: Vec<u8> })
emit("pty_closed", { pty_id, exit_code: i32 })
```

### 4. State Management
- Active PTY sessions (HashMap<String, WarpPty>)
- Tab state (Vec<TabInfo>)
- User settings (preferences, keybindings)
- Session persistence (save/restore state)

---

## Directory Structure

```
warp_open/
├── warp_core/               # Existing Rust core
│   ├── src/
│   │   ├── pty.rs          # PTY implementation ✅
│   │   ├── osc_parser.rs   # Parser ✅
│   │   └── ...
│   └── Cargo.toml
│
├── src-tauri/               # Tauri backend (NEW)
│   ├── src/
│   │   ├── main.rs         # Entry point
│   │   ├── pty_manager.rs  # PTY lifecycle management
│   │   ├── commands.rs     # Tauri IPC commands
│   │   └── state.rs        # App state
│   ├── Cargo.toml
│   ├── tauri.conf.json     # Tauri configuration
│   └── build.rs
│
├── src/                     # Frontend (NEW)
│   ├── main.tsx            # React entry
│   ├── App.tsx             # Main app component
│   ├── components/
│   │   ├── Terminal.tsx    # xterm.js wrapper
│   │   ├── TabBar.tsx      # Tab UI
│   │   └── Settings.tsx    # Settings panel
│   ├── hooks/
│   │   └── usePty.ts       # PTY IPC hook
│   └── styles/
│       └── main.css
│
├── public/                  # Static assets
├── package.json            # Frontend dependencies
├── vite.config.ts          # Vite configuration
└── tsconfig.json           # TypeScript config
```

---

## Implementation Plan

### Phase 2.1: Tauri Setup (Task 7)
1. Initialize Tauri project
2. Set up basic window
3. Configure Tauri IPC
4. Add warp_core as dependency

### Phase 2.2: Terminal Component (Task 8)
1. Install xterm.js
2. Create Terminal.tsx component
3. Wire up basic rendering
4. Test with mock data

### Phase 2.3: PTY Integration (Task 9)
1. Implement PTY manager in Tauri backend
2. Create IPC commands (spawn, write, close)
3. Set up event emitter for output
4. Connect frontend to backend

### Phase 2.4: Input Handling (Task 10)
1. Capture keyboard events in xterm.js
2. Forward to Tauri backend
3. Handle special keys (Ctrl+C, etc.)
4. Test interactive commands

### Phase 2.5: Testing (Task 11)
1. Set up Playwright for Tauri
2. Write rendering tests
3. Write input/output tests
4. Automated CI tests

---

## Security Considerations

### Tauri Security Model
- Frontend cannot directly access filesystem
- All PTY operations via IPC (controlled by backend)
- No Node.js integration (no `require()` attacks)
- CSP (Content Security Policy) enforced
- Sandboxed webview

### Command Injection Prevention
- Validate all PTY inputs
- Escape shell metacharacters if needed
- Limit shell selection to known paths
- Don't eval user input

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Startup time | < 500ms | Cold start on macOS |
| Memory (idle) | < 100MB | Single tab, no scrollback |
| Memory (10k lines) | < 200MB | With full scrollback |
| Input latency | < 16ms | Keystroke to PTY |
| Render latency | < 50ms | PTY output to screen |
| Bundle size | < 10MB | Compressed app download |

---

## Alternative Considered: Web-only (No Desktop App)

**Pros**:
- No installation required
- Cross-platform by default
- Easy updates

**Cons**:
- Cannot spawn local PTY (browser security)
- Requires server component
- Network latency
- More complex architecture

**Verdict**: ❌ Not suitable for local terminal replacement

---

## Decision Rationale

### Why Tauri over Electron?

1. **Native Rust Integration**
   - warp_core is already in Rust
   - No FFI overhead
   - Type safety across stack

2. **Resource Efficiency**
   - 10-50x smaller binaries
   - 3-5x lower memory usage
   - Faster startup

3. **Modern Approach**
   - Built for 2025+
   - Security-first
   - Growing ecosystem

4. **Terminal-Specific Benefits**
   - Low overhead matters for terminals
   - Fast PTY I/O crucial
   - Users run many terminal instances

### Risk Mitigation

**Risk**: Tauri ecosystem less mature
**Mitigation**: Core terminal functionality doesn't require extensive plugins

**Risk**: Platform webview differences
**Mitigation**: Test on all platforms, use progressive enhancement

**Risk**: Rust learning curve for web devs
**Mitigation**: Frontend is standard React/TS, backend is isolated

---

## Next Steps (Task 8)

1. Initialize Tauri project: `npm create tauri-app`
2. Install xterm.js: `npm install xterm @xterm/addon-fit`
3. Create basic Terminal component
4. Test rendering with mock PTY data
5. Verify build and run on macOS

---

**Status**: ✅ Decision complete  
**Next Task**: Task 8 - Terminal Window Component  
**Estimated Time**: 2 hours
