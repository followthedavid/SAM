#!/usr/bin/env python3
"""
Smart Summarizer for SAM Phase 2.3.2

Extractive summarization that preserves key facts without LLM calls.
Optimized for speed on 8GB M2 Mac Mini.

Features:
- Extracts key sentences based on importance scoring
- Preserves: names, numbers, code snippets, action items, URLs
- Compresses conversation history intelligently
- No LLM calls - pure algorithmic extraction

Usage:
    from smart_summarizer import SmartSummarizer

    summarizer = SmartSummarizer()
    summary = summarizer.summarize(text, max_tokens=200)
    facts = summarizer.extract_key_facts(text)
    condensed = summarizer.summarize_conversation(messages, max_tokens=500)
"""

import re
from collections import Counter
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class FactType(Enum):
    """Types of extractable facts."""
    NAME = "name"           # Person/entity names
    NUMBER = "number"       # Numbers, measurements, dates
    CODE = "code"           # Code snippets
    ACTION = "action"       # Action items, TODOs
    URL = "url"             # URLs, paths
    TECHNICAL = "technical" # Technical terms
    QUOTE = "quote"         # Quoted text
    QUESTION = "question"   # Questions asked


@dataclass
class ExtractedFact:
    """A fact extracted from text."""
    fact_type: FactType
    value: str
    context: str = ""       # Surrounding sentence
    position: int = 0       # Position in original text
    importance: float = 1.0

    def __str__(self) -> str:
        return f"[{self.fact_type.value}] {self.value}"


@dataclass
class ScoredSentence:
    """A sentence with importance score."""
    text: str
    position: int
    score: float
    facts: List[ExtractedFact] = field(default_factory=list)
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())


