# Warp_Open Terminal Replacement - Master Roadmap

## Executive Summary

**Current Status:** Phase 0 Complete (Test Infrastructure)  
**Next Milestone:** Phase 1 - Interactive CLI/PTY MVP  
**Target:** Full terminal replacement in ~62 hours (~8 workdays)

---

## Phase Status Overview

| Phase | Status | Duration | Progress |
|-------|--------|----------|----------|
| **Phase 0: Foundation** | ✅ Complete | - | 100% |
| **Phase 1: PTY Integration** | 🔄 In Progress | 12h | 10% |
| **Phase 2: UI Integration** | ⏳ Pending | 14h | 0% |
| **Phase 3: Multi-Session** | ⏳ Pending | 19h | 0% |
| **Phase 4: Testing** | ⏳ Pending | 9h | 0% |
| **Phase 5: Distribution** | ⏳ Pending | 8h | 0% |

**Total Estimated Time:** 62 hours

---

## Phase 0: Foundation ✅ COMPLETE

### Accomplishments
- ✅ Core parsing engine (OSC133Parser)
- ✅ CLI tool (warp_cli) with JSON output
- ✅ 27 tests passing (20 Rust + 7 Python)
- ✅ Integration tests for edge cases
- ✅ UI scaffold (Electron + Playwright)
- ✅ Full CI/CD pipeline (GitHub Actions)
- ✅ Comprehensive documentation

### Deliverables
- Rust library: `warp_core`
- CLI binary: `warp_cli`
- Test infrastructure: Rust + Python + Playwright
- Tooling: test_runner.sh, Makefile, CI workflow
- Documentation: 3 comprehensive guides

---

## Phase 1: PTY Integration (CLI MVP) 🔄

**Goal:** Enable interactive shell sessions with live ANSI/OSC parsing

### Tasks

#### 1.1 Add PTY Dependency ✅
- **Duration:** 1h
- **Status:** Complete
- **Action:** Add `portable-pty = "0.9"` to Cargo.toml

#### 1.2 Create pty.rs Module 🔄
- **Duration:** 2h
- **Status:** In Progress
- **File:** `warp_core/src/pty.rs`
- **Features:**
  - Spawn shell processes
  - Stream stdout/stderr to parser
  - Handle window resizing
  - Cross-platform compatibility

#### 1.3 Real-time Parser Integration ⏳
- **Duration:** 3h
- **Status:** Pending
- **Action:** Connect PTY output → OSC133Parser
- **Test:** Validate live ANSI/OSC/UTF-8 handling

#### 1.4 Input Forwarding ⏳
- **Duration:** 2h
- **Status:** Pending
- **Action:** Capture keyboard input → forward to PTY
- **Features:** Handle Ctrl+C, Ctrl+D, special keys

#### 1.5 CLI Subcommand ⏳
- **Duration:** 1h
- **Status:** Pending
- **File:** `warp_core/src/bin/warp_cli.rs`
- **Command:** `warp_cli run-pty --shell /bin/bash`

#### 1.6 Live Integration Tests ⏳
- **Duration:** 3h
- **Status:** Pending
- **Files:** `tests/integration/run_pty_*.py`
- **Tests:** Echo, long scroll, stress tests

### Deliverables
- ✅ Interactive CLI terminal
- ✅ Real-time ANSI/OSC parsing
- ✅ Live integration tests passing
- ✅ Cross-platform PTY support

### Acceptance Criteria
```bash
# Can run interactive shell
cargo run -- run-pty

# Python tests pass
./tests/integration/run_pty_live_test.py

# All edge cases handled
make test
```

---

## Phase 2: UI Integration

**Goal:** Visual terminal window with live rendering

### Tasks

#### 2.1 UI Architecture Decision (2h)
- **Options:** React + Canvas vs React + DOM
- **Decision:** React + DOM (better accessibility)
- **Document:** Architecture rationale

