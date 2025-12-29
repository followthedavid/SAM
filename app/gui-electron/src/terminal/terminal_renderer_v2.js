/**
 * terminal_renderer_v2.js - Phase 5 V2 Terminal Renderer
 * 
 * Orchestrates the Terminal dock tab UI, multi-PTY subtabs,
 * block streaming, input handling, and AI slash commands.
 * 
 * Responsibilities:
 * - Render Terminal dock tab with subtabs per PTY session
 * - Handle session lifecycle (create/switch/close)
 * - Stream PTY output to BlockManagerV2
 * - Process slash commands (/ask, /fix, /explain)
 * - Keyboard shortcuts (Cmd+T, Cmd+W, Cmd+K, Cmd+Z)
 * - Undo/redo integration with Phase 4 journal
 * 
 * Requires:
 * - window.ptyBridge (from preload)
 * - window.BlockManagerV2 (loaded before this script)
 * - window.ai2 (Phase 4 AI API)
 * 
 * Initialization:
 * - Auto-initializes when Terminal dock tab content exists
 * - Creates first PTY session automatically
 */

console.log('[TerminalRendererV2] Loading...');

// Embedded BlockManagerV2 for Phase 5 V2 Terminal
class BlockManagerV2 {
  constructor(containerId) {
    this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    if (!this.container) {
      console.warn(`[BlockManagerV2] Container not found: ${containerId}`);
      return;
    }
    
    this.blocks = new Map();
    this.sessionBlocks = new Map();
    this.undoStack = [];
    this.pendingFlushes = new Map();
  }

