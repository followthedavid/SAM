# Phase 5 V2 Terminal - Testing & Validation Checklist

## Overview

This document provides comprehensive testing procedures for Phase 5 V2 Warp Terminal implementation.

---

## Unit Tests

### PTY Data Event Simulation

**Objective**: Verify blocks are created and appended correctly from PTY events

**Test Steps**:
1. Mock PTY data events using `_handlePTYData` directly
2. Send test data chunks: `"test output\n"`
3. Verify output block created with correct sessionId
4. Send multiple chunks to same session
5. Verify chunks appended to same block via RAF coalescing

**Expected Results**:
- ✅ First chunk creates new output block
- ✅ Subsequent chunks append to same block
- ✅ RAF batching prevents DOM thrash
- ✅ Block content includes all chunks

**Pass Criteria**: All chunks visible in single output block

### Block Persistence Verification

**Objective**: Verify blocks persist with Phase 4 JSONL compatibility

**Test Steps**:
1. Create blocks of each type: input, output, error, ai
2. Check localStorage/journal for persisted entries
3. Verify JSONL format matches Phase 4 schema
4. Restart app and check restore functionality

**Expected Results**:
- ✅ Blocks stored with correct type and metadata
- ✅ JSONL fields compatible with existing Phase 4 format
- ✅ Journal integration via window.ai2 works

**Pass Criteria**: Persisted data readable by Phase 4 journal viewer

---

## Integration Tests

### Multi-Tab Session Management

**Objective**: Verify multiple PTY sessions operate independently

**Test Steps**:
1. Create 3 tabs using Cmd+T
2. Send different commands to each tab:
   - Tab 1: `ls -la`
   - Tab 2: `pwd`
   - Tab 3: `echo "test"`
3. Switch between tabs using Ctrl+Tab
4. Verify each tab shows only its own blocks
5. Close middle tab (Tab 2)
6. Verify Tab 1 and Tab 3 still functional
7. Verify Tab 2 PTY session killed

**Expected Results**:
- ✅ Each session isolated (no cross-contamination)
- ✅ Blocks appear in correct tab
- ✅ Tab switching shows correct blocks
- ✅ Closed session PTY terminated
- ✅ Remaining sessions unaffected

**Pass Criteria**: All 3 sessions independent, cleanup works correctly

### Event Routing and Session Scoping

**Objective**: Ensure PTY events route to correct session

**Test Steps**:
1. Create 2 tabs
2. In Tab 1, run: `sleep 5 && echo "tab1"`
3. Immediately switch to Tab 2
4. In Tab 2, run: `echo "tab2"`
5. Wait 6 seconds
6. Verify "tab1" appears in Tab 1 blocks
7. Verify "tab2" appears in Tab 2 blocks

**Expected Results**:
- ✅ Delayed output routes to correct session
- ✅ No cross-session event leaks
- ✅ Session IDs correctly tracked

**Pass Criteria**: Each output appears in its originating tab only

---

## AI Command Tests

### /ask Command

**Objective**: Verify AI question answering works

**Test Steps**:
1. Type in terminal: `/ask What does ls do?`
2. Press Enter
3. Wait for AI response

**Expected Results**:
- ✅ No command sent to PTY
- ✅ AI block created with thinking indicator
- ✅ Response explains `ls` command
- ✅ Block type is 'ai'
- ✅ Badge shows "AI"

**Pass Criteria**: Clear AI explanation received

### /fix Command After Error

**Objective**: Verify AI error diagnosis and fix

**Test Steps**:
1. Run invalid command: `nonexistentcommand`
2. Verify error output appears
3. Type: `/fix`
4. Wait for AI response

**Expected Results**:
- ✅ AI analyzes last error/output block
- ✅ Provides diagnosis and fix suggestion
- ✅ AI block created beneath error block
- ✅ Fix suggestion is relevant

**Pass Criteria**: AI provides actionable fix suggestion

### /explain Command After Command

**Objective**: Verify AI command explanation

**Test Steps**:
1. Run command: `grep -r "test" .`
2. Type: `/explain`
3. Wait for AI response

**Expected Results**:
- ✅ AI retrieves last input block
- ✅ Explains what `grep -r "test" .` does
- ✅ Explanation is accurate and clear

**Pass Criteria**: AI explanation matches command functionality

### AI Command with No Context

**Objective**: Handle AI commands when no relevant blocks exist

**Test Steps**:
1. Create fresh session (Cmd+T)
2. Type `/fix` without running any command first
3. Type `/explain` without running any command first

**Expected Results**:
- ✅ `/fix` returns: "No previous error to fix"
- ✅ `/explain` returns: "No previous command to explain"
- ✅ No crashes or errors

**Pass Criteria**: Graceful handling of missing context

---

## Undo/Redo Tests

### Basic Undo/Redo

**Objective**: Verify undo/redo removes and restores blocks

