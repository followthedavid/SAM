#!/usr/bin/env python3
"""
Infinite Context Engine - Advanced State Management for Tiny Models

Enables coherent long-form generation from small context window models through:
1. Hierarchical memory (working/short/long-term)
2. Domain-specific state handlers (story, code, analysis, conversation)
3. Adaptive chunking with natural break detection
4. Coherence scoring and self-healing
5. State compression and retrieval
6. Streaming with persistence

Usage:
    from infinite_context import InfiniteContext, Domain

    ctx = InfiniteContext(domain=Domain.STORY)

    # Single call, handles everything internally
    full_response = ctx.generate("Write a 10,000 word story about...")

    # Or streaming
    for chunk in ctx.stream("Write a detailed analysis of..."):
        print(chunk, end="", flush=True)
"""

import json
import hashlib
import sqlite3
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Generator, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import threading


# =============================================================================
# CORE TYPES
# =============================================================================

class Domain(Enum):
    """Generation domains with specialized state handling"""
    CONVERSATION = "conversation"  # Multi-turn chat
    STORY = "story"                # Creative writing, roleplay
    CODE = "code"                  # Programming tasks
    ANALYSIS = "analysis"          # Research, documentation
    INSTRUCTION = "instruction"    # Step-by-step guides
    FREEFORM = "freeform"          # No specific structure


class MemoryTier(Enum):
    """Hierarchical memory levels"""
    WORKING = "working"      # Current chunk context (always included)
    SHORT_TERM = "short"     # Recent chunks, compressed (sliding window)
    LONG_TERM = "long"       # Persistent facts, heavily compressed
    EPISODIC = "episodic"    # Key events/milestones (story beats, function defs)


@dataclass
class StateFragment:
    """A piece of tracked state"""
    key: str
    value: Any
    tier: MemoryTier
    domain: str
    importance: float  # 0.0 to 1.0, affects compression priority
    created_at: float
    accessed_at: float
    access_count: int = 0

    def touch(self):
        """Mark as recently accessed"""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class Chunk:
    """A generated text chunk with metadata"""
    content: str
    index: int
    tokens_approx: int
    coherence_score: float
    continuation_hint: str  # Last sentence/paragraph for next chunk
    state_snapshot: Dict[str, Any]
    generated_at: float


@dataclass
class GenerationPlan:
    """High-level plan for long generation"""
    outline: List[str]
    estimated_chunks: int
    domain: Domain
    quality_threshold: float
    max_retries: int


# =============================================================================
# STATE HANDLERS - Domain-Specific Intelligence
# =============================================================================

class StateHandler(ABC):
    """Abstract base for domain-specific state tracking"""

    @abstractmethod
    def extract_state(self, text: str, existing_state: Dict) -> Dict:
        """Extract relevant state from generated text"""
        pass

    @abstractmethod
    def compress_state(self, state: Dict, target_tokens: int) -> str:
        """Compress state to fit context window"""
        pass

    @abstractmethod
    def get_continuation_prompt(self, state: Dict, original_prompt: str, chunk_index: int) -> str:
        """Generate prompt for next chunk"""
        pass

    @abstractmethod
    def detect_natural_break(self, text: str) -> Tuple[str, str]:
        """Find natural break point, return (complete, overflow)"""
        pass

    @abstractmethod
    def score_coherence(self, prev_chunk: str, curr_chunk: str, state: Dict) -> float:
        """Score how well chunks flow together (0.0 to 1.0)"""
        pass


