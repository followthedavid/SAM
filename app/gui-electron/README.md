# Warp_Open Terminal

A modern terminal emulator built with Electron and xterm.js, featuring tabs, panes, session management, and extensive customization.

## Features

### Core Terminal
- **Multi-tabbed interface** with drag-reorder and rename
- **Split panes** (horizontal/vertical) with resizable dividers
- **Session persistence** with auto-save and restore
- **Shell configuration** with fallback support
- **Theme support** (Dark/Light/System)

### Session Management
- Auto-save sessions on quit and periodically
- Save/Load sessions to/from JSON files
- Recent sessions menu with file pruning
- Drag-and-drop session loading
- Restore precedence: local → autosave → last saved

### Customization
- **Preferences dialog** (Cmd/Ctrl+,) with live preview
- Font size, scrollback buffer, copy behavior
- Bell sound and toast notifications
- Default folder for new tabs
- Shell path, login flag, and extra arguments
- Window position/size persistence

### Advanced Features
- **Broadcast mode** - type to all panes in a tab
- **Find in terminal** with case/regex options
- **Path actions** - open/reveal/cd selected text with smart fallbacks
- **Export scrollback** to text files
- **Zoom pane** to focus on one pane
- **Status bar** showing CWD, terminal size, and modes

## Installation

```bash
npm install
npm run rebuild  # Rebuild native modules for Electron
```

## Usage

```bash
# Development (foreground)
npm run dev

# Development (detached, frees terminal)
npm run dev:bg

# Build for macOS
npm run pack:mac

# Rebuild native modules only
npm run rebuild

# Open packaged app on macOS
npm run open:mac
```

## Keyboard Shortcuts

### Tabs & Panes
- **New Tab**: Cmd/Ctrl+T
- **Split H/V**: Cmd/Ctrl+Shift+H / +Shift+V
- **Close Pane**: Cmd/Ctrl+Shift+W
- **Next/Prev Pane**: Cmd/Ctrl+] / Cmd/Ctrl+[
- **Grow/Shrink Pane**: Cmd/Ctrl+Shift+Right/Left
- **Equalize Panes**: Cmd/Ctrl+Shift+0
- **Toggle Zoom**: Cmd/Ctrl+Shift+Z

### Sessions
- **Save Session**: Cmd/Ctrl+S
- **Save Session As**: Cmd/Ctrl+Shift+S
- **Preferences**: Cmd/Ctrl+,

### Edit
- **Find**: Cmd/Ctrl+F, Next: Enter, Prev: Shift+Enter
- **Clear**: Cmd/Ctrl+K, Reset: Cmd/Ctrl+Shift+X
- **Select All**: Cmd/Ctrl+A

### View
- **Font +/-**: Cmd/Ctrl+= / Cmd/Ctrl+- (Reset: Cmd/Ctrl+0)

## Configuration

Settings are stored in `config.json` in the app's userData directory. Key options:

```json
{
  "theme": "dark",
  "fontSize": 13,
  "shellPath": "/bin/zsh",
  "shellLogin": true,
  "shellArgs": "",
  "openDevToolsOnStart": false,
  "autosaveEnabled": true,
  "autoSaveIntervalSec": 30,
  "autosaveToast": false,
  "restoreSessionOnLaunch": true,
  "confirmOnQuit": false,
  "writeLastOnQuit": true,
  "defaultCwd": "/path/to/default/folder",
  "newTabUseLastCwd": false,
  "lastSessionPath": null,
  "firstRun": true
}
```

## Session Format

Session files are JSON with this structure:

```json
{
  "version": 1,
  "savedAt": 1697123456789,
  "activeTabId": "tab-id",
  "theme": "dark",
  "tabs": [
    {
      "id": "tab-id",
      "title": "Tab 1",
      "cwd": "/Users/user",
      "panes": ["pane-id-1", "pane-id-2"],
      "orient": "cols",
      "sizes": [0.5, 0.5]
    }
  ]
}
```

## Development

The app uses:
- **Electron** for the desktop wrapper
- **xterm.js** for terminal emulation
- **node-pty** for pseudo-terminal spawning
- **@electron/rebuild** for native module compatibility

File structure:
- `src/main.js` - Electron main process
- `src/preload.js` - Secure IPC bridge
- `src/renderer.js` - Terminal UI and session logic
- `src/index.html` - App markup and styles

## License

Part of the Warp_Open project.