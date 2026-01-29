"""SAM API Intelligence Routes - Self-awareness, suggestions, learning, feedback, scan, think, orchestrate."""

from datetime import datetime
from shared_state import (
    get_sam_intelligence, get_distillation_db, get_distillation_stats,
    get_compression_monitor, get_vision_stats_monitor,
)


def get_training_stats() -> dict:
    """Get comprehensive training statistics for /api/self endpoint."""
    try:
        from learn.model_deployment import get_deployer
        deployer = get_deployer()
        deployment_stats = deployer.get_deployment_stats()

        from learn.training_pipeline import TrainingPipeline
        pipeline = TrainingPipeline()
        pipeline_stats = pipeline.stats()

        last_run = None
        if pipeline.runs:
            run = pipeline.runs[-1]
            last_run = {
                "run_id": run.run_id,
                "start_time": run.start_time,
                "samples_count": run.samples_count,
                "status": run.status,
                "metrics": run.metrics,
            }

        training_data_stats = {
            "total_samples": pipeline_stats.get("total_samples", 0),
            "min_for_training": pipeline_stats.get("min_for_training", 100),
            "ready_to_train": pipeline_stats.get("ready_to_train", False),
        }

        distillation_db = get_distillation_db()
        distillation_contribution = 0
        if distillation_db:
            try:
                dist_stats = distillation_db.get_stats()
                distillation_contribution = dist_stats.get("approved_examples", 0)
            except:
                pass

        training_data_stats["distilled_samples"] = distillation_contribution

        return {
            "available": True,
            "model_version": deployment_stats.get("current_version"),
            "deployed_at": deployment_stats.get("current_deployed_at"),
            "last_training": last_run,
            "training_data": training_data_stats,
            "evaluation_metrics": last_run["metrics"] if last_run else {},
            "deployment": {
                "total_versions": deployment_stats.get("total_versions", 0),
                "rollback_available": deployment_stats.get("rollback_available", False),
                "canary_active": deployment_stats.get("canary_active", False),
                "canary_traffic_pct": deployment_stats.get("canary_traffic_pct", 0),
                "base_model": deployment_stats.get("base_model", "unknown"),
            },
            "mlx_available": pipeline_stats.get("mlx_available", False),
            "available_models": pipeline_stats.get("available_models", 0),
            "completed_runs": pipeline_stats.get("completed_runs", 0),
        }
    except ImportError as e:
        return {
            "available": False,
            "error": f"Training modules not available: {str(e)}"
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


def api_self() -> dict:
    """SAM explains itself - self-awareness endpoint."""
    sam_intel = get_sam_intelligence()
    if not sam_intel:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        explanation = sam_intel.explain_myself()
        status = sam_intel.get_self_status()

        distillation_stats = get_distillation_stats()

        context_stats = None
        try:
            monitor = get_compression_monitor()
            context_stats = monitor.get_summary_for_self()
        except Exception:
            context_stats = {
                "avg_compression": 1.0,
                "tokens_saved_today": 0,
                "section_usage": {}
            }

        vision_stats = None
        try:
            vision_monitor = get_vision_stats_monitor()
            vision_stats = vision_monitor.get_summary_for_self()
        except Exception:
            vision_stats = {
                "requests_today": 0,
                "avg_time_ms": 0,
                "tier_usage": {},
                "memory_peak_mb": 0.0
            }

        training_stats = get_training_stats()

        return {
            "success": True,
            "explanation": explanation,
            "status": status,
            "distillation": distillation_stats,
            "context_stats": context_stats,
            "vision_stats": vision_stats,
            "training_stats": training_stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_suggest(limit: int = 5) -> dict:
    """Get top improvement suggestions (cached for speed)."""
    sam_intel = get_sam_intelligence()
    if not sam_intel:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        suggestions = sam_intel.get_top_suggestions_fast(limit)
        return {
            "success": True,
            "count": len(suggestions),
            "suggestions": suggestions,
            "cached": True,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_proactive() -> dict:
    """Get proactive suggestions - what SAM noticed on its own."""
    sam_intel = get_sam_intelligence()
    if not sam_intel:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        proactive = sam_intel.get_proactive_suggestions()
        return {
            "success": True,
            "count": len(proactive),
            "suggestions": proactive,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_learning() -> dict:
    """Get what SAM has learned from past improvements."""
    sam_intel = get_sam_intelligence()
    if not sam_intel:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        raw_patterns = getattr(sam_intel, 'learning', {})
        insights = sam_intel.get_learned_insights()

        learning_summary = []
        for key, pattern in raw_patterns.items():
            total = pattern.success_count + pattern.failure_count
            learning_summary.append({
                "category": key,
                "pattern_type": pattern.pattern_type,
                "pattern_value": pattern.pattern_value,
                "total_samples": total,
                "successes": pattern.success_count,
                "failures": pattern.failure_count,
                "success_rate": f"{pattern.success_rate:.0%}",
                "avg_impact": f"{pattern.avg_impact:.2f}",
                "confidence": f"{pattern.confidence:.0%}",
            })

        learning_summary.sort(key=lambda x: -x["total_samples"])

        return {
            "success": True,
            "patterns": learning_summary,
            "insights": insights,
            "total_learned": sum(p["total_samples"] for p in learning_summary),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_feedback(improvement_id: str, success: bool, impact: float = 0.5, lessons: str = "") -> dict:
    """Record feedback for an improvement."""
    sam_intel = get_sam_intelligence()
    if not sam_intel:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        sam_intel.learn_from_feedback(improvement_id, success, impact, lessons)
        return {
            "success": True,
            "improvement_id": improvement_id,
            "recorded": True,
            "message": f"Learned from {'successful' if success else 'failed'} improvement",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_scan() -> dict:
    """Trigger an improvement scan."""
    try:
        from learn.improvement_detector import ImprovementDetector
        detector = ImprovementDetector()

        improvements = detector.detect_all(quick=True)

        return {
            "success": True,
            "count": len(improvements),
            "improvements": [
                {
                    "id": imp.get("id", ""),
                    "type": imp.get("type", ""),
                    "project": imp.get("project_id", ""),
                    "priority": imp.get("priority", 3),
                    "description": imp.get("description", "")[:200],
                }
                for imp in improvements[:20]
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_think(query: str) -> dict:
    """Have SAM think about a query using its intelligence."""
    sam_intel = get_sam_intelligence()
    if not sam_intel:
        return {"success": False, "error": "SAM Intelligence not available"}

    try:
        start = datetime.now()
        response = sam_intel.think(query)
        duration = (datetime.now() - start).total_seconds() * 1000

        return {
            "success": True,
            "query": query,
            "response": response,
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_think_stream(query: str, mode: str = "structured"):
    """
    Stream of Consciousness - Real-time thinking display.

    Yields SSE formatted events showing SAM's thought process.
    """
    import json as json_module

    try:
        from serve.live_thinking import (
            stream_thinking, stream_structured_thinking, stream_coding_thinking,
            thinking_to_sse, ThinkingSession
        )

        if mode == "coding":
            generator = stream_coding_thinking(query, show_live=False)
        elif mode == "structured":
            generator = stream_structured_thinking(query, show_live=False)
        else:
            generator = stream_thinking(query, show_live=False)

        for chunk in generator:
            yield thinking_to_sse(chunk)

        yield f'data: {json_module.dumps({"done": True})}\n\n'

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_think_colors() -> dict:
    """Get color scheme for frontend thought display."""
    try:
        from serve.live_thinking import get_thinking_colors
        return {
            "success": True,
            "colors": get_thinking_colors(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_orchestrate(message: str, auto_escalate: bool = True) -> dict:
    """Process message through SAM with escalation handling."""
    try:
        start = datetime.now()

        try:
            from execution.escalation_handler import process_request, EscalationReason
            result = process_request(message, auto_escalate=auto_escalate)

            duration = (datetime.now() - start).total_seconds() * 1000

            return {
                "success": True,
                "message": message,
                "response": result.content,
                "confidence": result.confidence,
                "provider": result.provider,
                "escalated": result.provider == "claude",
                "escalation_reason": result.escalation_reason.value if result.escalation_reason != EscalationReason.NONE else None,
                "route": "escalation_handler",
                "model": "mlx-cognitive" if result.provider == "sam" else "claude-browser",
                "duration_ms": duration,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            from orchestrator import orchestrate
            result = orchestrate(message)
            duration = (datetime.now() - start).total_seconds() * 1000

            return {
                "success": True,
                "message": message,
                **result,
                "duration_ms": duration,
                "timestamp": datetime.now().isoformat(),
            }
    except ImportError as e:
        return {"success": False, "error": f"Orchestrator not available: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/self": lambda params: api_self(),
    "/api/suggest": lambda params: api_suggest(int(params.get("limit", ["5"])[0])),
    "/api/proactive": lambda params: api_proactive(),
    "/api/learning": lambda params: api_learning(),
    "/api/scan": lambda params: api_scan(),
    "/api/think": lambda params: api_think(params.get("q", [""])[0]) if params.get("q", [""])[0] else {"success": False, "error": "Missing query parameter 'q'"},
    "/api/think/colors": lambda params: api_think_colors(),
}

POST_ROUTES = {
    "/api/feedback": lambda data: api_feedback(data.get("improvement_id", ""), data.get("success", True), data.get("impact", 0.5), data.get("lessons", "")) if data.get("improvement_id") else {"success": False, "error": "Missing improvement_id"},
    "/api/think": lambda data: api_think(data.get("query", "")) if data.get("query") else {"success": False, "error": "Missing query"},
    "/api/orchestrate": lambda data: api_orchestrate(data.get("message", "")) if data.get("message") else {"success": False, "error": "Missing message"},
}

STREAM_POST_ROUTES = {
    "/api/think/stream": lambda data: api_think_stream(data.get("query", ""), data.get("mode", "structured")) if data.get("query") else None,
}