  createBlock(type, content, meta = {}) {
    const id = `block-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
    const block = {
      id,
      sessionId: meta.sessionId || 'default',
      type,
      content,
      collapsed: false,
      meta: { timestamp: new Date().toISOString(), badge: type.toUpperCase(), ...meta }
    };
    
    this.blocks.set(id, block);
    if (!this.sessionBlocks.has(block.sessionId)) this.sessionBlocks.set(block.sessionId, []);
    this.sessionBlocks.get(block.sessionId).push(id);
    
    this._renderBlock(block);
    this.undoStack.push({ action: 'create', block });
    
    return block;
  }

  appendToBlock(blockId, chunk) {
    const block = this.blocks.get(blockId);
    if (!block) return;
    
    block.content += chunk;
    
    if (this.pendingFlushes.has(blockId)) cancelAnimationFrame(this.pendingFlushes.get(blockId));
    
    const rafHandle = requestAnimationFrame(() => {
      this._updateBlockContent(blockId);
      this.pendingFlushes.delete(blockId);
    });
    
    this.pendingFlushes.set(blockId, rafHandle);
  }

  toggleCollapse(blockId) {
    const block = this.blocks.get(blockId);
    if (!block) return;
    
    block.collapsed = !block.collapsed;
    const el = document.querySelector(`.block[data-id="${blockId}"]`);
    if (el) el.classList.toggle('collapsed', block.collapsed);
  }

  getLastBlockOfType(sessionId, type) {
    const blockIds = this.sessionBlocks.get(sessionId) || [];
    for (let i = blockIds.length - 1; i >= 0; i--) {
      const block = this.blocks.get(blockIds[i]);
      if (block && block.type === type) return block;
    }
    return null;
  }

  async runSlash(commandString, context = {}) {
    const parts = commandString.trim().split(' ');
    const command = parts[0];
    const args = parts.slice(1).join(' ');
    const sessionId = context.sessionId || 'default';
    
    const thinkingBlock = this.createBlock('ai', '🤔 Thinking...', { sessionId, prompt: commandString });
    
    try {
      let response;
      
      if (command === '/ask' && window.ai2 && window.ai2.chat) {
        // Use the correct format for ai2.chat - it expects messages array
        const result = await window.ai2.chat({ 
          messages: [{ role: 'user', content: args }],
          model: 'llama3.2:3b-instruct-q4_K_M',
          temperature: 0.1,
          max_tokens: 800
        });
        response = result.text || result.response || String(result);
      } else if (command === '/fix') {
        const errorBlock = this.getLastBlockOfType(sessionId, 'error') || this.getLastBlockOfType(sessionId, 'output');
        if (!errorBlock) {
          response = 'No previous error to fix';
        } else if (window.ai2 && window.ai2.chat) {
          const result = await window.ai2.chat({ 
            messages: [{ role: 'user', content: `Fix this error:\n${errorBlock.content.substring(0, 500)}` }],
            model: 'llama3.2:3b-instruct-q4_K_M',
            temperature: 0.1,
            max_tokens: 800
          });
          response = result.text || result.response || String(result);
        } else {
          response = 'AI not available';
        }
      } else if (command === '/explain') {
        const inputBlock = this.getLastBlockOfType(sessionId, 'input');
        if (!inputBlock) {
          response = 'No previous command to explain';
        } else if (window.ai2 && window.ai2.chat) {
          const result = await window.ai2.chat({ 
            messages: [{ role: 'user', content: `Explain this command:\n${inputBlock.content}` }],
            model: 'llama3.2:3b-instruct-q4_K_M',
            temperature: 0.1,
            max_tokens: 800
          });
          response = result.text || result.response || String(result);
        } else {
          response = 'AI not available';
        }
      } else {
        response = `Unknown command: ${command}`;
      }
      
      thinkingBlock.content = response;
      thinkingBlock.meta.badge = 'AI';
      this._updateBlockContent(thinkingBlock.id);
      
    } catch (err) {
      console.error('[BlockManagerV2] Slash command error:', err);
      thinkingBlock.content = `AI Error: ${err.message}`;
      thinkingBlock.type = 'error';
      this._updateBlockContent(thinkingBlock.id);
    }
  }

  async undo() {
    if (this.undoStack.length === 0) return { ok: false };
    
    const action = this.undoStack.pop();
    if (action.action === 'create') {
      const { block } = action;
      this.blocks.delete(block.id);
      const el = document.querySelector(`.block[data-id="${block.id}"]`);
      if (el) el.remove();
      
      const sessionBlockIds = this.sessionBlocks.get(block.sessionId) || [];
      const idx = sessionBlockIds.indexOf(block.id);
      if (idx >= 0) sessionBlockIds.splice(idx, 1);
    }
    
    if (window.ai2 && window.ai2.undoLast) {
      try { await window.ai2.undoLast(); } catch (err) { console.warn('Journal undo failed:', err); }
    }
    
    return { ok: true };
  }

  clearSession(sessionId) {
    const blockIds = this.sessionBlocks.get(sessionId) || [];
    blockIds.forEach(id => {
      this.blocks.delete(id);
      const el = document.querySelector(`.block[data-id="${id}"]`);
      if (el) el.remove();
    });
    this.sessionBlocks.set(sessionId, []);
  }

  restoreFromPersisted(sessionId) {
    // Placeholder - could load from localStorage
    console.log(`[BlockManagerV2] Restore for session ${sessionId} not yet implemented`);
  }

  _renderBlock(block) {
    const el = document.createElement('div');
    el.className = `block block-${block.type}`;
    el.dataset.id = block.id;
    
    const header = document.createElement('div');
    header.className = 'block-header';
    
    const badge = document.createElement('span');
    badge.className = 'block-badge';
    badge.textContent = block.meta.badge;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'block-timestamp';
    timestamp.textContent = this._formatTimestamp(block.meta.timestamp);
    
    const collapseBtn = document.createElement('button');
    collapseBtn.className = 'block-collapse-btn';
    collapseBtn.textContent = '▼';
    collapseBtn.onclick = () => this.toggleCollapse(block.id);
    
    header.append(badge, timestamp, collapseBtn);
    
    const content = document.createElement('pre');
    content.className = 'block-content';
    // Strip ANSI escape codes for cleaner display
    content.textContent = this._stripAnsi(block.content);
    
    const actions = document.createElement('div');
    actions.className = 'block-actions';
    
    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(block.content);
      copyBtn.textContent = '✓';
      setTimeout(() => copyBtn.textContent = 'Copy', 1500);
    };
    
    actions.appendChild(copyBtn);
    el.append(header, content, actions);
    
    this.container.appendChild(el);
    this.container.scrollTop = this.container.scrollHeight;
  }

  _updateBlockContent(blockId) {
    const block = this.blocks.get(blockId);
    if (!block) return;
    
    const el = document.querySelector(`.block[data-id="${blockId}"] .block-content`);
    if (el) {
      // Strip ANSI escape codes for cleaner display
      el.textContent = this._stripAnsi(block.content);
      if (this.container.scrollHeight - this.container.scrollTop - this.container.clientHeight < 100) {
        this.container.scrollTop = this.container.scrollHeight;
      }
    }
  }

  _formatTimestamp(isoString) {
    const date = new Date(isoString);
    const diffSec = Math.floor((new Date() - date) / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    return date.toLocaleTimeString();
  }
  
  /**
   * Strip ANSI escape codes from text
   */
  _stripAnsi(text) {
    // Remove ANSI escape sequences
    return text.replace(/\x1B\[[0-9;]*[A-Za-z]/g, '') // CSI sequences
               .replace(/\x1B\][0-9;]*[\x07\x1B\\]/g, '') // OSC sequences
               .replace(/\x1B[\(\)][AB012]/g, '') // Character set selection
               .replace(/[\x00-\x08\x0B-\x1F\x7F]/g, ''); // Control characters
  }
}

// Expose globally
if (typeof window !== 'undefined') {
  window.BlockManagerV2 = BlockManagerV2;
}

class TerminalRendererV2 {
  constructor() {
    this.sessions = new Map(); // sessionId -> { id, name, blockManager, outputBlockId }
    this.activeSessionId = null;
    this.initialized = false;
    
    // DOM elements (will be populated on init)
    this.tabsContainer = null;
    this.blocksContainer = null;
    this.inputBox = null;
    
    // Bind methods
    this._handlePTYData = this._handlePTYData.bind(this);
    this._handlePTYExit = this._handlePTYExit.bind(this);
  }

  /**
   * Initialize terminal renderer
   */
  async init() {
    if (this.initialized) {
      console.log('[TerminalRendererV2] Already initialized');
      return;
    }
    
    console.log('[TerminalRendererV2] Initializing...');
    
    // Check dependencies
    if (!window.bridge || !window.bridge.startPTY) {
      console.error('[TerminalRendererV2] window.bridge.startPTY not available');
      return;
    }
    
    if (!window.BlockManagerV2) {
      console.error('[TerminalRendererV2] window.BlockManagerV2 not available');
      return;
    }
    
    // Get DOM elements
    this.tabsContainer = document.getElementById('terminal-tabs');
    this.blocksContainer = document.getElementById('terminal-blocks');
    this.inputBox = document.getElementById('terminal-input');
    
    if (!this.tabsContainer || !this.blocksContainer || !this.inputBox) {
      console.error('[TerminalRendererV2] Required DOM elements not found');
      return;
    }
    
    // Setup PTY event listeners using existing bridge API
    window.bridge.onPTYData(this._handlePTYData);
    window.bridge.onPTYExit(this._handlePTYExit);
    
    // Setup input handling
    this._setupInputHandling();
    
    // Setup keyboard shortcuts
    this._setupKeyboardShortcuts();
    
    // Create initial session
    await this.createSession();
    
    this.initialized = true;
    console.log('[TerminalRendererV2] Initialized');
  }

  /**
   * Create a new PTY session
   */
  async createSession(opts = {}) {
    console.log('[TerminalRendererV2] createSession called with opts:', opts);
    
    try {
      // Get CWD from ai2 if available
      let cwd = opts.cwd;
      if (!cwd && window.ai2 && window.ai2.getCwd) {
        try {
          const cwdResult = await window.ai2.getCwd();
          cwd = cwdResult.cwd || process.env.HOME;
          console.log('[TerminalRendererV2] Got CWD from ai2:', cwd);
        } catch (err) {
          console.warn('[TerminalRendererV2] Failed to get CWD:', err);
        }
      }
      
      console.log('[TerminalRendererV2] Calling bridge.startPTY with:', { cols: opts.cols || 120, rows: opts.rows || 32, cwd });
      
      // Create PTY session using existing bridge API
      const result = await window.bridge.startPTY({ 
        cols: opts.cols || 120, 
        rows: opts.rows || 32, 
        cwd: cwd || undefined 
      });
      
      console.log('[TerminalRendererV2] startPTY returned:', result, 'type:', typeof result);
      
      if (!result) {
        console.error('[TerminalRendererV2] startPTY returned null/undefined');
        return null;
      }
      
      if (!result.id) {
        console.error('[TerminalRendererV2] startPTY result missing id property:', result);
        return null;
      }
      
      if (!result || !result.id) {
        console.error('[TerminalRendererV2] Failed to create session - invalid result:', result);
        return null;
      }
      
      const { id } = result;
      const name = `Tab ${this.sessions.size + 1}`;
      
      // Create block manager for this session
      const blockManager = new window.BlockManagerV2('terminal-blocks');
      
      // Store session
      const session = {
        id,
        name: name || `Tab ${this.sessions.size + 1}`,
        blockManager,
        outputBlockId: null, // Current streaming output block
        cwd: cwd || '~'
      };
      
      this.sessions.set(id, session);
      
      // Render tab
      this._renderTab(session);
      
      // Switch to new session
      this.switchSession(id);
      
      console.log(`[TerminalRendererV2] Created session ${id}`);
      
      return session;
    } catch (err) {
      console.error('[TerminalRendererV2] Create session error:', err);
      return null;
    }
  }

  /**
   * Switch to a different session
   */
  switchSession(sessionId) {
    if (!this.sessions.has(sessionId)) {
      console.warn(`[TerminalRendererV2] Session ${sessionId} not found`);
      return;
    }
    
    this.activeSessionId = sessionId;
    
    // Update tab UI
    document.querySelectorAll('.terminal-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.sessionId === sessionId);
    });
    
    // Clear blocks container and show blocks for this session
    this.blocksContainer.innerHTML = '';
    
    // Restore blocks from BlockManagerV2 for this session
    const session = this.sessions.get(sessionId);
    if (session && session.blockManager) {
      session.blockManager.container = this.blocksContainer;
      session.blockManager.restoreFromPersisted(sessionId);
    }
    
    // Focus input
    if (this.inputBox) {
      this.inputBox.focus();
    }
    
    console.log(`[TerminalRendererV2] Switched to session ${sessionId}`);
  }

  /**
   * Close a session
   */
  async closeSession(sessionId) {
    if (!this.sessions.has(sessionId)) return;
    
    try {
      // Kill PTY using existing bridge API
      window.bridge.killPTY(sessionId);
      
      // Remove session
      this.sessions.delete(sessionId);
      
      // Remove tab from UI
      const tab = document.querySelector(`.terminal-tab[data-session-id="${sessionId}"]`);
      if (tab) tab.remove();
      
      // Switch to another session if this was active
      if (this.activeSessionId === sessionId) {
        const remainingSessions = Array.from(this.sessions.keys());
        if (remainingSessions.length > 0) {
          this.switchSession(remainingSessions[0]);
        } else {
          // No sessions left - create a new one
          await this.createSession();
        }
      }
      
      console.log(`[TerminalRendererV2] Closed session ${sessionId}`);
    } catch (err) {
      console.error('[TerminalRendererV2] Close session error:', err);
    }
  }

  /**
   * Handle PTY data events
   */
  _handlePTYData(payload) {
    console.log('[TerminalRendererV2] _handlePTYData called with:', payload);
    
    // Handle both formats: { id, data } or just data
    const id = payload.id || payload.sessionId || this.activeSessionId;
    const data = payload.data || payload;
    
    console.log('[TerminalRendererV2] Processed - id:', id, 'data:', data.substring(0, 50));
    
    const session = this.sessions.get(id);
    if (!session) {
      console.warn('[TerminalRendererV2] No session found for id:', id);
      return;
    }
    
    // Only process if this is the active session
    if (this.activeSessionId !== id) {
      console.log('[TerminalRendererV2] Ignoring data for inactive session:', id);
      return;
    }
    
    console.log('[TerminalRendererV2] Creating/appending to output block');
    
    // Create or reuse output block
    if (!session.outputBlockId) {
      const block = session.blockManager.createBlock('output', data, { sessionId: id });
      session.outputBlockId = block.id;
      console.log('[TerminalRendererV2] Created new output block:', block.id);
    } else {
      session.blockManager.appendToBlock(session.outputBlockId, data);
      console.log('[TerminalRendererV2] Appended to existing block:', session.outputBlockId);
    }
  }

  /**
   * Handle PTY exit events
   */
  _handlePTYExit({ id, code, signal }) {
    console.log(`[TerminalRendererV2] PTY exited: ${id}, code: ${code}, signal: ${signal}`);
    
    const session = this.sessions.get(id);
    if (!session) return;
    
    // Mark last output block with exit code
    if (session.outputBlockId) {
      const block = session.blockManager.blocks.get(session.outputBlockId);
      if (block) {
        block.meta.exitCode = code;
        if (code !== 0) {
          block.type = 'error';
          block.meta.badge = 'ERROR';
        }
      }
    }
    
    // Close session UI
    this.closeSession(id);
  }

  /**
   * Setup input handling
   */
  _setupInputHandling() {
    this.inputBox.addEventListener('keydown', async (e) => {
      // Enter to send (unless Shift+Enter for newline)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        await this._handleInputSubmit();
      }
    });
  }

  /**
   * Handle input submit
   */
  async _handleInputSubmit() {
    const input = this.inputBox.value.trim();
    if (!input) return;
    
    if (!this.activeSessionId) {
      console.warn('[TerminalRendererV2] No active session');
      return;
    }
    
    const session = this.sessions.get(this.activeSessionId);
    if (!session) return;
    
    // Check for slash commands
    if (input.startsWith('/')) {
      await this._handleSlashCommand(input, session);
      this.inputBox.value = '';
      return;
    }
    
    // Create input block
    session.blockManager.createBlock('input', input, { sessionId: this.activeSessionId });
    
    // Reset output block (next output will create a new block)
    session.outputBlockId = null;
    
    // Send to PTY using existing bridge API
    try {
      window.bridge.sendInput(this.activeSessionId, input + '\n');
      this.inputBox.value = '';
    } catch (err) {
      console.error('[TerminalRendererV2] Write error:', err);
      session.blockManager.createBlock('error', `Failed to send command: ${err.message}`, {
        sessionId: this.activeSessionId
      });
    }
  }

  /**
   * Handle slash commands
   */
  async _handleSlashCommand(input, session) {
    console.log(`[TerminalRendererV2] Handling slash command: ${input}`);
    
    // Use BlockManagerV2's runSlash method
    try {
      await session.blockManager.runSlash(input, { sessionId: this.activeSessionId });
    } catch (err) {
      console.error('[TerminalRendererV2] Slash command error:', err);
      session.blockManager.createBlock('error', `Command error: ${err.message}`, {
        sessionId: this.activeSessionId
      });
    }
  }

  /**
   * Setup keyboard shortcuts
   */
  _setupKeyboardShortcuts() {
    document.addEventListener('keydown', async (e) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const cmdOrCtrl = isMac ? e.metaKey : e.ctrlKey;
      
      // Cmd+T: New tab
      if (cmdOrCtrl && e.key === 't' && !e.shiftKey) {
        e.preventDefault();
        await this.createSession();
      }
      
      // Cmd+W: Close tab
      if (cmdOrCtrl && e.key === 'w' && !e.shiftKey) {
        e.preventDefault();
        if (this.activeSessionId) {
          await this.closeSession(this.activeSessionId);
        }
      }
      
      // Cmd+K: Clear session
      if (cmdOrCtrl && e.key === 'k') {
        e.preventDefault();
        if (this.activeSessionId) {
          const session = this.sessions.get(this.activeSessionId);
          if (session) {
            session.blockManager.clearSession(this.activeSessionId);
          }
        }
      }
      
      // Cmd+Z: Undo
      if (cmdOrCtrl && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (this.activeSessionId) {
          const session = this.sessions.get(this.activeSessionId);
          if (session) {
            await session.blockManager.undo();
          }
        }
      }
      
      // Cmd+Shift+Z: Redo
      if (cmdOrCtrl && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        if (this.activeSessionId) {
          const session = this.sessions.get(this.activeSessionId);
          if (session) {
            session.blockManager.redo();
          }
        }
      }
      
      // Ctrl+Tab: Next tab
      if (e.ctrlKey && e.key === 'Tab' && !e.shiftKey) {
        e.preventDefault();
        this._switchToNextTab();
      }
      
      // Ctrl+Shift+Tab: Previous tab
      if (e.ctrlKey && e.key === 'Tab' && e.shiftKey) {
        e.preventDefault();
        this._switchToPreviousTab();
      }
    });
  }

  /**
   * Switch to next tab
   */
  _switchToNextTab() {
    const sessionIds = Array.from(this.sessions.keys());
    if (sessionIds.length <= 1) return;
    
    const currentIndex = sessionIds.indexOf(this.activeSessionId);
    const nextIndex = (currentIndex + 1) % sessionIds.length;
    this.switchSession(sessionIds[nextIndex]);
  }

  /**
   * Switch to previous tab
   */
  _switchToPreviousTab() {
    const sessionIds = Array.from(this.sessions.keys());
    if (sessionIds.length <= 1) return;
    
    const currentIndex = sessionIds.indexOf(this.activeSessionId);
    const prevIndex = (currentIndex - 1 + sessionIds.length) % sessionIds.length;
    this.switchSession(sessionIds[prevIndex]);
  }

  /**
   * Render a tab in the tab bar
   */
  _renderTab(session) {
    const tab = document.createElement('div');
    tab.className = 'terminal-tab';
    tab.dataset.sessionId = session.id;
    
    const title = document.createElement('span');
    title.className = 'terminal-tab-title';
    title.textContent = session.name;
    
    // Allow rename on double-click
    title.addEventListener('dblclick', () => {
      const newName = prompt('Rename tab:', session.name);
      if (newName) {
        session.name = newName;
        title.textContent = newName;
      }
    });
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'terminal-tab-close';
    closeBtn.textContent = '×';
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      this.closeSession(session.id);
    };
    
    tab.appendChild(title);
    tab.appendChild(closeBtn);
    
    tab.onclick = () => this.switchSession(session.id);
    
    // Insert before [+] button or append
    const newTabBtn = this.tabsContainer.querySelector('.terminal-new-tab-btn');
    if (newTabBtn) {
      this.tabsContainer.insertBefore(tab, newTabBtn);
    } else {
      this.tabsContainer.appendChild(tab);
      
      // Add [+] button if it doesn't exist
      const plusBtn = document.createElement('button');
      plusBtn.className = 'terminal-new-tab-btn';
      plusBtn.textContent = '+';
      plusBtn.onclick = () => this.createSession();
      this.tabsContainer.appendChild(plusBtn);
    }
  }
}

// Auto-initialize when DOM is ready and Terminal tab is visible
function autoInit() {
  // Check if Terminal dock tab exists
  const terminalContent = document.getElementById('ai-dock-terminal');
  if (!terminalContent) {
    console.log('[TerminalRendererV2] Terminal dock tab not found, skipping init');
    return;
  }
  
  // Check if required elements exist
  const tabsContainer = document.getElementById('terminal-tabs');
  const blocksContainer = document.getElementById('terminal-blocks');
  const inputBox = document.getElementById('terminal-input');
  
  if (!tabsContainer || !blocksContainer || !inputBox) {
    console.log('[TerminalRendererV2] Required DOM elements not found, skipping init');
    return;
  }
  
  // Initialize
  const renderer = new TerminalRendererV2();
  
  // Lazy init when Terminal tab becomes visible
  const observer = new MutationObserver(() => {
    const isVisible = terminalContent.style.display !== 'none';
    console.log('[TerminalRendererV2] MutationObserver - display:', terminalContent.style.display, 'initialized:', renderer.initialized);
    if (isVisible && !renderer.initialized) {
      console.log('[TerminalRendererV2] Terminal tab visible, initializing...');
      renderer.init();
      observer.disconnect();
    }
  });
  
  observer.observe(terminalContent, { attributes: true, attributeFilter: ['style'] });
  
  // Also try immediate init if already visible
  const initialDisplay = terminalContent.style.display;
  console.log('[TerminalRendererV2] Initial display style:', initialDisplay);
  if (initialDisplay !== 'none') {
    console.log('[TerminalRendererV2] Terminal tab already visible, initializing now');
    renderer.init();
  }
  
  // Expose to window for debugging and manual init
  window.__terminalRenderer = renderer;
  
  // Listen for clicks on Terminal tab button to force init
  setTimeout(() => {
    const terminalTabBtn = document.querySelector('.ai-dock-tab[data-tab="terminal"]');
    if (terminalTabBtn) {
      console.log('[TerminalRendererV2] Found Terminal tab button, adding click listener');
      terminalTabBtn.addEventListener('click', () => {
        console.log('[TerminalRendererV2] Terminal tab clicked');
        setTimeout(() => {
          if (!renderer.initialized) {
            console.log('[TerminalRendererV2] Force initializing after tab click');
            renderer.init();
          }
        }, 100);
      });
    } else {
      console.warn('[TerminalRendererV2] Terminal tab button not found');
    }
  }, 500);
}

// Run auto-init when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoInit);
} else {
  autoInit();
}

console.log('[TerminalRendererV2] Loaded');
