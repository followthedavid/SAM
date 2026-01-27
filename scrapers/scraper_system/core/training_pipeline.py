"""
Training Data Pipeline

Converts raw scraped content into training-ready format for SAM.

Produces:
1. Instruction-Response pairs (for fine-tuning)
2. Q&A pairs (from Stack Overflow, GitHub issues)
3. Problem-Solution pairs (debugging patterns)
4. Documentation chunks (for RAG)
5. Code examples with explanations

Output formats:
- JSONL for fine-tuning
- Parquet for efficient storage
- SQLite for quick querying
"""

import json
import logging
import re
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Tuple
import random

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """A single training example."""
    id: str
    source: str
    example_type: str  # instruction, qa, problem_solution, documentation, code

    # Core content
    instruction: str
    response: str

    # Optional context
    system_prompt: Optional[str] = None
    context: Optional[str] = None

    # Metadata
    url: str = ""
    quality_score: float = 0.0
    topics: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PipelineStats:
    """Statistics for a pipeline run."""
    total_items_processed: int = 0
    examples_generated: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)
    errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


class TrainingDataPipeline:
    """
    Pipeline for converting scraped content to training data.

    Usage:
        pipeline = TrainingDataPipeline()
        pipeline.initialize()

        # Process all unprocessed items
        stats = pipeline.process_all()

        # Export to training format
        pipeline.export_jsonl("/path/to/training.jsonl")
    """

    # System prompts for different content types
    SYSTEM_PROMPTS = {
        "coding": "You are SAM, an expert software developer specializing in Apple platforms (iOS, macOS, visionOS). You write clean, modern Swift code and follow Apple's Human Interface Guidelines.",
        "debugging": "You are SAM, an expert debugger. You analyze error messages, stack traces, and code to identify root causes and provide clear solutions.",
        "tutorial": "You are SAM, a patient programming teacher. You explain concepts clearly with practical examples, suitable for beginners.",
        "documentation": "You are SAM, a technical writer. You provide accurate, comprehensive documentation with code examples.",
        "ui_testing": "You are SAM, a UI/UX testing expert. You understand accessibility, automated testing, and user experience best practices.",
    }

    # Instruction templates for generating training pairs
    INSTRUCTION_TEMPLATES = {
        "how_to": [
            "How do I {action} in {technology}?",
            "What's the best way to {action} using {technology}?",
            "Can you show me how to {action}?",
            "I need help {action} in my {technology} app.",
        ],
        "explain": [
            "Explain {concept} in {technology}.",
            "What is {concept} and how does it work?",
            "Can you explain {concept} for a beginner?",
            "Help me understand {concept}.",
        ],
        "debug": [
            "I'm getting this error: {error}. How do I fix it?",
            "My app crashes with: {error}. What's wrong?",
            "Help me debug this: {error}",
            "Why am I seeing {error}?",
        ],
        "review": [
            "Review this code and suggest improvements:\n{code}",
            "What's wrong with this code?\n{code}",
            "How can I optimize this?\n{code}",
        ],
    }

    def __init__(self, output_dir: str = None):
        self._db = None
        self.examples: List[TrainingExample] = []
        self.stats = PipelineStats()

        # Output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            from ..config.settings import TRAINING_DATA_DIR
            self.output_dir = TRAINING_DATA_DIR

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Initialize the pipeline."""
        from ..storage.database import get_database

        try:
            self._db = get_database()
            logger.info("Training pipeline initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def process_all(self, limit: int = None, source: str = None) -> PipelineStats:
        """
        Process all unprocessed scraped items.

        Args:
            limit: Maximum items to process
            source: Filter by source (e.g., 'stackoverflow', 'github')

        Returns:
            Pipeline statistics
        """
        self.stats = PipelineStats()

        # Get unprocessed items from database
        items = self._get_unprocessed_items(limit=limit, source=source)

        for item in items:
            try:
                examples = self._process_item(item)
                self.examples.extend(examples)

                self.stats.total_items_processed += 1
                self.stats.examples_generated += len(examples)

                # Track by type and source
                for ex in examples:
                    self.stats.by_type[ex.example_type] = self.stats.by_type.get(ex.example_type, 0) + 1
                    self.stats.by_source[ex.source] = self.stats.by_source.get(ex.source, 0) + 1

                # Mark as processed
                if self._db and item.get('id'):
                    self._db.mark_processed([item['id']])

            except Exception as e:
                logger.error(f"Error processing item {item.get('id')}: {e}")
                self.stats.errors += 1

        self.stats.end_time = datetime.now()
        return self.stats

    def _get_unprocessed_items(self, limit: int = None, source: str = None) -> List[Dict]:
        """Get unprocessed items from database."""
        if not self._db:
            return []

        # Build query
        query = "SELECT * FROM scraped_items WHERE processed = FALSE"
        params = []

        if source:
            query += " AND source = %s"
            params.append(source)

        query += " ORDER BY scraped_at DESC"

        if limit:
            query += f" LIMIT {limit}"

        try:
            with self._db.cursor() as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get items: {e}")
            return []

    def _process_item(self, item: Dict) -> List[TrainingExample]:
        """Process a single scraped item into training examples."""
        source = item.get('source', '')
        content = item.get('content', '')
        metadata = item.get('metadata', {})

        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        examples = []

        # Route to appropriate processor based on source
        if source == 'stackoverflow':
            examples.extend(self._process_stackoverflow(item, content, metadata))
        elif source == 'github':
            examples.extend(self._process_github(item, content, metadata))
        elif source in ['apple_dev', 'swift_community', 'wwdc']:
            examples.extend(self._process_apple_docs(item, content, metadata))
        elif source in ['devto', 'hashnode']:
            examples.extend(self._process_tutorial(item, content, metadata))
        elif source == 'docs':
            examples.extend(self._process_documentation(item, content, metadata))
        elif source == 'uiux':
            examples.extend(self._process_uiux(item, content, metadata))
        elif source in ['ao3', 'nifty', 'literotica', 'dark_psych']:
            examples.extend(self._process_fiction(item, content, metadata))
        else:
            # Generic processing
            examples.extend(self._process_generic(item, content, metadata))

        return examples

    def _process_stackoverflow(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process Stack Overflow Q&A into training examples."""
        examples = []

        # Extract question and answers from content
        # Stack Overflow items should have question + accepted answer
        question_match = re.search(r'## Question:?\s*(.*?)(?=## |$)', content, re.DOTALL)
        answer_match = re.search(r'## (?:Accepted )?Answer:?\s*(.*?)(?=## |$)', content, re.DOTALL)

        if question_match and answer_match:
            question = question_match.group(1).strip()
            answer = answer_match.group(1).strip()

            if len(question) > 20 and len(answer) > 50:
                examples.append(TrainingExample(
                    id=self._generate_id(item),
                    source=item.get('source', 'stackoverflow'),
                    example_type='qa',
                    instruction=question,
                    response=answer,
                    system_prompt=self.SYSTEM_PROMPTS['debugging'],
                    url=item.get('url', ''),
                    quality_score=self._calculate_quality(metadata),
                    topics=metadata.get('tags', []),
                ))

        # Also create a "how to" style instruction
        title = item.get('title', '')
        if title and content:
            # Convert title to instruction
            instruction = self._title_to_instruction(title)
            if instruction:
                examples.append(TrainingExample(
                    id=self._generate_id(item, suffix='inst'),
                    source=item.get('source', 'stackoverflow'),
                    example_type='instruction',
                    instruction=instruction,
                    response=content[:3000],  # Truncate long responses
                    system_prompt=self.SYSTEM_PROMPTS['coding'],
                    url=item.get('url', ''),
                    quality_score=self._calculate_quality(metadata),
                    topics=metadata.get('tags', []),
                ))

        return examples

    def _process_github(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process GitHub content into training examples."""
        examples = []
        item_type = metadata.get('type', '')

        if item_type == 'issue':
            # Issue with solution pattern
            examples.extend(self._process_github_issue(item, content, metadata))
        elif item_type == 'readme':
            # README documentation
            examples.extend(self._process_github_readme(item, content, metadata))

        return examples

    def _process_github_issue(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process GitHub issue into problem-solution example."""
        examples = []

        # Extract problem (issue body) and solution (comments)
        issue_match = re.search(r'## Issue:?\s*(.*?)(?=## Comments|---|\Z)', content, re.DOTALL)
        comments_match = re.search(r'## Comments:?\s*(.*?)$', content, re.DOTALL)

        if issue_match:
            problem = issue_match.group(1).strip()
            solution = comments_match.group(1).strip() if comments_match else ""

            if len(problem) > 30 and len(solution) > 50:
                # Check for solution markers
                has_solution = metadata.get('has_solution_markers', False)

                if has_solution or 'fixed' in solution.lower() or 'solved' in solution.lower():
                    examples.append(TrainingExample(
                        id=self._generate_id(item),
                        source='github',
                        example_type='problem_solution',
                        instruction=f"I'm having this issue:\n\n{problem[:1500]}",
                        response=solution[:2500],
                        system_prompt=self.SYSTEM_PROMPTS['debugging'],
                        url=item.get('url', ''),
                        quality_score=self._calculate_quality(metadata),
                        topics=metadata.get('labels', []),
                    ))

        return examples

    def _process_github_readme(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process GitHub README into documentation examples."""
        examples = []

        # Extract installation section
        installation = metadata.get('installation_section', '')
        if installation and len(installation) > 100:
            repo_name = item.get('title', '').replace('README: ', '')
            examples.append(TrainingExample(
                id=self._generate_id(item, suffix='install'),
                source='github',
                example_type='documentation',
                instruction=f"How do I install and set up {repo_name}?",
                response=installation,
                system_prompt=self.SYSTEM_PROMPTS['documentation'],
                url=item.get('url', ''),
                quality_score=self._calculate_quality(metadata),
                topics=metadata.get('topics', []),
            ))

        # Create overview instruction
        if len(content) > 200:
            description = metadata.get('description', '')
            repo_name = item.get('title', '').replace('README: ', '')

            examples.append(TrainingExample(
                id=self._generate_id(item),
                source='github',
                example_type='documentation',
                instruction=f"What is {repo_name} and how do I use it?",
                response=content[:3000],
                system_prompt=self.SYSTEM_PROMPTS['documentation'],
                url=item.get('url', ''),
                quality_score=self._calculate_quality(metadata),
                topics=metadata.get('topics', []),
            ))

        return examples

    def _process_apple_docs(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process Apple documentation into training examples."""
        examples = []

        title = item.get('title', '')
        is_api = metadata.get('is_api_reference', False)
        is_tutorial = metadata.get('is_tutorial', False)
        has_code = metadata.get('has_code_examples', False)

        # Determine system prompt
        if is_tutorial:
            system_prompt = self.SYSTEM_PROMPTS['tutorial']
        else:
            system_prompt = self.SYSTEM_PROMPTS['coding']

        # Generate instruction based on content type
        if is_api:
            instruction = f"Explain how to use {title} in Swift."
        elif is_tutorial:
            instruction = f"Show me a tutorial for {title}."
        else:
            instruction = f"What is {title} and how do I use it in my app?"

        if len(content) > 200:
            examples.append(TrainingExample(
                id=self._generate_id(item),
                source=item.get('source', 'apple_dev'),
                example_type='documentation' if is_api else 'tutorial',
                instruction=instruction,
                response=content[:4000],
                system_prompt=system_prompt,
                url=item.get('url', ''),
                quality_score=0.9 if 'apple' in item.get('source', '') else 0.8,
                topics=metadata.get('platforms', []) + metadata.get('topics', []),
            ))

        return examples

    def _process_tutorial(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process tutorial content (Dev.to, Hashnode)."""
        examples = []

        title = item.get('title', '')
        is_beginner = metadata.get('is_beginner', False)
        has_code = metadata.get('has_code', False)

        # Convert title to instruction
        instruction = self._title_to_instruction(title)
        if not instruction:
            instruction = f"Explain {title}"

        if len(content) > 300:
            examples.append(TrainingExample(
                id=self._generate_id(item),
                source=item.get('source', 'tutorial'),
                example_type='tutorial',
                instruction=instruction,
                response=content[:4000],
                system_prompt=self.SYSTEM_PROMPTS['tutorial'] if is_beginner else self.SYSTEM_PROMPTS['coding'],
                url=item.get('url', ''),
                quality_score=self._calculate_quality(metadata),
                topics=metadata.get('all_tags', []),
            ))

        return examples

    def _process_documentation(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process package manager documentation."""
        examples = []

        title = item.get('title', '')
        site = metadata.get('site', '')
        has_commands = metadata.get('has_commands', False)
        has_troubleshooting = metadata.get('has_troubleshooting', False)

        # Create instruction based on content
        if has_commands:
            instruction = f"What are the {site} commands for {title}?"
        elif has_troubleshooting:
            instruction = f"How do I troubleshoot {title}?"
        else:
            instruction = f"Explain {title}"

        if len(content) > 200:
            examples.append(TrainingExample(
                id=self._generate_id(item),
                source='docs',
                example_type='documentation',
                instruction=instruction,
                response=content[:3500],
                system_prompt=self.SYSTEM_PROMPTS['documentation'],
                url=item.get('url', ''),
                quality_score=0.85,
                topics=[site] if site else [],
            ))

        return examples

    def _process_uiux(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process UI/UX and accessibility content."""
        examples = []

        title = item.get('title', '')
        is_accessibility = metadata.get('is_accessibility', False)
        is_testing = metadata.get('is_testing', False)

        if is_accessibility:
            instruction = f"What are the accessibility guidelines for {title}?"
            system_prompt = self.SYSTEM_PROMPTS['ui_testing']
        elif is_testing:
            instruction = f"How do I test {title}?"
            system_prompt = self.SYSTEM_PROMPTS['ui_testing']
        else:
            instruction = f"Explain the UI/UX best practices for {title}"
            system_prompt = self.SYSTEM_PROMPTS['coding']

        if len(content) > 200:
            examples.append(TrainingExample(
                id=self._generate_id(item),
                source='uiux',
                example_type='documentation',
                instruction=instruction,
                response=content[:3500],
                system_prompt=system_prompt,
                url=item.get('url', ''),
                quality_score=0.85,
                topics=['accessibility'] if is_accessibility else ['testing'] if is_testing else [],
            ))

        return examples

    def _process_fiction(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Process fiction content for dialogue/personality training."""
        examples = []

        # Fiction is used for dialogue patterns, not instruction-following
        # Create conversation-style examples

        if len(content) > 500:
            # Extract dialogue patterns
            dialogues = self._extract_dialogues(content)

            for i, (speaker, text) in enumerate(dialogues[:5]):  # Limit per item
                if len(text) > 50:
                    examples.append(TrainingExample(
                        id=self._generate_id(item, suffix=str(i)),
                        source=item.get('source', 'fiction'),
                        example_type='dialogue',
                        instruction=f"Continue this conversation naturally:",
                        response=text[:1500],
                        context=content[:500],  # Some context
                        url=item.get('url', ''),
                        quality_score=self._calculate_quality(metadata),
                        topics=metadata.get('tags', []),
                    ))

        return examples

    def _process_generic(self, item: Dict, content: str, metadata: Dict) -> List[TrainingExample]:
        """Generic processor for untyped content."""
        examples = []

        title = item.get('title', '')
        if title and len(content) > 200:
            examples.append(TrainingExample(
                id=self._generate_id(item),
                source=item.get('source', 'unknown'),
                example_type='documentation',
                instruction=f"Tell me about {title}",
                response=content[:3000],
                url=item.get('url', ''),
                quality_score=0.5,
            ))

        return examples

    def _extract_dialogues(self, content: str) -> List[Tuple[str, str]]:
        """Extract dialogue exchanges from fiction content."""
        dialogues = []

        # Pattern for quoted speech
        pattern = r'"([^"]+)"(?:\s+(?:said|asked|replied|whispered|shouted|muttered)\s+(\w+))?'
        matches = re.findall(pattern, content)

        for text, speaker in matches:
            if len(text) > 20:
                dialogues.append((speaker or "Character", text))

        return dialogues

    def _title_to_instruction(self, title: str) -> Optional[str]:
        """Convert a title to a natural instruction."""
        title_lower = title.lower()

        # Already a question
        if title.endswith('?'):
            return title

        # "How to X" pattern
        if 'how to' in title_lower:
            return title + "?"

        # Common patterns
        if any(word in title_lower for word in ['guide', 'tutorial', 'introduction']):
            return f"Can you give me a {title.lower()}?"

        if any(word in title_lower for word in ['error', 'fix', 'solve', 'debug']):
            return f"Help me with: {title}"

        # Default: explain it
        return f"Explain {title}"

    def _calculate_quality(self, metadata: Dict) -> float:
        """Calculate quality score from metadata."""
        score = 0.5  # Base score

        # Boost for engagement
        reactions = metadata.get('reactions', 0) or metadata.get('score', 0)
        if reactions > 100:
            score += 0.2
        elif reactions > 10:
            score += 0.1

        # Boost for code
        if metadata.get('has_code', False) or metadata.get('has_code_examples', False):
            score += 0.1

        # Boost for solutions
        if metadata.get('has_solution_markers', False):
            score += 0.15

        # Boost for being accepted answer
        if metadata.get('is_accepted', False):
            score += 0.2

        return min(score, 1.0)

    def _generate_id(self, item: Dict, suffix: str = '') -> str:
        """Generate unique ID for training example."""
        base = f"{item.get('source', '')}-{item.get('id', '')}-{suffix}"
        return hashlib.md5(base.encode()).hexdigest()[:16]

    # =========================================================================
    # Export Methods
    # =========================================================================

    def export_jsonl(self, filepath: str = None) -> str:
        """Export training examples to JSONL format."""
        if not filepath:
            filepath = self.output_dir / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

        filepath = Path(filepath)

        with open(filepath, 'w') as f:
            for example in self.examples:
                # Convert to fine-tuning format
                record = {
                    "id": example.id,
                    "messages": [
                        {"role": "system", "content": example.system_prompt or self.SYSTEM_PROMPTS['coding']},
                        {"role": "user", "content": example.instruction},
                        {"role": "assistant", "content": example.response},
                    ],
                    "metadata": {
                        "source": example.source,
                        "type": example.example_type,
                        "url": example.url,
                        "quality": example.quality_score,
                        "topics": example.topics,
                    }
                }
                f.write(json.dumps(record) + '\n')

        logger.info(f"Exported {len(self.examples)} examples to {filepath}")
        return str(filepath)

    def export_alpaca(self, filepath: str = None) -> str:
        """Export in Alpaca format (instruction, input, output)."""
        if not filepath:
            filepath = self.output_dir / f"alpaca_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = Path(filepath)

        records = []
        for example in self.examples:
            records.append({
                "instruction": example.instruction,
                "input": example.context or "",
                "output": example.response,
            })

        with open(filepath, 'w') as f:
            json.dump(records, f, indent=2)

        logger.info(f"Exported {len(records)} examples to {filepath}")
        return str(filepath)

    def get_stats_summary(self) -> str:
        """Get human-readable stats summary."""
        duration = (self.stats.end_time - self.stats.start_time).total_seconds() if self.stats.end_time else 0

        lines = [
            "=== Training Pipeline Stats ===",
            f"Items processed: {self.stats.total_items_processed}",
            f"Examples generated: {self.stats.examples_generated}",
            f"Errors: {self.stats.errors}",
            f"Duration: {duration:.1f}s",
            "",
            "By Type:",
        ]

        for type_name, count in sorted(self.stats.by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {type_name}: {count}")

        lines.append("")
        lines.append("By Source:")

        for source, count in sorted(self.stats.by_source.items(), key=lambda x: -x[1]):
            lines.append(f"  {source}: {count}")

        return '\n'.join(lines)


# Convenience function
def get_pipeline(output_dir: str = None) -> TrainingDataPipeline:
    """Get initialized training pipeline."""
    pipeline = TrainingDataPipeline(output_dir)
    pipeline.initialize()
    return pipeline
