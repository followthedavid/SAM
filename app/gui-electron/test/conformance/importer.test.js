/* eslint-disable */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..', '..'); // app/gui-electron
const proj = path.resolve(root, '..', '..'); // Warp_Open

function mkTmpDir() {
  const d = path.join(process.env.TMPDIR || '/tmp', `warp_open_extract_${Date.now()}`);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

test('import_workflows.py normalizes and dedupes entries', () => {
  const extract = mkTmpDir();
  const outdir = mkTmpDir();
  const mined = [
    { name: 'One', command: 'echo 1', base_cwd: '/tmp/a', tags: ['t1'], source_path: 'a' },
    { name: 'One', command: 'echo 1', base_cwd: '/tmp/a', tags: ['t1'], source_path: 'a' },
    { title: 'Two', cmd: 'echo 2' }
  ];
  fs.writeFileSync(path.join(extract, 'mined_workflow.json'), JSON.stringify(mined, null, 2));
  const script = path.resolve(proj, 'importers', 'import_workflows.py');
  const env = Object.assign({}, process.env, {
    WARP_OPEN_EXTRACT_DIR: extract,
    WARP_OPEN_OUTDIR: outdir
  });
  const out = spawnSync('python3', [script], { encoding: 'utf8', env });
  if (out.status !== 0) {
    throw new Error(`importer failed: ${out.stderr || out.stdout}`);
  }
  const fp = path.join(outdir, 'workflows.json');
  assert.ok(fs.existsSync(fp), 'workflows.json missing');
  const arr = JSON.parse(fs.readFileSync(fp, 'utf8'));
  assert.ok(Array.isArray(arr));
  assert.ok(arr.length >= 2, 'expected at least 2 items');
  // deduped (name, command) should collapse duplicates
  const dups = arr.filter(x => x.name === 'One' && x.command === 'echo 1');
  assert.strictEqual(dups.length, 1, 'duplicate entries were not deduped');
});