#!/bin/bash
# Setup Claude API key for SAM's teacher-student learning

echo "=== SAM Claude API Setup ==="
echo ""
echo "For SAM to learn from Claude API (overnight learning), you need an API key."
echo "Get one from: https://console.anthropic.com/settings/keys"
echo ""

read -p "Enter your Anthropic API key (or 'skip' to skip): " api_key

if [ "$api_key" = "skip" ]; then
    echo "Skipped. SAM will learn locally only."
    exit 0
fi

# Validate it looks like an API key
if [[ ! "$api_key" =~ ^sk-ant- ]]; then
    echo "Warning: Key doesn't look like an Anthropic key (should start with sk-ant-)"
    read -p "Continue anyway? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# Save to config
mkdir -p ~/.config/anthropic
echo "$api_key" > ~/.config/anthropic/key
chmod 600 ~/.config/anthropic/key

# Also add to shell config
SHELL_RC="$HOME/.zshrc"
if [ -f "$HOME/.bashrc" ] && [ ! -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if ! grep -q "ANTHROPIC_API_KEY" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Anthropic API key for SAM learning" >> "$SHELL_RC"
    echo "export ANTHROPIC_API_KEY=\"\$(cat ~/.config/anthropic/key 2>/dev/null)\"" >> "$SHELL_RC"
    echo "Added to $SHELL_RC"
fi

echo ""
echo "✅ API key saved!"
echo "   Location: ~/.config/anthropic/key"
echo ""
echo "To test, run:"
echo "   source $SHELL_RC"
echo "   python3 teacher_student.py learn"
