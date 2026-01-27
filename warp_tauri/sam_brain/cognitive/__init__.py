"""
SAM Cognitive System v1.13.0

A complete cognitive architecture for maximizing context utilization
on constrained hardware (8GB M2 Mac Mini).

Modules:
- enhanced_memory: Working memory limits, decay, procedural memory
- enhanced_retrieval: HyDE, multi-hop, reranking
- compression: LLMLingua-style prompt compression
- cognitive_control: Meta-cognition, goals, reasoning
- enhanced_learning: Active learning, predictive caching
- emotional_model: Mood state machine, relationships
- mlx_cognitive: MLX inference with dynamic model selection
- model_selector: Dynamic model selection (1.5B vs 3B)
- token_budget: Token budget management
- quality_validator: Response quality validation
- vision_engine: Multi-modal vision support (SmolVLM, Moondream)
- vision_selector: Resource-aware vision tier selection (Phase 3.2.4)
- image_preprocessor: Memory-efficient image preprocessing (Phase 3.2.5)
- unified_orchestrator: Integrates all systems, RAG stats (Phase 2.2.8)
    - ImageContext: Track shared images for follow-up questions (Phase 3.1.5)
    - detect_image_followup: Detect if query is about previous image
- code_indexer: Code entity indexing (functions, classes, modules)
- doc_indexer: Documentation indexing (markdown, comments, docstrings)
- relevance_scorer: Multi-factor result reranking (Phase 2.2.5)

Phase 3.2.5 Features:
- Image preprocessing before vision analysis
- Automatic resize of large images (>2048px) to save memory
- Format conversion for optimal model input
- Memory estimation for image processing
- Caching of processed images
- Methods: preprocess_image(), get_image_info(), estimate_memory_needed()

Phase 3.2.3 Features (Vision Resource Tracking):
- Vision model state tracking: is_loaded, memory_used, last_used, tier
- get_vision_status() - Full vision model status including availability
- can_load_vision_model(tier) - Check if enough RAM for a tier
- request_vision_resources(tier) - Reserve resources for vision model
- Auto-unload after configurable inactivity period (default 5 min)
- Integration hooks: notify_vision_loaded/used/unloaded
- Convenience functions: get_vision_status(), can_load_vision(), force_unload_vision()

Phase 3.2.4 Features:
- Vision tier selection based on available RAM
- Task complexity analysis for tier routing
- Success rate tracking for selection optimization
- Fallback chains when primary tier fails
- Methods: select_tier(), get_recommended_tier()

Phase 3.1.5 Features:
- Image context tracking for follow-up questions
- Automatic detection of image-related queries
- API endpoints: /api/image/chat, /api/image/context, /api/image/followup/check
- Examples: "What color is the car?" after sharing a car image
"""

from .enhanced_memory import (
    WorkingMemory,
    ProceduralMemory,
    EnhancedMemoryManager
)

from .enhanced_retrieval import (
    HyDERetriever,
    MultiHopRetriever,
    CrossEncoderReranker,
    EnhancedRetrievalSystem
)

from .compression import (
    TokenImportanceScorer,
    PromptCompressor,
    ContextualCompressor
)

from .cognitive_control import (
    MetaCognition,
    GoalManager,
    ReasoningEngine,
    AttentionController,
    CognitiveControl
)

from .enhanced_learning import (
    ActiveLearner,
    PredictiveCache,
    SleepConsolidator,
    EnhancedLearningSystem
)

from .emotional_model import (
    EmotionalState,
    RelationshipTracker,
    EmotionalModel,
    MoodState
)

from .mlx_cognitive import (
    MLXCognitiveEngine,
    GenerationConfig,
    GenerationResult,
    MODEL_CONFIGS,
    create_mlx_engine
)

from .mlx_optimized import (
    OptimizedMLXEngine,
    OptimizationConfig,
    create_optimized_engine
)

from .model_selector import (
    DynamicModelSelector,
    SelectionResult,
    TaskType,
    select_model
)

from .token_budget import (
    TokenBudget,
    TokenBudgetManager,
    PRESET_BUDGETS,
    get_preset_budget
)

from .quality_validator import (
    QualityValidator,
    QualityAssessment,
    QualityIssue,
    EscalationReason,
    validate_response,
    clean_response
)

