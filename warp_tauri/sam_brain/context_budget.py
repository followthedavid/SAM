#!/usr/bin/env python3
"""
SAM Context Budget Allocator - Intelligent token allocation for RAG results

Manages token distribution across context sections with query-type-aware
prioritization and intelligent truncation.

Designed for 8GB RAM constraint with MLX inference.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime
import time
import hashlib
import re


class SectionPriority(IntEnum):
    """
    Priority levels for context sections.

    Lower value = higher priority = placed at attention-critical positions.
    Attention follows a U-curve: highest at start (primacy) and end (recency).
    """
    CRITICAL = 1      # System prompt, direct query context
    HIGH = 2          # Query-relevant RAG, recent conversation
    MEDIUM = 3        # User facts, project context
    LOW = 4           # Background info, older history
    MINIMAL = 5       # Filler content, low-relevance RAG


@dataclass
class ContextSection:
    """
    A section of context with content and metadata for ordering.

    Attributes:
        name: Section identifier (e.g., 'system_prompt', 'rag_results')
        content: The actual text content
        priority: Base priority level
        relevance_score: Query relevance (0.0-1.0), affects final ordering
        token_count: Estimated tokens in this section
        position_hint: Preferred position ('start', 'end', 'middle', or None)
    """
    name: str
    content: str
    priority: SectionPriority = SectionPriority.MEDIUM
    relevance_score: float = 0.5
    token_count: int = 0
    position_hint: Optional[str] = None  # 'start', 'end', 'middle'

    def effective_priority(self) -> float:
        """
        Calculate effective priority combining base priority and relevance.

        Lower score = higher effective priority.
        Relevance can boost priority by up to 2 levels.
        """
        # Relevance boost: high relevance (1.0) can reduce priority by 2
        relevance_boost = (1.0 - self.relevance_score) * 2
        return float(self.priority) + relevance_boost

    def __lt__(self, other: 'ContextSection') -> bool:
        """Enable sorting by effective priority."""
        return self.effective_priority() < other.effective_priority()


class QueryType(Enum):
    """Query types that affect context budget prioritization."""
    CHAT = "chat"              # Casual conversation
    CODE = "code"              # Programming questions
    RECALL = "recall"          # Memory/fact retrieval
    REASONING = "reasoning"    # Complex logic/analysis
    ROLEPLAY = "roleplay"      # Persona interactions
    PROJECT = "project"        # Project-specific queries


@dataclass
class SectionBudget:
    """Token allocation for a single context section."""
    name: str
    tokens: int
    priority: int  # Lower = higher priority (1 is highest)
    is_fixed: bool = False  # If True, don't reduce during rebalancing

    def __post_init__(self):
        self.tokens = max(0, self.tokens)


@dataclass
class BudgetAllocation:
    """Complete budget allocation across all sections."""
    system_prompt: int
    user_facts: int
    project_context: int
    rag_results: int
    conversation_history: int
    working_memory: int
    query: int
    total: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "system_prompt": self.system_prompt,
            "user_facts": self.user_facts,
            "project_context": self.project_context,
            "rag_results": self.rag_results,
            "conversation_history": self.conversation_history,
            "working_memory": self.working_memory,
            "query": self.query,
            "total": self.total
        }

    def remaining(self) -> int:
        """Tokens remaining after allocation."""
        used = (
            self.system_prompt + self.user_facts + self.project_context +
            self.rag_results + self.conversation_history +
            self.working_memory + self.query
        )
        return max(0, self.total - used)


class ContextBudget:
    """
    Intelligent context budget allocator for RAG results.

    Allocates tokens across context sections based on:
    1. Query type (code queries need more RAG, recall needs more history)
    2. Available tokens (dynamic scaling)
    3. Section priorities (system prompt is fixed, others flexible)

    Default allocation for 2000 token context:
    - System prompt: 100 tokens (fixed)
    - User facts: 200 tokens
    - Project context: 150 tokens
    - RAG results: 400 tokens (variable)
    - Conversation history: 500 tokens
    - Working memory: 150 tokens
    - Query: variable (remaining)
    """

    # Base allocations (percentages for 2000 token budget)
    DEFAULT_RATIOS = {
        "system_prompt": 0.05,      # 100 tokens - fixed
        "user_facts": 0.10,         # 200 tokens
        "project_context": 0.075,   # 150 tokens
        "rag_results": 0.20,        # 400 tokens
        "conversation_history": 0.25,  # 500 tokens
        "working_memory": 0.075,    # 150 tokens
        # query gets remainder (~10% = 200 tokens + overhead)
    }

    # Priority adjustments by query type (multipliers)
    QUERY_TYPE_PRIORITIES = {
        QueryType.CHAT: {
            "conversation_history": 1.3,
            "rag_results": 0.7,
            "user_facts": 1.2,
        },
        QueryType.CODE: {
            "rag_results": 1.5,
            "project_context": 1.3,
            "conversation_history": 0.8,
        },
        QueryType.RECALL: {
            "user_facts": 1.5,
            "conversation_history": 1.3,
            "working_memory": 1.2,
            "rag_results": 0.7,
        },
        QueryType.REASONING: {
            "rag_results": 1.3,
            "project_context": 1.2,
            "conversation_history": 0.9,
        },
        QueryType.ROLEPLAY: {
            "system_prompt": 1.2,  # More personality context
            "conversation_history": 1.4,
            "rag_results": 0.5,
        },
        QueryType.PROJECT: {
            "project_context": 1.5,
            "rag_results": 1.2,
            "user_facts": 0.8,
        },
    }

    # Tokenization estimate (chars per token)
    CHARS_PER_TOKEN = 4

    # Section priority mapping by query type
    # Maps (section_name, query_type) -> SectionPriority
    SECTION_PRIORITIES = {
        # Default priorities (used when query type doesn't specify)
        "system_prompt": SectionPriority.CRITICAL,
        "user_facts": SectionPriority.MEDIUM,
        "project_context": SectionPriority.MEDIUM,
        "rag_results": SectionPriority.HIGH,
        "conversation_history": SectionPriority.HIGH,
        "working_memory": SectionPriority.LOW,
        "query": SectionPriority.CRITICAL,
    }

    # Priority overrides by query type
    PRIORITY_OVERRIDES = {
        QueryType.CHAT: {
            "conversation_history": SectionPriority.CRITICAL,
            "user_facts": SectionPriority.HIGH,
            "rag_results": SectionPriority.LOW,
        },
        QueryType.CODE: {
            "rag_results": SectionPriority.CRITICAL,
            "project_context": SectionPriority.HIGH,
            "conversation_history": SectionPriority.MEDIUM,
        },
        QueryType.RECALL: {
            "user_facts": SectionPriority.CRITICAL,
            "conversation_history": SectionPriority.CRITICAL,
            "working_memory": SectionPriority.HIGH,
            "rag_results": SectionPriority.MEDIUM,
        },
        QueryType.REASONING: {
            "rag_results": SectionPriority.CRITICAL,
            "project_context": SectionPriority.HIGH,
            "conversation_history": SectionPriority.MEDIUM,
        },
        QueryType.ROLEPLAY: {
            "system_prompt": SectionPriority.CRITICAL,
            "conversation_history": SectionPriority.CRITICAL,
            "user_facts": SectionPriority.HIGH,
            "rag_results": SectionPriority.MINIMAL,
        },
        QueryType.PROJECT: {
            "project_context": SectionPriority.CRITICAL,
            "rag_results": SectionPriority.CRITICAL,
            "conversation_history": SectionPriority.MEDIUM,
        },
    }

    # Position hints for attention optimization
    # 'start' = primacy effect, 'end' = recency effect
    POSITION_HINTS = {
        "system_prompt": "start",      # Always first
        "user_facts": "start",          # Early for persistent context
        "query": "end",                 # Always last (recency)
        "conversation_history": "end",  # Near query for recency
        "rag_results": None,            # Flexible based on relevance
        "project_context": "middle",    # Less attention-critical
        "working_memory": "middle",     # Less attention-critical
    }

    # Minimum tokens per section (prevents over-truncation)
    MIN_TOKENS = {
        "system_prompt": 50,
        "user_facts": 0,
        "project_context": 0,
        "rag_results": 50,
        "conversation_history": 100,
        "working_memory": 0,
        "query": 50,
    }

    def __init__(self, default_budget: int = 2000):
        """
        Initialize context budget allocator.

        Args:
            default_budget: Default total token budget (default: 2000)
        """
        self.default_budget = default_budget
        self._allocation_history: List[BudgetAllocation] = []

    def detect_query_type(self, query: str) -> QueryType:
        """
        Detect query type from content for automatic prioritization.

        Args:
            query: User query string

        Returns:
            Detected QueryType
        """
        query_lower = query.lower()

        # Code patterns
        code_patterns = [
            r'\b(code|function|class|method|bug|error|fix|debug|compile|syntax)\b',
            r'\b(python|javascript|typescript|rust|go|java|c\+\+|ruby|swift)\b',
            r'\b(how (do|to)|implement|create|write)\b.*\b(function|code|script|class|method)\b',
            r'\b(decorator|api|endpoint|algorithm|variable|loop|array|dict|list|string)\b',
            r'\b(import|export|module|package|library|framework|sdk)\b',
            r'\b(git|commit|push|pull|merge|branch|repo)\b',
        ]
        for pattern in code_patterns:
            if re.search(pattern, query_lower):
                return QueryType.CODE

        # Recall patterns
        recall_patterns = [
            r'\b(remember|recall|what (was|did)|earlier|before|previously)\b',
            r'\bmy (name|favorite|preference)\b',
            r'\bwhat.*(told|said|mentioned)\b',
        ]
        for pattern in recall_patterns:
            if re.search(pattern, query_lower):
                return QueryType.RECALL

        # Reasoning patterns
        reasoning_patterns = [
            r'\b(why|explain|analyze|compare|reason|think about)\b',
            r'\b(pros and cons|advantages|disadvantages)\b',
            r'\bwhat (should|would|could)\b',
        ]
        for pattern in reasoning_patterns:
            if re.search(pattern, query_lower):
                return QueryType.REASONING

        # Project patterns
        project_patterns = [
            r'\b(project|codebase|repository|file|module)\b',
            r'\b(architecture|structure|design)\b',
            r'\bsam\b.*\b(brain|pipeline|system)\b',
        ]
        for pattern in project_patterns:
            if re.search(pattern, query_lower):
                return QueryType.PROJECT

        # Roleplay patterns
        roleplay_patterns = [
            r'\b(roleplay|pretend|act as|you are)\b',
            r'\*.*\*',  # Action markers
        ]
        for pattern in roleplay_patterns:
            if re.search(pattern, query_lower):
                return QueryType.ROLEPLAY

        # Default to chat
        return QueryType.CHAT

    def allocate(
        self,
        query_type: QueryType,
        available_tokens: int,
        custom_priorities: Optional[Dict[str, float]] = None
    ) -> Dict[str, int]:
        """
        Allocate tokens across context sections based on query type.

        Args:
            query_type: Type of query for prioritization
            available_tokens: Total available tokens
            custom_priorities: Optional custom priority multipliers

        Returns:
            Dict mapping section names to allocated tokens
        """
        # Start with base ratios
        ratios = dict(self.DEFAULT_RATIOS)

        # Apply query-type priorities
        type_priorities = self.QUERY_TYPE_PRIORITIES.get(query_type, {})
        for section, multiplier in type_priorities.items():
            if section in ratios:
                ratios[section] *= multiplier

        # Apply custom priorities if provided
        if custom_priorities:
            for section, multiplier in custom_priorities.items():
                if section in ratios:
                    ratios[section] *= multiplier

        # Normalize ratios to sum to ~0.90 (leave 10% for query + overhead)
        total_ratio = sum(ratios.values())
        target_ratio = 0.90
        normalization_factor = target_ratio / total_ratio if total_ratio > 0 else 1.0

        # Calculate initial allocations
        allocations = {}
        for section, ratio in ratios.items():
            normalized_ratio = ratio * normalization_factor
            tokens = int(available_tokens * normalized_ratio)
            # Enforce minimums
            min_tokens = self.MIN_TOKENS.get(section, 0)
            allocations[section] = max(min_tokens, tokens)

        # Calculate query allocation (remainder)
        used = sum(allocations.values())
        query_tokens = max(self.MIN_TOKENS["query"], available_tokens - used)
        allocations["query"] = query_tokens

        # Create and store allocation
        allocation = BudgetAllocation(
            system_prompt=allocations.get("system_prompt", 100),
            user_facts=allocations.get("user_facts", 200),
            project_context=allocations.get("project_context", 150),
            rag_results=allocations.get("rag_results", 400),
            conversation_history=allocations.get("conversation_history", 500),
            working_memory=allocations.get("working_memory", 150),
            query=allocations.get("query", 200),
            total=available_tokens
        )
        self._allocation_history.append(allocation)

        return allocations

    def fit_content(
        self,
        section: str,
        content: str,
        max_tokens: int,
        preserve_start: bool = True,
        preserve_end: bool = False
    ) -> str:
        """
        Truncate content to fit within token budget.

        Uses intelligent truncation strategies:
        - Sentence boundary awareness
        - Preserve start for system prompts/facts
        - Preserve end for conversation history

        Args:
            section: Section name (for strategy selection)
            content: Content to truncate
            max_tokens: Maximum tokens allowed
            preserve_start: Keep beginning of content
            preserve_end: Keep end of content

        Returns:
            Truncated content
        """
        if not content:
            return ""

        current_tokens = self.count_tokens(content)
        if current_tokens <= max_tokens:
            return content

        # Calculate target character count
        target_chars = max_tokens * self.CHARS_PER_TOKEN

        # Strategy selection based on section
        if section == "conversation_history":
            # For history, prefer recent (end)
            preserve_start = False
            preserve_end = True
        elif section in ("system_prompt", "user_facts"):
            # For system/facts, prefer beginning
            preserve_start = True
            preserve_end = False
        elif section == "rag_results":
            # For RAG, try to keep complete chunks
            return self._truncate_rag_results(content, target_chars)

        # Apply truncation strategy
        if preserve_end:
            return self._truncate_preserve_end(content, target_chars)
        else:
            return self._truncate_preserve_start(content, target_chars)

    def _truncate_preserve_start(self, content: str, target_chars: int) -> str:
        """Truncate keeping beginning, trying to end at sentence boundary."""
        if len(content) <= target_chars:
            return content

        # Find sentence boundaries in truncation zone
        truncation_zone = content[:target_chars]

        # Look for sentence endings
        sentence_endings = [
            m.end() for m in re.finditer(r'[.!?]\s+', truncation_zone)
        ]

        if sentence_endings and sentence_endings[-1] > target_chars * 0.7:
            # Use last sentence boundary if it's reasonably close
            return content[:sentence_endings[-1]].rstrip() + "..."

        # Fall back to word boundary
        last_space = truncation_zone.rfind(' ')
        if last_space > target_chars * 0.8:
            return content[:last_space].rstrip() + "..."

        return content[:target_chars - 3] + "..."

    def _truncate_preserve_end(self, content: str, target_chars: int) -> str:
        """Truncate keeping end, trying to start at sentence boundary."""
        if len(content) <= target_chars:
            return content

        # Find where to start
        start_idx = len(content) - target_chars
        truncation_zone = content[start_idx:start_idx + int(target_chars * 0.3)]

        # Look for sentence starts
        sentence_starts = [
            start_idx + m.start() for m in re.finditer(r'[.!?]\s+[A-Z]', truncation_zone)
        ]

        if sentence_starts:
            # Start at sentence boundary
            start = sentence_starts[0] + 2  # After period and space
            return "..." + content[start:].lstrip()

        # Fall back to word boundary
        first_space = content.find(' ', start_idx)
        if first_space > 0 and first_space < start_idx + int(target_chars * 0.2):
            return "..." + content[first_space + 1:]

        return "..." + content[start_idx + 3:]

    def _truncate_rag_results(self, content: str, target_chars: int) -> str:
        """
        Truncate RAG results while preserving complete chunks.

        RAG results are typically structured as multiple chunks.
        This tries to keep complete chunks rather than cutting mid-chunk.
        """
        if len(content) <= target_chars:
            return content

        # Try to split by common RAG chunk separators
        chunk_patterns = [
            r'\n\n+',           # Double newlines
            r'\n---+\n',        # Horizontal rules
            r'\n\[\d+\]\s*',    # Numbered references
        ]

        chunks = [content]
        for pattern in chunk_patterns:
            new_chunks = []
            for chunk in chunks:
                splits = re.split(pattern, chunk)
                new_chunks.extend([s for s in splits if s.strip()])
            if len(new_chunks) > 1:
                chunks = new_chunks
                break

        # Select chunks to fit budget
        selected = []
        current_chars = 0

        for chunk in chunks:
            chunk_chars = len(chunk)
            if current_chars + chunk_chars + 2 <= target_chars:  # +2 for separator
                selected.append(chunk)
                current_chars += chunk_chars + 2
            elif current_chars == 0:
                # First chunk is too big, truncate it
                selected.append(chunk[:target_chars - 3] + "...")
                break

        return "\n\n".join(selected)

    def get_rag_budget(
        self,
        total_budget: int,
        query_type: QueryType,
        consumed_by_other_sections: int = 0
    ) -> int:
        """
        Calculate optimal RAG budget given constraints.

        Useful for deciding how many RAG results to retrieve before
        building the full context.

        Args:
            total_budget: Total available tokens
            query_type: Type of query
            consumed_by_other_sections: Tokens already committed elsewhere

        Returns:
            Recommended token budget for RAG results
        """
        # Get base allocation
        allocations = self.allocate(query_type, total_budget)
        base_rag = allocations.get("rag_results", 400)

        # Adjust for already consumed tokens
        remaining = total_budget - consumed_by_other_sections

        # RAG should be proportional to remaining budget
        if consumed_by_other_sections > 0:
            proportion = base_rag / total_budget
            adjusted_rag = int(remaining * proportion)
        else:
            adjusted_rag = base_rag

        # Enforce bounds
        min_rag = self.MIN_TOKENS.get("rag_results", 50)
        max_rag = int(remaining * 0.4)  # Never more than 40% of remaining

        return max(min_rag, min(adjusted_rag, max_rag))

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // self.CHARS_PER_TOKEN

    def tokens_to_chars(self, tokens: int) -> int:
        """Convert token count to character estimate."""
        return tokens * self.CHARS_PER_TOKEN

    def get_section_priority(
        self,
        section_type: str,
        query_type: QueryType,
        relevance_score: float = 0.5
    ) -> SectionPriority:
        """
        Get priority for a section given query type.

        Priority determines position in context for optimal attention:
        - CRITICAL: Start or end positions (primacy/recency)
        - HIGH: Near start or end
        - MEDIUM: Middle section
        - LOW/MINIMAL: Deep middle (lowest attention)

        Args:
            section_type: Section name (e.g., 'rag_results', 'user_facts')
            query_type: Type of query affecting priorities
            relevance_score: Relevance to query (0.0-1.0), can boost priority

        Returns:
            SectionPriority enum value
        """
        # Check for query-type specific override
        overrides = self.PRIORITY_OVERRIDES.get(query_type, {})
        if section_type in overrides:
            base_priority = overrides[section_type]
        else:
            # Fall back to default priority
            base_priority = self.SECTION_PRIORITIES.get(
                section_type,
                SectionPriority.MEDIUM
            )

        # High relevance can boost priority by one level
        if relevance_score >= 0.8 and base_priority > SectionPriority.CRITICAL:
            return SectionPriority(base_priority - 1)

        return base_priority

    def order_context_sections(
        self,
        sections: List[ContextSection],
        query: str,
        query_type: Optional[QueryType] = None
    ) -> List[ContextSection]:
        """
        Order context sections for optimal attention distribution.

        Uses primacy/recency effect: LLMs pay more attention to:
        1. Beginning of context (primacy)
        2. End of context, near the query (recency)
        3. Less attention to middle sections

        Ordering strategy:
        - CRITICAL priority with 'start' hint -> beginning
        - CRITICAL priority with 'end' hint -> end (before query)
        - HIGH priority -> near start/end based on hint
        - MEDIUM/LOW/MINIMAL -> middle sections

        The query itself is always placed last for maximum recency.

        Args:
            sections: List of ContextSection objects to order
            query: User query (for type detection if needed)
            query_type: Query type (auto-detected if None)

        Returns:
            Ordered list of ContextSection objects
        """
        if not sections:
            return []

        # Auto-detect query type if not provided
        if query_type is None:
            query_type = self.detect_query_type(query)

        # Update priorities based on query type
        for section in sections:
            section.priority = self.get_section_priority(
                section.name,
                query_type,
                section.relevance_score
            )
            # Set position hint if not already set
            if section.position_hint is None:
                section.position_hint = self.POSITION_HINTS.get(section.name)

        # Separate sections by position preference
        start_sections: List[ContextSection] = []
        end_sections: List[ContextSection] = []
        middle_sections: List[ContextSection] = []
        query_section: Optional[ContextSection] = None

        for section in sections:
            if section.name == "query":
                query_section = section
            elif section.position_hint == "start":
                start_sections.append(section)
            elif section.position_hint == "end":
                end_sections.append(section)
            else:
                middle_sections.append(section)

        # Sort each group by effective priority
        start_sections.sort()  # Uses __lt__ based on effective_priority
        end_sections.sort()
        middle_sections.sort()

        # Apply attention-aware ordering within middle sections
        # Highest priority items go to edges of middle (pseudo-primacy/recency)
        if len(middle_sections) > 2:
            middle_sections = self._distribute_middle_sections(middle_sections)

        # Combine: start -> middle -> end -> query
        ordered = start_sections + middle_sections + end_sections

        # Query always last (maximum recency effect)
        if query_section:
            ordered.append(query_section)

        return ordered

    def _distribute_middle_sections(
        self,
        sections: List[ContextSection]
    ) -> List[ContextSection]:
        """
        Distribute middle sections for attention optimization.

        Places higher-priority middle sections at edges of the middle
        zone (pseudo-primacy/recency within the middle).

        For example, with sections [A, B, C, D, E] sorted by priority:
        - A (highest) -> edge (front of middle)
        - B -> edge (back of middle)
        - C -> near edges
        - D, E (lowest) -> deep middle

        Args:
            sections: Pre-sorted list of middle sections

        Returns:
            Re-distributed sections
        """
        if len(sections) <= 2:
            return sections

        result: List[Optional[ContextSection]] = [None] * len(sections)
        left = 0
        right = len(sections) - 1
        use_left = True

        for section in sections:
            if use_left:
                result[left] = section
                left += 1
            else:
                result[right] = section
                right -= 1
            use_left = not use_left

        return [s for s in result if s is not None]

    def create_context_section(
        self,
        name: str,
        content: str,
        relevance_score: float = 0.5,
        query_type: Optional[QueryType] = None
    ) -> ContextSection:
        """
        Create a ContextSection with appropriate priority and hints.

        Convenience method for building sections with proper metadata.

        Args:
            name: Section name (e.g., 'rag_results')
            content: Section content
            relevance_score: Relevance to query (0.0-1.0)
            query_type: Query type for priority lookup

        Returns:
            Configured ContextSection
        """
        priority = self.get_section_priority(
            name,
            query_type or QueryType.CHAT,
            relevance_score
        )
        position_hint = self.POSITION_HINTS.get(name)
        token_count = self.count_tokens(content)

        return ContextSection(
            name=name,
            content=content,
            priority=priority,
            relevance_score=relevance_score,
            token_count=token_count,
            position_hint=position_hint
        )

    def build_ordered_context(
        self,
        sections: List[ContextSection],
        query: str,
        total_tokens: int = 2000,
        query_type: Optional[QueryType] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build context string with attention-optimized ordering.

        Combines ordering, budget allocation, and content fitting.

        Args:
            sections: List of ContextSection objects
            query: User query
            total_tokens: Total token budget
            query_type: Query type (auto-detected if None)

        Returns:
            Tuple of (formatted context string, metadata dict)
        """
        if query_type is None:
            query_type = self.detect_query_type(query)

        # Get budget allocations
        allocations = self.allocate(query_type, total_tokens)

        # Fit content to budgets and update token counts
        fitted_sections = []
        for section in sections:
            budget = allocations.get(section.name, 200)
            fitted_content = self.fit_content(
                section.name,
                section.content,
                budget
            )
            fitted_section = ContextSection(
                name=section.name,
                content=fitted_content,
                priority=section.priority,
                relevance_score=section.relevance_score,
                token_count=self.count_tokens(fitted_content),
                position_hint=section.position_hint
            )
            fitted_sections.append(fitted_section)

        # Order sections for optimal attention
        ordered = self.order_context_sections(
            fitted_sections,
            query,
            query_type
        )

        # Build formatted output
        section_tags = {
            "system_prompt": "SYSTEM",
            "user_facts": "USER_FACTS",
            "project_context": "PROJECT",
            "rag_results": "CONTEXT",
            "conversation_history": "HISTORY",
            "working_memory": "WORKING_MEMORY",
            "query": "QUERY",
        }

        parts = []
        token_usage = {}
        order_info = []

        for i, section in enumerate(ordered):
            if not section.content:
                continue

            tag = section_tags.get(section.name, section.name.upper())
            parts.append(f"<{tag}>\n{section.content}\n</{tag}>")
            token_usage[section.name] = section.token_count
            order_info.append({
                "position": i,
                "name": section.name,
                "priority": section.priority.name,
                "relevance": section.relevance_score,
                "tokens": section.token_count
            })

        formatted_context = "\n\n".join(parts)

        metadata = {
            "query_type": query_type.value,
            "total_tokens": self.count_tokens(formatted_context),
            "token_usage": token_usage,
            "section_order": order_info,
            "attention_positions": {
                "primacy": order_info[0]["name"] if order_info else None,
                "recency": order_info[-1]["name"] if order_info else None,
            }
        }

        return formatted_context, metadata

    def get_allocation_stats(self) -> Dict[str, Any]:
        """Get statistics on allocations."""
        if not self._allocation_history:
            return {"total_allocations": 0}

        total = len(self._allocation_history)

        # Calculate averages by section
        section_totals = {
            "system_prompt": 0,
            "user_facts": 0,
            "project_context": 0,
            "rag_results": 0,
            "conversation_history": 0,
            "working_memory": 0,
            "query": 0,
        }

        for alloc in self._allocation_history:
            section_totals["system_prompt"] += alloc.system_prompt
            section_totals["user_facts"] += alloc.user_facts
            section_totals["project_context"] += alloc.project_context
            section_totals["rag_results"] += alloc.rag_results
            section_totals["conversation_history"] += alloc.conversation_history
            section_totals["working_memory"] += alloc.working_memory
            section_totals["query"] += alloc.query

        averages = {k: v / total for k, v in section_totals.items()}

        return {
            "total_allocations": total,
            "average_by_section": averages,
            "last_allocation": self._allocation_history[-1].to_dict() if self._allocation_history else None
        }


