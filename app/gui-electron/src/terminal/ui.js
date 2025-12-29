/**
 * ui.js - DOM manipulation for terminal blocks
 * Vanilla JS rendering without dependencies
 */

/**
 * Append a block to the terminal container
 */
function appendBlockToUI(container, block) {
  const el = createBlockElement(block);
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}

/**
 * Create a block DOM element
 */
function createBlockElement(block) {
  const el = document.createElement('div');
  el.className = `block block-${block.type} block-${block.status || 'complete'}`;
  el.dataset.id = block.id;
  el.dataset.type = block.type;

  // Content
  const pre = document.createElement('pre');
  pre.textContent = block.content;
  el.appendChild(pre);

  // Metadata bar
  const meta = document.createElement('div');
  meta.className = 'block-meta';
  
  const timestamp = document.createElement('span');
  timestamp.className = 'timestamp';
  timestamp.textContent = formatTimestamp(block.timestamp);
  meta.appendChild(timestamp);

  // Status indicator
  if (block.status === 'running') {
    const spinner = document.createElement('span');
    spinner.className = 'status-spinner';
    spinner.textContent = '⏳';
    meta.appendChild(spinner);
  }

  // Type badge
  const typeBadge = document.createElement('span');
  typeBadge.className = 'type-badge';
  typeBadge.textContent = block.type.toUpperCase();
  meta.appendChild(typeBadge);

  el.appendChild(meta);

  // Add actions for certain block types
  if (block.type === 'output' || block.type === 'error') {
    const actions = createBlockActions(block);
    el.appendChild(actions);
  }

  return el;
}

/**
 * Create action buttons for a block
 */
function createBlockActions(block) {
  const actions = document.createElement('div');
  actions.className = 'block-actions';

  // Copy button
  const copyBtn = document.createElement('button');
  copyBtn.className = 'block-action';
  copyBtn.textContent = '📋 Copy';
  copyBtn.onclick = () => {
    navigator.clipboard.writeText(block.content);
    copyBtn.textContent = '✓ Copied';
    setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
  };
  actions.appendChild(copyBtn);

  // Explain button
  const explainBtn = document.createElement('button');
  explainBtn.className = 'block-action';
  explainBtn.textContent = '💡 Explain';
  explainBtn.onclick = () => {
    const event = new CustomEvent('block-action', { 
      detail: { action: 'explain', blockId: block.id }
    });
    document.dispatchEvent(event);
  };
  actions.appendChild(explainBtn);

  // Fix button (for errors)
  if (block.type === 'error') {
    const fixBtn = document.createElement('button');
    fixBtn.className = 'block-action';
    fixBtn.textContent = '🔧 Fix';
    fixBtn.onclick = () => {
      const event = new CustomEvent('block-action', { 
        detail: { action: 'fix', blockId: block.id }
      });
      document.dispatchEvent(event);
    };
    actions.appendChild(fixBtn);
  }

  return actions;
}

/**
 * Clear all blocks from container
 */
function clearUI(container) {
  container.innerHTML = '';
}

/**
 * Update an existing block in the UI
 */
function updateBlockUI(container, blockId, updates) {
  const el = container.querySelector(`[data-id="${blockId}"]`);
  if (!el) return;

  if (updates.content !== undefined) {
    const pre = el.querySelector('pre');
    if (pre) pre.textContent = updates.content;
  }

  if (updates.status !== undefined) {
    el.className = el.className.replace(/block-\w+$/, `block-${updates.status}`);
    
    // Remove spinner if complete
    if (updates.status === 'complete') {
      const spinner = el.querySelector('.status-spinner');
      if (spinner) spinner.remove();
    }
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  
  return date.toLocaleTimeString();
}

/**
 * Create tab bar UI
 */
function createTabBar(tabs, onSwitch, onClose, onNew) {
  const tabBar = document.createElement('div');
  tabBar.className = 'tab-bar';

  tabs.forEach(tab => {
    const tabEl = document.createElement('div');
    tabEl.className = `tab ${tab.active ? 'tab-active' : ''}`;
    tabEl.dataset.id = tab.id;

    const nameSpan = document.createElement('span');
    nameSpan.textContent = tab.name;
    tabEl.appendChild(nameSpan);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'tab-close';
    closeBtn.textContent = '×';
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      onClose(tab.id);
    };
    tabEl.appendChild(closeBtn);

    tabEl.onclick = () => onSwitch(tab.id);
    tabBar.appendChild(tabEl);
  });

  // New tab button
  const newTabBtn = document.createElement('button');
  newTabBtn.className = 'tab-new';
  newTabBtn.textContent = '+';
  newTabBtn.onclick = onNew;
  tabBar.appendChild(newTabBtn);

  return tabBar;
}

module.exports = {
  appendBlockToUI,
  createBlockElement,
  clearUI,
  updateBlockUI,
  createTabBar,
  formatTimestamp,
};
