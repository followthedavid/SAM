/**
 * Replay Loader - Integrates automation pipeline with Phase 5 Terminal
 * 
 * Loads generated replay scripts from warp_auto/generated/ directory
 * and executes them in the terminal renderer.
 */

class ReplayLoader {
  constructor() {
    this.loaded = new Set();
    this.replayDir = null;
  }

  /**
   * Initialize replay loader
   */
  init() {
    console.log('[ReplayLoader] Initializing...');
    
    // Check for replay query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const replaySession = urlParams.get('replay');
    
    if (replaySession) {
      console.log(`[ReplayLoader] Auto-loading session: ${replaySession}`);
      this.loadReplay(replaySession);
    }
    
    // Expose API
    window.replayLoader = this;
  }

  /**
   * Load a specific replay session
   */
  async loadReplay(sessionId) {
    if (this.loaded.has(sessionId)) {
      console.warn(`[ReplayLoader] Session already loaded: ${sessionId}`);
      return;
    }

    try {
      // Try to load from generated directory
      const scriptPath = `../../generated/replay_${sessionId}.js`;
      
      // Dynamic import
      const replayModule = await import(scriptPath);
      
      console.log(`[ReplayLoader] Loaded replay: ${sessionId}`);
      this.loaded.add(sessionId);
      
      return replayModule;
    } catch (err) {
      console.error(`[ReplayLoader] Failed to load ${sessionId}:`, err);
      
      // Fallback: try to load as script tag
      this.loadReplayViaScript(sessionId);
    }
  }

  /**
   * Load replay via script tag (fallback)
   */
  loadReplayViaScript(sessionId) {
    const script = document.createElement('script');
    script.src = `../generated/replay_${sessionId}.js`;
    script.onload = () => {
      console.log(`[ReplayLoader] Loaded replay via script: ${sessionId}`);
      this.loaded.add(sessionId);
    };
    script.onerror = (err) => {
      console.error(`[ReplayLoader] Failed to load replay script: ${sessionId}`, err);
    };
    document.head.appendChild(script);
  }

  /**
   * Load all available replays
   */
  async loadAll() {
    console.log('[ReplayLoader] Loading all available replays...');
    
    // List of known sessions (could be dynamic)
    const sessions = ['sample_session_1', 'sample_session_2'];
    
    for (const session of sessions) {
      await this.loadReplay(session);
    }
    
    console.log(`[ReplayLoader] Loaded ${this.loaded.size} replays`);
  }

  /**
   * Get list of loaded replays
   */
  getLoaded() {
    return Array.from(this.loaded);
  }

  /**
   * Clear a replay
   */
  clearReplay(sessionId) {
    this.loaded.delete(sessionId);
    console.log(`[ReplayLoader] Cleared replay: ${sessionId}`);
  }
}

// Auto-initialize on load
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    const loader = new ReplayLoader();
    loader.init();
  });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ReplayLoader };
}
