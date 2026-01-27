#!/bin/bash
# Convert fine-tuned MLX model to Ollama format

set -e

FUSED_MODEL="./sam-finetuned/fused"
OUTPUT_NAME="sam-custom"

echo "=== Converting to Ollama ==="

# First, fuse the adapter if not already done
if [ ! -d "$FUSED_MODEL" ]; then
    echo "Fusing adapter into base model..."
    python3 -m mlx_lm.fuse \
        --model "mlx-community/dolphin-2.6-phi-2-4bit" \
        --adapter-path "./sam-finetuned/adapters" \
        --save-path "$FUSED_MODEL"
fi

# Convert to GGUF format
echo "Converting to GGUF..."
python3 << 'EOF'
# Note: This requires llama.cpp's convert script
# For now, we'll create an Ollama Modelfile that uses the MLX model directly
# Full GGUF conversion requires additional tooling

print("""
To complete conversion to Ollama:

Option 1 - Use with MLX directly:
  python3 -m mlx_lm.generate --model ./sam-finetuned/fused --prompt "Hello"

Option 2 - Full Ollama conversion:
  1. Install llama.cpp: brew install llama.cpp
  2. Convert: python3 llama.cpp/convert_hf_to_gguf.py ./sam-finetuned/fused --outfile sam-custom.gguf
  3. Quantize: llama-quantize sam-custom.gguf sam-custom-q4.gguf q4_k_m
  4. Create Ollama model:
     echo 'FROM ./sam-custom-q4.gguf' > Modelfile.sam-custom
     ollama create sam-custom -f Modelfile.sam-custom

The fused MLX model is ready at: ./sam-finetuned/fused
""")
EOF

echo ""
echo "See instructions above for Ollama conversion."