from .unified_orchestrator import (
    CognitiveOrchestrator,
    CognitiveResponse,
    RAGStats,
    ImageContext,
    detect_image_followup,
    IMAGE_REFERENCE_PATTERNS,
    create_cognitive_orchestrator
)

# Vision Engine (multi-modal support)
from .vision_engine import (
    VisionEngine,
    VisionConfig,
    VisionResult,
    VisionTaskType,
    VisionModelSelector,
    VisionQualityValidator,
    VISION_MODELS,
    create_vision_engine,
    describe_image,
    detect_objects,
    answer_about_image,
)

# Vision Client (easy integration - Phase 3.1.3)
from .vision_client import (
    VisionClient,
    DirectVisionClient,
    VisionResponse,
    VisionTier,
    process_image,
    extract_text,
    smart_analyze,
)

# Image Preprocessor (Phase 3.2.5) - memory-efficient image handling
from .image_preprocessor import (
    ImagePreprocessor,
    ImageInfo,
    ImageFormat,
    PreprocessResult,
    preprocess_image,
    get_image_info,
    estimate_memory_needed,
    get_preprocessor,
)

# Resource Management (prevents freezes on 8GB systems)
# Phase 3.2.3: Added vision model tracking
from .resource_manager import (
    ResourceManager,
    ResourceConfig,
    ResourceLevel,
    ResourceSnapshot,
    VisionTier as ResourceVisionTier,  # Avoid conflict with vision_client.VisionTier
    VisionModelState,
    VISION_TIER_MEMORY_MB,
    check_resources,
    get_safe_max_tokens,
    get_vision_status,
    can_load_vision,
    force_unload_vision,
)

# Vision Selector (Phase 3.2.4 - Resource-aware tier selection)
from .vision_selector import (
    VisionSelector,
    TierSelection,
    TierCapabilities,
    TierSuccessTracker,
    SelectionContext,
    VisionTier as SelectorVisionTier,  # Avoid conflict with vision_client.VisionTier
    MEMORY_THRESHOLDS,
    TIER_CAPABILITIES,
    TASK_MINIMUM_TIERS,
    get_selector,
    select_tier,
    get_recommended_tier,
)

# Self-Knowledge Handler (Phase 1.3.10)
from .self_knowledge_handler import (
    handle_self_knowledge_query,
    detect_self_knowledge_query,
    format_self_knowledge_response,
    SelfKnowledgeResponse,
)

# Code Indexer (Phase 2.2)
from .code_indexer import (
    CodeIndexer,
    CodeEntity,
    PythonParser,
    JavaScriptParser,
    RustParser,
    get_code_indexer,
)

# Documentation Indexer (Phase 2.2.3)
from .doc_indexer import (
    DocIndexer,
    DocEntity,
    MarkdownParser,
    CommentParser,
    get_doc_indexer,
)

# Relevance Scorer (Phase 2.2.5) - from parent sam_brain directory
try:
    import sys
    import os
    # Add parent directory to path if not already there
    _parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)

    from relevance_scorer import (
        RelevanceScorer,
        ScoredResult,
        ScoringWeights,
        CodeRelevanceScorer,
        DocRelevanceScorer,
        KeywordMatcher,
        MLXCrossEncoder,
        get_relevance_scorer,
        get_code_scorer,
        get_doc_scorer,
        rerank_code_results,
        rerank_doc_results,
        rerank_mixed_results,
    )
    RELEVANCE_SCORER_AVAILABLE = True
except ImportError as e:
    # Fallback if import fails
    RELEVANCE_SCORER_AVAILABLE = False
    # Define placeholder types so imports don't fail
    RelevanceScorer = None
    ScoredResult = None
    ScoringWeights = None
    CodeRelevanceScorer = None
    DocRelevanceScorer = None
    KeywordMatcher = None
    MLXCrossEncoder = None
    get_relevance_scorer = None
    get_code_scorer = None
    get_doc_scorer = None
    rerank_code_results = None
    rerank_doc_results = None
    rerank_mixed_results = None

