/**
 * blockManager.js - High-level block management and UI coordination
 * Integrates PTY, UI rendering, and AI/journal hooks
 */

const { PTYManager } = require('./ptyManager');
const { appendBlockToUI, clearUI, updateBlockUI } = require('./ui');

class BlockManager {
  constructor(container, options = {}) {
    this.container = container;
    this.ptyManager = new PTYManager();
    this.ai2 = options.ai2 || null; // window.ai2 bridge
    this.onBlockCreated = options.onBlockCreated || null;

    // Set up PTY output handler
    this.ptyManager.onOutput((event) => {
      this._handlePTYEvent(event);
    });
  }

  /**
   * Create a new terminal tab
   */
  createTab(tabName = 'Terminal', shell = null, cwd = null) {
    const tabId = this.ptyManager.createTerminal(tabName, shell, cwd);
    this.renderAllBlocks();
    return tabId;
  }

  /**
   * Switch to a different tab
   */
  switchTab(tabId) {
    if (this.ptyManager.switchTab(tabId)) {
      this.renderAllBlocks();
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
    // Log to journal via ai2
    if (this.ai2) {
      try {
        await this.ai2.logAction('command', `Run: ${cmd}`, { 
          command: cmd,
          terminal: this.ptyManager.activeTab 
        });
      } catch (err) {
        console.error('[BlockManager] Journal log failed:', err);
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
   * Add an AI response block
   */
  async addAIBlock(content, context = {}) {
    const block = {
      id: crypto.randomUUID(),
      type: 'ai',
      content,
      timestamp: new Date().toISOString(),
      terminalId: this.ptyManager.activeTab,
      status: 'complete',
      context,
    };

    // Add to PTY manager's block list
    const term = this.ptyManager.terminals[this.ptyManager.activeTab];
    if (term) {
      term.blocks.push(block);
    }

    // Render
    appendBlockToUI(this.container, block);

    // Log to journal
    if (this.ai2) {
      try {
        await this.ai2.logAction('ai_response', content.substring(0, 100), {
          fullContent: content,
          context,
        });
      } catch (err) {
        console.error('[BlockManager] AI journal log failed:', err);
      }
    }

    return block;
  }

  /**
   * Handle AI command (e.g., /fix, /explain)
   */
  async handleAICommand(command, args) {
    const lastBlock = this.getLastOutputBlock();
    
    switch (command) {
      case '/fix':
        return this._handleFixCommand(lastBlock, args);
      case '/explain':
        return this._handleExplainCommand(lastBlock, args);
      case '/ask':
        return this._handleAskCommand(args);
      default:
        return this.addAIBlock(`Unknown command: ${command}`);
    }
  }

  async _handleFixCommand(lastBlock, args) {
    if (!lastBlock) {
      return this.addAIBlock('No previous command to fix.');
    }

    const aiPrompt = `Fix this command:\nInput: ${lastBlock.content}\nError: ${args}`;
    
    if (this.ai2) {
      try {
        const response = await this.ai2.askAI(aiPrompt);
        return this.addAIBlock(response, { command: 'fix', original: lastBlock.content });
      } catch (err) {
        return this.addAIBlock(`AI error: ${err.message}`);
      }
    } else {
      return this.addAIBlock('[AI Placeholder] Would fix the command here.');
    }
  }

  async _handleExplainCommand(lastBlock, args) {
    if (!lastBlock) {
      return this.addAIBlock('No previous command to explain.');
    }

    const aiPrompt = `Explain this command:\n${lastBlock.content}`;
    
    if (this.ai2) {
      try {
        const response = await this.ai2.askAI(aiPrompt);
        return this.addAIBlock(response, { command: 'explain' });
      } catch (err) {
        return this.addAIBlock(`AI error: ${err.message}`);
      }
    } else {
      return this.addAIBlock('[AI Placeholder] Would explain the command here.');
    }
  }

  async _handleAskCommand(question) {
    if (this.ai2) {
      try {
        const response = await this.ai2.askAI(question);
        return this.addAIBlock(response, { command: 'ask' });
      } catch (err) {
        return this.addAIBlock(`AI error: ${err.message}`);
      }
    } else {
      return this.addAIBlock(`[AI Placeholder] You asked: ${question}`);
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
    blocks.forEach(block => appendBlockToUI(this.container, block));
  }

  /**
   * Handle PTY events
   */
  _handlePTYEvent(event) {
    switch (event.type) {
      case 'block':
        // New block created, render it
        appendBlockToUI(this.container, event.block);
        break;
      case 'output':
        // Real-time output (optional: update last block)
        break;
      case 'exit':
        console.log(`[BlockManager] Terminal ${event.terminalId} exited`);
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
  }
}

module.exports = { BlockManager };
