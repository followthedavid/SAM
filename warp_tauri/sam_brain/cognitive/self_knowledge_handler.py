"""
Self-Knowledge Query Handler for SAM
Phase 1.3.10: Handles "What do you know about me?" queries

Detects queries asking about stored user knowledge and returns
formatted responses with all active facts organized by category.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Import fact memory
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.fact_memory import get_fact_memory, FactMemory, UserFact, FactCategory
    _fact_memory_available = True
except ImportError:
    _fact_memory_available = False
    FactMemory = None
    UserFact = None


# ============================================================================
# QUERY DETECTION PATTERNS
# ============================================================================

SELF_KNOWLEDGE_PATTERNS = [
    # Direct questions about knowledge
    re.compile(r"what do you (?:know|remember|recall) about me\??", re.IGNORECASE),
    re.compile(r"what have you (?:learned|discovered|figured out) about me\??", re.IGNORECASE),
    re.compile(r"what (?:do you|can you) remember about me\??", re.IGNORECASE),
    re.compile(r"what facts? (?:do you )?(?:know|have) about me\??", re.IGNORECASE),
    re.compile(r"what information (?:do you )?have (?:about|on) me\??", re.IGNORECASE),

    # Tell me variants
    re.compile(r"tell me what you (?:know|remember|learned) about me", re.IGNORECASE),
    re.compile(r"tell me (?:everything|all) you (?:know|remember) about me", re.IGNORECASE),

    # Show me variants
    re.compile(r"show (?:me )?(?:what you know|my facts?|my profile|my info)", re.IGNORECASE),
    re.compile(r"list (?:what you know|my facts?|everything)(?: about me)?", re.IGNORECASE),

    # My profile/memory
    re.compile(r"(?:what's|what is) (?:in )?my (?:profile|memory|file)\??", re.IGNORECASE),
    re.compile(r"show (?:me )?my (?:profile|memory|stored (?:info|data))", re.IGNORECASE),

    # Do you know anything
    re.compile(r"do you (?:know|remember) anything about me\??", re.IGNORECASE),
    re.compile(r"have you learned anything about me\??", re.IGNORECASE),
]


# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

@dataclass
class SelfKnowledgeResponse:
    """Response for self-knowledge queries"""
    is_self_knowledge_query: bool
    response: str
    facts_count: int
    categories_found: List[str]
    metadata: Dict[str, Any]


def detect_self_knowledge_query(text: str) -> bool:
    """
    Detect if the input is asking about SAM's knowledge of the user.

    Args:
        text: User input text

    Returns:
        True if this is a self-knowledge query
    """
    text = text.strip()

    for pattern in SELF_KNOWLEDGE_PATTERNS:
        if pattern.search(text):
            return True

    return False


def format_confidence_label(confidence: float) -> str:
    """Convert confidence value to human-readable label."""
    if confidence >= 0.9:
        return "very confident"
    elif confidence >= 0.7:
        return "confident"
    elif confidence >= 0.5:
        return "fairly sure"
    elif confidence >= 0.3:
        return "uncertain"
    else:
        return "vague memory"


def format_time_ago(iso_timestamp: Optional[str]) -> str:
    """Convert ISO timestamp to relative time string."""
    if not iso_timestamp:
        return "unknown"

    try:
        then = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        delta = now - then

        if delta.days == 0:
            if delta.seconds < 60:
                return "just now"
            elif delta.seconds < 3600:
                mins = delta.seconds // 60
                return f"{mins} minute{'s' if mins != 1 else ''} ago"
            else:
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
    except (ValueError, TypeError):
        return "unknown"


# Category display names and order
CATEGORY_DISPLAY = {
    "biographical": ("About You", 1),
    "preferences": ("Your Preferences", 2),
    "projects": ("Your Projects", 3),
    "skills": ("Your Skills", 4),
    "relationships": ("People & Relationships", 5),
    "system": ("How You Like Me to Respond", 6),
    "corrections": ("Things You've Corrected Me On", 7),
    "context": ("Current Context", 8),
}


def format_self_knowledge_response(
    user_id: str = "david",
    min_confidence: float = 0.3,
    include_timestamps: bool = True,
    include_confidence: bool = True,
    personality_intro: bool = True,
) -> SelfKnowledgeResponse:
    """
    Build a formatted response for self-knowledge queries.

    Args:
        user_id: User identifier
        min_confidence: Minimum confidence to include
        include_timestamps: Whether to show when facts were learned
        include_confidence: Whether to show confidence levels
        personality_intro: Whether to add SAM's personality to intro

    Returns:
        SelfKnowledgeResponse with formatted message
    """
    if not _fact_memory_available:
        return SelfKnowledgeResponse(
            is_self_knowledge_query=True,
            response="I don't have my fact memory system available right now. Check back later!",
            facts_count=0,
            categories_found=[],
            metadata={"error": "fact_memory_not_available"}
        )

    try:
        fact_memory = get_fact_memory()
    except Exception as e:
        return SelfKnowledgeResponse(
            is_self_knowledge_query=True,
            response=f"Having trouble accessing my memory banks: {e}",
            facts_count=0,
            categories_found=[],
            metadata={"error": str(e)}
        )

    # Get all active facts for the user
    facts = fact_memory.get_facts(
        user_id=user_id,
        min_confidence=min_confidence,
        limit=100,  # Get plenty of facts
        include_inactive=False
    )

    if not facts:
        intro = "Hmm, I don't seem to have learned anything about you yet. " if personality_intro else ""
        return SelfKnowledgeResponse(
            is_self_knowledge_query=True,
            response=f"{intro}Tell me about yourself and I'll remember!",
            facts_count=0,
            categories_found=[],
            metadata={"user_id": user_id}
        )

    # Group facts by category
    by_category: Dict[str, List[UserFact]] = {}
    for fact in facts:
        cat = fact.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(fact)

    # Sort categories by display order
    sorted_categories = sorted(
        by_category.keys(),
        key=lambda c: CATEGORY_DISPLAY.get(c, (c, 99))[1]
    )

    # Build response
    parts = []

    # Intro with personality
    if personality_intro:
        count = len(facts)
        cat_count = len(sorted_categories)
        intro = f"Alright, let me share what I've picked up about you. I've got {count} thing{'s' if count != 1 else ''} noted across {cat_count} categor{'ies' if cat_count != 1 else 'y'}:\n"
    else:
        intro = f"I have {len(facts)} facts stored about you:\n"

    parts.append(intro)

    # Build each category section
    for category in sorted_categories:
        cat_facts = by_category[category]
        display_name = CATEGORY_DISPLAY.get(category, (category.title(), 99))[0]

        parts.append(f"\n**{display_name}:**")

        # Sort facts within category by confidence (highest first)
        cat_facts.sort(key=lambda f: f.confidence, reverse=True)

        for fact in cat_facts:
            # Build fact line
            line_parts = [f"- {fact.fact}"]

            # Add confidence indicator
            if include_confidence:
                conf_label = format_confidence_label(fact.confidence)
                line_parts.append(f"({conf_label})")

            # Add time learned
            if include_timestamps and fact.first_seen:
                time_ago = format_time_ago(fact.first_seen)
                line_parts.append(f"[learned {time_ago}]")

            parts.append(" ".join(line_parts))

    # Closing with personality
    if personality_intro:
        parts.append("\n\nAnything I should add, update, or forget? Just let me know.")

    response_text = "\n".join(parts)

    return SelfKnowledgeResponse(
        is_self_knowledge_query=True,
        response=response_text,
        facts_count=len(facts),
        categories_found=sorted_categories,
        metadata={
            "user_id": user_id,
            "min_confidence": min_confidence,
            "facts_by_category": {cat: len(facts) for cat, facts in by_category.items()},
            "avg_confidence": sum(f.confidence for f in facts) / len(facts) if facts else 0,
        }
    )


def handle_self_knowledge_query(
    user_input: str,
    user_id: str = "david",
) -> Optional[SelfKnowledgeResponse]:
    """
    Main entry point for handling self-knowledge queries.

    Args:
        user_input: The user's message
        user_id: User identifier

    Returns:
        SelfKnowledgeResponse if this is a self-knowledge query, None otherwise
    """
    if not detect_self_knowledge_query(user_input):
        return None

    return format_self_knowledge_response(
        user_id=user_id,
        min_confidence=0.3,
        include_timestamps=True,
        include_confidence=True,
        personality_intro=True,
    )


# ============================================================================
# CLI / TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test self-knowledge handler")
    parser.add_argument("--user", "-u", default="david", help="User ID")
    parser.add_argument("--query", "-q", help="Test query detection")
    parser.add_argument("--show", "-s", action="store_true", help="Show knowledge for user")

    args = parser.parse_args()

    if args.query:
        is_query = detect_self_knowledge_query(args.query)
        print(f"Query: '{args.query}'")
        print(f"Is self-knowledge query: {is_query}")

        if is_query:
            response = handle_self_knowledge_query(args.query, args.user)
            print(f"\nResponse:\n{response.response}")

    elif args.show:
        response = format_self_knowledge_response(args.user)
        print(response.response)
        print(f"\n---")
        print(f"Facts: {response.facts_count}")
        print(f"Categories: {response.categories_found}")

    else:
        # Test pattern detection
        test_queries = [
            "What do you know about me?",
            "What have you learned about me?",
            "What do you remember about me?",
            "Tell me what you know about me",
            "Show me my profile",
            "What's in my memory?",
            "Do you know anything about me?",
            "List my facts",
            # Negatives
            "What's the weather like?",
            "Help me with Python",
            "What do you know about Python?",
        ]

        print("Testing self-knowledge query detection:\n")
        for query in test_queries:
            result = detect_self_knowledge_query(query)
            status = "YES" if result else "no"
            print(f"  [{status:3}] {query}")
