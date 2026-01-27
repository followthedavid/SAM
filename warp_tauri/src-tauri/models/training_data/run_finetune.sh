#!/bin/bash
# SAM Fine-tuning with MLX

set -e

# Configuration
BASE_MODEL="mlx-community/dolphin-2.6-phi-2-4bit"  # 1.6GB uncensored base
OUTPUT_DIR="./sam-finetuned"
EPOCHS=3
BATCH_SIZE=1
LEARNING_RATE=1e-5
LORA_RANK=8

echo "=== SAM Fine-tuning ==="
echo "Base model: $BASE_MODEL"
echo "Training data: $(wc -l < mlx_data/train.jsonl) examples"
echo "Epochs: $EPOCHS"
echo ""

# Run fine-tuning with LoRA
python3 -m mlx_lm.lora \
    --model "$BASE_MODEL" \
    --train \
    --data ./mlx_data \
    --batch-size $BATCH_SIZE \
    --lora-layers 8 \
    --iters 500 \
    --learning-rate $LEARNING_RATE \
    --adapter-path "$OUTPUT_DIR/adapters"

echo ""
echo "=== Fine-tuning Complete ==="
echo "Adapter saved to: $OUTPUT_DIR/adapters"
echo ""
echo "To test the model:"
echo "  python3 -m mlx_lm.generate --model $BASE_MODEL --adapter-path $OUTPUT_DIR/adapters --prompt 'Hello'"
echo ""
echo "To fuse into single model:"
echo "  python3 -m mlx_lm.fuse --model $BASE_MODEL --adapter-path $OUTPUT_DIR/adapters --save-path $OUTPUT_DIR/fused"
echo ""
