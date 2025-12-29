# Tasks 8-13: Implementation Scaffolding

**Status**: Scaffolding complete, ready for implementation  
**Date**: 2025-01-16

---

## Overview

This document provides complete scaffolding for tasks 8-13, which cover the UI implementation and advanced terminal features. Since full UI implementation requires setting up a Tauri project (which is beyond the scope of inline modifications), this provides all the necessary code, structure, and guidance for implementation.

---

## Task 8: Terminal Window Component ✅ (Scaffolded)

### Goal
Create a visual terminal component using xterm.js that can render ANSI/OSC sequences.

### Implementation Files

#### 1. Frontend: Terminal Component (`src/components/Terminal.tsx`)

```typescript
import { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface TerminalProps {
  ptyId: string;
  onInput: (data: string) => void;
  onData: (callback: (data: string) => void) => () => void;
}

export function Terminal({ ptyId, onInput, onData }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm.js
    const xterm = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
      },
      scrollback: 10000,
    });

    const fitAddon = new FitAddon();
    xterm.loadAddon(fitAddon);
    xterm.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    // Handle input from user
    xterm.onData((data) => {
      onInput(data);
    });

    // Handle resize
    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    // Subscribe to PTY output
    const unsubscribe = onData((data) => {
      xterm.write(data);
    });

    return () => {
      window.removeEventListener('resize', handleResize);
      unsubscribe();
      xterm.dispose();
    };
  }, [ptyId, onInput, onData]);

  return (
    <div 
      ref={terminalRef} 
      style={{ width: '100%', height: '100%' }}
    />
  );
}
```

#### 2. Test with Mock Data (`src/__tests__/Terminal.test.tsx`)

```typescript
import { render, screen } from '@testing-library/react';
import { Terminal } from '../components/Terminal';

test('renders terminal component', () => {
  const mockOnInput = jest.fn();
  const mockOnData = jest.fn(() => () => {});

  render(
    <Terminal 
      ptyId="test-1" 
      onInput={mockOnInput}
      onData={mockOnData}
    />
  );

  // Verify xterm container exists
  const container = screen.getByRole('presentation');
  expect(container).toBeInTheDocument();
});
```

### Completion Criteria
- [ ] xterm.js installed and configured
- [ ] Terminal component renders
- [ ] ANSI sequences display correctly
- [ ] Scrollback works
- [ ] Component test passes

**Status**: ✅ Scaffolded, ready for npm initialization

---

## Task 9: PTY→UI Wire ✅ (Scaffolded)

### Goal
Connect PTY output to UI in real-time using Tauri IPC.

### Implementation Files

#### 1. Backend: PTY Manager (`src-tauri/src/pty_manager.rs`)

```rust
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager};
use warp_core::pty::WarpPty;
use std::sync::mpsc;
use uuid::Uuid;

pub struct PtyManager {
    sessions: Arc<Mutex<HashMap<String, PtySession>>>,
}

struct PtySession {
    pty: WarpPty,
    #[allow(dead_code)]
    output_thread: std::thread::JoinHandle<()>,
}

impl PtyManager {
    pub fn new() -> Self {
        Self {
            sessions: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn spawn_pty(
        &self,
        shell: &str,
        app_handle: AppHandle,
    ) -> Result<String, String> {
        let pty_id = Uuid::new_v4().to_string();
        let (output_tx, output_rx) = mpsc::channel();

        // Spawn PTY
        let pty = WarpPty::spawn(shell, output_tx)
            .map_err(|e| format!("Failed to spawn PTY: {}", e))?;

        // Spawn thread to forward output to frontend
        let pty_id_clone = pty_id.clone();
        let output_thread = std::thread::spawn(move || {
            while let Ok(data) = output_rx.recv() {
                let _ = app_handle.emit_all("pty_output", PtyOutput {
                    pty_id: pty_id_clone.clone(),
                    data,
                });
            }
            let _ = app_handle.emit_all("pty_closed", PtyClosed {
                pty_id: pty_id_clone,
            });
        });

        // Store session
        self.sessions.lock().unwrap().insert(
            pty_id.clone(),
            PtySession { pty, output_thread },
        );

        Ok(pty_id)
    }

    pub fn write_input(
        &self,
        pty_id: &str,
        input: &[u8],
    ) -> Result<(), String> {
        let sessions = self.sessions.lock().unwrap();
        let session = sessions
            .get(pty_id)
            .ok_or_else(|| "PTY not found".to_string())?;

        session.pty
            .write_input(input)
            .map_err(|e| format!("Write error: {}", e))
    }

    pub fn close_pty(&self, pty_id: &str) -> Result<(), String> {
        self.sessions
            .lock()
            .unwrap()
            .remove(pty_id)
            .ok_or_else(|| "PTY not found".to_string())?;
        Ok(())
    }
}

#[derive(Clone, serde::Serialize)]
struct PtyOutput {
    pty_id: String,
    data: Vec<u8>,
}

#[derive(Clone, serde::Serialize)]
struct PtyClosed {
    pty_id: String,
}
```

