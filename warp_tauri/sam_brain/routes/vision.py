"""SAM API Vision Routes - Image processing, OCR, detection, smart routing, streaming."""

from datetime import datetime
from shared_state import (
    get_vision_engine, get_smart_vision_router, get_vision_stats_monitor,
    record_vision_stats,
)


def api_vision_process(image_path: str = None, prompt: str = "", model: str = None,
                       image_base64: str = None) -> dict:
    """Process an image with a prompt."""
    engine = get_vision_engine()
    if not engine:
        return {"success": False, "error": "Vision engine not available"}

    try:
        import tempfile
        import base64

        temp_path = None
        if image_base64:
            image_data = base64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            image_path = temp_path

        if not image_path:
            return {"success": False, "error": "No image provided (path or base64)"}

        from cognitive import VisionConfig
        config = VisionConfig()
        if model:
            config.model_key = model

        start = datetime.now()
        result = engine.process_image(image_path, prompt, config)

        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        tier = "CLAUDE" if result.escalated else "LOCAL_VLM"
        record_vision_stats(
            tier=tier,
            processing_time_ms=result.processing_time_ms,
            task_type=result.task_type.value,
            escalated=result.escalated,
            success=True
        )

        return {
            "success": True,
            "image_path": image_path if not temp_path else "[base64 image]",
            "prompt": prompt,
            "response": result.response,
            "description": result.response,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "task_type": result.task_type.value,
            "escalated": result.escalated,
            "escalation_reason": result.escalation_reason,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="unknown",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_stream(image_base64: str = None, image_path: str = None, prompt: str = "Describe this image"):
    """Stream vision response via Server-Sent Events (Phase 3.1.8)."""
    import json as json_module
    import tempfile
    import base64 as b64_module
    import time

    start_time = time.time()

    def elapsed_ms():
        return int((time.time() - start_time) * 1000)

    try:
        yield f'data: {json_module.dumps({"status": "loading", "message": "Preparing image..."})}\n\n'

        temp_path = None
        actual_path = image_path
        if image_base64:
            image_data = b64_module.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            actual_path = temp_path

        if not actual_path:
            yield f'data: {json_module.dumps({"error": "No image provided"})}\n\n'
            return

        # Try vision server first
        try:
            import requests
            VISION_SERVER_URL = "http://localhost:8766"

            health = requests.get(f"{VISION_SERVER_URL}/health", timeout=2)
            if health.status_code == 200 and health.json().get("status") == "ok":
                yield f'data: {json_module.dumps({"status": "analyzing", "message": "Processing via vision server...", "elapsed_ms": elapsed_ms()})}\n\n'

                with open(actual_path, "rb") as f:
                    img_b64 = b64_module.b64encode(f.read()).decode("utf-8")

                response = requests.post(
                    f"{VISION_SERVER_URL}/process",
                    json={"image_base64": img_b64, "prompt": prompt},
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        text = result.get("response", "")
                        words = text.split()
                        for i, word in enumerate(words):
                            yield f'data: {json_module.dumps({"token": word + " "})}\n\n'
                            if i < 5:
                                time.sleep(0.05)

                        yield f'data: {json_module.dumps({"done": True, "response": text, "processing_time_ms": elapsed_ms()})}\n\n'

                        if temp_path:
                            import os
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        return

        except (Exception,):
            pass

        # Direct mlx_vlm streaming
        yield f'data: {json_module.dumps({"status": "loading", "message": "Loading vision model (this takes 30-60s first time)...", "elapsed_ms": elapsed_ms()})}\n\n'

        try:
            from mlx_vlm import load, stream_generate
            from mlx_vlm.prompt_utils import apply_chat_template
            from mlx_vlm.utils import load_config

            model_path = "mlx-community/nanoLLaVA-1.5-bf16"

            yield f'data: {json_module.dumps({"status": "loading", "message": f"Loading {model_path}...", "elapsed_ms": elapsed_ms()})}\n\n'

            config = load_config(model_path)
            model, processor = load(model_path, {"trust_remote_code": True})

            yield f'data: {json_module.dumps({"status": "analyzing", "message": "Analyzing image...", "elapsed_ms": elapsed_ms()})}\n\n'

            formatted_prompt = apply_chat_template(processor, config, prompt, num_images=1)

            full_response = []
            for token in stream_generate(
                model, processor,
                formatted_prompt,
                image=actual_path,
                max_tokens=200,
                temperature=0.3
            ):
                full_response.append(token)
                yield f'data: {json_module.dumps({"token": token})}\n\n'

            final_text = "".join(full_response).strip()
            yield f'data: {json_module.dumps({"done": True, "response": final_text, "processing_time_ms": elapsed_ms()})}\n\n'

        except ImportError as e:
            yield f'data: {json_module.dumps({"error": f"mlx_vlm not available: {e}"})}\n\n'
        except Exception as e:
            yield f'data: {json_module.dumps({"error": f"Vision processing failed: {e}"})}\n\n'

        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_vision_analyze(image_base64: str = None, image_path: str = None, prompt: str = "Describe this image") -> dict:
    """Non-streaming vision analysis endpoint (Phase 3.1.8)."""
    import tempfile
    import base64 as b64_module
    import time

    start_time = time.time()

    try:
        temp_path = None
        actual_path = image_path
        if image_base64:
            image_data = b64_module.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            actual_path = temp_path

        if not actual_path:
            return {"success": False, "error": "No image provided"}

        engine = get_vision_engine()
        if not engine:
            return {"success": False, "error": "Vision engine not available", "analysis": "Vision system is not loaded"}

        from cognitive import VisionConfig
        config = VisionConfig()

        result = engine.process_image(actual_path, prompt, config)

        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        processing_time_ms = int((time.time() - start_time) * 1000)

        tier = "CLAUDE" if getattr(result, 'escalated', False) else "LOCAL_VLM"
        task_type_val = result.task_type.value if hasattr(result.task_type, 'value') else str(result.task_type)
        record_vision_stats(
            tier=tier,
            processing_time_ms=processing_time_ms,
            task_type=task_type_val,
            escalated=getattr(result, 'escalated', False),
            success=True
        )

        return {
            "success": True,
            "response": result.response,
            "analysis": result.response,
            "description": result.response,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "task_type": task_type_val,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="unknown",
            success=False
        )
        return {"success": False, "error": str(e), "analysis": f"Analysis failed: {str(e)}"}


def api_vision_describe(image_path: str, detail_level: str = "medium") -> dict:
    """Describe an image at specified detail level."""
    try:
        from cognitive import describe_image
        start = datetime.now()
        result = describe_image(image_path, detail_level)
        duration = (datetime.now() - start).total_seconds() * 1000

        tier = "LIGHTWEIGHT" if detail_level == "basic" else "LOCAL_VLM"
        record_vision_stats(
            tier=tier,
            processing_time_ms=result.processing_time_ms,
            task_type="describe",
            success=True
        )

        return {
            "success": True,
            "image_path": image_path,
            "detail_level": detail_level,
            "description": result.response,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="describe",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_ocr(image_path: str = None, image_base64: str = None) -> dict:
    """Extract text from an image using Apple Vision (fast, accurate, no GPU)."""
    try:
        import tempfile
        import base64

        temp_path = None
        if image_base64:
            image_data = base64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            image_path = temp_path

        if not image_path:
            return {"success": False, "error": "No image provided"}

        start = datetime.now()

        # Try Apple Vision first
        try:
            from see.apple_ocr import extract_text
            result = extract_text(image_path)

            if result.get("success"):
                processing_time = int((datetime.now() - start).total_seconds() * 1000)

                if temp_path:
                    import os
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

                record_vision_stats(
                    tier="ZERO_COST",
                    processing_time_ms=processing_time,
                    task_type="ocr",
                    success=True
                )

                return {
                    "success": True,
                    "image_path": image_path if not temp_path else "[base64]",
                    "text": result.get("text", ""),
                    "lines": result.get("lines", []),
                    "line_count": result.get("line_count", 0),
                    "confidence": 1.0,
                    "model_used": "apple_vision",
                    "processing_time_ms": processing_time,
                    "timestamp": datetime.now().isoformat(),
                }
        except ImportError:
            pass

        # Fallback: Use vision model
        engine = get_vision_engine()
        if not engine:
            return {"success": False, "error": "No OCR engine available"}

        from cognitive import VisionConfig
        config = VisionConfig()
        config.max_tokens = 200

        ocr_prompt = "Read the text in this image word by word. List all text exactly as written."
        result = engine.process_image(image_path, ocr_prompt, config)

        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=result.processing_time_ms,
            task_type="ocr",
            success=True
        )

        return {
            "success": True,
            "image_path": image_path if not temp_path else "[base64]",
            "text": result.response,
            "confidence": result.confidence,
            "model_used": "vlm_fallback",
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
            "note": "Used VLM fallback - accuracy may vary"
        }
    except Exception as e:
        record_vision_stats(
            tier="LOCAL_VLM",
            processing_time_ms=0,
            task_type="ocr",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_detect(image_path: str, target: str = None) -> dict:
    """Detect objects in an image."""
    try:
        from cognitive import detect_objects
        start = datetime.now()
        result = detect_objects(image_path, target)
        duration = (datetime.now() - start).total_seconds() * 1000

        return {
            "success": True,
            "image_path": image_path,
            "target": target,
            "detections": result.response,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "bounding_boxes": result.bounding_boxes,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_vision_models() -> dict:
    """List available vision models."""
    try:
        from cognitive import VISION_MODELS
        models = []
        for key, config in VISION_MODELS.items():
            models.append({
                "key": key,
                "model_id": config["model_id"],
                "memory_mb": config["memory_mb"],
                "speed": config["speed"],
                "quality": config["quality"],
                "use_cases": config["use_cases"],
            })
        return {
            "success": True,
            "models": models,
            "count": len(models),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_vision_stats() -> dict:
    """Get comprehensive vision statistics (Phase 3.2.6 enhanced)."""
    usage_stats = {}
    try:
        vision_monitor = get_vision_stats_monitor()
        usage_stats = vision_monitor.get_stats()
    except Exception as e:
        usage_stats = {"error": str(e)}

    engine_stats = {}
    engine = get_vision_engine()
    if engine:
        try:
            engine_stats = engine.get_stats()
        except Exception:
            engine_stats = {"available": True, "error": "Could not get engine stats"}
    else:
        engine_stats = {"available": False}

    cache_stats = {}
    try:
        router = get_smart_vision_router()
        if router:
            cache_stats = router.memory.get_stats()
    except Exception:
        cache_stats = {"error": "Smart vision router not available"}

    return {
        "success": True,
        "engine": engine_stats,
        "usage": usage_stats,
        "cache": cache_stats,
        "timestamp": datetime.now().isoformat(),
    }


def api_vision_smart(image_path: str = None, image_base64: str = None,
                     prompt: str = "What is this?",
                     force_tier: str = None,
                     skip_cache: bool = False) -> dict:
    """Smart vision endpoint - automatically routes to best tier."""
    router = get_smart_vision_router()
    if not router:
        return {"success": False, "error": "Smart vision router not available"}

    try:
        import tempfile
        import base64
        from cognitive.smart_vision import VisionTier

        temp_path = None
        if image_base64:
            image_data = base64.b64decode(image_base64)
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            image_path = temp_path

        if not image_path:
            return {"success": False, "error": "No image provided (path or base64)"}

        tier_override = None
        if force_tier:
            tier_map = {
                "ZERO_COST": VisionTier.ZERO_COST,
                "LIGHTWEIGHT": VisionTier.LIGHTWEIGHT,
                "LOCAL_VLM": VisionTier.LOCAL_VLM,
                "CLAUDE": VisionTier.CLAUDE,
            }
            tier_override = tier_map.get(force_tier.upper())

        result = router.process(
            image_path=image_path,
            prompt=prompt,
            force_tier=tier_override,
            skip_cache=skip_cache
        )

        if temp_path:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

        escalated = result.tier_used == VisionTier.CLAUDE
        record_vision_stats(
            tier=result.tier_used.name,
            processing_time_ms=result.processing_time_ms,
            task_type=result.task_type.value,
            escalated=escalated,
            success=result.success,
            from_cache=result.from_cache
        )

        return {
            "success": result.success,
            "response": result.response,
            "tier_used": result.tier_used.name,
            "task_type": result.task_type.value,
            "processing_time_ms": result.processing_time_ms,
            "confidence": result.confidence,
            "from_cache": result.from_cache,
            "metadata": result.metadata,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        record_vision_stats(
            tier=force_tier or "LOCAL_VLM",
            processing_time_ms=0,
            task_type="unknown",
            success=False
        )
        return {"success": False, "error": str(e)}


def api_vision_smart_stats() -> dict:
    """Get smart vision cache statistics."""
    router = get_smart_vision_router()
    if not router:
        return {"success": False, "error": "Smart vision router not available"}

    try:
        stats = router.memory.get_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/vision/models": lambda params: api_vision_models(),
    "/api/vision/stats": lambda params: api_vision_stats(),
    "/api/vision/describe": lambda params: api_vision_describe(params.get("path", [""])[0], params.get("level", ["medium"])[0]) if params.get("path", [""])[0] else {"success": False, "error": "Missing query parameter 'path'"},
    "/api/vision/detect": lambda params: api_vision_detect(params.get("path", [""])[0], params.get("target", [None])[0]) if params.get("path", [""])[0] else {"success": False, "error": "Missing query parameter 'path'"},
    "/api/vision/smart": lambda params: api_vision_smart(
        image_path=params.get("path", [""])[0] if params.get("path", [""])[0] else None,
        prompt=params.get("prompt", ["What is this?"])[0],
        force_tier=params.get("tier", [None])[0],
        skip_cache=params.get("skip_cache", ["false"])[0].lower() == "true"
    ) if params.get("path", [""])[0] else {"success": False, "error": "Missing query parameter 'path'"},
    "/api/vision/smart/stats": lambda params: api_vision_smart_stats(),
}

POST_ROUTES = {
    "/api/vision/process": lambda data: api_vision_process(
        image_path=data.get("image_path") or None,
        prompt=data.get("prompt", "Describe this image"),
        model=data.get("model"),
        image_base64=data.get("image_base64") or None
    ) if data.get("image_path") or data.get("image_base64") else {"success": False, "error": "Missing image_path or image_base64"},
    "/api/vision/analyze": lambda data: api_vision_analyze(
        image_path=data.get("image_path") or None,
        image_base64=data.get("image_base64") or None,
        prompt=data.get("prompt", "Describe this image in detail.")
    ) if data.get("image_path") or data.get("image_base64") else {"success": False, "error": "Missing image_path or image_base64"},
    "/api/vision/describe": lambda data: api_vision_describe(data.get("image_path", ""), data.get("detail_level", "medium")) if data.get("image_path") else {"success": False, "error": "Missing image_path"},
    "/api/vision/detect": lambda data: api_vision_detect(data.get("image_path", ""), data.get("target")) if data.get("image_path") else {"success": False, "error": "Missing image_path"},
    "/api/vision/ocr": lambda data: api_vision_ocr(
        image_path=data.get("image_path") or None,
        image_base64=data.get("image_base64") or None
    ) if data.get("image_path") or data.get("image_base64") else {"success": False, "error": "Missing image_path or image_base64"},
    "/api/vision/smart": lambda data: api_vision_smart(
        image_path=data.get("image_path") or None,
        image_base64=data.get("image_base64") or None,
        prompt=data.get("prompt", "What is this?"),
        force_tier=data.get("force_tier"),
        skip_cache=data.get("skip_cache", False)
    ) if data.get("image_path") or data.get("image_base64") else {"success": False, "error": "Missing image_path or image_base64"},
}

STREAM_POST_ROUTES = {
    "/api/vision/stream": lambda data: api_vision_stream(
        image_base64=data.get("image_base64") or None,
        image_path=data.get("image_path") or None,
        prompt=data.get("prompt", "Describe this image")
    ) if data.get("image_path") or data.get("image_base64") else None,
}
