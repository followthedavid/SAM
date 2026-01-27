#!/bin/bash
# SAM Fine-tuning Setup for Apple Silicon

set -e

echo "=== SAM Fine-tuning Setup ==="

# Install MLX and MLX-LM
echo "Installing MLX (Apple Silicon ML framework)..."
pip3 install mlx mlx-lm

# Convert training data to MLX format
echo "Converting training data..."
python3 << 'EOF'
import json
from pathlib import Path

# Read combined data
with open('combined_training_data.jsonl', 'r') as f:
    data = [json.loads(line) for line in f]

# Convert to MLX chat format
mlx_data = []
for item in data:
    convs = item.get('conversations', [])
    if len(convs) >= 2:
        messages = []
        for c in convs:
            role = 'user' if c['from'] == 'human' else 'assistant'
            messages.append({'role': role, 'content': c['value']})
        mlx_data.append({'messages': messages})

# Split train/test (90/10)
split_idx = int(len(mlx_data) * 0.9)
train_data = mlx_data[:split_idx]
test_data = mlx_data[split_idx:]

# Save
Path('mlx_data').mkdir(exist_ok=True)
with open('mlx_data/train.jsonl', 'w') as f:
    for item in train_data:
        f.write(json.dumps(item) + '\n')

with open('mlx_data/test.jsonl', 'w') as f:
    for item in test_data:
        f.write(json.dumps(item) + '\n')

print(f"Created {len(train_data)} training examples, {len(test_data)} test examples")
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To fine-tune, run:"
echo "  ./run_finetune.sh"
echo ""
