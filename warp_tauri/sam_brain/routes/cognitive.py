"""SAM API Cognitive Routes - Cognitive processing, state, mood, resources, feedback, notifications."""

import sys
from datetime import datetime
from shared_state import (
    get_cognitive_orchestrator, get_compression_monitor, get_feedback_db,
    _update_activity, _get_idle_seconds,
)


def api_cognitive_process(query: str, user_id: str = "default") -> dict:
    """Process query through cognitive system with MLX inference."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        _update_activity()
        start = datetime.now()
        result = orchestrator.process(query, user_id=user_id)
        duration = (datetime.now() - start).total_seconds() * 1000
        _update_activity()

        return {
            "success": True,
            "query": query,
            "response": result.response,
            "confidence": result.confidence,
            "mood": result.mood,
            "model_used": result.metadata.get("model_used", "unknown"),
            "escalated": result.metadata.get("escalated", False),
            "escalation_recommended": result.metadata.get("escalation_recommended", False),
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_state() -> dict:
    """Get cognitive system state."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        state = orchestrator.get_state()
        return {
            "success": True,
            "state": state,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_mood() -> dict:
    """Get current emotional state."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        emotional_state = orchestrator.emotional.get_state()
        return {
            "success": True,
            "mood": emotional_state,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_resources() -> dict:
    """Get current system resource state."""
    try:
        from cognitive.resource_manager import ResourceManager
        manager = ResourceManager()
        snapshot = manager.get_snapshot()
        stats = manager.get_stats()

        model_memory_mb = 0.0
        model_loaded = None
        orchestrator = get_cognitive_orchestrator()
        if orchestrator and hasattr(orchestrator, 'mlx_engine'):
            model_memory_mb = orchestrator.mlx_engine.get_memory_usage_mb()
            model_loaded = orchestrator.mlx_engine._current_model_key

        return {
            "success": True,
            "resources": snapshot.to_dict(),
            "model": {
                "loaded": model_loaded,
                "memory_mb": model_memory_mb,
                "idle_seconds": _get_idle_seconds(),
            },
            "stats": {
                "total_requests": stats.get('total_requests', 0),
                "rejected_requests": stats.get('rejected_requests', 0),
                "completed_requests": stats.get('completed_requests', 0),
                "timeouts": stats.get('timeouts', 0),
            },
            "limits": {
                "max_tokens": manager.get_max_tokens_for_level(),
                "can_perform_heavy_op": manager.can_perform_heavy_operation()[0],
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_context_stats() -> dict:
    """Get compression statistics for context management."""
    try:
        monitor = get_compression_monitor()
        stats = monitor.get_stats()

        try:
            from memory.context_budget import ContextBudget
            budget = ContextBudget()
            allocation_stats = budget.get_allocation_stats()
            stats["budget_allocations"] = allocation_stats
        except Exception:
            stats["budget_allocations"] = None

        try:
            from cognitive.compression import ContextualCompressor
            compressor = ContextualCompressor()
            last_stats = compressor.get_last_stats()
            if last_stats:
                stats["last_compression"] = {
                    "original_tokens": last_stats.original_tokens,
                    "compressed_tokens": last_stats.compressed_tokens,
                    "ratio": round(last_stats.ratio, 3),
                    "query_type": last_stats.query_type,
                    "importance_threshold": round(last_stats.importance_threshold, 3)
                }
        except Exception:
            stats["last_compression"] = None

        return {
            "success": True,
            **stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_unload_model() -> dict:
    """Unload the MLX model to free memory."""
    try:
        orchestrator = get_cognitive_orchestrator()
        if not orchestrator:
            return {"success": False, "error": "Cognitive system not available"}

        if not hasattr(orchestrator, 'mlx_engine'):
            return {"success": False, "error": "MLX engine not available"}

        engine = orchestrator.mlx_engine
        was_loaded = engine._current_model_key

        if was_loaded is None:
            return {
                "success": True,
                "message": "No model was loaded",
                "freed_mb": 0,
                "timestamp": datetime.now().isoformat(),
            }

        memory_before = engine.get_memory_usage_mb()
        engine.unload_model()

        return {
            "success": True,
            "message": f"Unloaded model {was_loaded}",
            "freed_mb": memory_before,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_feedback(
    response_id: str,
    helpful: bool = True,
    comment: str = "",
    query: str = "",
    response: str = "",
    user_id: str = "default",
    session_id: str = "default",
    feedback_type: str = "rating",
    rating: int = None,
    correction: str = None,
    correction_type: str = None,
    what_was_wrong: str = None,
    preferred_response: str = None,
    comparison_basis: str = None,
    flag_type: str = None,
    flag_details: str = None,
    domain: str = "general",
    response_confidence: float = None,
    escalated_to_claude: bool = False,
    response_timestamp: float = None,
    conversation_context: str = None,
) -> dict:
    """Record user feedback on a response for learning."""
    try:
        feedback_id = None

        if rating is None:
            rating = 1 if helpful else -1

        if correction is None and comment:
            correction = comment
            if feedback_type == "rating" and correction:
                feedback_type = "correction"

        fb_db = get_feedback_db()
        if fb_db:
            try:
                feedback_id = fb_db.save_feedback(
                    response_id=response_id,
                    session_id=session_id,
                    original_query=query,
                    original_response=response,
                    feedback_type=feedback_type,
                    rating=rating,
                    correction=correction,
                    correction_type=correction_type,
                    what_was_wrong=what_was_wrong,
                    preferred_response=preferred_response,
                    comparison_basis=comparison_basis,
                    flag_type=flag_type,
                    flag_details=flag_details,
                    domain=domain,
                    response_confidence=response_confidence,
                    escalated_to_claude=escalated_to_claude,
                    user_id=user_id,
                    response_timestamp=response_timestamp,
                    conversation_context=conversation_context,
                )
            except Exception as e:
                print(f"Warning: FeedbackDB save failed: {e}", file=sys.stderr)

        try:
            from learn.intelligence_core import get_intelligence_core
            core = get_intelligence_core()

            legacy_rating = "helpful" if rating == 1 else ("corrected" if correction else "not_helpful")
            core.record_feedback(
                response_id=response_id,
                query=query,
                response=response,
                rating=legacy_rating,
                correction=correction if correction else None,
                user_id=user_id
            )
        except ImportError:
            pass

        try:
            from execution.escalation_learner import EscalationLearner
            learner = EscalationLearner()
            learner.record_local_attempt(
                query=response_id,
                task_type="feedback",
                confidence=1.0 if rating == 1 else 0.0,
                success=rating == 1
            )
        except:
            pass

        return {
            "success": True,
            "feedback_id": feedback_id,
            "response_id": response_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "helpful": rating == 1,
            "correction_recorded": bool(correction),
            "recorded": True,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_feedback_stats() -> dict:
    """Get feedback statistics."""
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        stats = fb_db.get_feedback_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_feedback_recent(
    limit: int = 20,
    domain: str = None,
    feedback_type: str = None,
    session_id: str = None
) -> dict:
    """Get recent feedback entries for dashboard."""
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        recent = fb_db.get_recent_feedback(
            limit=limit,
            domain=domain,
            feedback_type=feedback_type,
            session_id=session_id
        )

        return {
            "success": True,
            "count": len(recent),
            "feedback": recent,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_notifications() -> dict:
    """Get proactive feedback notifications for the UI."""
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        data = fb_db.get_feedback_notifications_data()

        return {
            "success": True,
            "daily_corrections": data.get("daily_corrections", 0),
            "daily_negative": data.get("daily_negative", 0),
            "unprocessed_count": data.get("unprocessed_count", 0),
            "declining_domains": data.get("declining_domains", []),
            "alerts": data.get("threshold_alerts", []),
            "alert_count": len(data.get("threshold_alerts", [])),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_feedback_dashboard() -> dict:
    """Get comprehensive feedback dashboard data for review UI."""
    try:
        fb_db = get_feedback_db()
        if not fb_db:
            return {"success": False, "error": "FeedbackDB not available"}

        data = fb_db.get_dashboard_data()

        return {
            "success": True,
            "summary": data.get("summary", {}),
            "domain_breakdown": data.get("domain_breakdown", {}),
            "recent_corrections": data.get("recent_corrections", []),
            "training_status": data.get("training_status", {}),
            "trends": data.get("trends", {}),
            "generated_at": data.get("generated_at"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_escalate(query: str) -> dict:
    """Force escalation to Claude via browser bridge."""
    try:
        from execution.escalation_handler import escalate_to_claude
        response = escalate_to_claude(query)
        return {
            "success": True,
            "query": query,
            "response": response,
            "provider": "claude",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_cognitive_stream(query: str, user_id: str = "default"):
    """Stream cognitive response via Server-Sent Events."""
    import json as json_module

    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        yield f'data: {json_module.dumps({"error": "Cognitive system not available"})}\n\n'
        return

    try:
        engine = orchestrator.mlx_engine

        cognitive_state = {
            "confidence": 0.5,
            "emotional_valence": 0.0
        }

        working_context = orchestrator.memory.get_context(max_tokens=100)

        full_response = []
        for token in engine.generate_streaming(
            prompt=query,
            context=working_context,
            cognitive_state=cognitive_state
        ):
            if isinstance(token, str):
                full_response.append(token)
                yield f'data: {json_module.dumps({"token": token})}\n\n'

        final_text = "".join(full_response)
        yield f'data: {json_module.dumps({"done": True, "response": final_text, "confidence": 0.75})}\n\n'

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


# Route tables
GET_ROUTES = {
    "/api/cognitive/state": lambda params: api_cognitive_state(),
    "/api/cognitive/mood": lambda params: api_cognitive_mood(),
    "/api/resources": lambda params: api_resources(),
    "/api/context/stats": lambda params: api_context_stats(),
    "/api/unload": lambda params: api_unload_model(),
    "/api/cognitive/process": lambda params: api_cognitive_process(params.get("q", [""])[0]) if params.get("q", [""])[0] else {"success": False, "error": "Missing query parameter 'q'"},
    "/api/cognitive/feedback": lambda params: api_cognitive_feedback_stats(),
    "/api/cognitive/feedback/recent": lambda params: api_cognitive_feedback_recent(
        limit=int(params.get("limit", ["20"])[0]),
        domain=params.get("domain", [None])[0],
        feedback_type=params.get("type", [None])[0],
        session_id=params.get("session", [None])[0]
    ),
    "/api/notifications": lambda params: api_notifications(),
    "/api/feedback/dashboard": lambda params: api_feedback_dashboard(),
}

POST_ROUTES = {
    "/api/cognitive/process": lambda data: api_cognitive_process(data.get("query", ""), data.get("user_id", "default")) if data.get("query") else {"success": False, "error": "Missing query"},
    "/api/cognitive/feedback": lambda data: api_cognitive_feedback(
        response_id=data.get("response_id", ""),
        helpful=data.get("helpful", True),
        comment=data.get("comment", ""),
        query=data.get("query", data.get("original_query", "")),
        response=data.get("response", data.get("original_response", "")),
        user_id=data.get("user_id", "default"),
        session_id=data.get("session_id", "default"),
        feedback_type=data.get("feedback_type", "rating"),
        rating=data.get("rating"),
        correction=data.get("correction"),
        correction_type=data.get("correction_type"),
        what_was_wrong=data.get("what_was_wrong"),
        preferred_response=data.get("preferred_response"),
        comparison_basis=data.get("comparison_basis"),
        flag_type=data.get("flag_type"),
        flag_details=data.get("flag_details"),
        domain=data.get("domain", "general"),
        response_confidence=data.get("response_confidence"),
        escalated_to_claude=data.get("escalated_to_claude", False),
        response_timestamp=data.get("response_timestamp"),
        conversation_context=data.get("conversation_context"),
    ) if data.get("response_id") else {"success": False, "error": "Missing response_id"},
    "/api/cognitive/escalate": lambda data: api_cognitive_escalate(data.get("query", "")) if data.get("query") else {"success": False, "error": "Missing query"},
}

STREAM_POST_ROUTES = {
    "/api/cognitive/stream": lambda data: api_cognitive_stream(data.get("query", ""), data.get("user_id", "default")) if data.get("query") else None,
}