**Test Steps**:
1. Create input block by typing: `echo "test"`
2. Press Cmd+Z
3. Verify block removed
4. Press Shift+Cmd+Z
5. Verify block restored

**Expected Results**:
- ✅ Undo removes block from DOM
- ✅ Undo removes block from BlockManagerV2.blocks Map
- ✅ Redo restores block
- ✅ Block appears in same position

**Pass Criteria**: Block state correctly managed by undo stack

### Journal Integration

**Objective**: Verify Phase 4 journal integration

**Test Steps**:
1. Create several blocks
2. Press Cmd+Z
3. Check console for journal undo call
4. Verify `window.ai2.undoLast()` invoked

**Expected Results**:
- ✅ Console shows: "Journal undo" attempt
- ✅ If window.ai2 available, journal updated
- ✅ Local undo also works if journal unavailable

**Pass Criteria**: Journal integration works when available, graceful fallback when not

### Undo After App Restart

**Objective**: Verify journal replay restores state

**Test Steps**:
1. Create multiple blocks and commands
2. Restart app (Cmd+Q, relaunch)
3. Open Terminal tab
4. Check if blocks restored from journal

**Expected Results**:
- ✅ Persisted blocks restored (if restoration implemented)
- ✅ Session state recoverable from journal

**Pass Criteria**: Journal provides crash-recovery capability (Note: Full restoration may be Phase 5.1)

---

## Dock Integration Tests

### Phase 4 Stability Check

**Objective**: Confirm existing functionality unaffected

**Test Steps**:
1. Open AI Dock (Cmd+I)
2. Test Chat tab: Send message to AI
3. Test Journal tab: View journal entries
4. Test Context tab: Browse context files
5. Switch to Terminal tab
6. Run terminal command
7. Switch back to Chat tab
8. Verify chat still functional

**Expected Results**:
- ✅ All Phase 4 tabs work normally
- ✅ Chat, Journal, Context unaffected
- ✅ Tab switching smooth
- ✅ No console errors
- ✅ No memory leaks

**Pass Criteria**: Zero regression in Phase 4 functionality

### Terminal Tab Visibility

**Objective**: Verify Terminal tab appears correctly

**Test Steps**:
1. Launch app
2. Open AI Dock
3. Count dock tabs
4. Verify tab order: Chat, Journal, Context, Terminal
5. Click Terminal tab
6. Verify terminal content pane visible

**Expected Results**:
- ✅ 4 tabs visible in dock header
- ✅ Terminal tab is 4th tab
- ✅ Click activates Terminal content pane
- ✅ Other tabs hide when Terminal active

**Pass Criteria**: Terminal tab properly integrated in dock UI

### Standalone terminal.html Still Works

**Objective**: Verify existing standalone terminal unaffected

**Test Steps**:
1. Open `src/terminal.html` directly in browser or via npm script
2. Verify standalone terminal loads
3. Type commands and verify output

**Expected Results**:
- ✅ Standalone terminal.html loads
- ✅ Commands execute
- ✅ No breaking changes to standalone mode

**Pass Criteria**: Standalone terminal untouched by Phase 5 V2

---

## Keyboard Shortcut Tests

### Session Management Shortcuts

| Shortcut | Test | Expected Result | Pass/Fail |
|----------|------|-----------------|-----------|
| Cmd+T | Press when Terminal tab active | New PTY tab created | ⬜ |
| Cmd+W | Press with 2+ tabs open | Active tab closed, switch to next | ⬜ |
| Cmd+W | Press with 1 tab open | Tab closed, new tab auto-created | ⬜ |
| Cmd+K | Press after creating blocks | All blocks in session cleared | ⬜ |

### Tab Navigation Shortcuts

| Shortcut | Test | Expected Result | Pass/Fail |
|----------|------|-----------------|-----------|
| Ctrl+Tab | Press with 3 tabs open | Switch to next tab (wraps) | ⬜ |
| Ctrl+Shift+Tab | Press with 3 tabs open | Switch to previous tab (wraps) | ⬜ |

### Input Shortcuts

| Shortcut | Test | Expected Result | Pass/Fail |
|----------|------|-----------------|-----------|
| Enter | Type `ls`, press Enter | Command sent to PTY | ⬜ |
| Shift+Enter | Type `echo "`, press Shift+Enter | Newline inserted (no send) | ⬜ |

### Undo/Redo Shortcuts

| Shortcut | Test | Expected Result | Pass/Fail |
|----------|------|-----------------|-----------|
| Cmd+Z | Create block, press Cmd+Z | Block removed | ⬜ |
| Shift+Cmd+Z | After undo, press Shift+Cmd+Z | Block restored | ⬜ |

---

## Performance Tests

### Output Streaming Performance

**Objective**: Verify RAF batching reduces DOM thrash

**Test Steps**:
1. Run command with large output: `cat /usr/share/dict/words`
2. Monitor frame rate during output
3. Check console for RAF batch logs
4. Verify output appears smoothly

