#!/usr/bin/env python3
"""
SAM Vision Client - Easy Integration Helper for Vision API

A simple client class for connecting to SAM's vision endpoints.
Supports both HTTP API calls (for remote integration) and direct
in-process calls (for Python scripts).

Phase 3.1.3: Vision API Integration

Usage:
    # HTTP client (for external apps, Tauri, etc.)
    from cognitive.vision_client import VisionClient

    client = VisionClient(base_url="http://localhost:8765")
    result = client.process("/path/to/image.png", "What is in this image?")
    print(result.response)

    # Direct client (for Python scripts, no HTTP overhead)
    from cognitive.vision_client import DirectVisionClient

    client = DirectVisionClient()
    result = client.process("/path/to/image.png", "Describe this")
    print(result.response)

API Endpoints Covered:
    POST /api/vision/process   - General image processing with custom prompt
    POST /api/vision/describe  - Describe image at detail level
    POST /api/vision/detect    - Object detection
    POST /api/vision/ocr       - Text extraction (Apple Vision)
    POST /api/vision/smart     - Smart auto-routing to best tier
    GET  /api/vision/models    - List available models
    GET  /api/vision/stats     - Engine statistics

Created: 2026-01-25
"""

import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from enum import Enum


class VisionTier(Enum):
    """Processing tiers for smart routing."""
    ZERO_COST = "ZERO_COST"       # Apple Vision, PIL (instant, 0 RAM)
    LIGHTWEIGHT = "LIGHTWEIGHT"   # CoreML, small classifiers (~200MB)
    LOCAL_VLM = "LOCAL_VLM"       # nanoLLaVA (4GB RAM, 60s)
    CLAUDE = "CLAUDE"             # Claude escalation (complex tasks)


@dataclass
class VisionResponse:
    """Unified response from vision processing."""
    success: bool
    response: str
    confidence: float = 0.0
    model_used: str = ""
    task_type: str = ""
    processing_time_ms: int = 0
    escalated: bool = False
    escalation_reason: Optional[str] = None
    tier_used: Optional[str] = None
    from_cache: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: Dict) -> "VisionResponse":
        """Create VisionResponse from API JSON response."""
        return cls(
            success=data.get("success", False),
            response=data.get("response", data.get("description", "")),
            confidence=data.get("confidence", 0.0),
            model_used=data.get("model_used", ""),
            task_type=data.get("task_type", ""),
            processing_time_ms=data.get("processing_time_ms", 0),
            escalated=data.get("escalated", False),
            escalation_reason=data.get("escalation_reason"),
            tier_used=data.get("tier_used"),
            from_cache=data.get("from_cache", False),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "response": self.response,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "task_type": self.task_type,
            "processing_time_ms": self.processing_time_ms,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
            "tier_used": self.tier_used,
            "from_cache": self.from_cache,
            "error": self.error,
            "metadata": self.metadata,
        }


