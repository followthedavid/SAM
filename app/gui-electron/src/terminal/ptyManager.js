/**
 * ptyManager.js - Multi-PTY and tab manager for Phase 5 Terminal
 * Manages multiple shell sessions with block-based output
 */

const { spawn } = require('node-pty');
const { randomUUID } = require('crypto');
const os = require('os');

class PTYManager {
  constructor() {
    this.terminals = {}; // id -> { pty, tabName, blocks, buffer }
    this.activeTab = null;
    this.outputHandlers = []; // callbacks for output
  }

  /**
   * Create a new terminal session
   * @param {string} tabName - Name for the tab
   * @param {string} shell - Shell to spawn (default: zsh/bash)
   * @param {string} cwd - Working directory
   * @returns {string} Terminal ID
   */
  createTerminal(tabName = 'Terminal', shell = null, cwd = null) {
    const id = randomUUID();
    const defaultShell = shell || process.env.SHELL || (os.platform() === 'win32' ? 'powershell.exe' : 'zsh');
    const workingDir = cwd || process.env.HOME || process.cwd();

    const pty = spawn(defaultShell, [], {
      name: 'xterm-256color',
      cols: 120,
      rows: 30,
      cwd: workingDir,
      env: process.env,
    });

    this.terminals[id] = {
      pty,
      tabName,
      blocks: [],
      buffer: '',
      cwd: workingDir,
      shell: defaultShell,
    };

    // Set up output handler
    pty.onData((data) => {
      this._handleOutput(id, data);
    });

    pty.onExit((exitCode) => {
      console.log(`[PTY ${id}] Exited with code ${exitCode}`);
      this._notifyHandlers({ type: 'exit', terminalId: id, exitCode });
    });

    this.activeTab = id;
    console.log(`[PTYManager] Created terminal ${id}: ${tabName}`);
    return id;
  }

  /**
   * Send command to active terminal
   * @param {string} cmd - Command to execute
   * @returns {object} Block representing the command
   */
  sendCommand(cmd) {
    const term = this.terminals[this.activeTab];
    if (!term) {
      throw new Error('No active terminal');
    }

    // Create user input block
    const block = this._createBlock('input', cmd, this.activeTab);
    
    // Send to PTY
    term.pty.write(cmd + '\r');

    return block;
  }

  /**
   * Write data directly to PTY (for paste, etc.)
   */
  write(data, terminalId = null) {
    const id = terminalId || this.activeTab;
    const term = this.terminals[id];
    if (term) {
      term.pty.write(data);
    }
  }

  /**
   * Create a block entry
   */
  _createBlock(type, content, terminalId) {
    const block = {
      id: randomUUID(),
      type, // 'input', 'output', 'error', 'ai'
      content,
      timestamp: new Date().toISOString(),
      terminalId,
      status: type === 'input' ? 'running' : 'complete',
    };

    const term = this.terminals[terminalId];
    if (term) {
      term.blocks.push(block);
    }

    this._notifyHandlers({ type: 'block', block });
    return block;
  }

  /**
   * Handle output from PTY
   */
  _handleOutput(terminalId, data) {
    const term = this.terminals[terminalId];
    if (!term) return;

    term.buffer += data;

    // Check for command completion markers (optional: OSC 133 support)
    // For now, create output blocks on newlines or after delay
    
    this._notifyHandlers({ 
      type: 'output', 
      terminalId, 
      data,
      rawBuffer: term.buffer 
    });

    // Simple heuristic: flush buffer to block on prompt detection
    // (In production, use OSC 133 or similar markers)
    if (data.includes('$') || data.includes('>') || data.includes('#')) {
      this._flushBufferToBlock(terminalId);
    }
  }

  /**
   * Flush accumulated buffer to output block
   */
  _flushBufferToBlock(terminalId) {
    const term = this.terminals[terminalId];
    if (!term || !term.buffer.trim()) return;

    // Find last input block and mark complete
    const lastInput = [...term.blocks].reverse().find(b => b.type === 'input');
    if (lastInput && lastInput.status === 'running') {
      lastInput.status = 'complete';
    }

    // Create output block
    this._createBlock('output', term.buffer.trim(), terminalId);
    term.buffer = '';
  }

  /**
   * Register output handler
   */
  onOutput(handler) {
    this.outputHandlers.push(handler);
  }

  _notifyHandlers(event) {
    this.outputHandlers.forEach(h => h(event));
  }

  /**
   * Switch active tab
   */
  switchTab(terminalId) {
    if (this.terminals[terminalId]) {
      this.activeTab = terminalId;
      return true;
    }
    return false;
  }

  /**
   * Get blocks for a terminal
   */
  getBlocks(terminalId = null) {
    const id = terminalId || this.activeTab;
    return this.terminals[id]?.blocks || [];
  }

  /**
   * Get all terminal tabs
   */
  getTabs() {
    return Object.keys(this.terminals).map(id => ({
      id,
      name: this.terminals[id].tabName,
      active: id === this.activeTab,
      cwd: this.terminals[id].cwd,
    }));
  }

  /**
   * Resize terminal
   */
  resize(cols, rows, terminalId = null) {
    const id = terminalId || this.activeTab;
    const term = this.terminals[id];
    if (term) {
      term.pty.resize(cols, rows);
    }
  }

  /**
   * Close terminal
   */
  closeTerminal(terminalId) {
    const term = this.terminals[terminalId];
    if (term) {
      term.pty.kill();
      delete this.terminals[terminalId];

      // Switch to another tab if active was closed
      if (this.activeTab === terminalId) {
        const remainingIds = Object.keys(this.terminals);
        this.activeTab = remainingIds.length > 0 ? remainingIds[0] : null;
      }

      return true;
    }
    return false;
  }

  /**
   * Cleanup all terminals
   */
  destroy() {
    Object.keys(this.terminals).forEach(id => {
      this.terminals[id].pty.kill();
    });
    this.terminals = {};
    this.activeTab = null;
  }
}

module.exports = { PTYManager };
