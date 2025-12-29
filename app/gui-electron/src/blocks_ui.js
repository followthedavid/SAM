/**
 * Blocks UI v1.5 - Renderer-side UI for displaying blocks with rerun/export actions
 */

class BlocksUI {
  constructor() {
    this.isVisible = false;
    this.blocksCache = [];
    this.init();
  }

  init() {
    this.createUI();
    this.bindEvents();
    this.loadBlocks();
    
    // Auto-refresh blocks every 5 seconds when visible
    setInterval(() => {
      if (this.isVisible) this.loadBlocks();
    }, 5000);
  }

  createUI() {
    // Create blocks panel container
    const panel = document.createElement('div');
    panel.id = 'blocks-panel';
    panel.innerHTML = `
      <div class="blocks-header">
        <h3>Command Blocks</h3>
        <button id="blocks-close">×</button>
      </div>
      <div class="blocks-content">
        <div id="blocks-list">Loading blocks...</div>
      </div>
    `;
    document.body.appendChild(panel);

    // Create toggle button
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'blocks-toggle';
    toggleBtn.innerHTML = '📋';
    toggleBtn.title = 'Toggle Blocks Panel (Cmd+B)';
    document.body.appendChild(toggleBtn);
  }

  bindEvents() {
    // Toggle button
    document.getElementById('blocks-toggle').addEventListener('click', () => {
      this.toggle();
    });

    // Close button
    document.getElementById('blocks-close').addEventListener('click', () => {
      this.hide();
    });

    // Keyboard shortcut: Cmd+B
    document.addEventListener('keydown', (e) => {
      if (e.metaKey && e.key === 'b') {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  async loadBlocks() {
    try {
      if (window.bridge && window.bridge.getBlocks) {
        this.blocksCache = await window.bridge.getBlocks();
        this.renderBlocks();
      }
    } catch (err) {
      console.warn('Failed to load blocks:', err);
    }
  }

  renderBlocks() {
    const listEl = document.getElementById('blocks-list');
    if (!listEl) return;

    if (!this.blocksCache.length) {
      listEl.innerHTML = '<div class="no-blocks">No command blocks yet</div>';
      return;
    }

    const html = this.blocksCache
      .slice(-20) // Show last 20 blocks
      .reverse() // Most recent first
      .map(block => this.renderBlock(block))
      .join('');

    listEl.innerHTML = html;

    // Bind action buttons
    listEl.querySelectorAll('.block-action').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const action = btn.dataset.action;
        const blockId = btn.dataset.blockId;
        this.handleBlockAction(action, blockId);
      });
    });
  }

  renderBlock(block) {
    const statusClass = block.exit === 0 ? 'success' : 
                       block.exit === null ? 'running' : 'error';
    const duration = block.endedAt && block.startedAt ? 
                    Math.round((new Date(block.endedAt) - new Date(block.startedAt)) / 1000) : '?';
    
    return `
      <div class="block-item ${statusClass}">
        <div class="block-header">
          <span class="block-cmd">${this.escapeHtml(block.cmd || '')}</span>
          <span class="block-status">${block.exit === null ? 'running' : `exit ${block.exit}`}</span>
        </div>
        <div class="block-meta">
          <span class="block-cwd">${this.escapeHtml(block.cwd || '')}</span>
          <span class="block-time">${duration}s</span>
        </div>
        <div class="block-actions">
          <button class="block-action" data-action="rerun" data-block-id="${block.id}">↻ Rerun</button>
          <button class="block-action" data-action="rerun-new" data-block-id="${block.id}">↗️ New Tab</button>
          <button class="block-action" data-action="export" data-block-id="${block.id}">💾 Export</button>
        </div>
      </div>
    `;
  }

  async handleBlockAction(action, blockId) {
    try {
      switch (action) {
        case 'rerun':
          await window.bridge.rerunBlock(blockId, false);
          break;
        case 'rerun-new':
          await window.bridge.rerunBlock(blockId, true);
          break;
        case 'export':
          await window.bridge.exportBlock(blockId, 'text');
          break;
      }
    } catch (err) {
      console.error(`Block action ${action} failed:`, err);
    }
  }

  toggle() {
    this.isVisible ? this.hide() : this.show();
  }

  show() {
    this.isVisible = true;
    document.getElementById('blocks-panel').classList.add('visible');
    this.loadBlocks();
  }

  hide() {
    this.isVisible = false;
    document.getElementById('blocks-panel').classList.remove('visible');
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new BlocksUI());
} else {
  new BlocksUI();
}