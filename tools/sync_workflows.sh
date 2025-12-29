#!/usr/bin/env bash
set -euo pipefail
python3 "$HOME/ReverseLab/Warp_Open/importers/import_workflows.py"
if command -v jq >/dev/null 2>&1; then
  echo "Preview (first 20):"
  jq -r '.[] | (.name + "\t→\t" + .command)' "$HOME/.warp_open/workflows.json" | head -20 || true
else
  echo "Install jq for a nicer preview. Showing raw head:"
  head -40 "$HOME/.warp_open/workflows.json" || true
fi