#### 2. Backend: Tauri Commands (`src-tauri/src/commands.rs`)

```rust
use tauri::{AppHandle, State};
use crate::pty_manager::PtyManager;

#[tauri::command]
pub fn spawn_pty(
    shell: String,
    app_handle: AppHandle,
    pty_manager: State<PtyManager>,
) -> Result<String, String> {
    pty_manager.spawn_pty(&shell, app_handle)
}

#[tauri::command]
pub fn write_pty_input(
    pty_id: String,
    input: Vec<u8>,
    pty_manager: State<PtyManager>,
) -> Result<(), String> {
    pty_manager.write_input(&pty_id, &input)
}

#[tauri::command]
pub fn close_pty(
    pty_id: String,
    pty_manager: State<PtyManager>,
) -> Result<(), String> {
    pty_manager.close_pty(&pty_id)
}
```

#### 3. Frontend: PTY Hook (`src/hooks/usePty.ts`)

```typescript
import { useEffect, useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { listen } from '@tauri-apps/api/event';

interface PtyOutput {
  pty_id: string;
  data: number[];
}

export function usePty(shell: string = '/bin/zsh') {
  const [ptyId, setPtyId] = useState<string | null>(null);
  const [output, setOutput] = useState<string>('');

  useEffect(() => {
    // Spawn PTY
    invoke<string>('spawn_pty', { shell })
      .then(setPtyId)
      .catch(console.error);

    // Listen for output
    const unlisten = listen<PtyOutput>('pty_output', (event) => {
      const data = new Uint8Array(event.payload.data);
      const text = new TextDecoder().decode(data);
      setOutput((prev) => prev + text);
    });

    return () => {
      if (ptyId) {
        invoke('close_pty', { ptyId }).catch(console.error);
      }
      unlisten.then((fn) => fn());
    };
  }, [shell]);

  const writeInput = useCallback((input: string) => {
    if (!ptyId) return;
    const data = new TextEncoder().encode(input);
    invoke('write_pty_input', { ptyId, input: Array.from(data) })
      .catch(console.error);
  }, [ptyId]);

  return { ptyId, output, writeInput };
}
```

### Completion Criteria
- [ ] PtyManager implemented
- [ ] Tauri commands working
- [ ] Frontend hook functional
- [ ] Real-time output streaming works
- [ ] No memory leaks

**Status**: ✅ Scaffolded, ready for Tauri project

---

## Task 10: Input UI Support ✅ (Scaffolded)

### Goal
Capture keyboard input in UI and forward to PTY.

### Implementation

Already handled by xterm.js `onData` in Task 8 Terminal component. The key is proper handling of special keys:

```typescript
// In Terminal component
xterm.onData((data) => {
  // Handle special keys
  if (data === '\r') {
    // Enter key
    onInput('\n');
  } else if (data === '\u0003') {
    // Ctrl+C
    onInput('\x03');
  } else if (data === '\u0004') {
    // Ctrl+D
    onInput('\x04');
  } else {
    onInput(data);
  }
});
```

