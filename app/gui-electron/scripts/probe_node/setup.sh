#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Create an isolated mini-project so we don't touch Electron's node_modules
if [ ! -f package.json ]; then
  cat > package.json <<'JSON'
{
  "name": "node-pty-probe",
  "private": true,
  "type": "commonjs",
  "version": "0.0.0",
  "dependencies": {
    "node-pty": "^1.0.0"
  }
}
JSON
fi
# Install against *system Node* ABI
npm install --no-audit --no-fund