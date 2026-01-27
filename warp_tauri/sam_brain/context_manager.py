#!/usr/bin/env python3
"""
SAM Context Manager - Maximize context utilization on limited hardware

Strategies:
1. Structured anchors - critical info at start/end where attention is highest
2. Rolling summarization - compress old context, keep recent verbatim
3. RAG integration - fetch only relevant context, not everything
4. Token budgeting - allocate tokens by importance

See also: context_budget.py for advanced RAG-aware budget allocation
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

# Try to import sentence-transformers for embeddings, fall back to simple matching
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# Import advanced context budget allocator
try:
    from context_budget import ContextBudget, QueryType, ContextBuilder
    CONTEXT_BUDGET_AVAILABLE = True
except ImportError:
    CONTEXT_BUDGET_AVAILABLE = False


@dataclass
class ContextChunk:
    """A piece of context with metadata"""
    content: str
    source: str  # 'user', 'assistant', 'system', 'rag'
    importance: float  # 0-1, higher = more important
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0

    def __post_init__(self):
        # Rough token estimate: ~4 chars per token
        self.tokens = len(self.content) // 4


class ContextManager:
    """
    Manages context window for maximum utilization.

    Token budget allocation (512 tokens):
    - CRITICAL section: 100 tokens (system prompt, personality)
    - RAG section: 150 tokens (retrieved relevant content)
    - HISTORY section: 200 tokens (summarized old + recent verbatim)
    - QUERY section: 62 tokens (current user input)
    """

    MAX_TOKENS = 512
    BUDGET = {
        'critical': 100,   # Always included, high attention
        'rag': 150,        # Retrieved context
        'history': 200,    # Conversation history
        'query': 62        # Current input
    }

    def __init__(self,
                 db_paths: Optional[List[str]] = None,
                 personality_prompt: Optional[str] = None):
        """
        Args:
            db_paths: List of SQLite database paths for RAG
            personality_prompt: SAM's core personality (goes in CRITICAL)
        """
        self.db_paths = db_paths or []
        self.conversation_history: List[ContextChunk] = []
        self.summary = ""  # Compressed old conversation

        # Default SAM personality
        self.personality = personality_prompt or (
            "You are SAM, a confident and flirty AI assistant. "
            "Be direct, witty, and helpful. Keep responses concise."
        )

        # Initialize embeddings if available
        self.embedder = None
        if EMBEDDINGS_AVAILABLE:
            try:
                # Use small, fast model
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                pass

    def add_message(self, role: str, content: str, importance: float = 0.5):
        """Add a message to conversation history"""
        chunk = ContextChunk(
            content=content,
            source=role,
            importance=importance
        )
        self.conversation_history.append(chunk)

        # Trigger summarization if history too long
        self._maybe_summarize()

    def _maybe_summarize(self):
        """Summarize old messages if history exceeds budget"""
        total_tokens = sum(c.tokens for c in self.conversation_history)

        if total_tokens > self.BUDGET['history'] * 1.5:
            # Keep last 3 messages verbatim, summarize the rest
            if len(self.conversation_history) > 3:
                old_messages = self.conversation_history[:-3]
                self.conversation_history = self.conversation_history[-3:]

                # Create summary of old messages
                old_text = "\n".join([
                    f"{c.source}: {c.content[:100]}"
                    for c in old_messages
                ])

                # Simple extractive summary: key points
                self.summary = self._extract_summary(old_text)

    def _extract_summary(self, text: str) -> str:
        """Extract key points from text (no LLM needed)"""
        lines = text.split('\n')

        # Keep lines with important markers
        important = []
        for line in lines:
            # Prioritize questions, actions, key facts
            if any(marker in line.lower() for marker in
                   ['?', 'remember', 'important', 'must', 'need', 'want',
                    'code:', 'error:', 'file:', 'created', 'fixed']):
                important.append(line[:80])

        return " | ".join(important[:5]) if important else ""

    def retrieve_context(self, query: str, top_k: int = 3) -> List[str]:
        """
        RAG: Retrieve relevant context from databases.

        Uses embeddings if available, falls back to keyword matching.
        """
        results = []

        for db_path in self.db_paths:
            if not Path(db_path).exists():
                continue

            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get table info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                for table in tables:
                    # Try to find text columns
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]

                    text_cols = [c for c in columns if any(
                        t in c.lower() for t in ['text', 'content', 'body', 'description', 'title']
                    )]

                    if not text_cols:
                        continue

                    # Keyword search
                    keywords = query.lower().split()[:5]
                    for col in text_cols:
                        for kw in keywords:
                            if len(kw) < 3:
                                continue
                            try:
                                cursor.execute(
                                    f"SELECT {col} FROM {table} WHERE {col} LIKE ? LIMIT 2",
                                    (f"%{kw}%",)
                                )
                                for row in cursor.fetchall():
                                    text = str(row[0])[:200]
                                    if text and text not in results:
                                        results.append(text)
                            except:
                                continue

                conn.close()

            except Exception as e:
                continue

        # Use embeddings to rank if available
        if self.embedder and results:
            query_emb = self.embedder.encode(query)
            result_embs = self.embedder.encode(results)

            # Cosine similarity
            scores = np.dot(result_embs, query_emb) / (
                np.linalg.norm(result_embs, axis=1) * np.linalg.norm(query_emb)
            )

            # Sort by score
            ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
            results = [r[0] for r in ranked[:top_k]]

        return results[:top_k]

    def build_context(self, query: str) -> str:
        """
        Build optimized context for the model.

        Structure:
        <CRITICAL>personality + key facts</CRITICAL>
        <RAG>retrieved relevant content</RAG>
        <HISTORY>summary + recent messages</HISTORY>
        <QUERY>current user input</QUERY>

        This structure puts important info at positions with highest attention.
        """
        sections = []

        # 1. CRITICAL section (start - high attention)
        critical_content = self.personality
        if self.summary:
            critical_content += f"\n[Previous: {self.summary}]"

        sections.append(f"<CRITICAL>\n{critical_content[:self.BUDGET['critical']*4]}\n</CRITICAL>")

        # 2. RAG section (retrieved context)
        rag_results = self.retrieve_context(query)
        if rag_results:
            rag_text = "\n".join(rag_results)[:self.BUDGET['rag']*4]
            sections.append(f"<CONTEXT>\n{rag_text}\n</CONTEXT>")

        # 3. HISTORY section (recent conversation)
        if self.conversation_history:
            history_text = "\n".join([
                f"{c.source}: {c.content}"
                for c in self.conversation_history[-3:]
            ])[:self.BUDGET['history']*4]
            sections.append(f"<RECENT>\n{history_text}\n</RECENT>")

        # 4. QUERY section (end - high attention)
        sections.append(f"<QUERY>\n{query[:self.BUDGET['query']*4]}\n</QUERY>")

        return "\n\n".join(sections)

    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage by section"""
        return {
            'critical': len(self.personality) // 4,
            'summary': len(self.summary) // 4,
            'history': sum(c.tokens for c in self.conversation_history),
            'total_budget': self.MAX_TOKENS
        }

    def build_context_with_budget(
        self,
        query: str,
        total_tokens: int = 2000,
        user_facts: str = "",
        project_context: str = "",
        working_memory: str = ""
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build context using advanced ContextBudget allocation.

        This method provides query-type-aware budget allocation and
        intelligent truncation for each context section.

        Args:
            query: User query
            total_tokens: Total token budget (default: 2000)
            user_facts: Optional user facts/preferences
            project_context: Optional project context
            working_memory: Optional working memory content

        Returns:
            Tuple of (formatted context, token usage dict)

        Falls back to build_context() if ContextBudget is unavailable.
        """
        if not CONTEXT_BUDGET_AVAILABLE:
            # Fallback to simple context building
            return self.build_context(query), self.get_token_usage()

        budget = ContextBudget(default_budget=total_tokens)
        builder = ContextBuilder(budget)

        # Prepare conversation history
        history_text = ""
        if self.conversation_history:
            history_text = "\n".join([
                f"{c.source}: {c.content}"
                for c in self.conversation_history
            ])

        # Prepare system prompt with summary
        system_prompt = self.personality
        if self.summary:
            system_prompt += f"\n[Previous: {self.summary}]"

        # Retrieve RAG results
        rag_results = "\n".join(self.retrieve_context(query))

        # Build context with budget allocation
        context, usage = builder.build(
            query=query,
            system_prompt=system_prompt,
            user_facts=user_facts,
            project_context=project_context,
            rag_results=rag_results,
            conversation_history=history_text,
            working_memory=working_memory,
            total_tokens=total_tokens
        )

        return context, usage

    def get_rag_budget(self, total_tokens: int, query: str) -> int:
        """
        Get recommended RAG token budget based on query type.

        Args:
            total_tokens: Total available tokens
            query: User query (used to detect query type)

        Returns:
            Recommended token budget for RAG results
        """
        if not CONTEXT_BUDGET_AVAILABLE:
            # Simple fallback: ~20% of budget for RAG
            return int(total_tokens * 0.20)

        budget = ContextBudget(default_budget=total_tokens)
        query_type = budget.detect_query_type(query)
        return budget.get_rag_budget(total_tokens, query_type)


class TrainingDataGenerator:
    """
    Generate training examples that teach context attention.

    Creates examples where the model must use information from
    different positions in the context.
    """

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)

    def generate_recall_examples(self, n: int = 100) -> List[Dict]:
        """
        Generate examples that require recalling info from context.

        Pattern: Tell model something → distraction → ask about it
        """
        examples = []

        # Facts to remember
        facts = [
            ("favorite color", "blue", "What's my favorite color?"),
            ("secret code", "ALPHA7", "What was the secret code?"),
            ("meeting time", "3pm", "When is the meeting?"),
            ("project name", "Phoenix", "What's the project called?"),
            ("password hint", "my cat's name", "What's the password hint?"),
            ("deadline", "Friday", "When is the deadline?"),
            ("budget", "$5000", "What's the budget?"),
            ("contact", "sarah@email.com", "Who should I contact?"),
        ]

        distractions = [
            "Tell me about machine learning.",
            "What's the weather like?",
            "How do I make pasta?",
            "Explain quantum computing.",
            "What's 2+2?",
        ]

        import random

        for i in range(n):
            fact_name, fact_value, question = random.choice(facts)
            distraction = random.choice(distractions)

            example = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Remember this: my {fact_name} is {fact_value}. Got it?"
                    },
                    {
                        "role": "assistant",
                        "content": f"Got it! Your {fact_name} is {fact_value}. I'll remember that."
                    },
                    {
                        "role": "user",
                        "content": distraction
                    },
                    {
                        "role": "assistant",
                        "content": "[Brief response to distraction]"
                    },
                    {
                        "role": "user",
                        "content": question
                    },
                    {
                        "role": "assistant",
                        "content": f"Your {fact_name} is {fact_value}."
                    }
                ]
            }
            examples.append(example)

        return examples

    def generate_structured_context_examples(self, n: int = 50) -> List[Dict]:
        """
        Generate examples using <CRITICAL>/<CONTEXT>/<QUERY> structure.

        Teaches model to pay attention to marked sections.
        """
        examples = []

        scenarios = [
            {
                "critical": "User prefers short answers. User's name is Alex.",
                "context": "Previous topic: Python programming",
                "query": "What's my name?",
                "response": "Your name is Alex."
            },
            {
                "critical": "User is expert level. Skip basics.",
                "context": "Discussing neural networks",
                "query": "How does backprop work?",
                "response": "Backprop computes gradients via chain rule, propagating error from output to input layers. dL/dw = dL/da * da/dz * dz/dw for each layer."
            },
            {
                "critical": "User wants SAM personality: confident, witty.",
                "context": "User asked about the weather earlier",
                "query": "You're pretty smart",
                "response": "Pretty smart? I prefer devastatingly intelligent, but I'll take the compliment. What can this big brain do for you?"
            },
        ]

        import random

        for i in range(n):
            scenario = random.choice(scenarios)

            structured_input = f"""<CRITICAL>
{scenario['critical']}
</CRITICAL>

<CONTEXT>
{scenario['context']}
</CONTEXT>

<QUERY>
{scenario['query']}
</QUERY>"""

            example = {
                "messages": [
                    {"role": "user", "content": structured_input},
                    {"role": "assistant", "content": scenario['response']}
                ]
            }
            examples.append(example)

        return examples

    def save_examples(self, examples: List[Dict]):
        """Save examples as JSONL"""
        with open(self.output_path, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')
        print(f"Saved {len(examples)} examples to {self.output_path}")


def generate_context_training_data():
    """Generate training data for context attention"""
    output_dir = Path("/Volumes/David External/sam_training")
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = TrainingDataGenerator(output_dir / "context_attention.jsonl")

    recall_examples = generator.generate_recall_examples(100)
    structured_examples = generator.generate_structured_context_examples(50)

    all_examples = recall_examples + structured_examples
    generator.save_examples(all_examples)

    return len(all_examples)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        count = generate_context_training_data()
        print(f"Generated {count} context attention training examples")
    else:
        # Demo usage
        cm = ContextManager(
            db_paths=[
                "/Volumes/David External/dark_psych_archive/dark_psych.db",
                "/Volumes/David External/coding_training/code_training.db"
            ],
            personality_prompt="You are SAM, a confident and flirty AI. Be witty and helpful."
        )

        # Simulate conversation
        cm.add_message("user", "Remember: my favorite number is 42")
        cm.add_message("assistant", "Got it! 42 - the answer to everything, right?")
        cm.add_message("user", "Tell me about Python decorators")
        cm.add_message("assistant", "Decorators wrap functions to add behavior...")

        # Build context for new query
        context = cm.build_context("What was my favorite number?")
        print("=" * 50)
        print("OPTIMIZED CONTEXT:")
        print("=" * 50)
        print(context)
        print("=" * 50)
        print("\nToken usage:", cm.get_token_usage())
