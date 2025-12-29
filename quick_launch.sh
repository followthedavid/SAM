#!/usr/bin/env bash
# Quick launch with verbose logging and enter-heuristic blocks
export APP="$HOME/ReverseLab/Warp_Open/app/gui-electron"
cd "$APP"

# Extra logging from Electron + stack dumping
export ELECTRON_ENABLE_LOGGING=1
export ELECTRON_ENABLE_STACK_DUMPING=1

# Force Blocks on (enter heuristic) and open DevTools on start
export WARP_OPEN_ENABLE_BLOCKS=1
export WARP_OPEN_BLOCKS_MODE=enter

echo "🚀 Launching with enter-heuristic blocks + verbose logs"
echo "Environment: ELECTRON_ENABLE_LOGGING=1, WARP_OPEN_BLOCKS_MODE=enter"
echo "Test: type 'echo hello', 'pwd', 'ls' (press Enter each), click 💾 Flush"

# Run our helper launcher
./scripts/dev_enter_blocks.sh