class StoryStateHandler(StateHandler):
    """Handler for creative writing and roleplay"""

    def extract_state(self, text: str, existing_state: Dict) -> Dict:
        state = existing_state.copy()

        # Track characters (look for capitalized names with actions)
        char_pattern = r'\b([A-Z][a-z]+)\s+(?:said|asked|replied|whispered|shouted|looked|turned|walked|ran|felt|thought|knew|wanted)'
        characters = set(re.findall(char_pattern, text))
        state.setdefault("characters", set()).update(characters)

        # Track locations (after prepositions)
        loc_pattern = r'(?:in|at|to|from|inside|outside|near|by)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        locations = set(re.findall(loc_pattern, text))
        state.setdefault("locations", set()).update(locations)

        # Track current scene (last paragraph context)
        paragraphs = text.strip().split('\n\n')
        if paragraphs:
            state["current_scene"] = paragraphs[-1][:500]

        # Track emotional tone
        positive = len(re.findall(r'\b(happy|joy|love|excited|pleased|delighted|warm)\b', text.lower()))
        negative = len(re.findall(r'\b(sad|angry|fear|worried|anxious|dark|cold|pain)\b', text.lower()))
        state["emotional_tone"] = "positive" if positive > negative else "negative" if negative > positive else "neutral"

        # Track plot points (sentences with strong verbs)
        plot_pattern = r'[A-Z][^.!?]*(?:discovered|revealed|realized|decided|escaped|arrived|died|killed|married|betrayed|found|lost)[^.!?]*[.!?]'
        plot_points = re.findall(plot_pattern, text)
        state.setdefault("plot_points", []).extend(plot_points[-3:])  # Keep last 3

        # Track time markers
        time_pattern = r'\b(morning|afternoon|evening|night|dawn|dusk|midnight|noon|next day|hours later|days later|weeks later|years later)\b'
        times = re.findall(time_pattern, text.lower())
        if times:
            state["last_time_marker"] = times[-1]

        return state

    def compress_state(self, state: Dict, target_tokens: int) -> str:
        """Compress story state to brief context"""
        parts = []

        # Characters (most important)
        if state.get("characters"):
            chars = list(state["characters"])[:5]  # Top 5 characters
            parts.append(f"Characters: {', '.join(chars)}")

        # Current location
        if state.get("locations"):
            locs = list(state["locations"])[-2:]  # Recent locations
            parts.append(f"Location: {', '.join(locs)}")

        # Recent plot
        if state.get("plot_points"):
            recent_plot = state["plot_points"][-2:]
            parts.append(f"Recent events: {' '.join(recent_plot)}")

        # Current scene summary
        if state.get("current_scene"):
            scene = state["current_scene"][:200]
            parts.append(f"Current scene: {scene}...")

        # Tone
        if state.get("emotional_tone"):
            parts.append(f"Tone: {state['emotional_tone']}")

        return "\n".join(parts)

    def get_continuation_prompt(self, state: Dict, original_prompt: str, chunk_index: int) -> str:
        compressed = self.compress_state(state, 500)

        if chunk_index == 0:
            return original_prompt

        return f"""Continue this story seamlessly. DO NOT repeat previous content.

STORY STATE:
{compressed}

LAST PARAGRAPH (continue directly from here):
{state.get('current_scene', '')[-300:]}

Continue the story naturally, picking up exactly where it left off:"""

    def detect_natural_break(self, text: str) -> Tuple[str, str]:
        """Find natural story break (end of paragraph, scene, or sentence)"""
        # Prefer paragraph breaks
        if '\n\n' in text[-500:]:
            idx = text.rfind('\n\n', 0, len(text) - 100)
            if idx > len(text) * 0.6:  # At least 60% through
                return text[:idx], text[idx:].strip()

        # Fall back to sentence breaks
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 2:
            # Keep all but last sentence
            break_point = text.rfind(sentences[-1])
            if break_point > len(text) * 0.6:
                return text[:break_point].strip(), text[break_point:].strip()

        return text, ""

    def score_coherence(self, prev_chunk: str, curr_chunk: str, state: Dict) -> float:
        score = 1.0

        # Check for repeated opening (bad)
        if curr_chunk[:100] in prev_chunk:
            score -= 0.5

        # Check character consistency
        prev_chars = set(re.findall(r'\b([A-Z][a-z]+)\b', prev_chunk[-500:]))
        curr_chars = set(re.findall(r'\b([A-Z][a-z]+)\b', curr_chunk[:500]))
        if prev_chars and curr_chars:
            overlap = len(prev_chars & curr_chars) / max(len(prev_chars), 1)
            score *= (0.5 + 0.5 * overlap)  # Some overlap expected

        # Check for smooth transition
        prev_end = prev_chunk.strip()[-100:]
        curr_start = curr_chunk.strip()[:100]

        # Penalize if starts with same words
        if curr_start.split()[:3] == prev_end.split()[-3:]:
            score -= 0.3

        return max(0.0, min(1.0, score))


