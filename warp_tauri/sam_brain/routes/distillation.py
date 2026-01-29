"""SAM API Distillation Routes - Review pending examples, approve/reject, batch operations."""

from datetime import datetime
from shared_state import get_distillation_db


def api_distillation_review_pending(limit: int = 10, domain: str = None) -> dict:
    """Get pending distillation examples for review."""
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        pending = db.get_pending_review(limit=limit, domain=domain)
        stats = db.get_review_stats()

        examples = []
        for item in pending:
            examples.append({
                "id": item['id'],
                "query": item['query'],
                "sam_attempt": item.get('sam_attempt'),
                "claude_response": item['claude_response'],
                "domain": item['domain'],
                "reasoning_type": item.get('reasoning_type'),
                "quality_score": item['quality_score'],
                "complexity": item.get('complexity'),
                "priority": item.get('priority', 5),
                "review_reason": item.get('review_reason'),
                "has_correction": bool(item.get('sam_attempt')),
            })

        return {
            "success": True,
            "examples": examples,
            "count": len(examples),
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_details(example_id: str) -> dict:
    """Get full details of a distillation example."""
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        details = db.get_example_details(example_id)
        if not details:
            return {"success": False, "error": f"Example not found: {example_id}"}

        return {
            "success": True,
            "example": details,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_action(
    example_id: str,
    action: str,
    notes: str = ""
) -> dict:
    """Approve or reject a distillation example."""
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        if action == "approve":
            success = db.approve_example(example_id, notes=notes)
            action_past = "approved"
        elif action == "reject":
            success = db.reject_example(example_id, reason=notes)
            action_past = "rejected"
        else:
            return {"success": False, "error": f"Invalid action: {action}. Use 'approve' or 'reject'"}

        if success:
            return {
                "success": True,
                "message": f"Example {example_id} {action_past}",
                "example_id": example_id,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": f"Failed to {action} example {example_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_batch(
    action: str,
    threshold: float
) -> dict:
    """Batch approve or reject examples based on quality threshold."""
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        if not 0.0 <= threshold <= 1.0:
            return {"success": False, "error": f"Threshold must be between 0.0 and 1.0, got {threshold}"}

        if action == "approve":
            result = db.batch_approve_above_threshold(threshold)
            return {
                "success": True,
                "action": "batch_approve",
                "threshold": threshold,
                "affected_count": result['approved_count'],
                "affected_ids": result['ids'],
                "timestamp": datetime.now().isoformat(),
            }
        elif action == "reject":
            result = db.batch_reject_below_threshold(threshold)
            return {
                "success": True,
                "action": "batch_reject",
                "threshold": threshold,
                "affected_count": result['rejected_count'],
                "affected_ids": result['ids'],
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": f"Invalid action: {action}. Use 'approve' or 'reject'"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_distillation_review_stats() -> dict:
    """Get distillation review queue statistics."""
    db = get_distillation_db()
    if not db:
        return {"success": False, "error": "Distillation DB not available"}

    try:
        stats = db.get_review_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/distillation/review": lambda params: api_distillation_review_pending(
        limit=int(params.get("limit", ["10"])[0]),
        domain=params.get("domain", [None])[0]
    ),
    "/api/distillation/review/stats": lambda params: api_distillation_review_stats(),
}

# Prefix-matched GET routes (for /api/distillation/review/<id>)
PREFIX_GET_ROUTES = {
    "/api/distillation/review/": lambda path, params: api_distillation_review_details(path.split("/")[-1]) if path.split("/")[-1] and path.split("/")[-1] not in ["review", "stats"] else {"success": False, "error": "Missing example ID"},
}

POST_ROUTES = {
    "/api/distillation/review": lambda data: api_distillation_review_action(
        example_id=data.get("example_id", ""),
        action=data.get("action", ""),
        notes=data.get("notes", "")
    ) if data.get("example_id") and data.get("action") else {"success": False, "error": "Missing example_id or action"},
    "/api/distillation/review/batch": lambda data: api_distillation_review_batch(
        action=data.get("action", ""),
        threshold=float(data.get("threshold", 0.0))
    ) if data.get("action") and data.get("threshold") is not None else {"success": False, "error": "Missing action or threshold"},
}