class ContextBuilder:
    """
    Helper class to build context using ContextBudget allocations.

    Combines budget allocation with actual content fitting.
    """

    def __init__(self, budget: ContextBudget):
        """
        Initialize context builder.

        Args:
            budget: ContextBudget instance for allocation
        """
        self.budget = budget

    def build(
        self,
        query: str,
        system_prompt: str = "",
        user_facts: str = "",
        project_context: str = "",
        rag_results: str = "",
        conversation_history: str = "",
        working_memory: str = "",
        total_tokens: int = 2000,
        query_type: Optional[QueryType] = None
    ) -> Tuple[str, Dict[str, int]]:
        """
        Build optimized context from components.

        Args:
            query: User query
            system_prompt: System prompt content
            user_facts: User facts/preferences
            project_context: Current project context
            rag_results: Retrieved RAG results
            conversation_history: Recent conversation
            working_memory: Working memory content
            total_tokens: Total token budget
            query_type: Query type (auto-detected if None)

        Returns:
            Tuple of (formatted context string, token usage dict)
        """
        # Detect query type if not provided
        if query_type is None:
            query_type = self.budget.detect_query_type(query)

        # Get allocations
        allocations = self.budget.allocate(query_type, total_tokens)

        # Fit each section to its budget
        sections = {}
        token_usage = {}

        # System prompt (highest priority, fixed)
        if system_prompt:
            fitted = self.budget.fit_content(
                "system_prompt",
                system_prompt,
                allocations["system_prompt"]
            )
            sections["system_prompt"] = fitted
            token_usage["system_prompt"] = self.budget.count_tokens(fitted)

        # User facts
        if user_facts:
            fitted = self.budget.fit_content(
                "user_facts",
                user_facts,
                allocations["user_facts"]
            )
            sections["user_facts"] = fitted
            token_usage["user_facts"] = self.budget.count_tokens(fitted)

        # Project context
        if project_context:
            fitted = self.budget.fit_content(
                "project_context",
                project_context,
                allocations["project_context"]
            )
            sections["project_context"] = fitted
            token_usage["project_context"] = self.budget.count_tokens(fitted)

        # RAG results
        if rag_results:
            fitted = self.budget.fit_content(
                "rag_results",
                rag_results,
                allocations["rag_results"]
            )
            sections["rag_results"] = fitted
            token_usage["rag_results"] = self.budget.count_tokens(fitted)

        # Conversation history
        if conversation_history:
            fitted = self.budget.fit_content(
                "conversation_history",
                conversation_history,
                allocations["conversation_history"]
            )
            sections["conversation_history"] = fitted
            token_usage["conversation_history"] = self.budget.count_tokens(fitted)

        # Working memory
        if working_memory:
            fitted = self.budget.fit_content(
                "working_memory",
                working_memory,
                allocations["working_memory"]
            )
            sections["working_memory"] = fitted
            token_usage["working_memory"] = self.budget.count_tokens(fitted)

        # Query (truncate if needed)
        query_fitted = self.budget.fit_content(
            "query",
            query,
            allocations["query"]
        )
        sections["query"] = query_fitted
        token_usage["query"] = self.budget.count_tokens(query_fitted)

        # Build formatted context
        context_parts = []

        if "system_prompt" in sections:
            context_parts.append(f"<SYSTEM>\n{sections['system_prompt']}\n</SYSTEM>")

        if "user_facts" in sections:
            context_parts.append(f"<USER_FACTS>\n{sections['user_facts']}\n</USER_FACTS>")

        if "project_context" in sections:
            context_parts.append(f"<PROJECT>\n{sections['project_context']}\n</PROJECT>")

        if "rag_results" in sections:
            context_parts.append(f"<CONTEXT>\n{sections['rag_results']}\n</CONTEXT>")

        if "conversation_history" in sections:
            context_parts.append(f"<HISTORY>\n{sections['conversation_history']}\n</HISTORY>")

        if "working_memory" in sections:
            context_parts.append(f"<WORKING_MEMORY>\n{sections['working_memory']}\n</WORKING_MEMORY>")

        context_parts.append(f"<QUERY>\n{sections['query']}\n</QUERY>")

        formatted_context = "\n\n".join(context_parts)
        token_usage["total"] = self.budget.count_tokens(formatted_context)
        token_usage["query_type"] = query_type.value

        return formatted_context, token_usage

    def build_ordered(
        self,
        query: str,
        system_prompt: str = "",
        user_facts: str = "",
        project_context: str = "",
        rag_results: Union[str, List[Tuple[str, float]]] = "",
        conversation_history: str = "",
        working_memory: str = "",
        total_tokens: int = 2000,
        query_type: Optional[QueryType] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build context with attention-optimized ordering.

        Enhanced version of build() that uses priority-based ordering
        to place important content at attention-critical positions.

        Key differences from build():
        1. Sections are ordered by priority and position hints
        2. Uses primacy/recency effect for optimal attention
        3. RAG results can include relevance scores for dynamic priority
        4. Returns detailed ordering metadata

        Args:
            query: User query
            system_prompt: System prompt content
            user_facts: User facts/preferences
            project_context: Current project context
            rag_results: Either a string or list of (content, relevance_score) tuples
            conversation_history: Recent conversation
            working_memory: Working memory content
            total_tokens: Total token budget
            query_type: Query type (auto-detected if None)

        Returns:
            Tuple of (formatted context string, detailed metadata dict)
        """
        if query_type is None:
            query_type = self.budget.detect_query_type(query)

        # Build ContextSection objects
        sections: List[ContextSection] = []

        if system_prompt:
            sections.append(self.budget.create_context_section(
                "system_prompt", system_prompt, 1.0, query_type
            ))

        if user_facts:
            sections.append(self.budget.create_context_section(
                "user_facts", user_facts, 0.8, query_type
            ))

        if project_context:
            sections.append(self.budget.create_context_section(
                "project_context", project_context, 0.6, query_type
            ))

        # Handle RAG results with optional relevance scores
        if rag_results:
            if isinstance(rag_results, str):
                # Single string, use default relevance
                sections.append(self.budget.create_context_section(
                    "rag_results", rag_results, 0.7, query_type
                ))
            else:
                # List of (content, relevance) tuples - create multiple sections
                # Combine into single section with weighted relevance
                combined_content = []
                total_relevance = 0.0
                for content, relevance in rag_results:
                    combined_content.append(content)
                    total_relevance += relevance
                avg_relevance = total_relevance / len(rag_results) if rag_results else 0.5
                sections.append(self.budget.create_context_section(
                    "rag_results",
                    "\n\n".join(combined_content),
                    avg_relevance,
                    query_type
                ))

        if conversation_history:
            # Recent conversation has high relevance
            sections.append(self.budget.create_context_section(
                "conversation_history", conversation_history, 0.9, query_type
            ))

        if working_memory:
            sections.append(self.budget.create_context_section(
                "working_memory", working_memory, 0.5, query_type
            ))

        # Query section (always last due to position hint)
        sections.append(self.budget.create_context_section(
            "query", query, 1.0, query_type
        ))

        # Use the budget's ordered context builder
        return self.budget.build_ordered_context(
            sections, query, total_tokens, query_type
        )


# =============================================================================
# Context Importance Scorer (Phase 2.3.4)
# =============================================================================

class ContextType(Enum):
    """Types of context content for importance scoring."""
    RAG_RESULT = "rag_result"          # Retrieved from vector search
    CONVERSATION = "conversation"       # Chat history
    USER_FACT = "user_fact"            # Stored user preferences/facts
    PROJECT_CONTEXT = "project_context" # Project-specific info
    WORKING_MEMORY = "working_memory"   # Short-term memory
    SYSTEM_PROMPT = "system_prompt"     # System instructions
    CODE_SNIPPET = "code_snippet"       # Code from indexer
    DOCUMENTATION = "documentation"     # Doc sections


@dataclass
class ScoredContent:
    """
    A piece of context content with its importance score and metadata.

    Attributes:
        content_id: Unique identifier for this content
        content: The actual text content
        context_type: Type of context (RAG, conversation, etc.)
        importance_score: Combined importance score (0.0-1.0)
        query_relevance: How relevant to current query (0.0-1.0)
        recency_score: How recent (0.0-1.0, higher = more recent)
        reliability_score: Source reliability (0.0-1.0)
        usage_score: Based on usage history (0.0-1.0)
        token_count: Estimated tokens
        metadata: Additional metadata
    """
    content_id: str
    content: str
    context_type: ContextType
    importance_score: float = 0.0
    query_relevance: float = 0.0
    recency_score: float = 0.0
    reliability_score: float = 0.5
    usage_score: float = 0.5
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.token_count == 0 and self.content:
            self.token_count = len(self.content) // 4

    def __lt__(self, other: 'ScoredContent') -> bool:
        """Enable sorting by importance score (higher first)."""
        return self.importance_score > other.importance_score


class ContextImportanceScorer:
    """
    Scores context pieces for intelligent selection and ordering.

    Phase 2.3.4: Multi-factor importance scoring based on:
    - Query relevance (semantic similarity)
    - Recency (newer content scores higher)
    - Source reliability (trusted sources score higher)
    - Usage history (frequently useful content scores higher)

    Uses scores for:
    - Deciding what to keep vs truncate
    - Ordering within sections
    - Allocating variable token budgets

    Example:
        scorer = ContextImportanceScorer()

        # Score individual content
        score = scorer.score_content(
            "User likes Python",
            query="code help",
            context_type=ContextType.USER_FACT
        )

        # Rank multiple pieces of content
        ranked = scorer.rank_contents(contents, query="explain decorators")

        # Filter by threshold
        if scorer.should_include(content, query, score_threshold=0.3):
            include_in_context(content)
    """

    # Scoring weights by context type
    # Format: {context_type: (relevance_weight, recency_weight, reliability_weight, usage_weight)}
    TYPE_WEIGHTS = {
        ContextType.RAG_RESULT: (0.50, 0.15, 0.20, 0.15),       # High relevance importance
        ContextType.CONVERSATION: (0.30, 0.45, 0.10, 0.15),     # High recency importance
        ContextType.USER_FACT: (0.35, 0.10, 0.30, 0.25),        # High reliability & usage
        ContextType.PROJECT_CONTEXT: (0.40, 0.15, 0.25, 0.20),  # Balanced
        ContextType.WORKING_MEMORY: (0.25, 0.50, 0.10, 0.15),   # Very high recency
        ContextType.SYSTEM_PROMPT: (0.20, 0.05, 0.50, 0.25),    # High reliability
        ContextType.CODE_SNIPPET: (0.55, 0.10, 0.20, 0.15),     # Very high relevance
        ContextType.DOCUMENTATION: (0.45, 0.15, 0.25, 0.15),    # High relevance
    }

    # Base reliability scores by context type
    BASE_RELIABILITY = {
        ContextType.SYSTEM_PROMPT: 1.0,      # Always trusted
        ContextType.USER_FACT: 0.9,          # User-provided, high trust
        ContextType.DOCUMENTATION: 0.85,     # Official docs
        ContextType.CODE_SNIPPET: 0.8,       # From codebase
        ContextType.PROJECT_CONTEXT: 0.75,   # Curated context
        ContextType.CONVERSATION: 0.6,       # May contain errors
        ContextType.RAG_RESULT: 0.5,         # Variable quality
        ContextType.WORKING_MEMORY: 0.7,     # Short-term, may be stale
    }

    # Recency decay: half-life in seconds for each context type
    RECENCY_HALFLIFE = {
        ContextType.WORKING_MEMORY: 300,      # 5 minutes
        ContextType.CONVERSATION: 3600,       # 1 hour
        ContextType.RAG_RESULT: 86400,        # 1 day
        ContextType.PROJECT_CONTEXT: 604800,  # 1 week
        ContextType.CODE_SNIPPET: 259200,     # 3 days
        ContextType.DOCUMENTATION: 2592000,   # 30 days
        ContextType.USER_FACT: 31536000,      # 1 year
        ContextType.SYSTEM_PROMPT: float('inf'),  # Never decays
    }

    # Chars per token estimate
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        use_embeddings: bool = True,
        usage_history_path: Optional[str] = None,
        custom_weights: Optional[Dict[ContextType, Tuple[float, float, float, float]]] = None
    ):
        """
        Initialize the context importance scorer.

        Args:
            use_embeddings: Whether to use MLX embeddings for semantic similarity
            usage_history_path: Path to usage history JSON file
            custom_weights: Override default type weights
        """
        self.use_embeddings = use_embeddings
        self.usage_history_path = usage_history_path
        self._usage_history: Dict[str, Dict[str, Any]] = {}
        self._embedding_cache: Dict[str, Any] = {}
        self._now = time.time()

        # Override weights if provided
        if custom_weights:
            self.TYPE_WEIGHTS = {**self.TYPE_WEIGHTS, **custom_weights}

        # Try to load usage history
        if usage_history_path:
            self._load_usage_history()

        # Lazy-load embedding model
        self._mlx_model = None
        self._mlx_tokenizer = None

    def _load_usage_history(self) -> None:
        """Load usage history from file."""
        import json
        try:
            if self.usage_history_path:
                from pathlib import Path
                path = Path(self.usage_history_path)
                if path.exists():
                    with open(path) as f:
                        self._usage_history = json.load(f)
        except Exception:
            self._usage_history = {}

    def _save_usage_history(self) -> None:
        """Save usage history to file."""
        import json
        try:
            if self.usage_history_path:
                from pathlib import Path
                path = Path(self.usage_history_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    json.dump(self._usage_history, f, indent=2)
        except Exception:
            pass

    def _get_content_id(self, content: str) -> str:
        """Generate a stable ID for content."""
        return hashlib.md5(content[:500].encode()).hexdigest()[:16]

    def _get_embedding(self, text: str) -> Optional[Any]:
        """Get embedding for text using MLX (with caching)."""
        if not self.use_embeddings:
            return None

        # Check cache
        cache_key = self._get_content_id(text)
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        try:
            import mlx_embeddings
            import numpy as np

            # Lazy load model
            if self._mlx_model is None:
                self._mlx_model, self._mlx_tokenizer = mlx_embeddings.load(
                    "sentence-transformers/all-MiniLM-L6-v2"
                )

            output = mlx_embeddings.generate(
                self._mlx_model,
                self._mlx_tokenizer,
                text[:2000]
            )
            embedding = np.array(output.text_embeds[0])

            # Cache (limit size)
            if len(self._embedding_cache) > 500:
                # Remove oldest entries
                keys = list(self._embedding_cache.keys())[:100]
                for k in keys:
                    del self._embedding_cache[k]

            self._embedding_cache[cache_key] = embedding
            return embedding

        except Exception:
            return None

    def _compute_semantic_similarity(self, query: str, content: str) -> float:
        """Compute semantic similarity between query and content."""
        query_emb = self._get_embedding(query)
        content_emb = self._get_embedding(content)

        if query_emb is None or content_emb is None:
            # Fall back to keyword overlap
            return self._keyword_similarity(query, content)

        try:
            import numpy as np
            similarity = float(np.dot(query_emb, content_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(content_emb) + 1e-8
            ))
            # Normalize from [-1, 1] to [0, 1]
            return (similarity + 1) / 2
        except Exception:
            return self._keyword_similarity(query, content)

    def _keyword_similarity(self, query: str, content: str) -> float:
        """Simple keyword overlap similarity as fallback."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        overlap = len(query_words & content_words)
        return min(1.0, overlap / len(query_words))

    def _compute_recency_score(
        self,
        context_type: ContextType,
        timestamp: Optional[float] = None
    ) -> float:
        """
        Compute recency score based on age and context type half-life.

        Args:
            context_type: Type of context
            timestamp: Unix timestamp (uses now if None)

        Returns:
            Score from 0.0 (very old) to 1.0 (just now)
        """
        if timestamp is None:
            return 1.0

        age_seconds = self._now - timestamp
        if age_seconds <= 0:
            return 1.0

        halflife = self.RECENCY_HALFLIFE.get(context_type, 86400)
        if halflife == float('inf'):
            return 1.0

        # Exponential decay
        import math
        decay = 0.5 ** (age_seconds / halflife)
        return max(0.1, decay)  # Minimum 0.1 score

    def _compute_reliability_score(
        self,
        context_type: ContextType,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> float:
        """
        Compute reliability score based on context type and source.

        Args:
            context_type: Type of context
            source: Source identifier (e.g., database name, file path)
            metadata: Additional metadata

        Returns:
            Score from 0.0 (unreliable) to 1.0 (highly reliable)
        """
        base = self.BASE_RELIABILITY.get(context_type, 0.5)

        # Adjust based on metadata
        if metadata:
            # Boost for verified content
            if metadata.get("verified", False):
                base = min(1.0, base + 0.1)

            # Boost for high-confidence RAG results
            if "confidence" in metadata:
                conf = float(metadata["confidence"])
                base = (base + conf) / 2

            # Penalize if marked as uncertain
            if metadata.get("uncertain", False):
                base *= 0.8

        return base

    def _compute_usage_score(self, content_id: str) -> float:
        """
        Compute usage score based on historical effectiveness.

        Tracks:
        - How often this content was included in context
        - Whether including it led to positive outcomes

        Args:
            content_id: Unique content identifier

        Returns:
            Score from 0.0 (never useful) to 1.0 (always useful)
        """
        if content_id not in self._usage_history:
            return 0.5  # Neutral for unseen content

        history = self._usage_history[content_id]
        uses = history.get("uses", 0)
        successes = history.get("successes", 0)

        if uses == 0:
            return 0.5

        # Wilson score interval for small sample sizes
        # Gives reasonable estimates even with few data points
        z = 1.96  # 95% confidence
        n = uses
        p = successes / n

        denominator = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denominator
        margin = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5 / denominator

        # Use lower bound of confidence interval
        return max(0.1, min(1.0, center - margin))

    def record_usage(
        self,
        content_id: str,
        was_helpful: bool
    ) -> None:
        """
        Record that content was used and whether it was helpful.

        Call this after getting feedback on a response to improve
        future content selection.

        Args:
            content_id: Unique content identifier
            was_helpful: Whether the content contributed to a good response
        """
        if content_id not in self._usage_history:
            self._usage_history[content_id] = {"uses": 0, "successes": 0}

        self._usage_history[content_id]["uses"] += 1
        if was_helpful:
            self._usage_history[content_id]["successes"] += 1

        self._save_usage_history()

    def score_content(
        self,
        content: str,
        query: str,
        context_type: Union[ContextType, str],
        timestamp: Optional[float] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> float:
        """
        Score a piece of content for importance in the current context.

        Args:
            content: The text content to score
            query: Current user query
            context_type: Type of context (ContextType enum or string)
            timestamp: When the content was created/updated (Unix timestamp)
            source: Source identifier for reliability scoring
            metadata: Additional metadata

        Returns:
            Importance score from 0.0 to 1.0
        """
        # Normalize context type
        if isinstance(context_type, str):
            try:
                context_type = ContextType(context_type)
            except ValueError:
                context_type = ContextType.RAG_RESULT

        # Get weights for this context type
        weights = self.TYPE_WEIGHTS.get(
            context_type,
            (0.4, 0.2, 0.2, 0.2)  # Default balanced weights
        )
        rel_w, rec_w, reliability_w, usage_w = weights

        # Compute individual scores
        relevance = self._compute_semantic_similarity(query, content)
        recency = self._compute_recency_score(context_type, timestamp)
        reliability = self._compute_reliability_score(context_type, source, metadata)

        content_id = self._get_content_id(content)
        usage = self._compute_usage_score(content_id)

        # Weighted combination
        importance = (
            relevance * rel_w +
            recency * rec_w +
            reliability * reliability_w +
            usage * usage_w
        )

        return min(1.0, max(0.0, importance))

    def rank_contents(
        self,
        contents: List[Dict[str, Any]],
        query: str,
        return_scored: bool = False
    ) -> List[Union[Dict[str, Any], ScoredContent]]:
        """
        Rank multiple pieces of content by importance.

        Args:
            contents: List of content dicts with keys:
                - content: str (required)
                - context_type: str or ContextType (optional, default: rag_result)
                - timestamp: float (optional)
                - source: str (optional)
                - metadata: dict (optional)
            query: Current user query
            return_scored: If True, return ScoredContent objects instead of dicts

        Returns:
            Sorted list (highest importance first)
        """
        scored = []

        for item in contents:
            content = item.get("content", "")
            if not content:
                continue

            ctx_type = item.get("context_type", "rag_result")
            if isinstance(ctx_type, str):
                try:
                    ctx_type = ContextType(ctx_type)
                except ValueError:
                    ctx_type = ContextType.RAG_RESULT

            timestamp = item.get("timestamp")
            source = item.get("source")
            metadata = item.get("metadata", {})

            # Compute individual scores
            rel_w, rec_w, reliability_w, usage_w = self.TYPE_WEIGHTS.get(
                ctx_type, (0.4, 0.2, 0.2, 0.2)
            )

            relevance = self._compute_semantic_similarity(query, content)
            recency = self._compute_recency_score(ctx_type, timestamp)
            reliability = self._compute_reliability_score(ctx_type, source, metadata)
            content_id = self._get_content_id(content)
            usage = self._compute_usage_score(content_id)

            importance = (
                relevance * rel_w +
                recency * rec_w +
                reliability * reliability_w +
                usage * usage_w
            )
            importance = min(1.0, max(0.0, importance))

            scored_item = ScoredContent(
                content_id=content_id,
                content=content,
                context_type=ctx_type,
                importance_score=importance,
                query_relevance=relevance,
                recency_score=recency,
                reliability_score=reliability,
                usage_score=usage,
                token_count=len(content) // self.CHARS_PER_TOKEN,
                metadata={**metadata, **item}
            )
            scored.append(scored_item)

        # Sort by importance (highest first)
        scored.sort()

        if return_scored:
            return scored
        else:
            # Return original dicts in sorted order
            return [s.metadata for s in scored]

    def should_include(
        self,
        content: str,
        query: str,
        context_type: Union[ContextType, str] = ContextType.RAG_RESULT,
        score_threshold: float = 0.3,
        **kwargs
    ) -> bool:
        """
        Determine if content should be included based on importance threshold.

        Args:
            content: The text content
            query: Current user query
            context_type: Type of context
            score_threshold: Minimum importance score to include (default: 0.3)
            **kwargs: Additional args passed to score_content

        Returns:
            True if content should be included
        """
        score = self.score_content(content, query, context_type, **kwargs)
        return score >= score_threshold

    def allocate_token_budget(
        self,
        contents: List[Dict[str, Any]],
        query: str,
        total_budget: int
    ) -> List[Tuple[Dict[str, Any], int]]:
        """
        Allocate token budget across content pieces based on importance.

        Higher importance content gets more tokens. Content below threshold
        may be excluded entirely.

        Args:
            contents: List of content dicts (same format as rank_contents)
            query: Current user query
            total_budget: Total token budget to allocate

        Returns:
            List of (content_dict, allocated_tokens) tuples, sorted by importance
        """
        scored = self.rank_contents(contents, query, return_scored=True)

        if not scored:
            return []

        # Calculate total importance for normalization
        total_importance = sum(s.importance_score for s in scored)
        if total_importance == 0:
            # Equal distribution if no importance differentiation
            per_item = total_budget // len(scored)
            return [(s.metadata, per_item) for s in scored]

        # Allocate proportionally with minimum threshold
        allocations = []
        min_tokens = 10  # Minimum allocation if included
        remaining_budget = total_budget

        for scored_content in scored:
            if remaining_budget <= 0:
                break

            # Calculate proportional allocation
            proportion = scored_content.importance_score / total_importance
            allocated = int(total_budget * proportion)

            # Enforce minimum (at least min_tokens or content size, whichever is smaller)
            allocated = max(min(min_tokens, scored_content.token_count), allocated)
            # Don't exceed remaining budget or actual content size
            allocated = min(allocated, remaining_budget)
            allocated = min(allocated, scored_content.token_count)

            if allocated > 0:
                allocations.append((scored_content.metadata, allocated))
                remaining_budget -= allocated

        return allocations

    def select_for_budget(
        self,
        contents: List[Dict[str, Any]],
        query: str,
        token_budget: int,
        score_threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Select content pieces that fit within token budget, prioritized by importance.

        Args:
            contents: List of content dicts
            query: Current user query
            token_budget: Maximum tokens to include
            score_threshold: Minimum importance score

        Returns:
            List of content dicts that fit within budget
        """
        scored = self.rank_contents(contents, query, return_scored=True)

        selected = []
        used_tokens = 0

        for scored_content in scored:
            # Skip if below threshold
            if scored_content.importance_score < score_threshold:
                continue

            # Check if fits in budget
            if used_tokens + scored_content.token_count <= token_budget:
                selected.append(scored_content.metadata)
                used_tokens += scored_content.token_count

        return selected

    def refresh_timestamp(self) -> None:
        """Refresh the current time reference for recency calculations."""
        self._now = time.time()


# Singleton instance
_importance_scorer: Optional[ContextImportanceScorer] = None


def get_importance_scorer() -> ContextImportanceScorer:
    """Get singleton ContextImportanceScorer instance."""
    global _importance_scorer
    if _importance_scorer is None:
        _importance_scorer = ContextImportanceScorer()
    return _importance_scorer


# =============================================================================
# Adaptive Context Manager (Phase 2.3.5)
# =============================================================================

@dataclass
class AdaptiveSection:
    """
    Configuration for an adaptive context section.

    Attributes:
        name: Section identifier
        enabled: Whether to include this section
        budget_ratio: Ratio of total budget (0.0-1.0)
        min_tokens: Minimum token allocation
        max_tokens: Maximum token allocation (0 = unlimited)
        priority: Section priority for ordering
        required: If True, section cannot be disabled
    """
    name: str
    enabled: bool = True
    budget_ratio: float = 0.1
    min_tokens: int = 0
    max_tokens: int = 0  # 0 = no max
    priority: SectionPriority = SectionPriority.MEDIUM
    required: bool = False

    def get_allocation(self, total_budget: int) -> int:
        """Calculate token allocation for this section."""
        if not self.enabled:
            return 0

        base = int(total_budget * self.budget_ratio)
        base = max(self.min_tokens, base)

        if self.max_tokens > 0:
            base = min(self.max_tokens, base)

        return base


class AdaptiveContextManager:
    """
    Adaptive context manager that dynamically adjusts context based on query type.

    Phase 2.3.5: Query-type-aware context adaptation.

    This manager:
    1. Detects query type from user input
    2. Determines which sections should be included
    3. Adjusts budget allocations per section
    4. Provides section configurations for context building

    Query Type Adaptations:

    CODE:
        - More RAG results (code snippets, documentation)
        - Less personality/roleplay context
        - Include project context
        - Minimal conversation history

    CHAT:
        - More conversation history (recent context)
        - User facts for personalization
        - Standard personality context
        - Reduced RAG (unless topic-specific)

    RECALL:
        - Maximum user facts
        - Full conversation history
        - Working memory emphasized
        - Minimal RAG (user already knows the topic)

    REASONING:
        - More working memory (step tracking)
        - Project context for reference
        - RAG for relevant facts
        - Reduced personality

    ROLEPLAY:
        - Full personality/system prompt
        - Heavy conversation history (continuity)
        - User facts (relationship context)
        - Minimal RAG and project context

    PROJECT:
        - Maximum project context
        - RAG for project-related info
        - Working memory for task tracking
        - Standard conversation history

    Example:
        manager = AdaptiveContextManager()

        # Get sections for a code query
        sections = manager.get_adaptive_sections("How do I fix this Python bug?")
        # Returns: ['system_prompt', 'rag_results', 'project_context', 'query']

        # Get adapted budget
        budget = manager.adapt_budget(QueryType.CODE, total_tokens=2000)
        # Returns: {'system_prompt': 100, 'rag_results': 600, 'project_context': 300, ...}
    """

    # Section configurations by query type
    # Format: {query_type: {section_name: AdaptiveSection config dict}}
    SECTION_CONFIGS = {
        QueryType.CODE: {
            "system_prompt": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
            "user_facts": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.LOW},
            "project_context": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.HIGH},
            "rag_results": {"enabled": True, "budget_ratio": 0.35, "priority": SectionPriority.CRITICAL},  # Max RAG
            "conversation_history": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.MEDIUM},
            "working_memory": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.MEDIUM},
            "code_snippets": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.HIGH},  # New: code-specific
            "query": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
        },
        QueryType.CHAT: {
            "system_prompt": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.CRITICAL, "required": True},
            "user_facts": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.HIGH},  # Personalization
            "project_context": {"enabled": False, "budget_ratio": 0.0, "priority": SectionPriority.MINIMAL},  # Not needed
            "rag_results": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.LOW},  # Minimal RAG
            "conversation_history": {"enabled": True, "budget_ratio": 0.40, "priority": SectionPriority.CRITICAL},  # Max history
            "working_memory": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.MEDIUM},
            "personality": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.HIGH},  # SAM personality
            "query": {"enabled": True, "budget_ratio": 0.07, "priority": SectionPriority.CRITICAL, "required": True},
        },
        QueryType.RECALL: {
            "system_prompt": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
            "user_facts": {"enabled": True, "budget_ratio": 0.30, "priority": SectionPriority.CRITICAL},  # Max facts
            "project_context": {"enabled": False, "budget_ratio": 0.0, "priority": SectionPriority.MINIMAL},
            "rag_results": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.LOW},  # Minimal
            "conversation_history": {"enabled": True, "budget_ratio": 0.35, "priority": SectionPriority.CRITICAL},  # Max history
            "working_memory": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.HIGH},  # For recall context
            "query": {"enabled": True, "budget_ratio": 0.07, "priority": SectionPriority.CRITICAL, "required": True},
        },
        QueryType.REASONING: {
            "system_prompt": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
            "user_facts": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.LOW},
            "project_context": {"enabled": True, "budget_ratio": 0.12, "priority": SectionPriority.HIGH},
            "rag_results": {"enabled": True, "budget_ratio": 0.25, "priority": SectionPriority.CRITICAL},
            "conversation_history": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.MEDIUM},
            "working_memory": {"enabled": True, "budget_ratio": 0.25, "priority": SectionPriority.CRITICAL},  # Step tracking
            "reasoning_steps": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.HIGH},  # New: reasoning
            "query": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
        },
        QueryType.ROLEPLAY: {
            "system_prompt": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.CRITICAL, "required": True},  # Full persona
            "user_facts": {"enabled": True, "budget_ratio": 0.12, "priority": SectionPriority.HIGH},  # Relationship
            "project_context": {"enabled": False, "budget_ratio": 0.0, "priority": SectionPriority.MINIMAL},  # Not needed
            "rag_results": {"enabled": False, "budget_ratio": 0.0, "priority": SectionPriority.MINIMAL},  # Breaks immersion
            "conversation_history": {"enabled": True, "budget_ratio": 0.45, "priority": SectionPriority.CRITICAL},  # Continuity
            "working_memory": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.MEDIUM},
            "personality": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.CRITICAL},  # Full personality
            "query": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
        },
        QueryType.PROJECT: {
            "system_prompt": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
            "user_facts": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.LOW},
            "project_context": {"enabled": True, "budget_ratio": 0.30, "priority": SectionPriority.CRITICAL},  # Max project
            "rag_results": {"enabled": True, "budget_ratio": 0.25, "priority": SectionPriority.CRITICAL},  # Project docs
            "conversation_history": {"enabled": True, "budget_ratio": 0.15, "priority": SectionPriority.MEDIUM},
            "working_memory": {"enabled": True, "budget_ratio": 0.12, "priority": SectionPriority.HIGH},  # Task tracking
            "query": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.CRITICAL, "required": True},
        },
    }

    # Default section config (fallback)
    DEFAULT_SECTIONS = {
        "system_prompt": {"enabled": True, "budget_ratio": 0.05, "priority": SectionPriority.CRITICAL, "required": True},
        "user_facts": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.MEDIUM},
        "project_context": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.MEDIUM},
        "rag_results": {"enabled": True, "budget_ratio": 0.20, "priority": SectionPriority.HIGH},
        "conversation_history": {"enabled": True, "budget_ratio": 0.25, "priority": SectionPriority.HIGH},
        "working_memory": {"enabled": True, "budget_ratio": 0.08, "priority": SectionPriority.LOW},
        "query": {"enabled": True, "budget_ratio": 0.10, "priority": SectionPriority.CRITICAL, "required": True},
    }

    # Minimum tokens per section type (prevents over-truncation)
    MIN_TOKENS = {
        "system_prompt": 50,
        "user_facts": 0,
        "project_context": 0,
        "rag_results": 50,
        "conversation_history": 100,
        "working_memory": 0,
        "personality": 50,
        "code_snippets": 0,
        "reasoning_steps": 0,
        "query": 30,
    }

    # Maximum tokens per section type (prevents budget hogging)
    MAX_TOKENS = {
        "system_prompt": 300,
        "personality": 200,
        "reasoning_steps": 400,
    }

    def __init__(
        self,
        context_budget: Optional[ContextBudget] = None,
        default_budget: int = 2000
    ):
        """
        Initialize the adaptive context manager.

        Args:
            context_budget: Optional ContextBudget instance for query type detection
            default_budget: Default total token budget
        """
        self.budget = context_budget or ContextBudget(default_budget)
        self.default_budget = default_budget
        self._adaptation_history: List[Dict[str, Any]] = []

    def get_adaptive_sections(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        available_sections: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get list of sections to include based on query type.

        This method determines which sections should be populated and included
        in the context. Sections not in this list should be omitted entirely
        (not just given zero budget).

        Args:
            query: User query string
            query_type: Query type (auto-detected if None)
            available_sections: Optional list of sections that have content
                                (if provided, only returns intersection)

        Returns:
            List of section names to include, ordered by priority

        Example:
            sections = manager.get_adaptive_sections("fix this bug")
            # ['system_prompt', 'rag_results', 'project_context',
            #  'code_snippets', 'working_memory', 'conversation_history',
            #  'user_facts', 'query']
        """
        # Detect query type if not provided
        if query_type is None:
            query_type = self.budget.detect_query_type(query)

        # Get section config for this query type
        config = self.SECTION_CONFIGS.get(query_type, self.DEFAULT_SECTIONS)

        # Build list of enabled sections
        enabled_sections: List[Tuple[str, SectionPriority]] = []

        for section_name, section_config in config.items():
            if section_config.get("enabled", True):
                # If available_sections provided, check if we have content
                if available_sections is not None:
                    if section_name not in available_sections:
                        # Skip unless required
                        if not section_config.get("required", False):
                            continue

                priority = section_config.get("priority", SectionPriority.MEDIUM)
                enabled_sections.append((section_name, priority))

        # Sort by priority (CRITICAL first, then HIGH, etc.)
        enabled_sections.sort(key=lambda x: x[1].value)

        return [name for name, _ in enabled_sections]

    def adapt_budget(
        self,
        query_type: QueryType,
        total_budget: Optional[int] = None,
        available_sections: Optional[List[str]] = None,
        custom_overrides: Optional[Dict[str, float]] = None
    ) -> Dict[str, int]:
        """
        Get adapted budget allocations for a query type.

        Calculates token allocations for each section based on query type
        configuration. Sections not enabled get 0 tokens.

        Args:
            query_type: Type of query
            total_budget: Total available tokens (uses default if None)
            available_sections: Optional list of sections with content
            custom_overrides: Optional dict of {section: ratio_multiplier}

        Returns:
            Dict mapping section names to token allocations

        Example:
            budget = manager.adapt_budget(QueryType.CODE, total_budget=2000)
            # {'system_prompt': 100, 'rag_results': 700, 'project_context': 300,
            #  'code_snippets': 200, 'conversation_history': 300,
            #  'working_memory': 200, 'user_facts': 100, 'query': 100}
        """
        total = total_budget or self.default_budget

        # Get section config for this query type
        config = self.SECTION_CONFIGS.get(query_type, self.DEFAULT_SECTIONS)

        # Calculate base allocations
        allocations: Dict[str, int] = {}
        total_ratio = 0.0

        for section_name, section_config in config.items():
            if not section_config.get("enabled", True):
                allocations[section_name] = 0
                continue

            # Skip if section not available (unless required)
            if available_sections is not None:
                if section_name not in available_sections:
                    if not section_config.get("required", False):
                        allocations[section_name] = 0
                        continue

            ratio = section_config.get("budget_ratio", 0.1)

            # Apply custom overrides if provided
            if custom_overrides and section_name in custom_overrides:
                ratio *= custom_overrides[section_name]

            total_ratio += ratio
            allocations[section_name] = ratio  # Store ratio temporarily

        # Normalize ratios to fit total budget
        if total_ratio > 0:
            normalization = 1.0 / total_ratio
        else:
            normalization = 1.0

        # Convert ratios to token counts
        for section_name in allocations:
            if allocations[section_name] > 0:
                ratio = allocations[section_name] * normalization
                tokens = int(total * ratio)

                # Apply min/max constraints
                min_tok = self.MIN_TOKENS.get(section_name, 0)
                max_tok = self.MAX_TOKENS.get(section_name, 0)

                tokens = max(min_tok, tokens)
                if max_tok > 0:
                    tokens = min(max_tok, tokens)

                allocations[section_name] = tokens

        # Ensure we don't exceed total budget
        current_total = sum(allocations.values())
        if current_total > total:
            # Scale down proportionally
            scale = total / current_total
            for section_name in allocations:
                if allocations[section_name] > 0:
                    scaled = int(allocations[section_name] * scale)
                    min_tok = self.MIN_TOKENS.get(section_name, 0)
                    allocations[section_name] = max(min_tok, scaled)

        # Record this adaptation
        self._adaptation_history.append({
            "query_type": query_type.value,
            "total_budget": total,
            "allocations": dict(allocations),
            "timestamp": time.time()
        })

        return allocations

    def get_section_config(
        self,
        query_type: QueryType,
        section_name: str
    ) -> AdaptiveSection:
        """
        Get the configuration for a specific section and query type.

        Args:
            query_type: Query type
            section_name: Section name

        Returns:
            AdaptiveSection with configuration
        """
        config = self.SECTION_CONFIGS.get(query_type, self.DEFAULT_SECTIONS)
        section_config = config.get(section_name, {"enabled": False})

        return AdaptiveSection(
            name=section_name,
            enabled=section_config.get("enabled", True),
            budget_ratio=section_config.get("budget_ratio", 0.1),
            min_tokens=self.MIN_TOKENS.get(section_name, 0),
            max_tokens=self.MAX_TOKENS.get(section_name, 0),
            priority=section_config.get("priority", SectionPriority.MEDIUM),
            required=section_config.get("required", False)
        )

    def build_adaptive_context(
        self,
        query: str,
        sections: Dict[str, str],
        total_budget: Optional[int] = None,
        query_type: Optional[QueryType] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build context with adaptive section selection and budget allocation.

        This is the main entry point for building optimized context.

        Args:
            query: User query
            sections: Dict mapping section names to content
            total_budget: Total token budget
            query_type: Query type (auto-detected if None)

        Returns:
            Tuple of (formatted context string, metadata dict)

        Example:
            context, meta = manager.build_adaptive_context(
                query="How do I fix this Python decorator?",
                sections={
                    "system_prompt": "You are SAM...",
                    "rag_results": "Decorators are functions...",
                    "project_context": "Flask web app...",
                    "conversation_history": "User: Help with Python...",
                },
                total_budget=2000
            )
        """
        total = total_budget or self.default_budget

        # Detect query type
        if query_type is None:
            query_type = self.budget.detect_query_type(query)

        # Get adaptive sections (only those that are enabled AND have content)
        available = list(sections.keys())
        enabled_sections = self.get_adaptive_sections(
            query, query_type, available_sections=available
        )

        # Get budget allocations
        allocations = self.adapt_budget(
            query_type, total, available_sections=available
        )

        # Build context sections with fitted content
        context_sections: List[ContextSection] = []

        for section_name in enabled_sections:
            if section_name not in sections:
                continue

            content = sections[section_name]
            if not content:
                continue

            budget = allocations.get(section_name, 200)

            # Fit content to budget
            fitted = self.budget.fit_content(section_name, content, budget)

            # Get section priority
            section_config = self.get_section_config(query_type, section_name)

            context_sections.append(ContextSection(
                name=section_name,
                content=fitted,
                priority=section_config.priority,
                relevance_score=0.7,  # Default, can be overridden
                token_count=self.budget.count_tokens(fitted),
                position_hint=self.budget.POSITION_HINTS.get(section_name)
            ))

        # Add query section
        query_budget = allocations.get("query", 100)
        fitted_query = self.budget.fit_content("query", query, query_budget)
        context_sections.append(ContextSection(
            name="query",
            content=fitted_query,
            priority=SectionPriority.CRITICAL,
            relevance_score=1.0,
            token_count=self.budget.count_tokens(fitted_query),
            position_hint="end"
        ))

        # Use ContextBudget's ordered context building
        return self.budget.build_ordered_context(
            context_sections, query, total, query_type
        )

    def get_query_type_summary(self, query_type: QueryType) -> Dict[str, Any]:
        """
        Get a summary of how a query type affects context building.

        Useful for debugging and understanding adaptations.

        Args:
            query_type: Query type to summarize

        Returns:
            Dict with configuration summary
        """
        config = self.SECTION_CONFIGS.get(query_type, self.DEFAULT_SECTIONS)

        enabled = []
        disabled = []
        priorities = {}

        for section_name, section_config in config.items():
            if section_config.get("enabled", True):
                enabled.append(section_name)
                priorities[section_name] = section_config.get(
                    "priority", SectionPriority.MEDIUM
                ).name
            else:
                disabled.append(section_name)

        # Calculate expected allocations
        allocations = self.adapt_budget(query_type, self.default_budget)

        return {
            "query_type": query_type.value,
            "enabled_sections": enabled,
            "disabled_sections": disabled,
            "priorities": priorities,
            "allocations": allocations,
            "total_allocated": sum(allocations.values())
        }

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics on context adaptations."""
        if not self._adaptation_history:
            return {"total_adaptations": 0}

        # Count by query type
        type_counts: Dict[str, int] = {}
        for adaptation in self._adaptation_history:
            qt = adaptation["query_type"]
            type_counts[qt] = type_counts.get(qt, 0) + 1

        return {
            "total_adaptations": len(self._adaptation_history),
            "by_query_type": type_counts,
            "last_adaptation": self._adaptation_history[-1]
        }


# Singleton instance for AdaptiveContextManager
_adaptive_manager: Optional[AdaptiveContextManager] = None


def get_adaptive_context_manager() -> AdaptiveContextManager:
    """Get singleton AdaptiveContextManager instance."""
    global _adaptive_manager
    if _adaptive_manager is None:
        _adaptive_manager = AdaptiveContextManager()
    return _adaptive_manager


if __name__ == "__main__":
    # Demo usage
    print("SAM Context Budget Allocator Demo")
    print("=" * 60)

    budget = ContextBudget(default_budget=2000)

    # Test query type detection
    test_queries = [
        "How do I implement a Python decorator?",
        "What was my favorite color that I told you earlier?",
        "Let's roleplay, you are a pirate captain",
        "Explain the pros and cons of microservices",
        "Tell me about the SAM brain architecture",
        "Hey, how's it going?"
    ]

    print("\nQuery Type Detection:")
    print("-" * 40)
    for query in test_queries:
        query_type = budget.detect_query_type(query)
        print(f"  '{query[:40]}...' -> {query_type.value}")

    # Test allocation
    print("\n\nBudget Allocation (2000 tokens):")
    print("-" * 40)

    for qt in [QueryType.CHAT, QueryType.CODE, QueryType.RECALL]:
        print(f"\n{qt.value.upper()}:")
        allocations = budget.allocate(qt, 2000)
        for section, tokens in allocations.items():
            bar = "=" * (tokens // 20)
            print(f"  {section:25} {tokens:4} tokens {bar}")

    # Test content fitting
    print("\n\nContent Truncation:")
    print("-" * 40)

    long_content = """This is a long piece of content that needs to be truncated.
    It contains multiple sentences. Each sentence provides some information.
    We want to truncate this intelligently at sentence boundaries when possible.
    This is the fourth sentence. And here is the fifth. The sixth sentence follows.
    Finally, this is the last sentence of the content."""

    print(f"Original ({budget.count_tokens(long_content)} tokens):")
    print(f"  {long_content[:80]}...")

    truncated = budget.fit_content("conversation_history", long_content, 50)
    print(f"\nTruncated for history ({budget.count_tokens(truncated)} tokens, preserve end):")
    print(f"  {truncated}")

    truncated = budget.fit_content("system_prompt", long_content, 50)
    print(f"\nTruncated for system ({budget.count_tokens(truncated)} tokens, preserve start):")
    print(f"  {truncated}")

    # Test RAG budget
    print("\n\nRAG Budget Calculation:")
    print("-" * 40)

    for qt in [QueryType.CHAT, QueryType.CODE, QueryType.RECALL]:
        rag_budget = budget.get_rag_budget(2000, qt)
        print(f"  {qt.value:12} -> {rag_budget} tokens for RAG")

    # Test with consumed tokens
    print("\n  With 800 tokens already consumed:")
    for qt in [QueryType.CHAT, QueryType.CODE]:
        rag_budget = budget.get_rag_budget(2000, qt, consumed_by_other_sections=800)
        print(f"    {qt.value:12} -> {rag_budget} tokens for RAG")

    # Test full context building
    print("\n\nFull Context Build:")
    print("-" * 40)

    builder = ContextBuilder(budget)

    context, usage = builder.build(
        query="How do I implement a custom decorator in Python?",
        system_prompt="You are SAM, a confident and helpful AI assistant.",
        user_facts="User is experienced with Python. Prefers concise answers.",
        project_context="Working on a Flask web application.",
        rag_results="Decorators are functions that modify other functions. Use @functools.wraps to preserve metadata.",
        conversation_history="User: Can you help with Python?\nSAM: Of course! What do you need?",
        working_memory="Current task: Python code assistance",
        total_tokens=2000
    )

    print(f"Query type detected: {usage['query_type']}")
    print(f"Total tokens used: {usage['total']}")
    print("\nToken usage by section:")
    for section, tokens in usage.items():
        if section not in ('total', 'query_type'):
            print(f"  {section:25} {tokens:4} tokens")

    # Test section priority
    print("\n\nSection Priority by Query Type:")
    print("-" * 40)

    for qt in [QueryType.CHAT, QueryType.CODE, QueryType.RECALL]:
        print(f"\n{qt.value.upper()}:")
        for section in ["system_prompt", "rag_results", "user_facts", "conversation_history"]:
            priority = budget.get_section_priority(section, qt)
            print(f"  {section:25} -> {priority.name}")

    # Test context ordering
    print("\n\nContext Ordering Demo:")
    print("-" * 40)

    # Create sections for ordering test
    test_sections = [
        ContextSection("system_prompt", "System instructions", SectionPriority.CRITICAL, 1.0),
        ContextSection("user_facts", "User preferences", SectionPriority.MEDIUM, 0.8),
        ContextSection("project_context", "Project details", SectionPriority.MEDIUM, 0.5),
        ContextSection("rag_results", "Retrieved context", SectionPriority.HIGH, 0.9),
        ContextSection("conversation_history", "Recent chat", SectionPriority.HIGH, 0.7),
        ContextSection("working_memory", "Current task info", SectionPriority.LOW, 0.4),
        ContextSection("query", "User question", SectionPriority.CRITICAL, 1.0),
    ]

    print("\nOriginal order:")
    for i, s in enumerate(test_sections):
        print(f"  {i}: {s.name} (priority={s.priority.name}, relevance={s.relevance_score})")

    ordered = budget.order_context_sections(test_sections, "How do I fix this bug?")

    print("\nAttention-optimized order (CODE query):")
    for i, s in enumerate(ordered):
        pos = "START" if i == 0 else ("END" if i == len(ordered)-1 else f"mid-{i}")
        print(f"  {pos}: {s.name} (priority={s.priority.name})")

    # Test ordered context building with relevance scores
    print("\n\nOrdered Context Build with Relevance:")
    print("-" * 40)

    context_ordered, metadata = builder.build_ordered(
        query="How do I implement a custom decorator in Python?",
        system_prompt="You are SAM, a confident and helpful AI assistant.",
        user_facts="User is experienced with Python. Prefers concise answers.",
        project_context="Working on a Flask web application.",
        rag_results=[
            ("Decorators are higher-order functions.", 0.95),
            ("Use @functools.wraps to preserve metadata.", 0.85),
            ("Python supports nested decorators.", 0.60),
        ],
        conversation_history="User: Can you help with Python?\nSAM: Of course!",
        working_memory="Current task: Python code assistance",
        total_tokens=2000
    )

    print(f"Query type: {metadata['query_type']}")
    print(f"Total tokens: {metadata['total_tokens']}")
    print(f"Primacy position: {metadata['attention_positions']['primacy']}")
    print(f"Recency position: {metadata['attention_positions']['recency']}")

    print("\nSection ordering:")
    for info in metadata['section_order']:
        print(f"  [{info['position']}] {info['name']:25} "
              f"priority={info['priority']:8} relevance={info['relevance']:.2f}")

    # Compare standard vs ordered output for different query types
    print("\n\nOrdering Comparison by Query Type:")
    print("-" * 40)

    for qt in [QueryType.CHAT, QueryType.CODE, QueryType.RECALL, QueryType.ROLEPLAY]:
        test_sections_copy = [
            ContextSection("system_prompt", "sys", SectionPriority.CRITICAL, 1.0),
            ContextSection("user_facts", "facts", SectionPriority.MEDIUM, 0.8),
            ContextSection("rag_results", "rag", SectionPriority.HIGH, 0.7),
            ContextSection("conversation_history", "history", SectionPriority.HIGH, 0.9),
            ContextSection("query", "query", SectionPriority.CRITICAL, 1.0),
        ]
        ordered = budget.order_context_sections(test_sections_copy, "test query", qt)
        order_str = " -> ".join([s.name.split("_")[0] for s in ordered])
        print(f"  {qt.value:10}: {order_str}")

    print("\n" + "=" * 60)
    print("Stats:", budget.get_allocation_stats())

    # =================================================================
    # Context Importance Scorer Demo (Phase 2.3.4)
    # =================================================================
    print("\n\n" + "=" * 60)
    print("Context Importance Scorer Demo (Phase 2.3.4)")
    print("=" * 60)

    scorer = ContextImportanceScorer(use_embeddings=False)  # Disable embeddings for demo

    # Test content pieces with various context types
    test_contents = [
        {
            "content": "User prefers Python and concise code examples",
            "context_type": "user_fact",
            "timestamp": time.time() - 86400,  # 1 day ago
        },
        {
            "content": "Decorators in Python are functions that modify other functions",
            "context_type": "rag_result",
            "timestamp": time.time() - 3600,  # 1 hour ago
            "metadata": {"confidence": 0.9},
        },
        {
            "content": "User: How do I use decorators?\nSAM: Let me explain...",
            "context_type": "conversation",
            "timestamp": time.time() - 300,  # 5 minutes ago
        },
        {
            "content": "Flask uses decorators extensively for route definitions",
            "context_type": "rag_result",
            "timestamp": time.time() - 7200,  # 2 hours ago
        },
        {
            "content": "Current project: sam_brain module improvements",
            "context_type": "working_memory",
            "timestamp": time.time() - 60,  # 1 minute ago
        },
        {
            "content": "JavaScript arrow functions are different from Python lambdas",
            "context_type": "rag_result",
            "timestamp": time.time() - 1800,  # 30 minutes ago
        },
    ]

    query = "How do I create a Python decorator?"

    print(f"\nQuery: '{query}'")
    print("\nIndividual Content Scoring:")
    print("-" * 50)

    for item in test_contents:
        score = scorer.score_content(
            item["content"],
            query,
            item["context_type"],
            timestamp=item.get("timestamp"),
            metadata=item.get("metadata")
        )
        age_mins = int((time.time() - item.get("timestamp", time.time())) / 60)
        print(f"  [{item['context_type']:15}] Score: {score:.3f} | Age: {age_mins:4}m | {item['content'][:40]}...")

    # Test ranking
    print("\n\nRanked Contents (highest importance first):")
    print("-" * 50)

    ranked = scorer.rank_contents(test_contents, query, return_scored=True)
    for i, scored in enumerate(ranked):
        print(f"  {i+1}. [{scored.context_type.value:15}] "
              f"Score: {scored.importance_score:.3f} "
              f"(rel={scored.query_relevance:.2f}, rec={scored.recency_score:.2f}, "
              f"reliability={scored.reliability_score:.2f})")
        print(f"     {scored.content[:60]}...")

    # Test should_include
    print("\n\nFiltering by Threshold (0.4):")
    print("-" * 50)

    for item in test_contents:
        include = scorer.should_include(
            item["content"],
            query,
            item["context_type"],
            score_threshold=0.4,
            timestamp=item.get("timestamp"),
            metadata=item.get("metadata")
        )
        status = "INCLUDE" if include else "EXCLUDE"
        print(f"  [{status:7}] {item['content'][:50]}...")

    # Test budget allocation
    print("\n\nToken Budget Allocation (500 tokens total):")
    print("-" * 50)

    allocations = scorer.allocate_token_budget(test_contents, query, total_budget=500)
    if allocations:
        for item, tokens in allocations:
            content = item.get("content", "")[:40]
            print(f"  {tokens:3} tokens -> {content}...")
    else:
        print("  (No allocations - content too small for budget)")

    # Test select_for_budget
    print("\n\nSelect for Budget (100 tokens, threshold 0.35):")
    print("-" * 50)

    selected = scorer.select_for_budget(test_contents, query, token_budget=100, score_threshold=0.35)
    for item in selected:
        print(f"  - {item['content'][:50]}...")

    print(f"\n  Selected {len(selected)} of {len(test_contents)} items")

    print("\n" + "=" * 60)
    print("Phase 2.3.4 Demo Complete")

    # =================================================================
    # Adaptive Context Manager Demo (Phase 2.3.5)
    # =================================================================
    print("\n\n" + "=" * 60)
    print("Adaptive Context Manager Demo (Phase 2.3.5)")
    print("=" * 60)

    adaptive = AdaptiveContextManager(default_budget=2000)

    # Test query type to sections mapping
    print("\nQuery Type to Sections Mapping:")
    print("-" * 50)

    test_queries_adaptive = [
        ("How do I fix this Python bug?", QueryType.CODE),
        ("Hey, what's up?", QueryType.CHAT),
        ("What did I tell you my name was?", QueryType.RECALL),
        ("Explain why microservices are better than monoliths", QueryType.REASONING),
        ("*walks into the tavern* Hello there, barkeep", QueryType.ROLEPLAY),
        ("Tell me about the SAM brain architecture", QueryType.PROJECT),
    ]

    for query_text, expected_type in test_queries_adaptive:
        sections = adaptive.get_adaptive_sections(query_text)
        print(f"\n  Query: '{query_text[:40]}...'")
        print(f"  Detected type: {adaptive.budget.detect_query_type(query_text).value}")
        print(f"  Enabled sections: {', '.join(sections[:5])}{'...' if len(sections) > 5 else ''}")

    # Test budget adaptation for each query type
    print("\n\nBudget Adaptation by Query Type (2000 tokens):")
    print("-" * 50)

    for qt in QueryType:
        print(f"\n{qt.value.upper()}:")
        allocations = adaptive.adapt_budget(qt, 2000)
        enabled = [(k, v) for k, v in allocations.items() if v > 0]
        disabled = [k for k, v in allocations.items() if v == 0]

        for section, tokens in sorted(enabled, key=lambda x: -x[1]):
            bar = "=" * (tokens // 40)
            print(f"    {section:25} {tokens:4} tokens {bar}")

        if disabled:
            print(f"    Disabled: {', '.join(disabled)}")

    # Test query type summary
    print("\n\nQuery Type Summaries:")
    print("-" * 50)

    for qt in [QueryType.CODE, QueryType.ROLEPLAY]:
        summary = adaptive.get_query_type_summary(qt)
        print(f"\n{qt.value.upper()}:")
        print(f"  Enabled: {', '.join(summary['enabled_sections'])}")
        print(f"  Disabled: {', '.join(summary['disabled_sections']) or 'None'}")
        print(f"  Total allocated: {summary['total_allocated']} tokens")

    # Test full adaptive context building
    print("\n\nFull Adaptive Context Build:")
    print("-" * 50)

    test_sections = {
        "system_prompt": "You are SAM, a confident and cocky AI assistant with a flirty personality.",
        "user_facts": "User name: David. Prefers Python. Works on AI projects. Lives in Australia.",
        "project_context": "SAM brain module - MLX-based cognitive engine with semantic memory.",
        "rag_results": """Python decorators are functions that modify other functions.
        Use @functools.wraps to preserve function metadata.
        Decorators can accept arguments using a wrapper function.
        Common use cases: logging, authentication, caching.""",
        "conversation_history": """User: Hey SAM, can you help with some Python?
SAM: Of course! Python's my jam. What do you need?
User: I'm trying to understand decorators better.
SAM: Ah, decorators - one of Python's coolest features. Let me break it down for you.""",
        "working_memory": "Current task: Explaining Python decorators. User expertise: Intermediate.",
        "personality": "SAM is cocky, confident, and flirtatious. Male personality. Loyal to David.",
    }

    # Test CODE query
    print("\nCODE Query: 'How do I create a caching decorator?'")
    context, meta = adaptive.build_adaptive_context(
        query="How do I create a caching decorator?",
        sections=test_sections,
        total_budget=2000
    )

    print(f"  Query type: {meta['query_type']}")
    print(f"  Total tokens: {meta['total_tokens']}")
    print(f"  Sections included: {len(meta['section_order'])}")
    print(f"  Section order: {' -> '.join([s['name'].split('_')[0] for s in meta['section_order']])}")

    # Test ROLEPLAY query
    print("\nROLEPLAY Query: '*leans against the bar* So, tell me about yourself'")
    context_rp, meta_rp = adaptive.build_adaptive_context(
        query="*leans against the bar* So, tell me about yourself",
        sections=test_sections,
        total_budget=2000
    )

    print(f"  Query type: {meta_rp['query_type']}")
    print(f"  Total tokens: {meta_rp['total_tokens']}")
    print(f"  Sections included: {len(meta_rp['section_order'])}")
    print(f"  Section order: {' -> '.join([s['name'].split('_')[0] for s in meta_rp['section_order']])}")

    # Test RECALL query
    print("\nRECALL Query: 'What's my name again?'")
    context_recall, meta_recall = adaptive.build_adaptive_context(
        query="What's my name again?",
        sections=test_sections,
        total_budget=2000
    )

    print(f"  Query type: {meta_recall['query_type']}")
    print(f"  Total tokens: {meta_recall['total_tokens']}")
    print(f"  Sections included: {len(meta_recall['section_order'])}")
    print(f"  Section order: {' -> '.join([s['name'].split('_')[0] for s in meta_recall['section_order']])}")

    # Test with limited available sections
    print("\n\nAdaptive with Limited Sections:")
    print("-" * 50)

    limited_sections = {
        "system_prompt": "You are SAM.",
        "conversation_history": "User: Hi\nSAM: Hey!",
        "query": "How are you?",
    }

    enabled = adaptive.get_adaptive_sections(
        "How are you?",
        available_sections=list(limited_sections.keys())
    )
    print(f"  Available: {list(limited_sections.keys())}")
    print(f"  Enabled for CHAT: {enabled}")

    allocations = adaptive.adapt_budget(
        QueryType.CHAT,
        2000,
        available_sections=list(limited_sections.keys())
    )
    print(f"  Allocations: {[(k, v) for k, v in allocations.items() if v > 0]}")

    # Show adaptation statistics
    print("\n\nAdaptation Statistics:")
    print("-" * 50)
    stats = adaptive.get_adaptation_stats()
    print(f"  Total adaptations: {stats['total_adaptations']}")
    print(f"  By query type: {stats.get('by_query_type', {})}")

    print("\n" + "=" * 60)
    print("Phase 2.3.5 Demo Complete")
    print("=" * 60)
