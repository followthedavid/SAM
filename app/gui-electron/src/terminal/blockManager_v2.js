/**
 * blockManager_v2.js - Enhanced block management with advanced features
 * - Collapsible blocks with state persistence
 * - Multi-level undo/redo stack
 * - Context-aware AI (git status, recent errors, file tree)
 * - Keyboard navigation
 * - OSC 133 marker support
 * 
 * Note: This is a browser-compatible version that doesn't use Node.js require()
 * It expects PTYManager and UI utilities to be available globally or via window.ptyBridge
 */

// Browser-compatible - no require() statements

class BlockManagerV2 {
  constructor(container, options = {}) {
    this.container = container;
    this.ptyManager = new PTYManager();
    this.ai2 = options.ai2 || null;
    this.onBlockCreated = options.onBlockCreated || null;

    // Enhanced state
    this.collapsedBlocks = new Set(); // Track collapsed block IDs
    this.undoStack = []; // Multi-level undo
    this.redoStack = []; // Multi-level redo
    this.selectedBlockId = null; // For keyboard navigation
    this.contextCache = null; // Cached context for AI
    this.contextCacheTime = 0;

    // Set up PTY output handler with OSC 133 support
    this.ptyManager.onOutput((event) => {
      this._handlePTYEvent(event);
    });

    // Set up keyboard navigation
    this._setupKeyboardNav();
  }

  /**
   * Create a new terminal tab
   */
  async createTab(tabName = 'Terminal', shell = null, cwd = null) {
    const tabId = this.ptyManager.createTerminal(tabName, shell, cwd);
    
    // Log to journal
    if (this.ai2) {
      await this.ai2.logAction('tab_create', `Created tab: ${tabName}`, {
        tabId,
        shell,
        cwd,
      });
    }

    this.renderAllBlocks();
    return tabId;
  }

  /**
   * Switch to a different tab
   */
  switchTab(tabId) {
    if (this.ptyManager.switchTab(tabId)) {
      this.renderAllBlocks();
      
      // Restore collapsed state for this tab
      this._restoreCollapsedState();
      
      return true;
    }
    return false;
  }

  /**
   * Get list of tabs
   */
  getTabs() {
    return this.ptyManager.getTabs();
  }

  /**
   * Run a command in the active terminal
   */
  async runCommand(cmd) {
    // Save state for undo
    this._saveStateForUndo('command', { command: cmd });

    // Get context for potential AI use
    const context = await this._getEnhancedContext();

    // Log to journal via ai2
    if (this.ai2) {
      try {
        await this.ai2.logAction('command', `Run: ${cmd}`, {
          command: cmd,
          terminal: this.ptyManager.activeTab,
          context: context.cwd,
        });
      } catch (err) {
        console.error('[BlockManagerV2] Journal log failed:', err);
      }
    }

    // Send to PTY
    const block = this.ptyManager.sendCommand(cmd);
    appendBlockToUI(this.container, block);

    if (this.onBlockCreated) {
      this.onBlockCreated(block);
    }

    return block;
  }

  /**
   * Add an AI response block with enhanced context
   */
  async addAIBlock(content, context = {}) {
    // Save state for undo
    this._saveStateForUndo('ai_block', { content, context });

    const block = {
      id: crypto.randomUUID(),
      type: 'ai',
      content,
      timestamp: new Date().toISOString(),
      terminalId: this.ptyManager.activeTab,
      status: 'complete',
      context,
      collapsible: true,
    };

    // Add to PTY manager's block list
    const term = this.ptyManager.terminals[this.ptyManager.activeTab];
    if (term) {
      term.blocks.push(block);
    }

    // Render with collapse support
    const blockEl = createBlockElement(block);
    this._addCollapseSupport(blockEl, block);
    this.container.appendChild(blockEl);
    this.container.scrollTop = this.container.scrollHeight;

    // Log to journal
    if (this.ai2) {
      try {
        await this.ai2.logAction('ai_response', content.substring(0, 100), {
          fullContent: content,
          context,
        });
      } catch (err) {
        console.error('[BlockManagerV2] AI journal log failed:', err);
      }
    }

    return block;
  }

