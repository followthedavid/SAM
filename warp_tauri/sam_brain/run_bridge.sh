#!/bin/bash
# Run the ChatGPT/Claude browser bridge using Playwright
source ~/.local/pipx/venvs/playwright/bin/activate
python3 /Users/davidquinton/ReverseLab/SAM/warp_tauri/chatgpt_bridge.py "$@"
