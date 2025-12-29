const assert = require('assert');
const { test } = require('node:test');
const { createOscDecoder } = require('../../src/osc');

test('osc 133 markers and osc 7 cwd', () => {
  const seen = { marks: [], cwd: [] };
  const dec = createOscDecoder({
    onOsc133: m => seen.marks.push(m),
    onOsc7: p => seen.cwd.push(p)
  });
  // Compose sequences with mix of BEL/ST terminators
  const seqs = [
    '\x1b]133;A\x07',
    '\x1b]133;B\x1b\\',
    '\x1b]133;C\x07',
    '\x1b]133;D\x1b\\',
    '\x1b]7;file://host/Users/test/project\x07'
  ];
  dec.feed(seqs.join(''));
  assert.deepStrictEqual(seen.marks, ['A','B','C','D']);
  assert.ok(seen.cwd[0].endsWith('/Users/test/project'));
});