class SmartSummarizer:
    """
    Extractive summarizer that preserves key facts.

    Uses sentence scoring based on:
    - Position (first/last sentences matter more)
    - Fact density (sentences with names, numbers, code)
    - Keyword overlap with query (if provided)
    - TF-IDF of words in sentence
    """

    # Patterns for fact extraction
    PATTERNS = {
        # Names: Capitalized words (2+ in sequence for full names)
        FactType.NAME: [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',  # "John Smith" or "John David Smith"
            r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.\s*[A-Z][a-z]+\b',  # "Dr. Smith"
            r'@[a-zA-Z_][a-zA-Z0-9_]+',  # "@username"
        ],
        # Numbers: measurements, dates, percentages, counts
        FactType.NUMBER: [
            r'\b\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|ms|s|m|h|min|sec|%)\b',  # "8GB", "100ms"
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # "01/20/2026"
            r'\b\d{4}-\d{2}-\d{2}\b',  # "2026-01-20"
            r'\b\d+(?:,\d{3})*\b(?=\s+(?:times|users|files|items|requests|tokens|words))',  # "1,000 users"
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # "$100.00"
            r'\b\d+\s*(?:to|-)\s*\d+\b',  # "5 to 10", "5-10"
            r'\bport\s+\d+\b',  # "port 8765"
        ],
        # Code: backtick snippets, function calls, paths
        FactType.CODE: [
            r'`[^`]+`',  # `code`
            r'```[\s\S]*?```',  # ```code blocks```
            r'\b[a-z_][a-z0-9_]+\([^)]*\)',  # function_call() - min 2 chars
            r'\b[a-z_][a-z0-9_]+\.[a-z_][a-z0-9_]+',  # module.function - min 2 chars each
            r'(?:^|[\s(])[~/][a-zA-Z0-9_\-./]+\.[a-z]{1,4}\b',  # /path/to/file.py or ~/path
        ],
        # Action items: TODO, FIXME, action verbs
        FactType.ACTION: [
            r'\b(?:TODO|FIXME|NOTE|HACK|XXX):\s*[^.!?\n]+',
            r'\b(?:need to|must|should|have to)\s+[^.!?\n]{10,}',  # Min 10 chars after verb
            r'\b(?:action item|next step)s?:\s*[^.!?\n]+',
        ],
        # URLs
        FactType.URL: [
            r'https?://[^\s<>"\']+',
            r'www\.[^\s<>"\']+',
        ],
        # Technical terms: CamelCase, SCREAMING_SNAKE, known tech terms
        FactType.TECHNICAL: [
            r'\b[A-Z][a-z]{2,}[A-Z][a-z]+(?:[A-Z][a-z]+)*\b',  # CamelCase (min 3+2 chars per part)
            r'\b[A-Z]{2}[A-Z0-9_]{2,}\b',  # CONSTANT_NAME (starts with 2+ caps, min 4 total)
            r'\b(?:MLX|API|SDK|CLI|SQL|HTTP|JSON|XML|HTML|CSS|RAM|CPU|GPU|LLM|LoRA|RVC)\b',
            r'\b(?:Qwen|Llama|Mistral|Claude|GPT)[0-9\.\-]+[A-Za-z]*\b',  # Model names
            r'\b[a-z]+2vec\b',  # *2vec models like emotion2vec
        ],
        # Quoted text (min 10 chars)
        FactType.QUOTE: [
            r'"[^"]{10,}"',  # "quoted text"
            r"'[^']{10,}'",  # 'quoted text'
        ],
        # Questions
        FactType.QUESTION: [
            r'[A-Z][^.!?]*\?',  # Sentence starting with capital ending with ?
        ],
    }

    # Stop words for TF-IDF
    STOP_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
        'before', 'after', 'this', 'that', 'these', 'those', 'it', 'its',
        'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'which',
        'who', 'whom', 'whose', 'what', 'why', 'how', 'all', 'each', 'every',
        'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'also', 'now', 'here', 'there', 'can', 'about', 'over', 'out', 'up',
        'i', 'you', 'he', 'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'our', 'their', 'mine', 'yours', 'ours', 'theirs',
    }

    # Tokenization factor (words to tokens, ~1.3 for Qwen)
    TOKENIZATION_FACTOR = 1.3

    def __init__(self, preserve_types: Optional[List[str]] = None):
        """
        Initialize summarizer.

        Args:
            preserve_types: List of fact types to always preserve.
                           Default: ['names', 'code', 'numbers', 'actions']
        """
        self.preserve_types = preserve_types or ['names', 'code', 'numbers', 'actions']
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for speed."""
        self._compiled_patterns = {}
        # Types that need case-sensitive matching
        case_sensitive_types = {FactType.NAME, FactType.TECHNICAL, FactType.CODE}

        for fact_type, patterns in self.PATTERNS.items():
            flags = 0 if fact_type in case_sensitive_types else re.IGNORECASE
            self._compiled_patterns[fact_type] = [
                re.compile(p, flags) for p in patterns
            ]

    def extract_key_facts(self, text: str) -> List[ExtractedFact]:
        """
        Extract key facts from text.

        Returns list of facts with types: names, numbers, code, actions, etc.

        Args:
            text: Input text to extract from

        Returns:
            List of ExtractedFact objects
        """
        facts = []
        seen_values = set()  # Deduplicate

        for fact_type, compiled_list in self._compiled_patterns.items():
            for pattern in compiled_list:
                for match in pattern.finditer(text):
                    value = match.group().strip()

                    # Skip if too short or already seen
                    if len(value) < 2 or value.lower() in seen_values:
                        continue

                    # Get context (surrounding text)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()

                    # Calculate importance
                    importance = self._calculate_fact_importance(fact_type, value)

                    facts.append(ExtractedFact(
                        fact_type=fact_type,
                        value=value,
                        context=context,
                        position=match.start(),
                        importance=importance
                    ))
                    seen_values.add(value.lower())

        # Sort by position
        facts.sort(key=lambda f: f.position)
        return facts

    def _calculate_fact_importance(self, fact_type: FactType, value: str) -> float:
        """Calculate importance score for a fact."""
        base_scores = {
            FactType.ACTION: 1.0,      # Actions are most important
            FactType.CODE: 0.95,       # Code snippets
            FactType.QUESTION: 0.9,    # Questions need answers
            FactType.NUMBER: 0.85,     # Measurements, dates
            FactType.NAME: 0.8,        # Names/entities
            FactType.URL: 0.75,        # URLs
            FactType.TECHNICAL: 0.7,   # Technical terms
            FactType.QUOTE: 0.6,       # Quotes
        }
        score = base_scores.get(fact_type, 0.5)

        # Boost for longer values (more specific)
        if len(value) > 20:
            score += 0.05

        return min(1.0, score)

    def summarize(
        self,
        text: str,
        max_tokens: int = 200,
        preserve_types: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> str:
        """
        Summarize text while preserving key facts.

        Uses extractive summarization - selects most important sentences.

        Args:
            text: Text to summarize
            max_tokens: Maximum tokens in summary (~1.3x words)
            preserve_types: Override default preserve types
            query: Optional query to boost relevant sentences

        Returns:
            Summarized text
        """
        if not text or not text.strip():
            return ""

        # Convert max_tokens to max_words
        max_words = int(max_tokens / self.TOKENIZATION_FACTOR)

        # Extract facts first
        facts = self.extract_key_facts(text)

        # Split into sentences
        sentences = self._split_sentences(text)
        if not sentences:
            return text[:max_words * 5]  # Fallback: truncate

        # Score sentences
        scored = self._score_sentences(sentences, facts, query)

        # Select sentences that fit budget
        selected = self._select_sentences(scored, max_words)

        # Reconstruct in original order
        selected.sort(key=lambda s: s.position)

        # Build summary
        summary_parts = [s.text for s in selected]
        summary = " ".join(summary_parts)

        # Ensure we include critical facts even if not in selected sentences
        summary = self._ensure_critical_facts(summary, facts, max_words, preserve_types)

        return summary.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Handle common abbreviations
        text = re.sub(r'(Mr|Mrs|Ms|Dr|Prof|Jr|Sr|vs|etc|i\.e|e\.g)\.',
                      r'\1<PERIOD>', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Restore periods
        sentences = [s.replace('<PERIOD>', '.') for s in sentences]

        # Filter empty/too short
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        return sentences

    def _score_sentences(
        self,
        sentences: List[str],
        facts: List[ExtractedFact],
        query: Optional[str] = None
    ) -> List[ScoredSentence]:
        """Score sentences for importance."""
        scored = []
        total_sentences = len(sentences)

        # Build word frequency for TF-IDF
        all_words = []
        for s in sentences:
            all_words.extend(self._tokenize(s))
        word_freq = Counter(all_words)
        max_freq = max(word_freq.values()) if word_freq else 1

        # Query terms for boosting
        query_terms = set()
        if query:
            query_terms = set(self._tokenize(query)) - self.STOP_WORDS

        # Map facts to sentence positions
        fact_positions = {}
        for fact in facts:
            for i, sent in enumerate(sentences):
                if fact.value in sent:
                    if i not in fact_positions:
                        fact_positions[i] = []
                    fact_positions[i].append(fact)

        for i, sentence in enumerate(sentences):
            words = self._tokenize(sentence)

            # Position score (U-shaped: first and last sentences important)
            position_ratio = i / total_sentences
            position_score = 1.0 - 4 * (position_ratio - 0.5) ** 2
            position_score = max(0.3, min(1.0, position_score))

            # First sentence bonus
            if i == 0:
                position_score = 1.0

            # TF-IDF score
            tfidf_score = 0.0
            content_words = [w for w in words if w.lower() not in self.STOP_WORDS]
            if content_words:
                for word in content_words:
                    tf = word_freq[word] / max_freq
                    # Simple IDF approximation
                    idf = 1.0 / (1.0 + word_freq[word])
                    tfidf_score += tf * idf
                tfidf_score /= len(content_words)

            # Fact density score
            sentence_facts = fact_positions.get(i, [])
            fact_score = min(1.0, len(sentence_facts) * 0.3)

            # High-value fact bonus
            for fact in sentence_facts:
                if fact.fact_type in [FactType.ACTION, FactType.CODE, FactType.NUMBER]:
                    fact_score += 0.1

            # Query overlap score
            query_score = 0.0
            if query_terms:
                overlap = len(query_terms & set(w.lower() for w in words))
                query_score = min(1.0, overlap / len(query_terms)) if query_terms else 0.0

            # Combined score
            score = (
                position_score * 0.25 +
                tfidf_score * 0.2 +
                fact_score * 0.35 +
                query_score * 0.2
            )

            scored.append(ScoredSentence(
                text=sentence,
                position=i,
                score=score,
                facts=sentence_facts
            ))

        return scored

    def _select_sentences(
        self,
        scored: List[ScoredSentence],
        max_words: int
    ) -> List[ScoredSentence]:
        """Select best sentences that fit word budget."""
        # Sort by score (descending)
        sorted_sentences = sorted(scored, key=lambda s: s.score, reverse=True)

        selected = []
        current_words = 0

        for sentence in sorted_sentences:
            if current_words + sentence.word_count <= max_words:
                selected.append(sentence)
                current_words += sentence.word_count

            # Stop if we have enough
            if current_words >= max_words * 0.9:
                break

        return selected

    def _ensure_critical_facts(
        self,
        summary: str,
        facts: List[ExtractedFact],
        max_words: int,
        preserve_types: Optional[List[str]] = None
    ) -> str:
        """Ensure critical facts are in summary."""
        preserve = preserve_types or self.preserve_types
        type_map = {
            'names': FactType.NAME,
            'numbers': FactType.NUMBER,
            'code': FactType.CODE,
            'actions': FactType.ACTION,
            'urls': FactType.URL,
            'technical': FactType.TECHNICAL,
        }

        # Get types to preserve
        preserve_fact_types = {type_map.get(t) for t in preserve if t in type_map}

        # Find critical facts not in summary
        missing_facts = []
        for fact in facts:
            if fact.fact_type in preserve_fact_types:
                if fact.value not in summary:
                    missing_facts.append(fact)

        # Add top missing facts if space allows
        current_words = len(summary.split())
        facts_to_add = []

        for fact in sorted(missing_facts, key=lambda f: f.importance, reverse=True):
            fact_words = len(fact.value.split())
            if current_words + fact_words + 5 <= max_words:  # +5 for connector
                facts_to_add.append(fact.value)
                current_words += fact_words + 2

            if len(facts_to_add) >= 3:  # Limit additions
                break

        if facts_to_add:
            summary = summary.rstrip('.') + ". Key: " + ", ".join(facts_to_add) + "."

        return summary

    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        return re.findall(r'\b\w+\b', text.lower())

    def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        preserve_recent: int = 2
    ) -> List[Dict[str, str]]:
        """
        Summarize conversation history while preserving meaning.

        Keeps recent messages intact, summarizes older ones.

        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            max_tokens: Total token budget for all messages
            preserve_recent: Number of recent messages to keep intact

        Returns:
            Condensed message list
        """
        if not messages:
            return messages

        # Estimate current tokens
        total_tokens = sum(
            int(len(m.get("content", "").split()) * self.TOKENIZATION_FACTOR)
            for m in messages
        )

        if total_tokens <= max_tokens:
            return messages  # Already fits

        # Split recent and older
        if len(messages) <= preserve_recent:
            # Just summarize all
            return self._summarize_all_messages(messages, max_tokens)

        recent = messages[-preserve_recent:]
        older = messages[:-preserve_recent]

        # Calculate budgets
        recent_tokens = sum(
            int(len(m.get("content", "").split()) * self.TOKENIZATION_FACTOR)
            for m in recent
        )
        older_budget = max(100, max_tokens - recent_tokens)

        # Merge older messages into summary
        older_text = self._merge_messages(older)
        summary = self.summarize(older_text, max_tokens=older_budget)

        # Create condensed history
        condensed = [
            {"role": "system", "content": f"[Earlier conversation summary: {summary}]"}
        ]
        condensed.extend(recent)

        return condensed

    def _merge_messages(self, messages: List[Dict[str, str]]) -> str:
        """Merge messages into single text for summarization."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prefix = "User:" if role == "user" else "Assistant:"
            parts.append(f"{prefix} {content}")
        return "\n".join(parts)

    def _summarize_all_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """Summarize all messages when we can't preserve any."""
        merged = self._merge_messages(messages)
        summary = self.summarize(merged, max_tokens=max_tokens - 20)
        return [
            {"role": "system", "content": f"[Conversation summary: {summary}]"}
        ]

    def get_compression_stats(
        self,
        original: str,
        summary: str
    ) -> Dict[str, Any]:
        """Get statistics about the summarization."""
        orig_words = len(original.split())
        summ_words = len(summary.split())

        orig_facts = self.extract_key_facts(original)
        summ_facts = self.extract_key_facts(summary)

        # Count preserved facts
        orig_values = {f.value.lower() for f in orig_facts}
        summ_values = {f.value.lower() for f in summ_facts}
        preserved = orig_values & summ_values

        return {
            "original_words": orig_words,
            "summary_words": summ_words,
            "compression_ratio": summ_words / orig_words if orig_words > 0 else 1.0,
            "original_facts": len(orig_facts),
            "preserved_facts": len(preserved),
            "fact_retention": len(preserved) / len(orig_facts) if orig_facts else 1.0,
            "reduction_percent": (1 - summ_words / orig_words) * 100 if orig_words > 0 else 0
        }


