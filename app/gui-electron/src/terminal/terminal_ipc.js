/**
 * terminal_ipc.js - IPC handlers for Phase 5 Terminal
 * Bridges renderer <-> BlockManager in main process
 */

const { ipcMain } = require('electron');
const { BlockManager } = require('./blockManager');

class TerminalIPC {
  constructor() {
    this.blockManagers = new Map(); // windowId -> BlockManager
  }

  /**
   * Initialize IPC handlers
   */
  setup() {
    // Create terminal tab
    ipcMain.handle('terminal:createTab', async (event, tabName, shell, cwd) => {
      const windowId = event.sender.id;
      let bm = this.blockManagers.get(windowId);
      
      if (!bm) {
        // Create BlockManager for this window
        // Note: container is null since we're in main process
        bm = new BlockManager(null, { 
          ai2: null // AI is handled in renderer
        });
        this.blockManagers.set(windowId, bm);
      }

      const tabId = bm.createTab(tabName, shell, cwd);
      
      // Send blocks to renderer
      bm.ptyManager.onOutput((outputEvent) => {
        if (outputEvent.type === 'block') {
          event.sender.send('terminal:block', outputEvent.block);
        }
      });

      return tabId;
    });

    // Run command
    ipcMain.handle('terminal:runCommand', async (event, cmd) => {
      const windowId = event.sender.id;
      const bm = this.blockManagers.get(windowId);
      
      if (!bm) {
        throw new Error('Terminal not initialized');
      }

      const block = await bm.runCommand(cmd);
      return block;
    });

    // Switch tab
    ipcMain.handle('terminal:switchTab', (event, tabId) => {
      const windowId = event.sender.id;
      const bm = this.blockManagers.get(windowId);
      
      if (!bm) {
        throw new Error('Terminal not initialized');
      }

      return bm.switchTab(tabId);
    });

    // Get tabs
    ipcMain.handle('terminal:getTabs', (event) => {
      const windowId = event.sender.id;
      const bm = this.blockManagers.get(windowId);
      
      if (!bm) {
        return [];
      }

      return bm.getTabs();
    });

    // Close tab
    ipcMain.handle('terminal:closeTab', (event, tabId) => {
      const windowId = event.sender.id;
      const bm = this.blockManagers.get(windowId);
      
      if (!bm) {
        throw new Error('Terminal not initialized');
      }

      bm.ptyManager.closeTerminal(tabId);
      return true;
    });

    // Resize
    ipcMain.handle('terminal:resize', (event, cols, rows) => {
      const windowId = event.sender.id;
      const bm = this.blockManagers.get(windowId);
      
      if (bm) {
        bm.resize(cols, rows);
      }
    });

    // Cleanup on window close
    ipcMain.on('terminal:destroy', (event) => {
      const windowId = event.sender.id;
      const bm = this.blockManagers.get(windowId);
      
      if (bm) {
        bm.destroy();
        this.blockManagers.delete(windowId);
      }
    });

    console.log('[TerminalIPC] Handlers registered');
  }

  /**
   * Cleanup all terminals
   */
  destroyAll() {
    for (const bm of this.blockManagers.values()) {
      bm.destroy();
    }
    this.blockManagers.clear();
  }
}

module.exports = { TerminalIPC };