class VisionClient:
    """
    HTTP client for SAM Vision API.

    Use this for:
    - Tauri frontend integration
    - External applications
    - Remote API calls
    - Cross-language integration

    Example:
        client = VisionClient("http://localhost:8765")

        # Basic processing
        result = client.process("photo.jpg", "What objects are in this image?")

        # OCR (uses Apple Vision, instant)
        text = client.ocr("screenshot.png")

        # Smart routing (auto-selects best tier)
        result = client.smart("complex.jpg", "Explain the relationship between objects")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        timeout: float = 120.0,
    ):
        """
        Initialize the vision client.

        Args:
            base_url: SAM API base URL (default: http://localhost:8765)
            timeout: Request timeout in seconds (default: 120s for VLM processing)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = None

    def _get_session(self):
        """Get or create requests session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def _post(self, endpoint: str, data: Dict) -> Dict:
        """Make a POST request to the API."""
        import requests

        session = self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            response = session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Request timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"Cannot connect to {self.base_url}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the API."""
        import requests

        session = self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _prepare_image(self, image: Union[str, Path, bytes]) -> Dict:
        """Prepare image for API request."""
        if isinstance(image, bytes):
            return {"image_base64": base64.b64encode(image).decode("utf-8")}
        elif isinstance(image, Path):
            return {"image_path": str(image)}
        elif isinstance(image, str):
            if image.startswith("data:"):
                # Data URL
                b64 = image.split(",")[1] if "," in image else image
                return {"image_base64": b64}
            else:
                return {"image_path": image}
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def process(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "Describe this image",
        model: Optional[str] = None,
    ) -> VisionResponse:
        """
        Process an image with a custom prompt.

        Args:
            image: Image path, Path object, or raw bytes
            prompt: Question or instruction about the image
            model: Force specific model (e.g., "nanollava", "smolvlm-500m")

        Returns:
            VisionResponse with the result

        Example:
            result = client.process("/tmp/photo.jpg", "Count the people in this image")
            if result.success:
                print(f"Answer: {result.response}")
        """
        data = self._prepare_image(image)
        data["prompt"] = prompt
        if model:
            data["model"] = model

        response = self._post("/api/vision/process", data)
        return VisionResponse.from_api_response(response)

    def describe(
        self,
        image: Union[str, Path, bytes],
        detail_level: str = "medium",
    ) -> VisionResponse:
        """
        Describe an image at specified detail level.

        Args:
            image: Image path, Path object, or raw bytes
            detail_level: "quick", "medium", or "detailed"

        Returns:
            VisionResponse with description

        Example:
            result = client.describe("/tmp/photo.jpg", detail_level="detailed")
            print(result.response)
        """
        data = self._prepare_image(image)
        data["detail_level"] = detail_level

        response = self._post("/api/vision/describe", data)
        return VisionResponse.from_api_response(response)

    def detect(
        self,
        image: Union[str, Path, bytes],
        target: Optional[str] = None,
    ) -> VisionResponse:
        """
        Detect objects in an image.

        Args:
            image: Image path, Path object, or raw bytes
            target: Specific object to find (optional)

        Returns:
            VisionResponse with detection results

        Example:
            result = client.detect("/tmp/photo.jpg", target="cat")
            print(result.response)
        """
        data = self._prepare_image(image)
        if target:
            data["target"] = target

        response = self._post("/api/vision/detect", data)
        return VisionResponse.from_api_response(response)

    def ocr(self, image: Union[str, Path, bytes]) -> VisionResponse:
        """
        Extract text from an image using Apple Vision.

        This is the fastest vision operation - uses native Apple APIs
        with zero ML model loading. Instant results.

        Args:
            image: Image path, Path object, or raw bytes

        Returns:
            VisionResponse with extracted text

        Example:
            result = client.ocr("/tmp/screenshot.png")
            print(f"Text: {result.response}")
        """
        data = self._prepare_image(image)
        response = self._post("/api/vision/ocr", data)
        return VisionResponse.from_api_response(response)

    def smart(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "What is this?",
        force_tier: Optional[VisionTier] = None,
        skip_cache: bool = False,
    ) -> VisionResponse:
        """
        Smart vision processing with automatic tier routing.

        Routes to the most efficient handler based on the task:
        - ZERO_COST: OCR, color analysis (instant, 0 RAM)
        - LIGHTWEIGHT: Face detection, basic description (~200MB)
        - LOCAL_VLM: Detailed analysis (4GB, ~60s)
        - CLAUDE: Complex reasoning (escalation)

        Args:
            image: Image path, Path object, or raw bytes
            prompt: Question or instruction
            force_tier: Override automatic tier selection
            skip_cache: Bypass cache lookup

        Returns:
            VisionResponse with result and tier info

        Example:
            result = client.smart("/tmp/code.png", "Find bugs in this code")
            print(f"Used tier: {result.tier_used}")
            print(f"Response: {result.response}")
        """
        data = self._prepare_image(image)
        data["prompt"] = prompt
        data["skip_cache"] = skip_cache
        if force_tier:
            data["force_tier"] = force_tier.value

        response = self._post("/api/vision/smart", data)
        return VisionResponse.from_api_response(response)

    def get_models(self) -> Dict[str, Any]:
        """
        Get list of available vision models.

        Returns:
            Dictionary with model information

        Example:
            models = client.get_models()
            for name, info in models.get("models", {}).items():
                print(f"{name}: {info.get('quality', 'unknown')} quality")
        """
        return self._get("/api/vision/models")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vision engine statistics.

        Returns:
            Dictionary with engine stats

        Example:
            stats = client.get_stats()
            print(f"Generation count: {stats.get('generation_count', 0)}")
        """
        return self._get("/api/vision/stats")

    def get_smart_stats(self) -> Dict[str, Any]:
        """
        Get smart vision cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return self._get("/api/vision/smart/stats")

    def health_check(self) -> bool:
        """
        Check if the vision API is available.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Try vision-specific endpoint first
            response = self._get("/api/vision/stats")
            if response.get("success"):
                return True
            # Fall back to general health check
            response = self._get("/health")
            return response.get("status") == "ok" or response.get("success") is True
        except:
            return False

    def close(self):
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DirectVisionClient:
    """
    Direct Python client for SAM Vision - no HTTP overhead.

    Use this for:
    - Python scripts running on the same machine
    - Performance-critical applications
    - Avoiding network latency

    Example:
        client = DirectVisionClient()
        result = client.process("photo.jpg", "What is this?")
        print(result.response)
    """

    def __init__(self):
        """Initialize the direct vision client."""
        self._engine = None
        self._smart_router = None

    def _get_engine(self):
        """Lazy-load vision engine."""
        if self._engine is None:
            from .vision_engine import create_vision_engine
            self._engine = create_vision_engine()
        return self._engine

    def _get_smart_router(self):
        """Lazy-load smart vision router."""
        if self._smart_router is None:
            from .smart_vision import get_router
            self._smart_router = get_router()
        return self._smart_router

    def process(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "Describe this image",
        model: Optional[str] = None,
    ) -> VisionResponse:
        """
        Process an image with a custom prompt.

        Args:
            image: Image path, Path object, or raw bytes
            prompt: Question or instruction about the image
            model: Force specific model

        Returns:
            VisionResponse with the result
        """
        engine = self._get_engine()

        from .vision_engine import VisionConfig
        config = VisionConfig()
        if model:
            config.model_key = model

        # Handle bytes input
        image_path = image
        temp_file = None
        if isinstance(image, bytes):
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_file.write(image)
            temp_file.close()
            image_path = temp_file.name
        elif isinstance(image, Path):
            image_path = str(image)

        try:
            result = engine.process_image(image_path, prompt, config)

            return VisionResponse(
                success=True,
                response=result.response,
                confidence=result.confidence,
                model_used=result.model_used,
                task_type=result.task_type.value,
                processing_time_ms=result.processing_time_ms,
                escalated=result.escalated,
                escalation_reason=result.escalation_reason,
                metadata=result.metadata,
            )
        except Exception as e:
            return VisionResponse(
                success=False,
                response="",
                error=str(e),
            )
        finally:
            # Clean up temp file
            if temp_file:
                import os
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

    def describe(
        self,
        image: Union[str, Path, bytes],
        detail_level: str = "medium",
    ) -> VisionResponse:
        """Describe an image at specified detail level."""
        prompts = {
            "quick": "What is this image?",
            "medium": "Describe this image in a few sentences.",
            "detailed": "Provide a detailed description of everything you see.",
        }
        prompt = prompts.get(detail_level, prompts["medium"])
        return self.process(image, prompt)

    def detect(
        self,
        image: Union[str, Path, bytes],
        target: Optional[str] = None,
    ) -> VisionResponse:
        """Detect objects in an image."""
        if target:
            prompt = f"Find and locate '{target}' in this image. Describe its position."
        else:
            prompt = "List all objects you can see in this image."
        return self.process(image, prompt)

    def ocr(self, image: Union[str, Path, bytes]) -> VisionResponse:
        """Extract text from an image using Apple Vision."""
        try:
            from ..apple_ocr import extract_text

            # Handle bytes input
            image_path = image
            temp_file = None
            if isinstance(image, bytes):
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_file.write(image)
                temp_file.close()
                image_path = temp_file.name
            elif isinstance(image, Path):
                image_path = str(image)

            try:
                result = extract_text(image_path)

                if result.get("success"):
                    return VisionResponse(
                        success=True,
                        response=result.get("text", ""),
                        confidence=1.0,
                        model_used="apple_vision",
                        task_type="ocr",
                        processing_time_ms=result.get("processing_time_ms", 0),
                        metadata={"lines": result.get("lines", [])},
                    )
                else:
                    return VisionResponse(
                        success=False,
                        response="",
                        error=result.get("error", "OCR failed"),
                    )
            finally:
                if temp_file:
                    import os
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
        except ImportError:
            # Fallback to VLM
            return self.process(image, "Read all the text in this image")

    def smart(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "What is this?",
        force_tier: Optional[VisionTier] = None,
        skip_cache: bool = False,
    ) -> VisionResponse:
        """Smart vision processing with automatic tier routing."""
        router = self._get_smart_router()

        # Handle bytes input
        image_path = image
        temp_file = None
        if isinstance(image, bytes):
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_file.write(image)
            temp_file.close()
            image_path = temp_file.name
        elif isinstance(image, Path):
            image_path = str(image)

        try:
            from .smart_vision import VisionTier as SmartVisionTier

            tier = None
            if force_tier:
                tier = SmartVisionTier[force_tier.value]

            result = router.process(image_path, prompt, force_tier=tier, skip_cache=skip_cache)

            return VisionResponse(
                success=result.success,
                response=result.response,
                confidence=result.confidence,
                model_used="",
                task_type=result.task_type.value,
                processing_time_ms=result.processing_time_ms,
                tier_used=result.tier_used.name,
                from_cache=result.from_cache,
                metadata=result.metadata,
            )
        except Exception as e:
            return VisionResponse(
                success=False,
                response="",
                error=str(e),
            )
        finally:
            if temp_file:
                import os
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """Get vision engine statistics."""
        engine = self._get_engine()
        return engine.get_stats()

    def get_smart_stats(self) -> Dict[str, Any]:
        """Get smart vision cache statistics."""
        router = self._get_smart_router()
        return router.memory.get_stats()

    def unload_models(self):
        """Unload all models to free memory."""
        if self._engine:
            self._engine.unload_models()


# Convenience functions for quick usage
def process_image(
    image: Union[str, Path, bytes],
    prompt: str = "Describe this image",
    use_http: bool = False,
    base_url: str = "http://localhost:8765",
) -> VisionResponse:
    """
    Quick function to process an image.

    Args:
        image: Image path, Path object, or raw bytes
        prompt: Question or instruction
        use_http: Use HTTP client (default: direct Python)
        base_url: API base URL (if using HTTP)

    Returns:
        VisionResponse with result

    Example:
        result = process_image("/tmp/photo.jpg", "What is this?")
        print(result.response)
    """
    if use_http:
        with VisionClient(base_url) as client:
            return client.process(image, prompt)
    else:
        client = DirectVisionClient()
        return client.process(image, prompt)


def extract_text(
    image: Union[str, Path, bytes],
    use_http: bool = False,
    base_url: str = "http://localhost:8765",
) -> str:
    """
    Quick function to extract text from an image.

    Uses Apple Vision for instant OCR with no model loading.

    Args:
        image: Image path, Path object, or raw bytes
        use_http: Use HTTP client
        base_url: API base URL (if using HTTP)

    Returns:
        Extracted text as string

    Example:
        text = extract_text("/tmp/screenshot.png")
        print(text)
    """
    if use_http:
        with VisionClient(base_url) as client:
            result = client.ocr(image)
    else:
        client = DirectVisionClient()
        result = client.ocr(image)

    return result.response if result.success else ""


def smart_analyze(
    image: Union[str, Path, bytes],
    prompt: str = "What is this?",
    use_http: bool = False,
    base_url: str = "http://localhost:8765",
) -> VisionResponse:
    """
    Quick function for smart vision analysis.

    Auto-routes to the most efficient tier based on the task.

    Args:
        image: Image path, Path object, or raw bytes
        prompt: Question or instruction
        use_http: Use HTTP client
        base_url: API base URL (if using HTTP)

    Returns:
        VisionResponse with result and tier info

    Example:
        result = smart_analyze("/tmp/code.png", "Find bugs in this code")
        print(f"Used tier: {result.tier_used}")
    """
    if use_http:
        with VisionClient(base_url) as client:
            return client.smart(image, prompt)
    else:
        client = DirectVisionClient()
        return client.smart(image, prompt)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="SAM Vision Client CLI")
    parser.add_argument("image", help="Path to image")
    parser.add_argument("prompt", nargs="?", default="Describe this image",
                       help="Prompt/question about the image")
    parser.add_argument("--mode", choices=["process", "describe", "detect", "ocr", "smart"],
                       default="process", help="Processing mode")
    parser.add_argument("--http", action="store_true", help="Use HTTP client")
    parser.add_argument("--url", default="http://localhost:8765", help="API base URL")
    parser.add_argument("--tier", choices=["ZERO_COST", "LIGHTWEIGHT", "LOCAL_VLM", "CLAUDE"],
                       help="Force specific tier (smart mode only)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--detail", choices=["quick", "medium", "detailed"],
                       default="medium", help="Detail level (describe mode)")
    parser.add_argument("--target", help="Detection target (detect mode)")

    args = parser.parse_args()

    # Create client
    if args.http:
        client = VisionClient(args.url)
    else:
        client = DirectVisionClient()

    # Execute based on mode
    if args.mode == "process":
        result = client.process(args.image, args.prompt)
    elif args.mode == "describe":
        result = client.describe(args.image, args.detail)
    elif args.mode == "detect":
        result = client.detect(args.image, args.target)
    elif args.mode == "ocr":
        result = client.ocr(args.image)
    elif args.mode == "smart":
        tier = VisionTier[args.tier] if args.tier else None
        result = client.smart(args.image, args.prompt, force_tier=tier)

    # Output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Success: {result.success}")
        if result.model_used:
            print(f"Model: {result.model_used}")
        if result.tier_used:
            print(f"Tier: {result.tier_used}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Time: {result.processing_time_ms}ms")
        if result.from_cache:
            print(f"From Cache: Yes")
        if result.escalated:
            print(f"Escalated: {result.escalation_reason}")
        if result.error:
            print(f"Error: {result.error}")
        print(f"{'='*60}")
        print(f"\n{result.response}\n")
