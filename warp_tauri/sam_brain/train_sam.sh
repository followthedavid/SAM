#!/bin/bash
# SAM MLX LoRA Training Script
# Optimized for 8GB Mac Mini M2

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
TRAINING_DIR="/Volumes/David External/sam_training"
MODEL_DIR="/Volumes/David External/sam_models"
ADAPTER_DIR="$MODEL_DIR/adapters"

# Model selection (4-bit quantized for 8GB RAM)
BASE_MODEL="mlx-community/Qwen2.5-3B-Instruct-4bit"
# Alternative: "mlx-community/Llama-3.2-3B-Instruct-4bit"

# Training parameters (conservative for 8GB)
BATCH_SIZE=1
LORA_LAYERS=8
LORA_RANK=8
LEARNING_RATE=1e-4
ITERATIONS=1000

# ============================================================================
# FUNCTIONS
# ============================================================================

check_data() {
    echo "Checking training data..."

    if [ ! -f "$TRAINING_DIR/sam_training_train.jsonl" ]; then
        echo "ERROR: Training data not found at $TRAINING_DIR/sam_training_train.jsonl"
        echo "Run: python build_training_data.py build"
        exit 1
    fi

    TRAIN_COUNT=$(wc -l < "$TRAINING_DIR/sam_training_train.jsonl")
    VAL_COUNT=$(wc -l < "$TRAINING_DIR/sam_training_val.jsonl")

    echo "  Training examples: $TRAIN_COUNT"
    echo "  Validation examples: $VAL_COUNT"
}

check_mlx() {
    echo "Checking MLX installation..."

    if ! python3 -c "import mlx_lm" 2>/dev/null; then
        echo "Installing mlx-lm..."
        pip3 install mlx-lm
    fi

    echo "  MLX ready"
}

prepare_data() {
    echo "Preparing training data..."

    # Combine personality examples with main training data
    COMBINED="$TRAINING_DIR/combined_train.jsonl"

    cat "$TRAINING_DIR/sam_training_train.jsonl" > "$COMBINED"

    if [ -f "$TRAINING_DIR/personality_examples.jsonl" ]; then
        # Add personality examples multiple times for emphasis
        for i in {1..5}; do
            cat "$TRAINING_DIR/personality_examples.jsonl" >> "$COMBINED"
        done
        echo "  Added personality examples (5x weight)"
    fi

    TOTAL=$(wc -l < "$COMBINED")
    echo "  Total training examples: $TOTAL"
}

train_lora() {
    echo ""
    echo "=============================================="
    echo "  Starting MLX LoRA Training"
    echo "=============================================="
    echo ""
    echo "Model: $BASE_MODEL"
    echo "Adapter output: $ADAPTER_DIR/sam_lora"
    echo "Batch size: $BATCH_SIZE"
    echo "LoRA layers: $LORA_LAYERS"
    echo "LoRA rank: $LORA_RANK"
    echo "Iterations: $ITERATIONS"
    echo ""

    mkdir -p "$ADAPTER_DIR"

    # MLX LoRA training command
    python3 -m mlx_lm.lora \
        --model "$BASE_MODEL" \
        --train \
        --data "$TRAINING_DIR" \
        --batch-size $BATCH_SIZE \
        --lora-layers $LORA_LAYERS \
        --lora-rank $LORA_RANK \
        --learning-rate $LEARNING_RATE \
        --iters $ITERATIONS \
        --adapter-path "$ADAPTER_DIR/sam_lora" \
        --save-every 100 \
        2>&1 | tee "$MODEL_DIR/training.log"

    echo ""
    echo "=============================================="
    echo "  Training Complete!"
    echo "=============================================="
    echo ""
    echo "Adapter saved to: $ADAPTER_DIR/sam_lora"
    echo "Training log: $MODEL_DIR/training.log"
}

test_model() {
    echo ""
    echo "Testing trained model..."
    echo ""

    python3 -m mlx_lm.generate \
        --model "$BASE_MODEL" \
        --adapter-path "$ADAPTER_DIR/sam_lora" \
        --prompt "Hello, who are you?" \
        --max-tokens 100
}

# ============================================================================
# MAIN
# ============================================================================

case "${1:-train}" in
    check)
        check_data
        check_mlx
        ;;
    prepare)
        prepare_data
        ;;
    train)
        check_data
        check_mlx
        prepare_data
        train_lora
        ;;
    test)
        test_model
        ;;
    all)
        check_data
        check_mlx
        prepare_data
        train_lora
        test_model
        ;;
    *)
        echo "SAM MLX Training Script"
        echo ""
        echo "Usage: ./train_sam.sh [command]"
        echo ""
        echo "Commands:"
        echo "  check   - Check data and dependencies"
        echo "  prepare - Prepare combined training data"
        echo "  train   - Run LoRA training (default)"
        echo "  test    - Test the trained model"
        echo "  all     - Run everything"
        ;;
esac
