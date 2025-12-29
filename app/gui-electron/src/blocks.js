/**
 * Blocks v1.1
 * - Command boundary detection from OSC 133 (B/C/D) with fallback to Enter key heuristic
 * - CWD tracking via OSC 7
 * - Emits JSONL events to a provided writer
 */
class BlockTracker {
  constructor({ sessionId, writeJsonl }) {
    this.sessionId = sessionId;
    this.write = writeJsonl;
    this.active = null; // {id, ts, cwd, cmdline}
    this.cwd = process.env.HOME || '';
    this._id = 0;
  }
  now() { return new Date().toISOString(); }
  nextId() { return `${this.sessionId}-blk-${++this._id}`; }

  onCwd(path) {
    this.cwd = path || this.cwd;
    this.write({ t: this.now(), type: 'cwd:update', cwd: this.cwd });
  }

  osc133(mark) {
    // A=prompt, B=cmd start, C=cmd end, D=output end
    if (mark === 'B') {
      // Start a block on command start
      if (!this.active) {
        this.active = { id: this.nextId(), ts: this.now(), cwd: this.cwd, cmdline: '' };
        this.write({ t: this.now(), type: 'block:start', id: this.active.id, cwd: this.cwd });
      }
    } else if (mark === 'C') {
      // Command "execution finished" (exit status unknown here)
      if (this.active) {
        this.write({ t: this.now(), type: 'block:exec:end', id: this.active.id });
      }
    } else if (mark === 'D') {
      // Output finished — close block
      if (this.active) {
        this.write({ t: this.now(), type: 'block:end', id: this.active.id });
        this.active = null;
      }
    }
  }

  // Fallback when no OSC 133 is available: Enter pressed begins a block, next prompt ends it.
  onEnterHeuristic(lineSnapshot) {
    if (!this.active) {
      this.active = { id: this.nextId(), ts: this.now(), cwd: this.cwd, cmdline: lineSnapshot || '' };
      this.write({ t: this.now(), type: 'block:start', id: this.active.id, cwd: this.cwd, heuristic: true, cmdline: lineSnapshot || '' });
    } else {
      // If a block is stuck, end it to avoid leaks
      this.write({ t: this.now(), type: 'block:end', id: this.active.id, heuristic: true });
      this.active = null;
    }
  }

  attachToPty(pty) {
    // noop here; pty wiring happens in main.js where we call tracker.osc133/cwd/update
  }
}

module.exports = { BlockTracker };