__version__ = "1.13.0"  # Bumped for Vision Resource Tracking (Phase 3.2.3)
__all__ = [
    # Memory
    "WorkingMemory",
    "ProceduralMemory",
    "EnhancedMemoryManager",
    # Retrieval
    "HyDERetriever",
    "MultiHopRetriever",
    "CrossEncoderReranker",
    "EnhancedRetrievalSystem",
    # Compression
    "TokenImportanceScorer",
    "PromptCompressor",
    "ContextualCompressor",
    # Cognitive Control
    "MetaCognition",
    "GoalManager",
    "ReasoningEngine",
    "AttentionController",
    "CognitiveControl",
    # Learning
    "ActiveLearner",
    "PredictiveCache",
    "SleepConsolidator",
    "EnhancedLearningSystem",
    # Emotional
    "EmotionalState",
    "RelationshipTracker",
    "EmotionalModel",
    "MoodState",
    # MLX Cognitive
    "MLXCognitiveEngine",
    "GenerationConfig",
    "GenerationResult",
    "MODEL_CONFIGS",
    "create_mlx_engine",
    # MLX Optimized
    "OptimizedMLXEngine",
    "OptimizationConfig",
    "create_optimized_engine",
    # Model Selector
    "DynamicModelSelector",
    "SelectionResult",
    "TaskType",
    "select_model",
    # Token Budget
    "TokenBudget",
    "TokenBudgetManager",
    "PRESET_BUDGETS",
    "get_preset_budget",
    # Quality Validator
    "QualityValidator",
    "QualityAssessment",
    "QualityIssue",
    "EscalationReason",
    "validate_response",
    "clean_response",
    # Orchestrator
    "CognitiveOrchestrator",
    "CognitiveResponse",
    "RAGStats",
    "ImageContext",
    "detect_image_followup",
    "IMAGE_REFERENCE_PATTERNS",
    "create_cognitive_orchestrator",
    # Vision Engine
    "VisionEngine",
    "VisionConfig",
    "VisionResult",
    "VisionTaskType",
    "VisionModelSelector",
    "VisionQualityValidator",
    "VISION_MODELS",
    "create_vision_engine",
    "describe_image",
    "detect_objects",
    "answer_about_image",
    # Vision Client (Phase 3.1.3)
    "VisionClient",
    "DirectVisionClient",
    "VisionResponse",
    "VisionTier",
    "process_image",
    "extract_text",
    "smart_analyze",
    # Resource Management (Phase 3.2.3 - added vision tracking)
    "ResourceManager",
    "ResourceConfig",
    "ResourceLevel",
    "ResourceSnapshot",
    "ResourceVisionTier",
    "VisionModelState",
    "VISION_TIER_MEMORY_MB",
    "check_resources",
    "get_safe_max_tokens",
    "get_vision_status",
    "can_load_vision",
    "force_unload_vision",
    # Self-Knowledge Handler (Phase 1.3.10)
    "handle_self_knowledge_query",
    "detect_self_knowledge_query",
    "format_self_knowledge_response",
    "SelfKnowledgeResponse",
    # Code Indexer (Phase 2.2)
    "CodeIndexer",
    "CodeEntity",
    "PythonParser",
    "JavaScriptParser",
    "RustParser",
    "get_code_indexer",
    # Documentation Indexer (Phase 2.2.3)
    "DocIndexer",
    "DocEntity",
    "MarkdownParser",
    "CommentParser",
    "get_doc_indexer",
    # Relevance Scorer (Phase 2.2.5)
    "RelevanceScorer",
    "ScoredResult",
    "ScoringWeights",
    "CodeRelevanceScorer",
    "DocRelevanceScorer",
    "KeywordMatcher",
    "MLXCrossEncoder",
    "get_relevance_scorer",
    "get_code_scorer",
    "get_doc_scorer",
    "rerank_code_results",
    "rerank_doc_results",
    "rerank_mixed_results",
    "RELEVANCE_SCORER_AVAILABLE",
    # Vision Selector (Phase 3.2.4)
    "VisionSelector",
    "TierSelection",
    "TierCapabilities",
    "TierSuccessTracker",
    "SelectionContext",
    "SelectorVisionTier",
    "MEMORY_THRESHOLDS",
    "TIER_CAPABILITIES",
    "TASK_MINIMUM_TIERS",
    "get_selector",
    "select_tier",
    "get_recommended_tier",
    # Image Preprocessor (Phase 3.2.5)
    "ImagePreprocessor",
    "ImageInfo",
    "ImageFormat",
    "PreprocessResult",
    "preprocess_image",
    "get_image_info",
    "estimate_memory_needed",
    "get_preprocessor",
]