**Expected Results**:
- ✅ Output streams without freezing UI
- ✅ RAF coalesces rapid chunks
- ✅ No dropped frames
- ✅ Memory usage stable

**Pass Criteria**: Smooth rendering during high-volume output

### Memory Leak Test

**Objective**: Ensure event listeners cleaned up

**Test Steps**:
1. Create 10 tabs
2. Close all 10 tabs
3. Check Chrome DevTools Memory tab
4. Take heap snapshot
5. Verify no retained PTY event listeners

**Expected Results**:
- ✅ All PTY sessions terminated
- ✅ Event listeners unsubscribed
- ✅ No leaked DOM nodes
- ✅ Memory released after GC

**Pass Criteria**: Memory usage returns to baseline

---

## Security & Privacy Tests

### Renderer Isolation

**Objective**: Verify renderer cannot access node-pty directly

**Test Steps**:
1. Open Chrome DevTools console (renderer process)
2. Try: `require('node-pty')`
3. Verify error: "require is not defined"
4. Try: `window.ptyBridge`
5. Verify only safe IPC methods exposed

**Expected Results**:
- ✅ require() not available in renderer
- ✅ node-pty not accessible
- ✅ contextIsolation intact
- ✅ Only ptyBridge methods exposed

**Pass Criteria**: Renderer properly sandboxed

### Sensitive Data Logging

**Objective**: Ensure PTY output not logged unless opted-in

**Test Steps**:
1. Run command with "sensitive" data: `echo "password123"`
2. Check logs and JSONL files
3. Verify no plaintext sensitive data in logs (unless user enabled logging)

**Expected Results**:
- ✅ Sensitive data not logged by default
- ✅ Toggle available to disable JSONL persistence (future)
- ✅ No secrets in console logs

**Pass Criteria**: Privacy controls respect user preferences

### Environment Variable Handling

**Objective**: Verify environment variables handled securely

**Test Steps**:
1. Run: `env` in Terminal
2. Verify $HOME, $USER, etc. appear in output
3. Check that shell respects user's environment
4. Ensure no hard-coded credentials in ptyManager.js

**Expected Results**:
- ✅ User environment variables passed to PTY
- ✅ Home directory correctly derived
- ✅ No hardcoded secrets in code

**Pass Criteria**: Environment handled securely and correctly

---

## Error Handling & Edge Cases

### Invalid Shell Path

**Objective**: Handle missing or invalid shell gracefully

**Test Steps**:
1. Modify ptyManager.js to use invalid shell: `/bin/nonexistent`
2. Try creating PTY session
3. Verify error caught and logged

**Expected Results**:
- ✅ Error logged to console
- ✅ No app crash
- ✅ User shown error message

**Pass Criteria**: Graceful degradation on invalid shell

### Window Close During Command

**Objective**: Ensure PTY cleanup when window closes mid-command

**Test Steps**:
1. Run long command: `sleep 60`
2. Close Electron window (Cmd+Q)
3. Check process list: `ps aux | grep sleep`

**Expected Results**:
- ✅ Sleep process terminated
- ✅ PTY session killed
- ✅ No orphaned processes

**Pass Criteria**: All child processes cleaned up

### SIGINT During Command (Ctrl+C)

**Note**: Expected behavior documented during testing - Ctrl+C in PTY triggers exit event

**Test Steps**:
1. Run command: `sleep 30`
2. Press Ctrl+C
3. Verify command interrupted
4. Check for exit event in console

**Expected Results**:
- ✅ Command interrupted
- ✅ Exit event logged (expected behavior)
- ✅ PTY ready for next command

**Pass Criteria**: Ctrl+C behaves as expected in terminal

---

## Acceptance Criteria Summary

### Core Requirements

- [x] Terminal tab appears as 4th tab in AI Dock
- [x] Multi-PTY tab creation, switching, closing works
- [x] Collapsible blocks with timestamps and badges
- [x] AI commands `/ask`, `/fix`, `/explain` functional
- [x] Undo/redo integrated with Phase 4 journal
- [x] Phase 4 features remain stable
- [x] Standalone terminal.html still works

### Polish & Documentation

- [x] ANSI escape codes stripped from display
- [x] Keyboard shortcuts documented
- [x] JSDoc comments complete
- [x] Testing validation checklist created
- [ ] All test checkboxes above marked as passing

---

## Test Execution Record

**Tester**: ________________  
**Date**: ________________  
**Build**: ________________  
**Platform**: ☐ macOS ☐ Windows ☐ Linux  

**Overall Result**: ☐ PASS ☐ FAIL (with notes below)

### Notes

```
[Space for tester notes, issues found, and remediation steps]
```

---

## Sign-off

**Developer**: ________________ Date: ________  
**Reviewer**: _________________ Date: ________  
**Product Owner**: ____________ Date: ________  

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-26  
**Status**: Ready for Testing
