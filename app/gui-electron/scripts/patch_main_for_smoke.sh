#!/usr/bin/env bash
set -euo pipefail
MAIN="$1"
MARK="// WARP_OPEN_SMOKE_MARKER"
grep -q "$MARK" "$MAIN" && { echo "Already patched: $MAIN"; exit 0; }

# Insert right after the existing requires (first blank line after them).
awk -v mark="$MARK" '
BEGIN{inserted=0}
{
  print $0
  if (!inserted && $0 ~ /^$/) {
    print mark
    print "try {"
    print "  const { maybeRunSmoke } = require(\"./smoke\");"
    print "  if (maybeRunSmoke(require(\"electron\").app)) {"
    print "    // headless smoke handled; return early"
    print "    module.exports = {}; return;"
    print "  }"
    print "} catch (e) { /* smoke not fatal */ }"
    print mark
    inserted=1
  }
}
' "$MAIN" > "$MAIN.tmp"
mv "$MAIN.tmp" "$MAIN"
echo "Patched: $MAIN"