# Convenience functions
def summarize(text: str, max_tokens: int = 200) -> str:
    """Quick summarize function."""
    summarizer = SmartSummarizer()
    return summarizer.summarize(text, max_tokens=max_tokens)


def extract_facts(text: str) -> List[ExtractedFact]:
    """Quick fact extraction."""
    summarizer = SmartSummarizer()
    return summarizer.extract_key_facts(text)


def summarize_conversation(
    messages: List[Dict[str, str]],
    max_tokens: int = 500
) -> List[Dict[str, str]]:
    """Quick conversation summarization."""
    summarizer = SmartSummarizer()
    return summarizer.summarize_conversation(messages, max_tokens=max_tokens)


if __name__ == "__main__":
    # Demo
    print("Smart Summarizer Demo")
    print("=" * 60)

    # Test text - longer for compression testing
    test_text = """
    David Quinton has been working on SAM, a self-improving AI assistant that runs on his
    M2 Mac Mini with 8GB RAM. The project uses MLX for inference with Qwen2.5-1.5B
    as the base model. Yesterday on 01/20/2026, he implemented the voice pipeline
    using emotion2vec for emotion detection.

    The main code is at ~/ReverseLab/SAM/warp_tauri/sam_brain/sam_api.py which
    handles HTTP requests on port 8765. TODO: Implement smarter summarization
    to preserve key facts during context compression. This is a critical feature
    that will help manage the limited context window on small language models.

    Performance metrics show the system processes requests in under 100ms for
    simple queries. The semantic memory uses MiniLM-L6-v2 embeddings stored in
    /Volumes/David External/sam_memory/. John Smith from the MLX team mentioned
    that "KV-cache quantization can save 75% memory" which was very helpful.

    The architecture follows a modular design where each component can be updated
    independently. The cognitive module handles reasoning while the memory module
    handles persistence. Voice processing uses Apple's native speech APIs combined
    with the RVC voice cloning system for SAM's distinctive voice.

    Integration testing has shown promising results with response times averaging
    50-100ms for simple queries and 200-500ms for complex reasoning tasks. The
    system handles approximately 1,000 requests per day during active development.

    Next steps include: 1) Add conversation summarization, 2) Implement fact
    extraction, 3) Integrate with token budget manager. The target is to compress
    2000 tokens down to 500 tokens while retaining 90% of key information.

    The project timeline aims for completion by February 2026 with a budget of
    $5,000 for cloud compute resources if needed. Dr. Sarah Chen has offered to
    review the emotion detection algorithms once they are finalized.
    """

    summarizer = SmartSummarizer()

    # Test fact extraction
    print("\n1. Extracted Facts:")
    print("-" * 40)
    facts = summarizer.extract_key_facts(test_text)
    for fact in facts[:15]:  # Show top 15
        print(f"  {fact}")

    # Test summarization
    print("\n2. Summary (max 200 tokens):")
    print("-" * 40)
    summary = summarizer.summarize(test_text, max_tokens=200)
    print(summary)

    # Stats
    stats = summarizer.get_compression_stats(test_text, summary)
    print("\n3. Compression Stats:")
    print("-" * 40)
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    # Test conversation summarization
    print("\n4. Conversation Summarization:")
    print("-" * 40)
    messages = [
        {"role": "user", "content": "How do I set up the MLX model for SAM?"},
        {"role": "assistant", "content": "You need to install mlx-lm and download Qwen2.5-1.5B. The model should be placed in ~/ReverseLab/SAM/warp_tauri/sam_brain/models/."},
        {"role": "user", "content": "What about the LoRA adapter?"},
        {"role": "assistant", "content": "The LoRA adapter is trained separately using finetune_mlx.py. It fine-tunes the base model on SAM's personality data. Training takes about 2 hours on M2."},
        {"role": "user", "content": "Great, and how do I start the API server?"},
        {"role": "assistant", "content": "Run python3 sam_api.py server 8765 from the sam_brain directory. It will start the HTTP server on port 8765."},
        {"role": "user", "content": "What ports does SAM use and can I change them?"},
        {"role": "assistant", "content": "SAM uses port 8765 for the main API and port 8766 for the vision server. You can change these by passing different port numbers as command line arguments."},
        {"role": "user", "content": "Is there a way to run it in the background?"},
        {"role": "assistant", "content": "Yes, you can use nohup or create a launchd service. For development, I recommend using tmux or screen to keep the session alive."},
    ]

    condensed = summarizer.summarize_conversation(messages, max_tokens=150)
    print(f"Original messages: {len(messages)}")
    print(f"Condensed messages: {len(condensed)}")
    for msg in condensed:
        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        print(f"  [{msg['role']}]: {content}")

    # Test with query-based summarization
    print("\n5. Query-Focused Summary:")
    print("-" * 40)
    query_summary = summarizer.summarize(
        test_text,
        max_tokens=100,
        query="What are the performance metrics and response times?"
    )
    print(query_summary)