#### 2.2 Terminal Window Component (4h)
- **File:** `app/gui-electron/src/components/TerminalWindow.tsx`
- **Features:**
  - Scrollable viewport
  - Line/block rendering
  - Efficient scroll buffer
  - ANSI color support

#### 2.3 PTY→UI Wire (3h)
- **Technology:** WebSocket server in Rust
- **File:** `warp_core/src/ws_server.rs`
- **Flow:** PTY → Parser → JSON → WebSocket → UI

#### 2.4 Input Support (2h)
- **Action:** Capture keyboard in UI → send to PTY
- **Handle:** Special keys, clipboard, shortcuts

#### 2.5 UI Tests (3h)
- **Files:** `ui-tests/tests/replay_live_*.spec.ts`
- **Tests:** Live rendering, scroll, input routing

### Deliverables
- ✅ Interactive terminal UI
- ✅ Live PTY rendering
- ✅ Keyboard input working
- ✅ Playwright tests passing

---

## Phase 3: Multi-Session & Advanced Features

**Goal:** Full-featured terminal replacement

### 3.1 Tab Management (3h)
- **UI:** TabBar component
- **Backend:** Session registry `HashMap<SessionId, PTYHandle>`
- **Features:** Create, close, rename, switch tabs

### 3.2 Pane Splits (3h)
- **UI:** SplitPane component
- **Support:** Horizontal/vertical splits
- **Feature:** Independent PTY per pane

### 3.3 Session Persistence (4h)
- **Save:** Buffer, cursor, layout
- **Restore:** On startup
- **File:** `warp_core/src/session_manager.rs`

### 3.4 Performance Optimization (3h)
- **Targets:**
  - 100k+ line scrollback
  - <50ms UI lag
  - Virtual DOM batching
  - Async Rust streaming

### 3.5 Advanced Features (6h)
- **Mouse:** Click, scroll, selection
- **Hyperlinks:** Ctrl+Click URLs
- **Unicode:** Full CJK support
- **OSC:** Titles, colors, notifications

### Deliverables
- ✅ Multi-tab terminal
- ✅ Split panes
- ✅ Persistent sessions
- ✅ High performance
- ✅ Advanced terminal features

---

## Phase 4: Production Testing

**Goal:** Validate stability and performance

### Tasks (9h total)

#### 4.1 End-to-End Tests (4h)
- All Rust + Python + UI tests
- Cross-platform validation
- CI matrix (Ubuntu + macOS)

#### 4.2 Stress Tests (3h)
- 100k+ line scrollback
- Multiple concurrent sessions
- Memory/CPU profiling

#### 4.3 CI Validation (2h)
- Automated test suite
- Artifact collection
- Performance benchmarks

### Deliverables
- ✅ 100% test pass rate
- ✅ Performance validated
- ✅ CI fully automated

---

## Phase 5: Packaging & Distribution

**Goal:** Release production-ready terminal

### Tasks (8h total)

#### 5.1 Build Binaries (2h)
- Release mode compilation
- Strip debug symbols
- Platform-specific optimizations

#### 5.2 Package Electron App (3h)
- macOS: .app + .dmg
- Windows: .exe installer
- Linux: .AppImage + .deb

#### 5.3 Documentation (1h)
- Installation guide
- User manual
- Known limitations
- Troubleshooting

#### 5.4 Auto-Update (2h, optional)
- Update mechanism
- Version checking
- Release channels

### Deliverables
- ✅ Cross-platform binaries
- ✅ Installers for all OS
- ✅ Complete documentation
- ✅ Optional auto-update

---

## Architecture Overview

```
┌─────────────────┐
│  User Keyboard  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Input Handler  │  ← warp_core/src/input.rs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PTY / Shell   │  ← warp_core/src/pty.rs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OSC133Parser    │  ← warp_core/src/osc_parser.rs
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│  JSON Output    │ ───→  │  UI Renderer │
└─────────────────┘       └──────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐       ┌──────────────┐
│ Integration     │       │  Playwright  │
│ Tests (Python)  │       │  Tests (UI)  │
└─────────────────┘       └──────────────┘
```

