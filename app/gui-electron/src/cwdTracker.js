/**
 * cwdTracker - lightweight directory context tracker
 * - Keeps a current working directory per "session"
 * - Enforces simple sandboxing: optionally restrict cd to a project root
 */
const path = require('path');
const fs = require('fs').promises;
const os = require('os');

class CwdTracker {
  constructor({ initial = process.cwd(), projectRoot = null } = {}) {
    this._cwd = path.resolve(initial);
    this.projectRoot = projectRoot ? path.resolve(projectRoot) : null;
  }

  getCwd() { return this._cwd; }

  // Try to change directory; only succeed if path exists and (if projectRoot set) is inside projectRoot
  async cd(targetPath) {
    const resolved = path.resolve(this._cwd, targetPath);
    // ensure exists and is a directory
    try {
      const st = await fs.stat(resolved);
      if (!st.isDirectory()) throw new Error('Not a directory');
      if (this.projectRoot && !resolved.startsWith(this.projectRoot)) {
        throw new Error('cd outside project root denied');
      }
      this._cwd = resolved;
      return { ok: true, cwd: this._cwd };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }
}

module.exports = CwdTracker;
