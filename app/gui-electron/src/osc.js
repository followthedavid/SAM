/**
 * Minimal OSC parser for terminal streams.
 * Supports:
 *  - OSC 133;A (prompt start), 133;B (command start), 133;C (command end), 133;D (output end)
 *  - OSC 7;file://... (CWD)
 * Emits callbacks when sequences are detected.
 */
const BEL = '\u0007';
const ST  = '\u001b\\';
const OSC = '\u001b]';

function parseOscPayload(s) {
  // strip OSC introducer and terminator
  if (s.startsWith(OSC)) s = s.slice(2);
  s = s.replace(new RegExp(`${BEL}$|${ST}$`), '');
  return s;
}

function createOscDecoder({ onOsc133, onOsc7 }) {
  let buf = '';
  return {
    feed(chunk) {
      // Accumulate, scan for OSC patterns
      buf += chunk;
      for (;;) {
        const i = buf.indexOf(OSC);
        if (i < 0) { 
          // no OSC introducer; nothing to do
          return;
        }
        // copy anything before OSC through (ignored here)
        const tail = buf.slice(i);
        const jBel = tail.indexOf(BEL);
        const jSt  = tail.indexOf(ST);
        let endIdx = -1;
        let termLen = 1;
        if (jBel >= 0 && (jSt < 0 || jBel < jSt)) { endIdx = i + jBel + 1; termLen = 1; }
        else if (jSt >= 0) { endIdx = i + jSt + 2; termLen = 2; }
        if (endIdx < 0) {
          // need more data
          return;
        }
        const oscSeq = buf.slice(i, endIdx);
        // remove up to endIdx
        buf = buf.slice(endIdx);
        const payload = parseOscPayload(oscSeq);

        // Dispatch
        // Format examples:
        //   "133;A", "133;B", "133;C", "133;D"
        //   "7;file://host/path"
        if (payload.startsWith('133;')) {
          const marker = payload.slice(4).replace(/[^\w].*$/, '').toUpperCase();
          if (onOsc133) onOsc133(marker);
        } else if (payload.startsWith('7;')) {
          const rest = payload.slice(2);
          // Try to extract path after file://
          const idx = rest.indexOf('file://');
          if (idx >= 0) {
            const p = rest.slice(idx + 7);
            // strip host if present
            const firstSlash = p.indexOf('/');
            const path = firstSlash >= 0 ? p.slice(firstSlash) : p;
            if (onOsc7) onOsc7(path);
          }
        }
        // loop; there may be more
      }
    }
  };
}

module.exports = { createOscDecoder };