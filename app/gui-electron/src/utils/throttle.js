/**
 * Tiny debounce with maxWait (no external deps).
 * Usage: const d = debounce(fn, 150, { maxWait: 600 }); d();
 */
function debounce(fn, wait = 150, opts = {}) {
  let t = null, last = 0, maxWait = opts.maxWait || 0, mt = null;
  return function(...args){
    const now = Date.now();
    if (maxWait && !mt) {
      mt = setTimeout(() => { mt = null; last = 0; fn.apply(this, args); }, maxWait);
    }
    clearTimeout(t);
    t = setTimeout(() => {
      if (mt) { clearTimeout(mt); mt = null; }
      last = now; fn.apply(this, args);
    }, wait);
  };
}
module.exports = { debounce, debounceJson: debounce };