---

## Testing Strategy

### Test Coverage by Phase

| Phase | Rust Tests | Python Tests | UI Tests | Coverage |
|-------|-----------|--------------|----------|----------|
| Phase 0 | 20 | 7 | 2 | 100% |
| Phase 1 | +5 | +3 | - | 100% |
| Phase 2 | +2 | +2 | +5 | 100% |
| Phase 3 | +3 | +2 | +8 | 100% |
| Phase 4 | +5 | +5 | +5 | 100% |

### Test Types
1. **Unit Tests:** Rust functions, parser logic
2. **Integration Tests:** Python scripts, live PTY sessions
3. **Snapshot Tests:** Golden JSON output with insta
4. **UI Tests:** Playwright for rendering, input, scroll
5. **Stress Tests:** Performance, memory, large sessions
6. **E2E Tests:** Full workflow validation

---

## Dependencies

### Core Libraries
- `portable-pty = "0.9"` - Cross-platform PTY
- `tokio` - Async runtime
- `serde_json` - JSON serialization
- `insta` - Snapshot testing

### UI Stack
- Electron or Tauri
- React + TypeScript
- WebSocket for real-time communication
- Playwright for testing

---

## Timeline & Milestones

### Week 1: Phase 1 + Phase 2
- **Days 1-2:** PTY integration, interactive CLI
- **Days 3-4:** UI integration, live rendering
- **Milestone:** Basic interactive terminal

### Week 2: Phase 3 + Phase 4
- **Days 5-7:** Multi-session, tabs, splits
- **Day 8:** Performance optimization
- **Days 9-10:** Production testing
- **Milestone:** Full-featured terminal

### Week 3: Phase 5
- **Days 11-12:** Packaging & distribution
- **Day 13:** Documentation & release
- **Milestone:** Production release

---

## Success Criteria

### Phase 1
- [ ] Can spawn interactive shell
- [ ] Live ANSI/OSC parsing works
- [ ] Input forwarding functional
- [ ] All integration tests pass

### Phase 2
- [ ] UI renders live PTY output
- [ ] Keyboard input works
- [ ] Scrolling functional
- [ ] Playwright tests pass

### Phase 3
- [ ] Multiple tabs work
- [ ] Split panes functional
- [ ] Sessions persist across restarts
- [ ] Performance <50ms lag

### Phase 4
- [ ] All tests pass (Rust + Python + UI)
- [ ] Stress tests validate stability
- [ ] CI fully automated

### Phase 5
- [ ] Binaries built for all platforms
- [ ] Installers created
- [ ] Documentation complete
- [ ] Ready for public release

---

## Known Issues & Risks

### Current
- ✅ napi_bridge example broken (non-blocking)
- ✅ assert_cmd deprecation warnings (cosmetic)

### Potential Risks
1. **PTY Compatibility:** Windows PTY behavior differs
2. **Performance:** Large scrollback rendering
3. **UI Framework:** Electron vs Tauri decision
4. **Testing:** Live PTY tests may be flaky

### Mitigation
- Use `portable-pty` for cross-platform compatibility
- Implement virtual scrolling for performance
- Document UI framework decision rationale
- Add retry logic and timeouts to tests

---

## Next Steps

### Immediate (Phase 1.2)
1. ✅ Add `portable-pty` dependency
2. 🔄 Create `warp_core/src/pty.rs` module
3. ⏳ Implement `WarpPty::spawn()`
4. ⏳ Wire PTY output to parser
5. ⏳ Add `run-pty` CLI subcommand

### Commands to Execute
```bash
# Add dependency
cd warp_core
cargo add portable-pty

# Create module file
touch src/pty.rs

# Update lib.rs
echo "pub mod pty;" >> src/lib.rs

# Test compilation
cargo build

# Run interactive CLI
cargo run -- run-pty --shell /bin/zsh
```

---

**Last Updated:** 2025-01-16  
**Status:** Phase 1 In Progress  
**Next Milestone:** Interactive CLI MVP
