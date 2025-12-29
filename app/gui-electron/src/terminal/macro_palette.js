/**
 * Macro Palette UI - Command Macro System
 * 
 * Provides a command palette interface for inserting macros (command sequences)
 * Keyboard shortcut: Cmd+Shift+M
 */

class MacroPalette {
  constructor() {
    this.macros = [];
    this.isVisible = false;
    this.selectedIndex = 0;
    this.container = null;
    this.searchInput = null;
    this.macroList = null;
    this.filteredMacros = [];
    
    this.init();
    this.loadMacros();
    this.setupKeyboardShortcuts();
  }
  
  init() {
    // Create macro palette container
    this.container = document.createElement('div');
    this.container.id = 'macro-palette';
    this.container.className = 'macro-palette hidden';
    this.container.innerHTML = `
      <div class="macro-palette-overlay"></div>
      <div class="macro-palette-content">
        <div class="macro-palette-header">
          <input 
            type="text" 
            id="macro-search" 
            placeholder="Search macros... (Cmd+Shift+M to toggle)"
            autocomplete="off"
          />
          <button id="macro-close">✕</button>
        </div>
        <div class="macro-list" id="macro-list"></div>
        <div class="macro-palette-footer">
          <span class="macro-count">0 macros</span>
          <span class="macro-hint">↑↓ Navigate • Enter Select • Esc Close</span>
        </div>
      </div>
    `;
    
    document.body.appendChild(this.container);
    
    this.searchInput = document.getElementById('macro-search');
    this.macroList = document.getElementById('macro-list');
    
    // Event listeners
    this.searchInput.addEventListener('input', () => this.filterMacros());
    this.searchInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
    
    document.getElementById('macro-close').addEventListener('click', () => this.hide());
    this.container.querySelector('.macro-palette-overlay').addEventListener('click', () => this.hide());
  }
  
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Cmd+Shift+M to toggle
      if (e.metaKey && e.shiftKey && e.key === 'M') {
        e.preventDefault();
        this.toggle();
      }
      