  /**
   * Handle AI command with enhanced context
   */
  async handleAICommand(command, args) {
    const lastBlock = this.getLastOutputBlock();
    const context = await this._getEnhancedContext();

    switch (command) {
      case '/ask':
        return this._handleAskCommand(args, context);
      case '/explain':
        return this._handleExplainCommand(lastBlock, context);
      case '/fix':
        return this._handleFixCommand(lastBlock, args, context);
      default:
        return this.addAIBlock(`Unknown command: ${command}`);
    }
  }

  async _handleAskCommand(question, context) {
    if (!this.ai2) {
      return this.addAIBlock('[AI not available]');
    }

    // Build enhanced prompt with context
    const prompt = this._buildContextualPrompt(question, context);

    try {
      const response = await this.ai2.askAI(prompt);
      return this.addAIBlock(response, { command: 'ask', context });
    } catch (err) {
      return this.addAIBlock(`AI Error: ${err.message}`);
    }
  }

  async _handleExplainCommand(lastBlock, context) {
    if (!lastBlock) {
      return this.addAIBlock('No previous command to explain.');
    }

    if (!this.ai2) {
      return this.addAIBlock('[AI not available]');
    }

    const prompt = `Explain this command:
${lastBlock.textContent}

Context:
- Current directory: ${context.cwd}
- Recent errors: ${context.recentErrors.length > 0 ? context.recentErrors.join(', ') : 'none'}`;

    try {
      const response = await this.ai2.askAI(prompt);
      return this.addAIBlock(response, { command: 'explain', original: lastBlock.textContent });
    } catch (err) {
      return this.addAIBlock(`AI Error: ${err.message}`);
    }
  }

  async _handleFixCommand(lastBlock, args, context) {
    if (!lastBlock) {
      return this.addAIBlock('No previous command to fix.');
    }

    if (!this.ai2) {
      return this.addAIBlock('[AI not available]');
    }

    const prompt = `Fix this command:
Command: ${lastBlock.textContent}
Error: ${args || 'command failed'}

Context:
- Current directory: ${context.cwd}
- Git status: ${context.gitStatus || 'not a git repo'}
- Shell: ${context.shell}

Suggest a corrected command.`;

    try {
      const response = await this.ai2.askAI(prompt);
      return this.addAIBlock(response, { command: 'fix', original: lastBlock.textContent, error: args });
    } catch (err) {
      return this.addAIBlock(`AI Error: ${err.message}`);
    }
  }

  /**
   * Get enhanced context for AI
   */
  async _getEnhancedContext() {
    // Cache context for 5 seconds
    const now = Date.now();
    if (this.contextCache && (now - this.contextCacheTime) < 5000) {
      return this.contextCache;
    }

    try {
      // Get base context from ai2
      const baseContext = this.ai2 ? await this.ai2.getContextPack() : {};

      // Get recent blocks for error detection
      const blocks = this.ptyManager.getBlocks();
      const recentErrors = blocks
        .filter(b => b.type === 'error' || b.status === 'error')
        .slice(-3)
        .map(b => b.content.substring(0, 100));

      // Build enhanced context
      const context = {
        ...baseContext,
        recentErrors,
        blockCount: blocks.length,
        activeTab: this.ptyManager.activeTab,
        tabCount: Object.keys(this.ptyManager.terminals).length,
      };

      // Try to get git status if available
      if (this.ai2) {
        try {
          const gitResult = await this.ai2.runScript('git', ['status', '--short']);
          if (gitResult && gitResult.code === 0) {
            context.gitStatus = gitResult.stdout.trim();
          }
        } catch (err) {
          // Git not available or not a repo
        }
      }

      this.contextCache = context;
      this.contextCacheTime = now;

      return context;
    } catch (err) {
      console.error('[BlockManagerV2] Failed to get enhanced context:', err);
      return {
        cwd: '~',
        recentErrors: [],
        shell: 'unknown',
      };
    }
  }

