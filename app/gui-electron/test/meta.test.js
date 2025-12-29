/* eslint-disable */
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname ? path.resolve(__dirname, '..') : process.cwd();

function readJSON(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }

// package.json scripts sanity
test('package.json has expected scripts', () => {
  const pkg = readJSON(path.join(root, 'package.json'));
  assert.ok(pkg.scripts && typeof pkg.scripts === 'object');
  assert.ok(pkg.scripts['pack:mac'], 'pack:mac script missing');
  assert.ok(pkg.scripts['lint'], 'lint script missing');
  assert.ok(pkg.scripts['typecheck'], 'typecheck script missing');
});

// key source files exist
test('key source files exist', () => {
  assert.ok(fs.existsSync(path.join(root, 'src', 'main.js')), 'src/main.js missing');
  assert.ok(fs.existsSync(path.join(root, 'src', 'preload.js')), 'src/preload.js missing');
  assert.ok(fs.existsSync(path.join(root, 'src', 'renderer.js')), 'src/renderer.js missing');
});

// README contains usage section
test('README mentions build and usage', () => {
  const readme = fs.readFileSync(path.join(root, 'README.md'), 'utf8');
  assert.match(readme, /Usage/i, 'README missing Usage section');
  assert.match(readme, /pack:mac|Build for macOS/i, 'README missing macOS build info');
});
