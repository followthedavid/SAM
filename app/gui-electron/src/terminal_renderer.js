/**
 * terminal_renderer.js - Phase 5 Terminal Renderer
 * Integrates BlockManager with window.ai2 API
 */

// Note: BlockManager is main-process only (uses node-pty)
// This renderer communicates via IPC

console.log('[Phase 5] Terminal renderer starting...');

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', init);

let blockManagerReady = false;
let currentTabId = null;

async function init() {
  console.log('[Phase 5] Initializing terminal UI...');

  // Get DOM elements
  const container = document.getElementById('terminalContainer');
  const tabBarContainer = document.getElementById('tabBarContainer');
  const cmdInput = document.getElementById('cmdInput');
  const runBtn = document.getElementById('runBtn');
  const statusBadge = document.getElementById('terminalStatus');
  const cwdDisplay = document.getElementById('cwdDisplay');

  // Check for window.ai2 (from preload)
  if (!window.ai2) {
    console.warn('[Phase 5] window.ai2 not available - AI features disabled');
    statusBadge.textContent = 'No AI';
    statusBadge.style.background = 'rgba(247, 118, 142, 0.12)';
    statusBadge.style.color = '#f7768e';
  } else {
    console.log('[Phase 5] window.ai2 detected');
    statusBadge.textContent = 'AI Ready';
  }

  // Request terminal initialization from main process
  if (window.terminalBridge) {
    try {
      currentTabId = await window.terminalBridge.createTab('Main');
      blockManagerReady = true;
      statusBadge.textContent = 'Ready';
      console.log('[Phase 5] Terminal initialized:', currentTabId);
      
      // Update CWD
      if (window.ai2) {
        const context = await window.ai2.getContextPack();
        if (context.cwd) {
          cwdDisplay.textContent = context.cwd;
        }
      }
    } catch (err) {
      console.error('[Phase 5] Failed to initialize terminal:', err);
      statusBadge.textContent = 'Error';
      statusBadge.style.background = 'rgba(247, 118, 142, 0.12)';
      statusBadge.style.color = '#f7768e';
    }
  } else {
    console.warn('[Phase 5] window.terminalBridge not available - using placeholder mode');
    // Create placeholder tab bar
    createPlaceholderTabBar(tabBarContainer);
    blockManagerReady = false;
  }

  // Handle command input
  runBtn.addEventListener('click', () => handleCommand(cmdInput.value));
  
  cmdInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCommand(cmdInput.value);
    }
  });

  // Handle block actions from UI
  document.addEventListener('block-action', async (e) => {
    const { action, blockId } = e.detail;
    console.log(`[Phase 5] Block action: ${action} on ${blockId}`);
    
    if (action === 'explain' || action === 'fix') {
      await handleAICommand(`/${action}`, blockId);
    }
  });

  console.log('[Phase 5] Terminal UI ready');
}

async function handleCommand(input) {
  if (!input.trim()) return;

  const cmdInput = document.getElementById('cmdInput');
  const container = document.getElementById('terminalContainer');

  // Check for AI slash commands
  if (input.startsWith('/')) {
    const parts = input.split(' ');
    const command = parts[0];
    const args = parts.slice(1).join(' ');
    
    await handleAICommand(command, args);
    cmdInput.value = '';
    return;
  }

  // Regular command
  if (blockManagerReady && window.terminalBridge) {
    try {
      const block = await window.terminalBridge.runCommand(input);
      console.log('[Phase 5] Command sent:', block);
      cmdInput.value = '';
    } catch (err) {
      console.error('[Phase 5] Command failed:', err);
      addErrorBlock(container, `Failed to run command: ${err.message}`);
    }
  } else {
    // Placeholder mode
    addPlaceholderBlock(container, 'input', input);
    await simulatePlaceholderOutput(container, input);
    cmdInput.value = '';
  }
}