      // Escape to close
      if (e.key === 'Escape' && this.isVisible) {
        e.preventDefault();
        this.hide();
      }
    });
  }
  
  async loadMacros() {
    try {
      // Try to load from blueprints
      const response = await fetch('/blueprints/macros.json');
      if (response.ok) {
        const data = await response.json();
        this.macros = data.macros || [];
      } else {
        // Use default macros
        this.macros = this.getDefaultMacros();
      }
    } catch (error) {
      console.warn('Failed to load macros, using defaults:', error);
      this.macros = this.getDefaultMacros();
    }
    
    this.filteredMacros = this.macros;
    this.renderMacroList();
  }
  
  getDefaultMacros() {
    return [
      {
        id: 'git-commit-workflow',
        name: 'Git Commit Workflow',
        description: 'Stage, commit, and push changes',
        commands: [
          'git add .',
          'git commit -m "{{commit_message}}"',
          'git push origin {{branch}}'
        ],
        category: 'git',
        icon: '🔀'
      },
      {
        id: 'npm-dev-workflow',
        name: 'NPM Dev Workflow',
        description: 'Install, build, and start dev server',
        commands: [
          'npm install',
          'npm run build',
          'npm run dev'
        ],
        category: 'npm',
        icon: '📦'
      },
      {
        id: 'docker-rebuild',
        name: 'Docker Rebuild',
        description: 'Stop, rebuild, and restart container',
        commands: [
          'docker-compose down',
          'docker-compose build --no-cache',
          'docker-compose up -d'
        ],
        category: 'docker',
        icon: '🐋'
      },
      {
        id: 'test-coverage',
        name: 'Test with Coverage',
        description: 'Run tests and generate coverage report',
        commands: [
          'npm test -- --coverage',
          'open coverage/lcov-report/index.html'
        ],
        category: 'test',
        icon: '🧪'
      },
      {
        id: 'clean-node-modules',
        name: 'Clean Node Modules',
        description: 'Remove and reinstall dependencies',
        commands: [
          'rm -rf node_modules',
          'rm package-lock.json',
          'npm install'
        ],
        category: 'npm',
        icon: '🧹'
      },
      {
        id: 'rust-release-build',
        name: 'Rust Release Build',
        description: 'Clean, test, and build for release',
        commands: [
          'cargo clean',
          'cargo test',
          'cargo build --release'
        ],
        category: 'rust',
        icon: '🦀'
      }
    ];
  }
  
  filterMacros() {
    const query = this.searchInput.value.toLowerCase();
    
    if (!query) {
      this.filteredMacros = this.macros;
    } else {
      this.filteredMacros = this.macros.filter(macro => 
        macro.name.toLowerCase().includes(query) ||
        macro.description.toLowerCase().includes(query) ||
        macro.category.toLowerCase().includes(query) ||
        macro.commands.some(cmd => cmd.toLowerCase().includes(query))
      );
    }
    
    this.selectedIndex = 0;
    this.renderMacroList();
  }
  
  renderMacroList() {
    this.macroList.innerHTML = '';
    
    if (this.filteredMacros.length === 0) {
      this.macroList.innerHTML = '<div class="macro-item-empty">No macros found</div>';
      return;
    }
    
    this.filteredMacros.forEach((macro, index) => {
      const item = document.createElement('div');
      item.className = `macro-item ${index === this.selectedIndex ? 'selected' : ''}`;
      item.dataset.index = index;
      
      item.innerHTML = `
        <div class="macro-icon">${macro.icon}</div>
        <div class="macro-info">
          <div class="macro-name">${this.escapeHtml(macro.name)}</div>
          <div class="macro-description">${this.escapeHtml(macro.description)}</div>
          <div class="macro-commands">
            ${macro.commands.map(cmd => `<code>${this.escapeHtml(cmd)}</code>`).join('<br>')}
          </div>
        </div>
        <div class="macro-category">${macro.category}</div>
      `;
      
      item.addEventListener('click', () => this.selectMacro(index));
      this.macroList.appendChild(item);
    });
    
    // Update count
    const count = document.querySelector('.macro-count');
    if (count) {
      count.textContent = `${this.filteredMacros.length} macro${this.filteredMacros.length !== 1 ? 's' : ''}`;
    }
  }
  
  handleKeyDown(e) {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        this.selectedIndex = (this.selectedIndex + 1) % this.filteredMacros.length;
        this.renderMacroList();
        this.scrollToSelected();
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        this.selectedIndex = (this.selectedIndex - 1 + this.filteredMacros.length) % this.filteredMacros.length;
        this.renderMacroList();
        this.scrollToSelected();
        break;
        
      case 'Enter':
        e.preventDefault();
        this.selectMacro(this.selectedIndex);
        break;
    }
  }
  
  scrollToSelected() {
    const selected = this.macroList.querySelector('.macro-item.selected');
    if (selected) {
      selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }
  
  selectMacro(index) {
    const macro = this.filteredMacros[index];
    if (!macro) return;
    
    // Check if commands have placeholders
    const placeholders = this.extractPlaceholders(macro.commands);
    
    if (placeholders.length > 0) {
      this.promptForPlaceholders(macro, placeholders);
    } else {
      this.insertMacro(macro);
    }
  }
  
  extractPlaceholders(commands) {
    const placeholders = new Set();
    const regex = /\{\{([^}]+)\}\}/g;
    
    commands.forEach(cmd => {
      let match;
      while ((match = regex.exec(cmd)) !== null) {
        placeholders.add(match[1]);
      }
    });
    
    return Array.from(placeholders);
  }
  
  promptForPlaceholders(macro, placeholders) {
    // Simple prompt implementation (could be enhanced with a modal)
    const values = {};
    
    for (const placeholder of placeholders) {
      const value = prompt(`Enter value for ${placeholder}:`);
      if (value === null) return; // Cancelled
      values[placeholder] = value;
    }
    
    // Replace placeholders
    const filledCommands = macro.commands.map(cmd => {
      let filled = cmd;
      for (const [key, value] of Object.entries(values)) {
        filled = filled.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value);
      }
      return filled;
    });
    
    this.insertMacro({ ...macro, commands: filledCommands });
  }
  
  insertMacro(macro) {
    // Insert commands into terminal
    const terminal = this.findActiveTerminal();
    
    if (terminal) {
      // Send commands one by one
      macro.commands.forEach((cmd, index) => {
        setTimeout(() => {
          terminal.sendCommand(cmd);
        }, index * 100); // Small delay between commands
      });
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(macro.commands.join('\n'));
      alert('Macro copied to clipboard!');
    }
    
    this.hide();
  }
  
  findActiveTerminal() {
    // Try to find terminal instance (adjust based on your implementation)
    if (window.terminal) return window.terminal;
    if (window.xterm) return window.xterm;
    
    // Try to find via global functions
    if (typeof sendCommandToTerminal === 'function') {
      return {
        sendCommand: (cmd) => sendCommandToTerminal(cmd)
      };
    }
    
    return null;
  }
  
  show() {
    this.isVisible = true;
    this.container.classList.remove('hidden');
    this.searchInput.focus();
    this.searchInput.select();
  }
  
  hide() {
    this.isVisible = false;
    this.container.classList.add('hidden');
    this.searchInput.value = '';
    this.filteredMacros = this.macros;
    this.selectedIndex = 0;
    this.renderMacroList();
  }
  
  toggle() {
    if (this.isVisible) {
      this.hide();
    } else {
      this.show();
    }
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.macroPalette = new MacroPalette();
  });
} else {
  window.macroPalette = new MacroPalette();
}

module.exports = MacroPalette;
