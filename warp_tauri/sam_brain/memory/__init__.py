#!/usr/bin/env python3
"""
SAM Memory Systems Package

Consolidates all memory-related modules:
- context_budget: Token allocation for RAG results
- conversation_memory: Persistent conversation history
- fact_memory: User and project facts with decay
- infinite_context: State management for long generation
- project_context: Project detection and context injection
- rag_feedback: RAG quality feedback loop
- semantic_memory: Vector embeddings for recall

Usage:
    from memory import SemanticMemory, get_memory
    from memory import ContextBudget, QueryType
    from memory import FactMemory, get_fact_db
    from memory import ConversationMemory
    from memory import InfiniteContext, Domain
    from memory import RAGFeedbackTracker, get_rag_feedback_tracker
    from memory import ProjectContext, get_current_project
"""

# Context Budget (token allocation)
from memory.context_budget import (
    SectionPriority,
    ContextSection,
    QueryType,
    SectionBudget,
    BudgetAllocation,
    ContextBudget,
    ContextBuilder,
)

# Conversation Memory
from memory.conversation_memory import (
    Message,
    Fact,
    UserPreference,
    ConversationMemory,
    init_database,
)

# Fact Memory
from memory.fact_memory import (
    FactCategory,
    FactSource,
    UserFact,
    FactMemory,
    get_fact_db,
    get_fact_db_path,
    get_fact_memory,
    build_user_context,
    build_context_with_project,
    get_user_context,
)

# Infinite Context
from memory.infinite_context import (
    Domain,
    MemoryTier,
    StateFragment,
    Chunk,
    GenerationPlan,
    InfiniteContext,
)

# Project Context
from memory.project_context import (
    ProjectDetector,
    ProjectContext,
    ProjectProfile,
    ProjectProfileLoader,
    ProjectWatcher,
    SessionState,
    ProjectSessionState,
    SessionRecall,
    get_current_project,
    get_profile_loader,
    get_project_watcher,
    get_session_state,
    get_project_context,
    SSOT_PROJECTS,
    DB_PATH,
)

# RAG Feedback
from memory.rag_feedback import (
    RAGFeedbackEntry,
    SourceQualityMetrics,
    RAGFeedbackTracker,
    get_rag_feedback_tracker,
    get_rag_feedback_db_path,
    record_rag_feedback,
    get_source_quality_scores,
    adjust_relevance_score,
)

# Semantic Memory
from memory.semantic_memory import (
    MemoryEntry,
    SemanticMemory,
    get_memory,
)

__all__ = [
    # Context Budget
    "SectionPriority",
    "ContextSection",
    "QueryType",
    "SectionBudget",
    "BudgetAllocation",
    "ContextBudget",
    "ContextBuilder",
    # Conversation Memory
    "Message",
    "Fact",
    "UserPreference",
    "ConversationMemory",
    "init_database",
    # Fact Memory
    "FactCategory",
    "FactSource",
    "UserFact",
    "FactMemory",
    "get_fact_db",
    "get_fact_db_path",
    "get_fact_memory",
    "build_user_context",
    "build_context_with_project",
    "get_user_context",
    # Infinite Context
    "Domain",
    "MemoryTier",
    "StateFragment",
    "Chunk",
    "GenerationPlan",
    "InfiniteContext",
    # Project Context
    "ProjectDetector",
    "ProjectContext",
    "ProjectProfile",
    "ProjectProfileLoader",
    "ProjectWatcher",
    "SessionState",
    "ProjectSessionState",
    "SessionRecall",
    "get_current_project",
    "get_profile_loader",
    "get_project_watcher",
    "get_session_state",
    "get_project_context",
    "SSOT_PROJECTS",
    "DB_PATH",
    # RAG Feedback
    "RAGFeedbackEntry",
    "SourceQualityMetrics",
    "RAGFeedbackTracker",
    "get_rag_feedback_tracker",
    "get_rag_feedback_db_path",
    "record_rag_feedback",
    "get_source_quality_scores",
    "adjust_relevance_score",
    # Semantic Memory
    "MemoryEntry",
    "SemanticMemory",
    "get_memory",
]