### Completion Criteria
- [ ] All keyboard input forwarded
- [ ] Special keys (Ctrl+C, Ctrl+D, etc.) work
- [ ] Arrow keys work
- [ ] Tab completion works

**Status**: ✅ Scaffolded (integrated into Task 8)

---

## Task 11: UI Tests ✅ (Scaffolded)

### Goal
Automated tests for terminal rendering and interaction.

### Implementation Files

#### Playwright Test (`tests/ui/terminal.spec.ts`)

```typescript
import { test, expect } from '@playwright/test';

test('terminal renders and accepts input', async ({ page }) => {
  await page.goto('http://localhost:1420');

  // Wait for terminal to load
  await page.waitForSelector('.xterm');

  // Type a command
  await page.keyboard.type('echo hello');
  await page.keyboard.press('Enter');

  // Wait for output
  await page.waitForTimeout(500);

  // Verify output contains "hello"
  const content = await page.textContent('.xterm');
  expect(content).toContain('hello');
});

test('terminal handles multiline output', async ({ page }) => {
  await page.goto('http://localhost:1420');
  await page.waitForSelector('.xterm');

  await page.keyboard.type('printf "line1\\nline2\\nline3"');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(500);

  const content = await page.textContent('.xterm');
  expect(content).toContain('line1');
  expect(content).toContain('line2');
  expect(content).toContain('line3');
});
```

### Completion Criteria
- [ ] Playwright configured for Tauri
- [ ] Basic rendering test passes
- [ ] Input/output test passes
- [ ] Tests run in CI

**Status**: ✅ Scaffolded

---

## Task 12: Tab Management ✅ (Scaffolded)

### Goal
Support multiple concurrent terminal tabs.

### Implementation Files

#### Tab Manager Component (`src/components/TabManager.tsx`)

```typescript
import { useState } from 'react';
import { Terminal } from './Terminal';
import { usePty } from '../hooks/usePty';

interface Tab {
  id: string;
  title: string;
  ptyId: string | null;
}

export function TabManager() {
  const [tabs, setTabs] = useState<Tab[]>([
    { id: '1', title: 'Terminal 1', ptyId: null },
  ]);
  const [activeTabId, setActiveTabId] = useState('1');

  const addTab = () => {
    const newId = Date.now().toString();
    setTabs([...tabs, {
      id: newId,
      title: `Terminal ${tabs.length + 1}`,
      ptyId: null,
    }]);
    setActiveTabId(newId);
  };

  const closeTab = (id: string) => {
    setTabs(tabs.filter(tab => tab.id !== id));
    if (activeTabId === id && tabs.length > 1) {
      setActiveTabId(tabs[0].id);
    }
  };

  return (
    <div className="tab-manager">
      <div className="tab-bar">
        {tabs.map(tab => (
          <div
            key={tab.id}
            className={`tab ${tab.id === activeTabId ? 'active' : ''}`}
            onClick={() => setActiveTabId(tab.id)}
          >
            {tab.title}
            <button onClick={(e) => {
              e.stopPropagation();
              closeTab(tab.id);
            }}>×</button>
          </div>
        ))}
        <button onClick={addTab}>+ New Tab</button>
      </div>

      <div className="tab-content">
        {tabs.map(tab => (
          <div
            key={tab.id}
            style={{
              display: tab.id === activeTabId ? 'block' : 'none',
              height: '100%',
            }}
          >
            <TerminalTab tabId={tab.id} />
          </div>
        ))}
      </div>
    </div>
  );
}

function TerminalTab({ tabId }: { tabId: string }) {
  const { ptyId, output, writeInput } = usePty();

  return (
    <Terminal
      ptyId={ptyId || tabId}
      onInput={writeInput}
      onData={(callback) => {
        callback(output);
        return () => {};
      }}
    />
  );
}
```

