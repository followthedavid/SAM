#!/bin/bash
# Quick Perpetual Ladder - Uses Ollama + Claude Code
# Usage: ./ladder_quick.sh [project_id]

set -e

REGISTRY="$HOME/.sam/projects/registry.json"

echo "═══════════════════════════════════════"
echo "    QUICK PERPETUAL LADDER"
echo "═══════════════════════════════════════"

# Get top priority active project
if [ -n "$1" ]; then
  PROJECT_ID="$1"
else
  PROJECT_ID=$(cat "$REGISTRY" | python3 -c "
import sys, json
reg = json.load(sys.stdin)
active = [p for p in reg['projects'] if p.get('status') == 'active']
if active:
    print(sorted(active, key=lambda x: x['priority'])[0]['id'])
")
fi

# Get project details
PROJECT_INFO=$(cat "$REGISTRY" | python3 -c "
import sys, json
reg = json.load(sys.stdin)
p = next((p for p in reg['projects'] if p['id'] == '$PROJECT_ID'), None)
if p:
    print(f\"{p['name']}|{p['path']}|{p.get('currentFocus', 'General maintenance')}\")
")

NAME=$(echo "$PROJECT_INFO" | cut -d'|' -f1)
PATH_DIR=$(echo "$PROJECT_INFO" | cut -d'|' -f2)
FOCUS=$(echo "$PROJECT_INFO" | cut -d'|' -f3)

echo ""
echo "📁 Project: $NAME"
echo "📍 Path: $PATH_DIR"
echo "🎯 Focus: $FOCUS"
echo ""

# Ask SAM for a task
echo "🧠 Asking SAM for a task..."
TASK=$(curl -s http://localhost:11434/api/generate -d "{
  \"model\": \"sam-coder:latest\",
  \"prompt\": \"For project '$NAME' with focus on '$FOCUS', suggest ONE specific coding task. Just the task, nothing else. Example: 'Add unit tests for the auth module'\",
  \"stream\": false,
  \"options\": {\"num_predict\": 100}
}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','Run tests'))")

echo "📝 Task: $TASK"
echo ""

# Run Claude Code
echo "🤖 Running Claude Code..."
echo "═══════════════════════════════════════"
cd "$PATH_DIR"
claude -p "$TASK"
echo "═══════════════════════════════════════"
echo "✅ Done!"