class CodeStateHandler(StateHandler):
    """Handler for code generation tasks"""

    def extract_state(self, text: str, existing_state: Dict) -> Dict:
        state = existing_state.copy()

        # Track defined functions
        func_pattern = r'(?:def|function|fn|func)\s+(\w+)\s*\('
        functions = re.findall(func_pattern, text)
        state.setdefault("functions", []).extend(functions)
        state["functions"] = list(set(state["functions"]))

        # Track defined classes
        class_pattern = r'(?:class|struct|interface|type)\s+(\w+)'
        classes = re.findall(class_pattern, text)
        state.setdefault("classes", []).extend(classes)
        state["classes"] = list(set(state["classes"]))

        # Track imports
        import_pattern = r'(?:import|from|require|use)\s+([^\n;]+)'
        imports = re.findall(import_pattern, text)
        state.setdefault("imports", []).extend(imports)
        state["imports"] = list(set(state["imports"]))

        # Track TODO/FIXME comments
        todo_pattern = r'(?:TODO|FIXME|XXX)[:\s]+([^\n]+)'
        todos = re.findall(todo_pattern, text)
        state["pending_todos"] = todos

        # Track last code block
        code_blocks = re.findall(r'```[\w]*\n([\s\S]*?)```', text)
        if code_blocks:
            state["last_code_block"] = code_blocks[-1][-1000:]

        # Detect language
        if 'def ' in text and ':' in text:
            state["language"] = "python"
        elif 'function ' in text or 'const ' in text or 'let ' in text:
            state["language"] = "javascript/typescript"
        elif 'fn ' in text and '-> ' in text:
            state["language"] = "rust"

        return state

    def compress_state(self, state: Dict, target_tokens: int) -> str:
        parts = []

        if state.get("language"):
            parts.append(f"Language: {state['language']}")

        if state.get("imports"):
            parts.append(f"Imports: {', '.join(state['imports'][:10])}")

        if state.get("classes"):
            parts.append(f"Classes defined: {', '.join(state['classes'])}")

        if state.get("functions"):
            parts.append(f"Functions defined: {', '.join(state['functions'][:15])}")

        if state.get("pending_todos"):
            parts.append(f"TODOs: {'; '.join(state['pending_todos'][:5])}")

        return "\n".join(parts)

    def get_continuation_prompt(self, state: Dict, original_prompt: str, chunk_index: int) -> str:
        if chunk_index == 0:
            return original_prompt

        compressed = self.compress_state(state, 500)
        last_code = state.get("last_code_block", "")[-500:]

        return f"""Continue implementing. DO NOT repeat previous code.

CODE STATE:
{compressed}

LAST CODE WRITTEN:
```
{last_code}
```

Continue from here, implementing the next part:"""

    def detect_natural_break(self, text: str) -> Tuple[str, str]:
        """Break at function/class boundaries"""
        # Look for function/class end
        patterns = [
            r'\n\n(?=(?:def|class|function|fn|pub fn)\s+)',  # Before new definition
            r'\n\n(?=(?:#|//|/\*)\s*(?:TODO|NEXT|SECTION))',  # Before comment sections
            r'```\n\n',  # After code blocks
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                # Find one past 60% mark
                for m in reversed(matches):
                    if m.start() > len(text) * 0.6:
                        return text[:m.start()], text[m.start():].strip()

        # Fall back to paragraph break
        if '\n\n' in text[-500:]:
            idx = text.rfind('\n\n', 0, len(text) - 100)
            if idx > len(text) * 0.5:
                return text[:idx], text[idx:].strip()

        return text, ""

    def score_coherence(self, prev_chunk: str, curr_chunk: str, state: Dict) -> float:
        score = 1.0

        # Check for duplicate function definitions (very bad)
        prev_funcs = set(re.findall(r'(?:def|function|fn)\s+(\w+)', prev_chunk))
        curr_funcs = set(re.findall(r'(?:def|function|fn)\s+(\w+)', curr_chunk[:1000]))
        duplicates = prev_funcs & curr_funcs
        if duplicates:
            score -= 0.3 * len(duplicates)

        # Check for repeated imports
        prev_imports = set(re.findall(r'(?:import|from|require)\s+(\w+)', prev_chunk))
        curr_imports = set(re.findall(r'(?:import|from|require)\s+(\w+)', curr_chunk[:500]))
        if prev_imports & curr_imports:
            score -= 0.1

        return max(0.0, min(1.0, score))


class AnalysisStateHandler(StateHandler):
    """Handler for research, documentation, analysis"""

    def extract_state(self, text: str, existing_state: Dict) -> Dict:
        state = existing_state.copy()

        # Track headings/sections
        heading_pattern = r'^#+\s+(.+)$|^(.+)\n[=-]+$'
        headings = re.findall(heading_pattern, text, re.MULTILINE)
        headings = [h[0] or h[1] for h in headings if h[0] or h[1]]
        state.setdefault("sections_covered", []).extend(headings)

        # Track key terms (capitalized phrases, quoted terms)
        term_pattern = r'"([^"]+)"|\'([^\']+)\'|\*\*([^*]+)\*\*'
        terms = re.findall(term_pattern, text)
        terms = [t[0] or t[1] or t[2] for t in terms if any(t)]
        state.setdefault("key_terms", set()).update(terms[:20])

        # Track bullet points (conclusions/findings)
        bullet_pattern = r'^[\s]*[-*]\s+(.+)$'
        bullets = re.findall(bullet_pattern, text, re.MULTILINE)
        state.setdefault("key_points", []).extend(bullets[-10:])

        # Track numbers/statistics
        stat_pattern = r'\b(\d+(?:\.\d+)?%?)\s+(?:of|percent|times|users|items|cases)'
        stats = re.findall(stat_pattern, text)
        state.setdefault("statistics", []).extend(stats[-5:])

        # Last section content
        sections = re.split(r'\n#+\s+', text)
        if sections:
            state["current_section"] = sections[-1][:500]

        return state

    def compress_state(self, state: Dict, target_tokens: int) -> str:
        parts = []

        if state.get("sections_covered"):
            parts.append(f"Sections covered: {', '.join(state['sections_covered'][-10:])}")

        if state.get("key_terms"):
            terms = list(state["key_terms"])[:15]
            parts.append(f"Key terms: {', '.join(terms)}")

        if state.get("key_points"):
            points = state["key_points"][-5:]
            parts.append(f"Key points:\n- " + "\n- ".join(points))

        return "\n".join(parts)

    def get_continuation_prompt(self, state: Dict, original_prompt: str, chunk_index: int) -> str:
        if chunk_index == 0:
            return original_prompt

        compressed = self.compress_state(state, 500)

        return f"""Continue this analysis/documentation. DO NOT repeat covered sections.

PROGRESS:
{compressed}

Continue with the next section, maintaining the same style and depth:"""

    def detect_natural_break(self, text: str) -> Tuple[str, str]:
        """Break at section boundaries"""
        # Look for heading boundaries
        pattern = r'\n(?=#+\s+|\n[A-Z][^\n]+\n[=-]+)'
        matches = list(re.finditer(pattern, text))

        for m in reversed(matches):
            if m.start() > len(text) * 0.6:
                return text[:m.start()], text[m.start():].strip()

        return text, ""

    def score_coherence(self, prev_chunk: str, curr_chunk: str, state: Dict) -> float:
        score = 1.0

        # Check for repeated headings
        prev_headings = set(re.findall(r'^#+\s+(.+)$', prev_chunk, re.MULTILINE))
        curr_headings = set(re.findall(r'^#+\s+(.+)$', curr_chunk, re.MULTILINE))
        if prev_headings & curr_headings:
            score -= 0.4

        return max(0.0, min(1.0, score))


class ConversationStateHandler(StateHandler):
    """Handler for multi-turn conversations"""

    def extract_state(self, text: str, existing_state: Dict) -> Dict:
        state = existing_state.copy()

        # Track topics discussed
        # (simple keyword extraction)
        words = re.findall(r'\b[a-z]{5,}\b', text.lower())
        word_freq = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1

        top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:10]
        state.setdefault("topics", []).extend([w for w, _ in top_words])
        state["topics"] = list(set(state["topics"]))[-20:]

        # Track questions asked
        questions = re.findall(r'[^.!?]*\?', text)
        state.setdefault("questions", []).extend(questions[-5:])

        # Track user preferences/facts mentioned
        fact_pattern = r'(?:I|my|I\'m|I am)\s+([^.!?]+)[.!?]'
        facts = re.findall(fact_pattern, text, re.IGNORECASE)
        state.setdefault("user_facts", []).extend(facts[-10:])

        return state

    def compress_state(self, state: Dict, target_tokens: int) -> str:
        parts = []

        if state.get("topics"):
            parts.append(f"Topics discussed: {', '.join(state['topics'][-10:])}")

        if state.get("user_facts"):
            parts.append(f"User mentioned: {'; '.join(state['user_facts'][-5:])}")

        if state.get("questions"):
            parts.append(f"Open questions: {state['questions'][-2:]}")

        return "\n".join(parts)

    def get_continuation_prompt(self, state: Dict, original_prompt: str, chunk_index: int) -> str:
        if chunk_index == 0:
            return original_prompt

        compressed = self.compress_state(state, 300)

        return f"""Continue the conversation naturally.

CONTEXT:
{compressed}

Continue:"""

    def detect_natural_break(self, text: str) -> Tuple[str, str]:
        # Break at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 1:
            break_at = len(text) - len(sentences[-1])
            return text[:break_at].strip(), sentences[-1]
        return text, ""

    def score_coherence(self, prev_chunk: str, curr_chunk: str, state: Dict) -> float:
        # Conversations are naturally less structured
        return 0.9  # Usually fine


