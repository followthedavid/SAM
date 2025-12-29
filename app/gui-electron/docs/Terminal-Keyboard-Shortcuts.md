# Terminal Keyboard Shortcuts

Phase 5 V2 Warp Terminal supports the following keyboard shortcuts for efficient terminal management and navigation.

## Session Management

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd+T` (Mac) / `Ctrl+T` (Win/Linux) | New PTY Tab | Creates a new PTY session in a new subtab |
| `Cmd+W` (Mac) / `Ctrl+W` (Win/Linux) | Close Active Tab | Closes the current PTY session and removes its subtab |
| `Cmd+K` (Mac) / `Ctrl+K` (Win/Linux) | Clear Session | Clears all visible blocks in the current session |

## Tab Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+Tab` | Next Tab | Switches to the next PTY session subtab |
| `Ctrl+Shift+Tab` | Previous Tab | Switches to the previous PTY session subtab |

## Command Input

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | Send Command | Sends the current input as a command to the active PTY session |
| `Shift+Enter` | New Line | Inserts a newline in the input box for multi-line commands |

## Undo/Redo

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd+Z` (Mac) / `Ctrl+Z` (Win/Linux) | Undo | Undoes the last block operation, backed by Phase 4 journal |
| `Shift+Cmd+Z` (Mac) / `Ctrl+Y` (Win/Linux) | Redo | Redoes the last undone operation |

## Notes

- All shortcuts are implemented in `terminal_renderer_v2.js` (`_setupKeyboardShortcuts` method)
- Undo/redo operations integrate with Phase 4 journal via `window.ai2.undoLast()` when available
- Input shortcuts only work when the terminal input box has focus
- Session management shortcuts work globally within the Terminal tab
- Tab navigation wraps around (after last tab, goes to first tab)

## AI Slash Commands

While not keyboard shortcuts, these special commands can be typed in the input box:

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask the AI assistant a question about anything |
| `/fix` | Request AI assistance to fix the error from the last command |
| `/explain` | Request AI to explain what the last command does |

These commands are intercepted before being sent to the PTY and create special "ai" type blocks with the response.