  /**
   * Build contextual prompt with enhanced info
   */
  _buildContextualPrompt(question, context) {
    const parts = [question];

    if (context.cwd && context.cwd !== '~') {
      parts.push(`\nCurrent directory: ${context.cwd}`);
    }

    if (context.gitStatus) {
      parts.push(`\nGit status:\n${context.gitStatus}`);
    }

    if (context.recentErrors && context.recentErrors.length > 0) {
      parts.push(`\nRecent errors:\n${context.recentErrors.join('\n')}`);
    }

    return parts.join('');
  }

  /**
   * Toggle block collapse state
   */
  toggleBlockCollapse(blockId) {
    const blockEl = this.container.querySelector(`[data-id="${blockId}"]`);
    if (!blockEl) return;

    if (this.collapsedBlocks.has(blockId)) {
      this.collapsedBlocks.delete(blockId);
      blockEl.classList.remove('collapsed');
    } else {
      this.collapsedBlocks.add(blockId);
      blockEl.classList.add('collapsed');
    }

    // Save collapsed state per tab
    this._saveCollapsedState();
  }

  /**
   * Add collapse button to block
   */
  _addCollapseSupport(blockEl, block) {
    if (!block.collapsible && block.type !== 'output' && block.type !== 'ai') {
      return;
    }

    const collapseBtn = document.createElement('button');
    collapseBtn.className = 'block-collapse-btn';
    collapseBtn.textContent = '▼';
    collapseBtn.title = 'Collapse block';
    collapseBtn.onclick = () => this.toggleBlockCollapse(block.id);

    const meta = blockEl.querySelector('.block-meta');
    if (meta) {
      meta.insertBefore(collapseBtn, meta.firstChild);
    }

    // Restore collapsed state
    if (this.collapsedBlocks.has(block.id)) {
      blockEl.classList.add('collapsed');
      collapseBtn.textContent = '▶';
    }
  }

  /**
   * Save collapsed state per tab
   */
  _saveCollapsedState() {
    const tabId = this.ptyManager.activeTab;
    if (!tabId) return;

    const state = Array.from(this.collapsedBlocks);
    localStorage.setItem(`warp_collapsed_${tabId}`, JSON.stringify(state));
  }

  /**
   * Restore collapsed state for current tab
   */
  _restoreCollapsedState() {
    const tabId = this.ptyManager.activeTab;
    if (!tabId) return;

    const stateStr = localStorage.getItem(`warp_collapsed_${tabId}`);
    if (stateStr) {
      try {
        const state = JSON.parse(stateStr);
        this.collapsedBlocks = new Set(state);
      } catch (err) {
        console.error('[BlockManagerV2] Failed to restore collapsed state:', err);
      }
    } else {
      this.collapsedBlocks.clear();
    }
  }

  /**
   * Multi-level undo
   */
  async undo() {
    if (this.undoStack.length === 0) {
      console.log('[BlockManagerV2] Nothing to undo');
      return false;
    }

    const state = this.undoStack.pop();
    this.redoStack.push(state);

    // Remove last block if it was a command or AI block
    if (state.type === 'command' || state.type === 'ai_block') {
      const blocks = this.ptyManager.getBlocks();
      if (blocks.length > 0) {
        blocks.pop();
        this.renderAllBlocks();
      }
    }

    // Log undo
    if (this.ai2) {
      await this.ai2.logAction('undo', `Undid ${state.type}`, state.data);
    }

    console.log('[BlockManagerV2] Undo:', state.type);
    return true;
  }

  /**
   * Multi-level redo
   */
  async redo() {
    if (this.redoStack.length === 0) {
      console.log('[BlockManagerV2] Nothing to redo');
      return false;
    }

    const state = this.redoStack.pop();
    this.undoStack.push(state);

    // Re-run command or add AI block
    if (state.type === 'command') {
      await this.runCommand(state.data.command);
    } else if (state.type === 'ai_block') {
      await this.addAIBlock(state.data.content, state.data.context);
    }

    console.log('[BlockManagerV2] Redo:', state.type);
    return true;
  }

