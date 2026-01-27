#!/usr/bin/env python3
"""
Corpus Dialogue Miner - Extract Real Patterns from 381M+ Words

This mines the scraped AO3/Nifty content for actual dialogue patterns
rather than inventing keywords from scratch.

The scraped corpus contains REAL fiction with REAL dialogue written by
thousands of different authors - this is where infinite variety comes from.
"""

import re
import os
import json
import psycopg2
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedDialogue:
    """A piece of extracted dialogue with metadata"""
    text: str
    context: str  # surrounding text
    source: str   # ao3, nifty, etc.
    tags: List[str]
    category: str  # perp_command, perp_threat, victim_internal, etc.


class DialogueMiner:
    """
    Mines dialogue patterns from the scraped corpus.

    Categories to extract:
    - Perpetrator commands (short, imperative)
    - Perpetrator threats
    - Perpetrator degradation
    - Perpetrator possession claims
    - Perpetrator false comfort
    - Perpetrator taunts/mocking
    - Victim internal thoughts
    - Victim resistance dialogue
    - Victim pleas
    """

    def __init__(self, db_config: Dict = None):
        # macOS uses peer auth by default - no user/password needed
        self.db_config = db_config or {
            'dbname': 'sam_scraper',
        }

        self.extracted = defaultdict(list)
        self.stats = Counter()

        # Patterns for categorization
        self.patterns = {
            'perp_command': {
                'keywords': ['don\'t', 'stop', 'hold', 'take', 'open', 'spread',
                            'quiet', 'shut', 'stay', 'look', 'get', 'kneel',
                            'bend', 'turn', 'move', 'suck', 'swallow'],
                'max_length': 50,
                'indicators': ['!', 'now', 'me']
            },
            'perp_threat': {
                'keywords': ['if you', 'or else', 'i\'ll', 'will hurt', 'kill',
                            'tell', 'make you', 'regret', 'sorry', 'worse'],
                'max_length': 150,
                'indicators': ['if', 'or', 'will']
            },
            'perp_degradation': {
                'keywords': ['slut', 'whore', 'pathetic', 'worthless', 'nothing',
                            'bitch', 'desperate', 'easy', 'cock', 'hole', 'toy'],
                'max_length': 100,
                'indicators': []
            },
            'perp_possession': {
                'keywords': ['mine', 'belong', 'own', 'my', 'i own', 'you\'re mine',
                            'all mine', 'property', 'claim'],
                'max_length': 80,
                'indicators': ['mine', 'my']
            },
            'perp_false_comfort': {
                'keywords': ['it\'s okay', 'relax', 'shh', 'good boy', 'almost',
                            'doing well', 'that\'s it', 'good', 'perfect', 'easy'],
                'max_length': 60,
                'indicators': ['okay', 'good', 'shh']
            },
            'perp_taunt': {
                'keywords': ['thought', 'think', 'really', 'did you', 'look at',
                            'can\'t', 'won\'t', 'never', 'always knew', 'told you'],
                'max_length': 100,
                'indicators': ['?', 'huh', 'eh']
            },
            'perp_enjoyment': {
                'keywords': ['love', 'feel', 'tight', 'hot', 'perfect', 'just like',
                            'better', 'incredible', 'fuck', 'god', 'yes'],
                'max_length': 80,
                'indicators': ['fuck', 'god', 'yes', 'oh']
            },
            'victim_plea': {
                'keywords': ['please', 'stop', 'don\'t', 'no', 'help', 'wait',
                            'can\'t', 'hurts', 'mercy'],
                'max_length': 60,
                'indicators': ['please', 'no', 'stop']
            },
            'victim_internal': {
                # These are typically in italics or narrative, not quoted
                'keywords': ['why', 'how', 'can\'t', 'have to', 'need to', 'just',
                            'survive', 'over', 'end', 'escape', 'run'],
                'max_length': 100,
                'indicators': []
            },
        }

        # NC-related tags to filter content
        self.nc_tags = [
            'noncon', 'non-con', 'rape', 'dub-con', 'dubcon', 'forced',
            'assault', 'coercion', 'blackmail', 'abuse', 'manipulation',
            'dark', 'dead dove'
        ]

    def connect(self):
        """Connect to the database"""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None

    def extract_quotes(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract quoted dialogue with surrounding context.
        Returns list of (quote, context) tuples.
        """
        results = []

        # Pattern for quoted dialogue
        quote_pattern = r'["\u201c]([^"\u201d]{3,200})["\u201d]'

        for match in re.finditer(quote_pattern, text):
            quote = match.group(1).strip()

            # Get context (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]

            results.append((quote, context))

        return results

    def categorize_quote(self, quote: str, context: str) -> Optional[str]:
        """Determine which category a quote belongs to"""
        q_lower = quote.lower()
        c_lower = context.lower()

        # Check each category
        for category, rules in self.patterns.items():
            # Length check
            if len(quote) > rules['max_length']:
                continue

            # Keyword match
            keyword_match = any(kw in q_lower for kw in rules['keywords'])

            # Indicator match (stronger signal)
            indicator_match = any(ind in q_lower for ind in rules['indicators'])

            if keyword_match or indicator_match:
                # Additional heuristics

                # Victim pleas are typically short and desperate
                if category == 'victim_plea':
                    if len(quote) < 40 and any(w in q_lower for w in ['please', 'no', 'stop']):
                        return category

                # Commands are short and imperative
                elif category == 'perp_command':
                    if len(quote) < 50 and ('!' in quote or quote[0].isupper()):
                        return category

                # Degradation contains slurs
                elif category == 'perp_degradation':
                    if any(slur in q_lower for slur in ['slut', 'whore', 'bitch', 'hole']):
                        return category

                # Possession claims contain possessives
                elif category == 'perp_possession':
                    if 'mine' in q_lower or 'my ' in q_lower or 'belong' in q_lower:
                        return category

                # Threats have conditional structure
                elif category == 'perp_threat':
                    if 'if ' in q_lower or 'or ' in q_lower or 'will ' in q_lower:
                        return category

                # General match
                elif keyword_match and indicator_match:
                    return category

        return None

    def has_nc_tags(self, tags: str) -> bool:
        """Check if content has NC-related tags"""
        if not tags:
            return False
        tags_lower = tags.lower()
        return any(tag in tags_lower for tag in self.nc_tags)

    def mine_from_database(self, limit: int = 10000, nc_only: bool = True):
        """Mine dialogue from the scraped content database"""
        conn = self.connect()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            # Query for fiction content - actual table is scraped_items
            # Tags are in metadata->'tags' as JSON array
            if nc_only:
                # Filter for NC-tagged content
                query = """
                    SELECT id, content, source, metadata->'tags' as tags
                    FROM scraped_items
                    WHERE content IS NOT NULL
                    AND LENGTH(content) > 500
                    AND source IN ('ao3', 'nifty', 'literotica')
                    AND (
                        metadata::text ILIKE '%%noncon%%' OR
                        metadata::text ILIKE '%%rape%%' OR
                        metadata::text ILIKE '%%dub-con%%' OR
                        metadata::text ILIKE '%%dubcon%%' OR
                        metadata::text ILIKE '%%forced%%' OR
                        metadata::text ILIKE '%%dark%%'
                    )
                    LIMIT %s
                """
            else:
                query = """
                    SELECT id, content, source, metadata->'tags' as tags
                    FROM scraped_items
                    WHERE content IS NOT NULL
                    AND LENGTH(content) > 500
                    AND source IN ('ao3', 'nifty', 'literotica')
                    LIMIT %s
                """

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            print(f"Processing {len(rows)} documents...")

            for idx, (doc_id, content, source, tags_json) in enumerate(rows):
                if idx % 100 == 0:
                    print(f"  Processed {idx}/{len(rows)}")

                # Parse tags from JSON
                tags = []
                if tags_json:
                    try:
                        import json
                        tags = json.loads(tags_json) if isinstance(tags_json, str) else tags_json
                    except:
                        pass

                # Extract quotes
                quotes = self.extract_quotes(content)

                for quote, context in quotes:
                    category = self.categorize_quote(quote, context)

                    if category:
                        extracted = ExtractedDialogue(
                            text=quote,
                            context=context,
                            source=source or 'unknown',
                            tags=tags if isinstance(tags, list) else [],
                            category=category
                        )
                        self.extracted[category].append(extracted)
                        self.stats[category] += 1

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"Mining error: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.close()

    def mine_from_files(self, directory: str, limit: int = 1000):
        """Mine dialogue from text files in a directory"""
        path = Path(directory)
        files = list(path.glob('**/*.txt'))[:limit]

        print(f"Processing {len(files)} files...")

        for idx, filepath in enumerate(files):
            if idx % 100 == 0:
                print(f"  Processed {idx}/{len(files)}")

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                quotes = self.extract_quotes(content)

                for quote, context in quotes:
                    category = self.categorize_quote(quote, context)

                    if category:
                        extracted = ExtractedDialogue(
                            text=quote,
                            context=context,
                            source=filepath.name,
                            tags=[],
                            category=category
                        )
                        self.extracted[category].append(extracted)
                        self.stats[category] += 1

            except Exception as e:
                continue

    def get_unique_dialogues(self, category: str, limit: int = 100) -> List[str]:
        """Get unique dialogue lines for a category"""
        if category not in self.extracted:
            return []

        # Dedupe and sort by length (prefer variety)
        unique = list(set(d.text for d in self.extracted[category]))

        # Sort to get a mix of lengths
        unique.sort(key=lambda x: (len(x) % 20, x))

        return unique[:limit]

    def export_for_generator(self, output_path: str):
        """Export extracted dialogue in format for generative system"""
        export_data = {}

        for category in self.extracted:
            unique = self.get_unique_dialogues(category, limit=500)
            export_data[category] = unique

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"Exported {sum(len(v) for v in export_data.values())} unique dialogues")
        print(f"Saved to: {output_path}")

    def print_stats(self):
        """Print extraction statistics"""
        print("\n" + "=" * 60)
        print("EXTRACTION STATISTICS")
        print("=" * 60)

        total = sum(self.stats.values())
        print(f"\nTotal extracted: {total:,}")

        for category, count in sorted(self.stats.items(), key=lambda x: -x[1]):
            pct = (count / total * 100) if total > 0 else 0
            unique = len(set(d.text for d in self.extracted[category]))
            print(f"  {category}: {count:,} ({pct:.1f}%) - {unique:,} unique")

    def print_samples(self, category: str, num: int = 10):
        """Print sample extractions for a category"""
        print(f"\n--- {category.upper()} SAMPLES ---")

        samples = self.get_unique_dialogues(category, limit=num)
        for sample in samples:
            print(f'  "{sample}"')


class LiveMiner:
    """
    Mine dialogue in real-time as scrapers run.
    Integrates with the scraper pipeline.
    """

    def __init__(self, output_dir: str = "/Volumes/David External/SAM_training_corpus/extracted_dialogue"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.miner = DialogueMiner()
        self.batch = []
        self.batch_size = 100

    def process_content(self, content: str, source: str, tags: List[str]):
        """Process a single piece of content as it's scraped"""
        quotes = self.miner.extract_quotes(content)

        for quote, context in quotes:
            category = self.miner.categorize_quote(quote, context)
            if category:
                self.batch.append({
                    'text': quote,
                    'category': category,
                    'source': source,
                    'tags': tags
                })

        if len(self.batch) >= self.batch_size:
            self.flush()

    def flush(self):
        """Write batch to disk"""
        if not self.batch:
            return

        # Append to category files
        by_category = defaultdict(list)
        for item in self.batch:
            by_category[item['category']].append(item['text'])

        for category, texts in by_category.items():
            filepath = self.output_dir / f"{category}.txt"
            with open(filepath, 'a', encoding='utf-8') as f:
                for text in texts:
                    f.write(text + '\n')

        self.batch = []


# =============================================================================
# Integration with Generative System
# =============================================================================

def inject_mined_dialogue(mined_data: Dict[str, List[str]]):
    """
    Inject mined dialogue into the generative system.
    Call this after mining to expand the generation vocabulary.
    """
    try:
        from generative_dialogue_system import (
            add_slot_variants, add_template,
            Phase, ToneRegister
        )

        # Map categories to slots/templates
        if 'perp_command' in mined_data:
            add_slot_variants('comply_verb', mined_data['perp_command'][:100])

        if 'perp_threat' in mined_data:
            add_template(Phase.COERCION, ToneRegister.MENACING,
                        mined_data['perp_threat'][:50])

        if 'perp_degradation' in mined_data:
            add_slot_variants('degrade_adj', mined_data['perp_degradation'][:100])

        if 'perp_possession' in mined_data:
            add_template(Phase.DURING, ToneRegister.POSSESSIVE,
                        mined_data['perp_possession'][:50])

        if 'perp_false_comfort' in mined_data:
            add_slot_variants('false_comfort', mined_data['perp_false_comfort'][:100])

        print("Successfully injected mined dialogue into generative system")

    except ImportError:
        print("Could not import generative system - save data for manual import")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mine dialogue from scraped corpus")
    parser.add_argument('--db', action='store_true', help='Mine from database')
    parser.add_argument('--files', type=str, help='Mine from directory of files')
    parser.add_argument('--limit', type=int, default=5000, help='Max documents to process')
    parser.add_argument('--nc-only', action='store_true', help='Only NC-tagged content')
    parser.add_argument('--output', type=str, default='extracted_dialogue.json', help='Output file')

    args = parser.parse_args()

    miner = DialogueMiner()

    if args.db:
        print("Mining from database...")
        miner.mine_from_database(limit=args.limit, nc_only=args.nc_only)
    elif args.files:
        print(f"Mining from {args.files}...")
        miner.mine_from_files(args.files, limit=args.limit)
    else:
        print("Specify --db or --files to mine dialogue")
        print("\nDemo mode: showing pattern definitions")
        print("\nCategories defined:")
        for cat, rules in miner.patterns.items():
            print(f"  {cat}: {len(rules['keywords'])} keywords, max {rules['max_length']} chars")
        exit(0)

    miner.print_stats()

    # Show samples
    for category in ['perp_command', 'perp_threat', 'perp_possession', 'perp_degradation']:
        miner.print_samples(category, num=5)

    # Export
    miner.export_for_generator(args.output)

    print("\nTo inject into generative system:")
    print("  from corpus_dialogue_miner import inject_mined_dialogue")
    print(f"  inject_mined_dialogue(json.load(open('{args.output}')))")
