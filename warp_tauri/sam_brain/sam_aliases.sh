# SAM - Smart Assistant Manager aliases
# Add to ~/.zshrc: source ~/ReverseLab/SAM/warp_tauri/sam_brain/sam_aliases.sh

export SAM_HOME="$HOME/ReverseLab/SAM/warp_tauri/sam_brain"
export SAM_PYTHON="$SAM_HOME/venv/bin/python3"
export PATH="$SAM_HOME:$PATH"

# Main SAM command (uses venv for brain modules)
alias sam="$SAM_PYTHON $SAM_HOME/sam_enhanced.py"

# Project management
alias sam-projects="$SAM_PYTHON $SAM_HOME/project_manager.py"
alias sam-scan="$SAM_PYTHON $SAM_HOME/project_scanner.py"

# Watch mode
alias sam-watch="$SAM_PYTHON $SAM_HOME/sam_watch.py"

# Agent mode
alias sam-agent="$SAM_PYTHON $SAM_HOME/sam_agent.py"

# Brain modules
alias sam-brain="$SAM_PYTHON $SAM_HOME/sam_enhanced.py --brain"
alias sam-memory="$SAM_PYTHON $SAM_HOME/semantic_memory.py"
alias sam-multi="$SAM_PYTHON $SAM_HOME/multi_agent.py"
alias sam-ssot="$SAM_PYTHON $SAM_HOME/ssot_sync.py"
alias sam-fav="$SAM_PYTHON $SAM_HOME/project_favorites.py"
alias sam-voice="$SAM_PYTHON $SAM_HOME/voice_bridge.py"
alias sam-train="$SAM_PYTHON $SAM_HOME/training_pipeline.py"

# Quick shortcuts
alias s="sam"
alias sp="sam --projects"
alias sb="sam --brain"
alias ss="sam-projects search"
alias sl="sam list files"
alias sg="sam git status"

# Functions
sam-cd() {
    # CD into a project by name
    local project_path=$(python3 -c "
import json
from pathlib import Path
data = json.load(open(Path.home() / 'ReverseLab/SAM/warp_tauri/sam_brain/projects.json'))
for p in data.get('projects', []):
    if '$1'.lower() in p['name'].lower():
        print(p['path'])
        break
")
    if [ -n "$project_path" ]; then
        cd "$project_path"
        echo "Changed to: $project_path"
    else
        echo "Project not found: $1"
    fi
}

echo "SAM aliases loaded. Type 'sam' to start."