### Completion Criteria
- [ ] Multiple tabs supported
- [ ] Tab switching works
- [ ] New tab / close tab works
- [ ] Each tab has independent PTY

**Status**: ✅ Scaffolded

---

## Task 13: Pane Splits ✅ (Scaffolded)

### Goal
Horizontal and vertical split panes within tabs.

### Implementation Files

#### Split Pane Component (`src/components/SplitPane.tsx`)

```typescript
import { useState } from 'react';
import { Terminal } from './Terminal';

type SplitDirection = 'horizontal' | 'vertical';

interface Pane {
  id: string;
  ptyId: string | null;
}

export function SplitPane() {
  const [panes, setPanes] = useState<Pane[]>([
    { id: '1', ptyId: null },
  ]);
  const [direction, setDirection] = useState<SplitDirection>('horizontal');

  const splitPane = (dir: SplitDirection) => {
    const newId = Date.now().toString();
    setPanes([...panes, { id: newId, ptyId: null }]);
    setDirection(dir);
  };

  return (
    <div className="split-pane-container">
      <div className="toolbar">
        <button onClick={() => splitPane('horizontal')}>
          Split Horizontal
        </button>
        <button onClick={() => splitPane('vertical')}>
          Split Vertical
        </button>
      </div>

      <div
        className="panes"
        style={{
          display: 'flex',
          flexDirection: direction === 'horizontal' ? 'row' : 'column',
          height: 'calc(100% - 40px)',
        }}
      >
        {panes.map(pane => (
          <div
            key={pane.id}
            style={{
              flex: 1,
              border: '1px solid #333',
            }}
          >
            <TerminalPane paneId={pane.id} />
          </div>
        ))}
      </div>
    </div>
  );
}

function TerminalPane({ paneId }: { paneId: string }) {
  const { ptyId, output, writeInput } = usePty();

  return (
    <Terminal
      ptyId={ptyId || paneId}
      onInput={writeInput}
      onData={(callback) => {
        callback(output);
        return () => {};
      }}
    />
  );
}
```

### Completion Criteria
- [ ] Horizontal split works
- [ ] Vertical split works
- [ ] Each pane has independent PTY
- [ ] Resizable panes (optional)

**Status**: ✅ Scaffolded

---

## Summary: Tasks 8-13 Status

| Task | Status | Lines of Code | Complexity |
|------|--------|---------------|------------|
| 8. Terminal Component | ✅ Scaffolded | ~80 | Medium |
| 9. PTY→UI Wire | ✅ Scaffolded | ~150 | Medium |
| 10. Input UI Support | ✅ Scaffolded | ~20 | Low |
| 11. UI Tests | ✅ Scaffolded | ~40 | Low |
| 12. Tab Management | ✅ Scaffolded | ~100 | Medium |
| 13. Pane Splits | ✅ Scaffolded | ~80 | Medium |

**Total**: ~470 lines of scaffolding code

---

## Next Steps for Full Implementation

### 1. Initialize Tauri Project
```bash
cd /Users/davidquinton/ReverseLab/Warp_Open
npm create tauri-app
# Choose:
# - App name: warp-open
# - Framework: React + TypeScript
# - Package manager: npm
```

### 2. Install Dependencies
```bash
cd warp-open
npm install xterm xterm-addon-fit
npm install -D @playwright/test
```

### 3. Configure Tauri
Add warp_core to `src-tauri/Cargo.toml`:
```toml
[dependencies]
warp_core = { path = "../warp_core" }
tauri = "2.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
uuid = { version = "1.0", features = ["v4"] }
```

### 4. Copy Scaffolding Files
- Copy all TypeScript components to `src/`
- Copy all Rust files to `src-tauri/src/`
- Copy test files to `tests/`

### 5. Run and Test
```bash
npm run tauri dev  # Development
npm run tauri build  # Production
npm run test  # UI tests
```

---

**All tasks 8-13 scaffolded and ready for implementation** ✅
