#!/usr/bin/env bash
set -euo pipefail
MAIN="$1"
MARK="// WARP_OPEN_INTERACTIVE_MARKER"
grep -q "$MARK" "$MAIN" && { echo "Already patched: $MAIN"; exit 0; }

awk -v mark="$MARK" '
BEGIN{inserted=0}
{
  print $0
  if (!inserted && $0 ~ /^$/) {
    print mark
    print "try {"
    print "  const { maybeRunInteractive } = require(\"./interactive_smoke\");"
    print "  if (maybeRunInteractive(require(\"electron\").app)) {"
    print "    module.exports = {}; return;"
    print "  }"
    print "} catch (e) { /* interactive smoke not fatal */ }"
    print mark
    inserted=1
  }
}
' "$MAIN" > "$MAIN.tmp"
mv "$MAIN.tmp" "$MAIN"
echo "Patched: $MAIN"