  /**
   * Save state for undo
   */
  _saveStateForUndo(type, data) {
    this.undoStack.push({ type, data, timestamp: Date.now() });
    
    // Limit undo stack to 50 items
    if (this.undoStack.length > 50) {
      this.undoStack.shift();
    }

    // Clear redo stack on new action
    this.redoStack = [];
  }

  /**
   * Setup keyboard navigation
   */
  _setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      // Cmd/Ctrl+Z for undo
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        this.undo();
        return;
      }

      // Cmd/Ctrl+Shift+Z for redo
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        this.redo();
        return;
      }

      // Arrow keys for block navigation (when not in input)
      if (document.activeElement.tagName !== 'INPUT' && 
          document.activeElement.tagName !== 'TEXTAREA') {
        
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this._selectNextBlock();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this._selectPreviousBlock();
        } else if (e.key === 'Enter' && this.selectedBlockId) {
          e.preventDefault();
          this.toggleBlockCollapse(this.selectedBlockId);
        }
      }
    });
  }

  /**
   * Select next block for keyboard navigation
   */
  _selectNextBlock() {
    const blocks = Array.from(this.container.querySelectorAll('.block'));
    if (blocks.length === 0) return;

    let index = blocks.findIndex(b => b.dataset.id === this.selectedBlockId);
    index = (index + 1) % blocks.length;

    this._selectBlock(blocks[index].dataset.id);
  }

  /**
   * Select previous block for keyboard navigation
   */
  _selectPreviousBlock() {
    const blocks = Array.from(this.container.querySelectorAll('.block'));
    if (blocks.length === 0) return;

    let index = blocks.findIndex(b => b.dataset.id === this.selectedBlockId);
    if (index === -1) index = blocks.length;
    index = (index - 1 + blocks.length) % blocks.length;

    this._selectBlock(blocks[index].dataset.id);
  }

  /**
   * Select a block
   */
  _selectBlock(blockId) {
    // Deselect previous
    if (this.selectedBlockId) {
      const prevBlock = this.container.querySelector(`[data-id="${this.selectedBlockId}"]`);
      if (prevBlock) {
        prevBlock.classList.remove('selected');
      }
    }

    // Select new
    this.selectedBlockId = blockId;
    const block = this.container.querySelector(`[data-id="${blockId}"]`);
    if (block) {
      block.classList.add('selected');
      block.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  /**
   * Get last output block
   */
  getLastOutputBlock() {
    const blocks = this.ptyManager.getBlocks();
    return [...blocks].reverse().find(b => b.type === 'output' || b.type === 'input');
  }

  /**
   * Render all blocks for active terminal
   */
  renderAllBlocks() {
    clearUI(this.container);
    const blocks = this.ptyManager.getBlocks();
    blocks.forEach(block => {
      const blockEl = createBlockElement(block);
      this._addCollapseSupport(blockEl, block);
      this.container.appendChild(blockEl);
    });
  }

  /**
   * Handle PTY events
   */
  _handlePTYEvent(event) {
    switch (event.type) {
      case 'block':
        const blockEl = createBlockElement(event.block);
        this._addCollapseSupport(blockEl, event.block);
        this.container.appendChild(blockEl);
        this.container.scrollTop = this.container.scrollHeight;
        break;
      case 'output':
        // Real-time output (optional: update last block)
        break;
      case 'exit':
        console.log(`[BlockManagerV2] Terminal ${event.terminalId} exited`);
        break;
    }
  }

  /**
   * Resize PTY
   */
  resize(cols, rows) {
    this.ptyManager.resize(cols, rows);
  }

  /**
   * Close active tab
   */
  closeActiveTab() {
    if (this.ptyManager.activeTab) {
      this.ptyManager.closeTerminal(this.ptyManager.activeTab);
      this.renderAllBlocks();
    }
  }

  /**
   * Cleanup
   */
  destroy() {
    this.ptyManager.destroy();
    this.undoStack = [];
    this.redoStack = [];
    this.collapsedBlocks.clear();
  }
}

module.exports = { BlockManagerV2 };
