"""SAM API Image Context Routes - Image follow-up questions, image chat."""

from datetime import datetime
from shared_state import get_cognitive_orchestrator, _update_activity


def api_image_context_get() -> dict:
    """Phase 3.1.5: Get the current image context for follow-up questions."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        context = orchestrator.get_image_context()
        if context:
            return {
                "success": True,
                "has_context": True,
                "image_path": context.image_path,
                "image_hash": context.image_hash,
                "description": context.description,
                "task_type": context.task_type,
                "timestamp": context.timestamp.isoformat(),
                "age_seconds": (datetime.now() - context.timestamp).total_seconds(),
                "metadata": context.metadata,
            }
        else:
            return {
                "success": True,
                "has_context": False,
                "message": "No image context available. Share an image first.",
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_image_context_clear() -> dict:
    """Phase 3.1.5: Clear the current image context."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        orchestrator.clear_image_context()
        return {
            "success": True,
            "message": "Image context cleared",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_image_chat(
    query: str,
    image_path: str = None,
    image_base64: str = None,
    user_id: str = "default"
) -> dict:
    """Phase 3.1.5: Unified endpoint for image-aware chat."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        import tempfile
        import base64 as b64

        _update_activity()

        temp_path = None
        actual_image_path = image_path

        if image_base64:
            image_data = b64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            actual_image_path = temp_path

        start = datetime.now()
        result = orchestrator.process_with_image(
            user_input=query,
            image_path=actual_image_path,
            user_id=user_id
        )
        duration = (datetime.now() - start).total_seconds() * 1000

        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        _update_activity()

        response_data = {
            "success": True,
            "query": query,
            "response": result.response,
            "confidence": result.confidence,
            "mood": result.mood,
            "query_type": result.metadata.get("query_type", "text"),
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat(),
        }

        if result.metadata.get("image_path"):
            response_data["image_path"] = result.metadata["image_path"]
        if result.metadata.get("model_used"):
            response_data["model_used"] = result.metadata["model_used"]
        if result.metadata.get("escalated"):
            response_data["escalated"] = result.metadata["escalated"]
        if result.metadata.get("followup_confidence"):
            response_data["followup_confidence"] = result.metadata["followup_confidence"]
        if result.metadata.get("image_context"):
            response_data["image_context"] = result.metadata["image_context"]

        return response_data

    except Exception as e:
        return {"success": False, "error": str(e)}


def api_image_followup_check(query: str) -> dict:
    """Phase 3.1.5: Check if a query is a follow-up about a previous image."""
    orchestrator = get_cognitive_orchestrator()
    if not orchestrator:
        return {"success": False, "error": "Cognitive system not available"}

    try:
        is_followup, confidence = orchestrator.is_image_followup(query)
        has_context = orchestrator.has_image_context()

        return {
            "success": True,
            "query": query,
            "is_followup": is_followup,
            "confidence": confidence,
            "has_image_context": has_context,
            "will_use_image": is_followup and has_context and confidence >= 0.7,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/image/context": lambda params: api_image_context_get(),
    "/api/image/context/clear": lambda params: api_image_context_clear(),
    "/api/image/followup/check": lambda params: api_image_followup_check(params.get("q", [""])[0]) if params.get("q", [""])[0] else {"success": False, "error": "Missing query parameter 'q'"},
}

POST_ROUTES = {
    "/api/image/chat": lambda data: api_image_chat(
        query=data.get("query", ""),
        image_path=data.get("image_path") or None,
        image_base64=data.get("image_base64") or None,
        user_id=data.get("user_id", "default")
    ) if data.get("query") else {"success": False, "error": "Missing query"},
    "/api/image/followup/check": lambda data: api_image_followup_check(data.get("query", "")) if data.get("query") else {"success": False, "error": "Missing query"},
}