# =============================================================================
# MEMORY MANAGER
# =============================================================================

class MemoryManager:
    """Manages hierarchical memory with compression and retrieval"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".sam" / "infinite_context.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # In-memory cache for current session
        self.working_memory: Dict[str, StateFragment] = {}
        self.short_term: List[StateFragment] = []
        self.max_short_term = 20

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                key TEXT PRIMARY KEY,
                value TEXT,
                domain TEXT,
                importance REAL,
                created_at REAL,
                accessed_at REAL,
                access_count INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                content TEXT,
                importance REAL,
                timestamp REAL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS generation_sessions (
                id TEXT PRIMARY KEY,
                domain TEXT,
                original_prompt TEXT,
                final_output_path TEXT,
                chunks_generated INTEGER,
                total_tokens INTEGER,
                started_at REAL,
                completed_at REAL,
                state_snapshot TEXT
            )
        """)

        conn.commit()
        conn.close()

    def store_working(self, key: str, value: Any, domain: str, importance: float = 0.5):
        """Store in working memory (current chunk context)"""
        fragment = StateFragment(
            key=key,
            value=value,
            tier=MemoryTier.WORKING,
            domain=domain,
            importance=importance,
            created_at=time.time(),
            accessed_at=time.time()
        )
        self.working_memory[key] = fragment

    def promote_to_short_term(self, key: str):
        """Move from working to short-term memory"""
        if key in self.working_memory:
            fragment = self.working_memory.pop(key)
            fragment.tier = MemoryTier.SHORT_TERM
            self.short_term.append(fragment)

            # Evict oldest if over limit
            if len(self.short_term) > self.max_short_term:
                # Keep highest importance items
                self.short_term.sort(key=lambda x: (x.importance, x.accessed_at), reverse=True)
                evicted = self.short_term.pop()

                # Optionally promote to long-term if important
                if evicted.importance > 0.7:
                    self.store_long_term(evicted.key, evicted.value, evicted.domain, evicted.importance)

    def store_long_term(self, key: str, value: Any, domain: str, importance: float):
        """Store in persistent long-term memory"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO long_term_memory
            (key, value, domain, importance, created_at, accessed_at, access_count)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE(
                (SELECT access_count + 1 FROM long_term_memory WHERE key = ?), 1
            ))
        """, (key, json.dumps(value), domain, importance, time.time(), time.time(), key))

        conn.commit()
        conn.close()

    def recall_long_term(self, domain: str, limit: int = 10) -> List[Dict]:
        """Retrieve relevant long-term memories"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT key, value, importance FROM long_term_memory
            WHERE domain = ?
            ORDER BY importance DESC, accessed_at DESC
            LIMIT ?
        """, (domain, limit))

        results = []
        for row in cur.fetchall():
            try:
                results.append({
                    "key": row[0],
                    "value": json.loads(row[1]),
                    "importance": row[2]
                })
            except:
                pass

        conn.close()
        return results

    def store_episode(self, session_id: str, event_type: str, content: str, importance: float = 0.5):
        """Store an episodic memory (key event in generation)"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO episodic_memory (session_id, event_type, content, importance, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, event_type, content, importance, time.time()))

        conn.commit()
        conn.close()

    def get_context_for_chunk(self, domain: str, target_tokens: int = 500) -> str:
        """Assemble context from all memory tiers"""
        parts = []
        token_budget = target_tokens

        # Working memory (most recent, highest priority)
        for key, fragment in self.working_memory.items():
            if token_budget <= 0:
                break
            value_str = str(fragment.value)[:200]
            parts.append(f"{key}: {value_str}")
            token_budget -= len(value_str.split()) * 1.3

        # Short-term memory (recent context)
        for fragment in reversed(self.short_term[-5:]):
            if token_budget <= 0:
                break
            value_str = str(fragment.value)[:150]
            parts.append(f"[Recent] {fragment.key}: {value_str}")
            token_budget -= len(value_str.split()) * 1.3

        # Long-term memory (persistent facts)
        if token_budget > 100:
            long_term = self.recall_long_term(domain, limit=5)
            for mem in long_term:
                if token_budget <= 0:
                    break
                value_str = str(mem["value"])[:100]
                parts.append(f"[Memory] {mem['key']}: {value_str}")
                token_budget -= len(value_str.split()) * 1.3

        return "\n".join(parts)

    def clear_working(self):
        """Clear working memory (after chunk completion)"""
        # Promote important items before clearing
        for key, fragment in list(self.working_memory.items()):
            if fragment.importance > 0.6:
                self.promote_to_short_term(key)
        self.working_memory.clear()


# =============================================================================
# MAIN ENGINE
# =============================================================================

class InfiniteContext:
    """
    Main engine for infinite context generation.

    Coordinates state handlers, memory, and generation to produce
    coherent long-form output from small context window models.
    """

    # Handler registry
    HANDLERS = {
        Domain.STORY: StoryStateHandler,
        Domain.CODE: CodeStateHandler,
        Domain.ANALYSIS: AnalysisStateHandler,
        Domain.CONVERSATION: ConversationStateHandler,
        Domain.INSTRUCTION: AnalysisStateHandler,  # Reuse
        Domain.FREEFORM: ConversationStateHandler,  # Reuse
    }

    def __init__(
        self,
        domain: Domain = Domain.FREEFORM,
        model_fn: Optional[Callable[[str], str]] = None,
        chunk_size: int = 1500,  # Target tokens per chunk
        quality_threshold: float = 0.6,
        max_retries: int = 3,
        persistence_path: Optional[Path] = None
    ):
        self.domain = domain
        self.model_fn = model_fn or self._default_model
        self.chunk_size = chunk_size
        self.quality_threshold = quality_threshold
        self.max_retries = max_retries

        self.handler: StateHandler = self.HANDLERS[domain]()
        self.memory = MemoryManager(persistence_path)

        self.session_id = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:12]
        self.chunks: List[Chunk] = []
        self.state: Dict[str, Any] = {}

    def _default_model(self, prompt: str) -> str:
        """Default model call - uses local MLX or falls back to Ollama"""
        try:
            # Try MLX first
            from think.mlx_inference import load_model, generate_response
            model, tokenizer = load_model(use_fused=False)
            return generate_response(model, tokenizer, prompt, max_tokens=self.chunk_size * 2)
        except ImportError:
            pass

        try:
            # Fall back to Ollama
            import subprocess
            result = subprocess.run(
                ["ollama", "run", "dolphin-llama3", prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.stdout
        except:
            raise RuntimeError("No model available. Install MLX or Ollama.")

    def _estimate_needed_chunks(self, prompt: str) -> int:
        """Estimate how many chunks we'll need"""
        # Look for explicit length requests
        length_patterns = [
            (r'(\d+)\s*(?:word|words)', lambda m: int(m.group(1)) // 400),
            (r'(\d+)\s*(?:page|pages)', lambda m: int(m.group(1)) * 2),
            (r'(\d+)\s*(?:paragraph|paragraphs)', lambda m: max(1, int(m.group(1)) // 4)),
            (r'(?:long|detailed|comprehensive|extensive)', lambda m: 5),
            (r'(?:short|brief|quick|concise)', lambda m: 1),
        ]

        for pattern, estimator in length_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return estimator(match)

        # Default estimate based on domain
        domain_defaults = {
            Domain.STORY: 4,
            Domain.CODE: 3,
            Domain.ANALYSIS: 4,
            Domain.CONVERSATION: 1,
            Domain.INSTRUCTION: 3,
            Domain.FREEFORM: 2,
        }

        return domain_defaults.get(self.domain, 2)

    def _generate_chunk(self, prompt: str, chunk_index: int) -> Chunk:
        """Generate a single chunk with retry logic"""
        best_chunk = None
        best_score = 0.0

        for attempt in range(self.max_retries):
            raw_output = self.model_fn(prompt)

            # Find natural break point
            content, overflow = self.handler.detect_natural_break(raw_output)

            # Extract state from this chunk
            new_state = self.handler.extract_state(content, self.state)

            # Score coherence with previous chunk
            if self.chunks:
                coherence = self.handler.score_coherence(
                    self.chunks[-1].content,
                    content,
                    new_state
                )
            else:
                coherence = 1.0

            chunk = Chunk(
                content=content,
                index=chunk_index,
                tokens_approx=len(content.split()),
                coherence_score=coherence,
                continuation_hint=overflow or content[-300:],
                state_snapshot=new_state.copy(),
                generated_at=time.time()
            )

            if coherence > best_score:
                best_chunk = chunk
                best_score = coherence

            if coherence >= self.quality_threshold:
                break

        return best_chunk

    def generate(self, prompt: str, max_chunks: Optional[int] = None) -> str:
        """
        Generate long-form content with automatic chunking and state management.

        Args:
            prompt: The generation prompt
            max_chunks: Maximum chunks to generate (None = auto-estimate)

        Returns:
            Complete generated text
        """
        estimated_chunks = max_chunks or self._estimate_needed_chunks(prompt)

        print(f"[InfiniteContext] Starting generation: ~{estimated_chunks} chunks, domain={self.domain.value}")

        self.chunks = []
        self.state = {}

        for i in range(estimated_chunks):
            # Build continuation prompt
            continuation_prompt = self.handler.get_continuation_prompt(
                self.state, prompt, i
            )

            # Add memory context
            if i > 0:
                memory_context = self.memory.get_context_for_chunk(self.domain.value, 300)
                if memory_context:
                    continuation_prompt = f"CONTEXT:\n{memory_context}\n\n{continuation_prompt}"

            # Generate chunk
            chunk = self._generate_chunk(continuation_prompt, i)
            self.chunks.append(chunk)

            # Update state
            self.state = chunk.state_snapshot

            # Store in memory
            for key, value in self.state.items():
                self.memory.store_working(key, value, self.domain.value, importance=0.5)

            # Promote to short-term after each chunk
            self.memory.clear_working()

            # Log episode
            self.memory.store_episode(
                self.session_id,
                f"chunk_{i}",
                chunk.content[:200],
                importance=chunk.coherence_score
            )

            print(f"[InfiniteContext] Chunk {i+1}/{estimated_chunks} complete (coherence: {chunk.coherence_score:.2f})")

            # Check if we've reached a natural ending
            if self._detect_natural_ending(chunk.content):
                print("[InfiniteContext] Natural ending detected")
                break

        # Merge chunks
        return self._merge_chunks()

    def stream(self, prompt: str, max_chunks: Optional[int] = None) -> Generator[str, None, None]:
        """
        Stream generation chunk by chunk.

        Yields:
            Each chunk as it's generated
        """
        estimated_chunks = max_chunks or self._estimate_needed_chunks(prompt)

        self.chunks = []
        self.state = {}

        for i in range(estimated_chunks):
            continuation_prompt = self.handler.get_continuation_prompt(
                self.state, prompt, i
            )

            if i > 0:
                memory_context = self.memory.get_context_for_chunk(self.domain.value, 300)
                if memory_context:
                    continuation_prompt = f"CONTEXT:\n{memory_context}\n\n{continuation_prompt}"

            chunk = self._generate_chunk(continuation_prompt, i)
            self.chunks.append(chunk)
            self.state = chunk.state_snapshot
            self.memory.clear_working()

            yield chunk.content

            if self._detect_natural_ending(chunk.content):
                break

    def _detect_natural_ending(self, text: str) -> bool:
        """Detect if the content has reached a natural conclusion"""
        ending_patterns = [
            r'(?:The End|THE END|Fin|FIN)\.?\s*$',
            r'(?:In conclusion|To summarize|In summary)[^.]*\.\s*$',
            r'(?:That\'s all|That is all|And that\'s)[^.]*\.\s*$',
        ]

        for pattern in ending_patterns:
            if re.search(pattern, text[-200:], re.IGNORECASE):
                return True

        return False

    def _merge_chunks(self) -> str:
        """Merge all chunks into coherent output"""
        if not self.chunks:
            return ""

        parts = []
        for i, chunk in enumerate(self.chunks):
            content = chunk.content

            # Remove any duplicate overlap with previous chunk
            if i > 0 and parts:
                prev_end = parts[-1][-200:]
                # Find overlap and trim
                for overlap_len in range(min(100, len(content)), 0, -1):
                    if content[:overlap_len] in prev_end:
                        content = content[overlap_len:].lstrip()
                        break

            parts.append(content)

        return "\n\n".join(parts)

    def save_session(self, output_path: Path):
        """Save the generation session for later resumption"""
        conn = sqlite3.connect(self.memory.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO generation_sessions
            (id, domain, original_prompt, final_output_path, chunks_generated,
             total_tokens, started_at, completed_at, state_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            self.domain.value,
            "",  # Would need to track original prompt
            str(output_path),
            len(self.chunks),
            sum(c.tokens_approx for c in self.chunks),
            self.chunks[0].generated_at if self.chunks else time.time(),
            time.time(),
            json.dumps(self.state)
        ))

        conn.commit()
        conn.close()

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(self._merge_chunks())

        print(f"[InfiniteContext] Session saved to {output_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Infinite Context Engine")
    parser.add_argument("prompt", nargs="?", help="Generation prompt")
    parser.add_argument("--domain", "-d", choices=[d.value for d in Domain],
                       default="freeform", help="Generation domain")
    parser.add_argument("--chunks", "-c", type=int, help="Max chunks to generate")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--stream", "-s", action="store_true", help="Stream output")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    domain = Domain(args.domain)
    engine = InfiniteContext(domain=domain)

    if args.interactive:
        print(f"🧠 Infinite Context Engine - Domain: {domain.value}")
        print("Enter your prompt (multi-line, end with empty line):\n")

        lines = []
        while True:
            try:
                line = input()
                if not line:
                    break
                lines.append(line)
            except EOFError:
                break

        prompt = "\n".join(lines)

        if args.stream:
            for chunk in engine.stream(prompt, args.chunks):
                print(chunk, end="", flush=True)
            print()
        else:
            result = engine.generate(prompt, args.chunks)
            print("\n" + "="*60 + "\n")
            print(result)

        if args.output:
            engine.save_session(Path(args.output))

    elif args.prompt:
        if args.stream:
            for chunk in engine.stream(args.prompt, args.chunks):
                print(chunk, end="", flush=True)
            print()
        else:
            result = engine.generate(args.prompt, args.chunks)
            print(result)

        if args.output:
            engine.save_session(Path(args.output))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
