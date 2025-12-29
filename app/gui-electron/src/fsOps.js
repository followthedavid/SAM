/**
 * fsOps - abstraction layer for file & script operations
 * - readFile, writeFile, applyUnifiedDiff (lightweight), runScript
 * - returns normalized results for the renderer
 */
const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');
const os = require('os');
const crypto = require('crypto');

function makeId(prefix='id') {
  if (crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.floor(Math.random()*1e6)}`;
}

async function readTextFile(filePath, { maxBytes=64*1024 } = {}) {
  const content = await fs.readFile(filePath, 'utf8');
  if (content.length > maxBytes) {
    return content.slice(0, maxBytes/2) + '\n...TRUNCATED...\n' + content.slice(-maxBytes/2);
  }
  return content;
}

async function writeTextFile(filePath, content, { ensureDir=true, mode } = {}) {
  if (ensureDir) {
    await fs.mkdir(path.dirname(filePath), { recursive: true });
  }
  await fs.writeFile(filePath, content, 'utf8');
  if (mode) await fs.chmod(filePath, mode);
  return { ok: true, path: filePath };
}

// Very small, safe unified-diff applier for simple cases (ctx: small project patches).
// NOTE: This is a best-effort tool — complex diffs should use an external patcher.
async function applyUnifiedDiff(filePath, unifiedDiff, { dryRun=false } = {}) {
  // Simple fallback: if diff starts with "+++ " and "@@ " we attempt to replace entire file if diff contains "===REPLACE===\n<content>"
  // Safer approach: if unifiedDiff contains a marker "===REPLACE===", treat payload after marker as replacement content.
  const REPLACE_MARKER = '===REPLACE===';
  if (unifiedDiff.includes(REPLACE_MARKER)) {
    const parts = unifiedDiff.split(REPLACE_MARKER);
    const newContent = parts[1];
    if (dryRun) return { applied: true, reason: 'dry-run: replace detected' };
    await writeTextFile(filePath, newContent);
    return { applied: true, file: filePath };
  }
  // otherwise, no-op (caller should fall back to manual patch).
  return { applied: false, reason: 'unsupported-diff-format' };
}

function runScript(command, args = [], opts = {}) {
  const cwd = opts.cwd || process.cwd();
  const timeoutMs = opts.timeoutMs || 60_000;
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd, shell: true, env: process.env });
    let stdout = '';
    let stderr = '';
    const to = setTimeout(() => {
      child.kill('SIGKILL');
    }, timeoutMs);

    child.stdout?.on('data', (d) => { stdout += d.toString(); });
    child.stderr?.on('data', (d) => { stderr += d.toString(); });
    child.on('error', (err) => {
      clearTimeout(to);
      resolve({ code: null, error: err.message, stdout, stderr });
    });
    child.on('close', (code, signal) => {
      clearTimeout(to);
      resolve({ code, signal, stdout, stderr });
    });
  });
}

module.exports = {
  readTextFile,
  writeTextFile,
  applyUnifiedDiff,
  runScript,
  makeId
};
