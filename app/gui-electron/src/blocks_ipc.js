// blocks_ipc.js — main-process helper to expose Blocks data/actions
const { ipcMain, dialog, shell } = require('electron');
const fs = require('fs');
const path = require('path');

function humanDuration(ms){ if(!Number.isFinite(ms)) return ''; const s=Math.round(ms/100)/10; return (s%1? s.toFixed(1): s.toFixed(0))+'s'; }

function wireBlocksIpc({ getBlocksSnapshot, writeToActivePty, getActiveCwd }) {
  ipcMain.handle('blocks:get-all', async (_e, limit=50) => {
    const all = getBlocksSnapshot();
    return all.slice(-limit).map(b => ({
      id:b.id, cmd:b.cmd, cwd:b.cwd, exit:b.exit, startedAt:b.startedAt, endedAt:b.endedAt,
      durationMs: (b.endedAt && b.startedAt) ? (b.endedAt - b.startedAt) : null
    }));
  });

  ipcMain.handle('blocks:rerun', async (_e, id, inNewTab=false) => {
    const b = getBlocksSnapshot().find(x => x.id===id);
    if(!b || !b.cmd) return {ok:false, error:'not_found'};
    // naive cwd respect
    const cwd = b.cwd || getActiveCwd();
    const cmd = (cwd ? `cd ${JSON.stringify(cwd)} && ` : '') + b.cmd + '\r';
    writeToActivePty(cmd, { inNewTab });
    return {ok:true};
  });

  ipcMain.handle('blocks:export', async (_e, id, format='text') => {
    const b = getBlocksSnapshot().find(x => x.id===id);
    if(!b) return {ok:false, error:'not_found'};
    const defName = `block-${b.id.replace(/[^a-z0-9_-]/gi,'') || 'unnamed'}.txt`;
    const res = await dialog.showSaveDialog({ defaultPath: defName });
    if(res.canceled || !res.filePath) return {ok:false, error:'canceled'};
    try {
      const lines = [];
      lines.push(`# cmd: ${b.cmd}`);
      if (b.cwd) lines.push(`# cwd: ${b.cwd}`);
      if (Number.isFinite(b.exit)) lines.push(`# exit: ${b.exit}`);
      if (b.startedAt) lines.push(`# started: ${new Date(b.startedAt).toISOString()}`);
      if (b.endedAt) lines.push(`# ended:   ${new Date(b.endedAt).toISOString()}  (${humanDuration(b.endedAt-b.startedAt)})`);
      lines.push('');
      if (b.output && b.output.length) lines.push(b.output.join(''));
      fs.writeFileSync(res.filePath, lines.join('\n'), 'utf8');
      shell.showItemInFolder(res.filePath);
      return {ok:true, path:res.filePath};
    } catch (e) {
      return {ok:false, error:String(e)};
    }
  });
}

module.exports = { wireBlocksIpc };