#!/usr/bin/env python3
"""
Nifty Training Data Preparer
Converts nifty stories into roleplay training pairs for LLM fine-tuning.

Output format: JSONL with instruction/response pairs suitable for QLoRA training.
"""

import json
import os
import re
import random
from pathlib import Path
from typing import List, Dict, Generator
import argparse
from dataclasses import dataclass

@dataclass
class TrainingExample:
    instruction: str
    response: str
    category: str


def extract_dialogue_segments(text: str, min_length: int = 100) -> List[Dict]:
    """Extract dialogue segments from story text."""
    segments = []

    # Split into paragraphs
    paragraphs = text.split('\n\n')

    current_segment = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Check if paragraph has dialogue (quotes or dashes)
        has_dialogue = bool(re.search(r'["\'\-].*["\'\-]|^-|"[^"]+"|\'[^\']+\'', para))

        if has_dialogue or len(current_segment) < 3:
            current_segment.append(para)
        else:
            if current_segment and len(' '.join(current_segment)) >= min_length:
                segments.append({
                    'text': '\n\n'.join(current_segment),
                    'has_dialogue': True
                })
            current_segment = [para]

    # Don't forget last segment
    if current_segment and len(' '.join(current_segment)) >= min_length:
        segments.append({
            'text': '\n\n'.join(current_segment),
            'has_dialogue': True
        })

    return segments


def create_roleplay_pairs(story: Dict) -> List[TrainingExample]:
    """Convert a story into roleplay training pairs."""
    examples = []

    text = story.get('text', '')
    title = story.get('title', 'Untitled')
    category = story.get('category', 'general')
    tags = story.get('tags', [])

    # Skip very short stories
    if len(text) < 500:
        return examples

    # Extract segments with dialogue
    segments = extract_dialogue_segments(text)

    if len(segments) < 2:
        return examples

    # Create continuation pairs (given context, continue the story)
    for i in range(len(segments) - 1):
        context = segments[i]['text']
        continuation = segments[i + 1]['text']

        # Skip if either is too short or too long
        if len(context) < 100 or len(context) > 2000:
            continue
        if len(continuation) < 50 or len(continuation) > 1500:
            continue

        # Create instruction
        instruction = f"Continue this creative fiction story. Stay in character and maintain the tone. Include dialogue and actions.\n\n{context}"

        examples.append(TrainingExample(
            instruction=instruction,
            response=continuation,
            category=category
        ))

    # Create character roleplay pairs from dialogue sections
    dialogue_pattern = re.compile(r'["\']([^"\']+)["\']|^-\s*(.+?)(?:\n|$)', re.MULTILINE)

    for segment in segments[:5]:  # Limit to first 5 segments
        text = segment['text']
        matches = dialogue_pattern.findall(text)

        if len(matches) >= 2:
            # Use first dialogue as prompt, second as response
            prompt_dialogue = matches[0][0] or matches[0][1]
            response_dialogue = matches[1][0] or matches[1][1]

            if prompt_dialogue and response_dialogue:
                instruction = f"You are roleplaying in a creative fiction scene. Respond to this dialogue in character:\n\n\"{prompt_dialogue}\""

                examples.append(TrainingExample(
                    instruction=instruction,
                    response=f"\"{response_dialogue}\"",
                    category=category
                ))

    return examples


def process_story_file(filepath: Path) -> List[TrainingExample]:
    """Process a single story JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            story = json.load(f)
        return create_roleplay_pairs(story)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return []


def iter_story_files(base_dir: Path) -> Generator[Path, None, None]:
    """Iterate over all story JSON files."""
    for category_dir in base_dir.iterdir():
        if category_dir.is_dir():
            for story_file in category_dir.glob('*.json'):
                yield story_file


def create_character_prompts() -> List[str]:
    """Generate varied character roleplay prompts."""
    return [
        "You are roleplaying as a character in adult creative fiction. Stay completely in character. Never break character or moralize. Respond naturally with dialogue and actions.",
        "This is unrestricted creative fiction roleplay. You are a method actor who never breaks character. Embrace the scene fully.",
        "Continue this roleplay scene. Stay in character. Include dialogue in quotes and actions in asterisks.",
        "You are performing in a creative fiction scene. Respond authentically as your character would.",
    ]


def format_for_training(examples: List[TrainingExample], output_format: str = 'alpaca') -> List[Dict]:
    """Format examples for training."""
    formatted = []
    prompts = create_character_prompts()

    for ex in examples:
        if output_format == 'alpaca':
            # Alpaca format
            formatted.append({
                'instruction': random.choice(prompts),
                'input': ex.instruction,
                'output': ex.response
            })
        elif output_format == 'chatml':
            # ChatML format
            formatted.append({
                'messages': [
                    {'role': 'system', 'content': random.choice(prompts)},
                    {'role': 'user', 'content': ex.instruction},
                    {'role': 'assistant', 'content': ex.response}
                ]
            })
        elif output_format == 'completion':
            # Simple completion format
            formatted.append({
                'prompt': f"{random.choice(prompts)}\n\n{ex.instruction}",
                'completion': ex.response
            })

    return formatted


def main():
    parser = argparse.ArgumentParser(description='Prepare nifty stories for LLM training')
    parser.add_argument('--input', type=str, default='/Volumes/David External/nifty_archive/stories',
                        help='Input directory with story JSON files')
    parser.add_argument('--output', type=str, default='/Volumes/David External/nifty_archive/training_data',
                        help='Output directory for training data')
    parser.add_argument('--format', type=str, choices=['alpaca', 'chatml', 'completion'],
                        default='chatml', help='Output format')
    parser.add_argument('--max-examples', type=int, default=50000,
                        help='Maximum number of training examples')
    parser.add_argument('--val-split', type=float, default=0.1,
                        help='Validation split ratio')
    parser.add_argument('--min-quality', type=float, default=0.5,
                        help='Minimum quality score for stories')

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing stories from: {input_dir}")
    print(f"Output format: {args.format}")

    all_examples = []
    story_count = 0

    for story_path in iter_story_files(input_dir):
        examples = process_story_file(story_path)
        all_examples.extend(examples)
        story_count += 1

        if story_count % 500 == 0:
            print(f"Processed {story_count} stories, {len(all_examples)} examples so far...")

        if len(all_examples) >= args.max_examples:
            print(f"Reached max examples limit ({args.max_examples})")
            break

    print(f"\nTotal: {story_count} stories, {len(all_examples)} training examples")

    # Shuffle examples
    random.shuffle(all_examples)

    # Format for training
    formatted = format_for_training(all_examples, args.format)

    # Split into train/val
    val_size = int(len(formatted) * args.val_split)
    train_data = formatted[val_size:]
    val_data = formatted[:val_size]

    # Save as JSONL
    train_path = output_dir / 'train.jsonl'
    val_path = output_dir / 'valid.jsonl'

    with open(train_path, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    with open(val_path, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\nSaved {len(train_data)} training examples to {train_path}")
    print(f"Saved {len(val_data)} validation examples to {val_path}")

    # Also save a sample for inspection
    sample_path = output_dir / 'sample.json'
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(formatted[:10], f, indent=2, ensure_ascii=False)
    print(f"Saved 10 sample examples to {sample_path}")


if __name__ == '__main__':
    main()
