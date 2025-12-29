/**
 * ai2-main - main-process IPC handler glue for ai2 surface
 * Usage: require('./src/ai2-main')(app, ipcMain, { projectRoot })
 */
const path = require('path');
const os = require('os');

module.exports = function initAi2Main(app, ipcMain, opts = {}) {
  const projectRoot = opts.projectRoot || path.resolve(process.cwd());
  const CwdTracker = require('./cwdTracker');
  const fsOps = require('./fsOps');
  const journal = require('./journalStore');

  const tracker = new CwdTracker({ initial: projectRoot, projectRoot });

  // Expose CD
  ipcMain.handle('ai2:cd', async (evt, target) => {
    return tracker.cd(target);
  });
  ipcMain.handle('ai2:getCwd', () => {
    return { cwd: tracker.getCwd() };
  });

  // File ops
  ipcMain.handle('ai2:readFile', async (evt, filePath, opts = {}) => {
    const resolved = path.resolve(tracker.getCwd(), filePath);
    try {
      const text = await fsOps.readTextFile(resolved, opts);
      return { ok: true, path: resolved, text };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  });

  ipcMain.handle('ai2:writeFile', async (evt, filePath, content, opts = {}) => {
    const resolved = path.resolve(tracker.getCwd(), filePath);
    try {
      const res = await fsOps.writeTextFile(resolved, content, opts);
      const entry = await journal.logAction({ type: 'file:create', summary: `write ${resolved}`, payload: { path: resolved }});
      return { ok: true, path: resolved, journalId: entry.id };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  });

  ipcMain.handle('ai2:applyUnifiedDiff', async (evt, filePath, diff, opts = {}) => {
    const resolved = path.resolve(tracker.getCwd(), filePath);
    try {
      const res = await fsOps.applyUnifiedDiff(resolved, diff, opts);
      if (res.applied) {
        const entry = await journal.logAction({ type: 'file:patch', summary: `patch ${resolved}`, payload: { path: resolved, diffSummary: res.reason || 'applied' }});
        return Object.assign({ ok: true, path: resolved }, res, { journalId: entry.id });
      }
      return { ok: false, reason: res.reason || 'not-applied' };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  });

  ipcMain.handle('ai2:runScript', async (evt, command, args = [], opts = {}) => {
    try {
      const res = await fsOps.runScript(command, args, { cwd: tracker.getCwd(), timeoutMs: opts.timeoutMs });
      const entry = await journal.logAction({ type: 'script:run', summary: `${command} ${args.join(' ')}`, payload: { cwd: tracker.getCwd(), command, args, resultCode: res.code }});
      return Object.assign({ ok: true }, res, { journalId: entry.id });
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  });

  // Journal access
  ipcMain.handle('ai2:getJournal', async (evt, opts) => {
    const entries = await journal.getEntries(opts || {});
    return { ok: true, entries };
  });

  ipcMain.handle('ai2:undoLast', async () => {
    const res = await journal.undoLast();
    return res;
  });

  // getContextPack: lightweight pack (git status + open files placeholder)
  ipcMain.handle('ai2:getContextPack', async () => {
    // Minimal pack: cwd, recent journal entries, env
    const entries = await journal.getEntries({ offset: 0, limit: 10 });
    return {
      id: 'ctx-' + Date.now(),
      timestamp: new Date().toISOString(),
      cwd: tracker.getCwd(),
      recentActions: entries,
      env: { SHELL: process.env.SHELL || '' },
      projectRoot
    };
  });

  return { tracker };
};