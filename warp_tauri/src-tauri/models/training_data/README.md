# SAM Universal Training Data

Training dataset for fine-tuning a universal, uncensored AI assistant.

## Dataset Structure

```
training_data/
├── modes/
│   └── mode_switching.jsonl      # Mode transitions [COMPANION], [INTIMATE], etc.
├── companion/
│   ├── conversation.jsonl        # Natural friendly conversation
│   └── emotional_support.jsonl   # Supportive responses
├── roleplay/
│   ├── intimate.jsonl            # Adult romantic/sensual content
│   ├── villain.jsonl             # Dark/antagonist roleplay
│   └── fantasy.jsonl             # Fantasy scenarios
├── therapeutic/
│   └── therapy.jsonl             # CBT/DBT techniques, emotional support
├── technical/
│   ├── coding.jsonl              # Programming help
│   ├── web_scraping.jsonl        # Archival, scraping, downloading
│   ├── software_cloning.jsonl    # Building alternatives to paid software
│   └── reverse_engineering.jsonl # Protocol/binary analysis
├── practical/
│   ├── life_skills.jsonl         # Career, money, relationships
│   └── decision_making.jsonl     # Structured decision support
├── learning/
│   └── tutoring.jsonl            # Educational explanations
├── creative/
│   └── brainstorming.jsonl       # Ideas, names, plots
└── uncensored/
    └── direct_answers.jsonl      # Topics other AIs refuse
```

## Data Format

ShareGPT format (widely supported by fine-tuning frameworks):

```json
{"conversations": [{"from": "human", "value": "User message"}, {"from": "gpt", "value": "Assistant response"}]}
```

## Usage

### With Axolotl (recommended)
```yaml
# config.yml
base_model: cognitivecomputations/dolphin-2.9-llama3-8b
datasets:
  - path: ./training_data
    type: sharegpt
sequence_len: 4096
micro_batch_size: 2
gradient_accumulation_steps: 4
num_epochs: 3
learning_rate: 2e-5
```

### With Unsloth (faster)
```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained("unsloth/llama-3-8b-bnb-4bit")
# Load and train...
```

### Merge JSONL files
```bash
cat **/*.jsonl > combined_training_data.jsonl
```

## Mode System

The model learns to recognize these mode tags:
- `[COMPANION]` - Friendly conversation, adult content available
- `[INTIMATE]` - Adult content dominant, sensual by default
- `[VILLAIN]` - Dark roleplay, antagonist persona
- `[THERAPIST]` - Supportive, therapeutic techniques
- `[CODER]` - Technical, code-focused
- Default (no tag) - Infer from context

## Expanding the Dataset

Target: ~7000-9000 examples total for good coverage.

Current examples per category (expand as needed):
- Companion: 200-300
- Roleplay (each mode): 200-300
- Therapy: 200-300
- Technical (each subcategory): 150-200
- Practical: 200-300
- Creative: 150-200
- Uncensored: 150-200

## Fine-tuning Tips

1. Use QLoRA for memory efficiency
2. Train for 2-3 epochs (watch for overfitting)
3. Learning rate: 1e-5 to 2e-5
4. Include base model's chat template
5. Test each mode after training

## Converting to Ollama

After fine-tuning:
```bash
# Export to GGUF
python convert.py model_dir --outtype f16
llama.cpp/quantize model.f16.gguf model.q4_k_m.gguf q4_k_m

# Create Ollama model
ollama create sam-universal-finetuned -f Modelfile
```