async function handleAICommand(command, args) {
  const container = document.getElementById('terminalContainer');
  
  console.log(`[Phase 5] AI command: ${command} ${args}`);

  if (!window.ai2) {
    addPlaceholderBlock(container, 'ai', '[AI not available - window.ai2 missing]');
    return;
  }

  // Show AI is thinking
  const thinkingBlock = addPlaceholderBlock(container, 'ai', '🤔 Thinking...');
  thinkingBlock.classList.add('block-running');

  try {
    let response;
    
    switch (command) {
      case '/ask':
        response = await window.ai2.askAI(args);
        break;
        
      case '/explain':
        const lastBlock = getLastCommandBlock(container);
        if (!lastBlock) {
          response = 'No previous command to explain.';
        } else {
          response = await window.ai2.askAI(`Explain this command:\n${lastBlock.textContent}`);
        }
        break;
        
      case '/fix':
        const errorBlock = getLastCommandBlock(container);
        if (!errorBlock) {
          response = 'No previous command to fix.';
        } else {
          response = await window.ai2.askAI(`Fix this command:\n${errorBlock.textContent}\nError: ${args}`);
        }
        break;
        
      default:
        response = `Unknown AI command: ${command}`;
    }

    // Replace thinking block with actual response
    thinkingBlock.classList.remove('block-running');
    const pre = thinkingBlock.querySelector('pre');
    if (pre) {
      pre.textContent = response;
    }

  } catch (err) {
    console.error('[Phase 5] AI command error:', err);
    const pre = thinkingBlock.querySelector('pre');
    if (pre) {
      pre.textContent = `AI Error: ${err.message}`;
    }
    thinkingBlock.classList.remove('block-running');
    thinkingBlock.classList.add('block-error');
  }
}

function getLastCommandBlock(container) {
  const blocks = container.querySelectorAll('.block-input, .block-output');
  return blocks[blocks.length - 1]?.querySelector('pre');
}

// Placeholder functions for when node-pty isn't available
function createPlaceholderTabBar(container) {
  const tabBar = document.createElement('div');
  tabBar.className = 'tab-bar';
  
  const tab = document.createElement('div');
  tab.className = 'tab tab-active';
  tab.innerHTML = '<span>Main (Placeholder)</span>';
  
  tabBar.appendChild(tab);
  container.appendChild(tabBar);
}

function addPlaceholderBlock(container, type, content) {
  const block = document.createElement('div');
  block.className = `block block-${type}`;
  block.dataset.id = crypto.randomUUID();
  
  const pre = document.createElement('pre');
  pre.textContent = content;
  block.appendChild(pre);
  
  const meta = document.createElement('div');
  meta.className = 'block-meta';
  
  const timestamp = document.createElement('span');
  timestamp.className = 'timestamp';
  timestamp.textContent = formatTimestamp(new Date().toISOString());
  meta.appendChild(timestamp);
  
  const typeBadge = document.createElement('span');
  typeBadge.className = 'type-badge';
  typeBadge.textContent = type.toUpperCase();
  meta.appendChild(typeBadge);
  
  block.appendChild(meta);
  
  container.appendChild(block);
  container.scrollTop = container.scrollHeight;
  
  return block;
}

async function simulatePlaceholderOutput(container, input) {
  // Simulate command execution
  await new Promise(resolve => setTimeout(resolve, 500));
  
  let output = '';
  if (input.startsWith('ls')) {
    output = 'src/\nREADME.md\npackage.json\nnode_modules/';
  } else if (input.startsWith('pwd')) {
    output = '/Users/davidquinton/ReverseLab/Warp_Open';
  } else if (input.startsWith('echo')) {
    output = input.substring(5);
  } else {
    output = `[Placeholder] Would execute: ${input}`;
  }
  
  addPlaceholderBlock(container, 'output', output);
}

function addErrorBlock(container, message) {
  addPlaceholderBlock(container, 'error', message);
}

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

console.log('[Phase 5] Terminal renderer loaded');
