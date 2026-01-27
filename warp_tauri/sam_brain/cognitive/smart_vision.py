#!/usr/bin/env python3
"""
SAM Smart Vision System - Cutting Edge Multi-Tier Architecture

Routes vision tasks to the most efficient handler:
- Tier 0: Zero-cost (Apple APIs, PIL analysis) - instant, 0 RAM
- Tier 1: Lightweight (CoreML, small classifiers) - fast, ~200MB
- Tier 2: Local VLM (nanoLLaVA) - 60s, 4GB
- Tier 3: Claude Escalation (dual terminal bridge) - complex tasks, 0 local RAM

Features:
- Smart task classification
- Progressive analysis (quick → detailed on demand)
- Vision memory (cache + similarity matching)
- Resource-aware routing
"""

import os
import json
import hashlib
import sqlite3
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart_vision")

# ============================================================================
# CONFIGURATION
# ============================================================================

VISION_DB_PATH = Path.home() / ".sam" / "vision_memory.db"
VISION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class VisionTier(Enum):
    """Processing tiers from cheapest to most expensive."""
    ZERO_COST = 0      # Apple Vision, PIL, basic analysis
    LIGHTWEIGHT = 1    # CoreML, small classifiers
    LOCAL_VLM = 2      # nanoLLaVA (4GB RAM)
    CLAUDE = 3         # Escalate to Claude via dual terminal

class TaskType(Enum):
    """Types of vision tasks."""
    OCR = "ocr"                    # Text extraction
    COLOR = "color"                # Color analysis
    BASIC_DESCRIBE = "basic"       # Quick description
    DETAILED_DESCRIBE = "detailed" # Full analysis
    OBJECT_DETECT = "detect"       # Find specific objects
    FACE_DETECT = "face"           # Face detection
    COMPARE = "compare"            # Compare images
    REASONING = "reasoning"        # Complex visual reasoning
    CODE_REVIEW = "code"           # Screenshot of code
    UI_ANALYSIS = "ui"             # UI/screenshot analysis

# Task → Tier mapping (which tier handles what)
TASK_ROUTING = {
    TaskType.OCR: VisionTier.ZERO_COST,           # Apple Vision
    TaskType.COLOR: VisionTier.ZERO_COST,         # PIL
    TaskType.BASIC_DESCRIBE: VisionTier.LIGHTWEIGHT,  # Quick classifier
    TaskType.FACE_DETECT: VisionTier.LIGHTWEIGHT,     # CoreML
    TaskType.OBJECT_DETECT: VisionTier.LOCAL_VLM,     # VLM
    TaskType.DETAILED_DESCRIBE: VisionTier.LOCAL_VLM, # VLM
    TaskType.CODE_REVIEW: VisionTier.CLAUDE,          # Claude (complex)
    TaskType.UI_ANALYSIS: VisionTier.CLAUDE,          # Claude (complex)
    TaskType.REASONING: VisionTier.CLAUDE,            # Claude (complex)
    TaskType.COMPARE: VisionTier.CLAUDE,              # Claude (complex)
}

# Keywords for task classification
TASK_KEYWORDS = {
    TaskType.OCR: ["read", "text", "ocr", "words", "says", "written", "transcribe"],
    TaskType.COLOR: ["color", "colour", "hue", "shade", "rgb", "what color"],
    TaskType.FACE_DETECT: ["face", "person", "who", "people", "portrait"],
    TaskType.CODE_REVIEW: ["code", "programming", "function", "bug", "error", "syntax"],
    TaskType.UI_ANALYSIS: ["ui", "interface", "button", "screen", "app", "click", "layout"],
    TaskType.REASONING: ["why", "explain", "analyze", "compare", "difference", "relationship"],
    TaskType.OBJECT_DETECT: ["find", "locate", "detect", "where", "count", "how many"],
    TaskType.DETAILED_DESCRIBE: ["describe", "detail", "everything", "full", "comprehensive"],
    TaskType.BASIC_DESCRIBE: ["what", "is this", "quick", "brief"],
}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class VisionResult:
    """Result from vision processing."""
    success: bool
    response: str
    tier_used: VisionTier
    task_type: TaskType
    processing_time_ms: int
    confidence: float = 0.0
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ImageAnalysis:
    """Quick analysis of an image (Tier 0)."""
    width: int
    height: int
    format: str
    has_text: bool
    dominant_colors: List[Tuple[int, int, int]]
    brightness: float  # 0-1
    complexity: float  # 0-1 (edge density)
    hash: str

# ============================================================================
# VISION MEMORY (Caching + Similarity)
# ============================================================================

class VisionMemory:
    """Persistent memory for vision results - avoid reprocessing."""

    def __init__(self, db_path: Path = VISION_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vision_cache (
                    image_hash TEXT PRIMARY KEY,
                    task_type TEXT,
                    prompt TEXT,
                    response TEXT,
                    tier_used INTEGER,
                    confidence REAL,
                    created_at TEXT,
                    access_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task ON vision_cache(task_type)
            """)

    def get_cached(self, image_hash: str, task_type: str) -> Optional[Dict]:
        """Get cached result for image+task combo."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT response, tier_used, confidence, created_at
                   FROM vision_cache
                   WHERE image_hash = ? AND task_type = ?""",
                (image_hash, task_type)
            )
            row = cursor.fetchone()
            if row:
                # Update access count
                conn.execute(
                    "UPDATE vision_cache SET access_count = access_count + 1 WHERE image_hash = ?",
                    (image_hash,)
                )
                return {
                    "response": row[0],
                    "tier_used": row[1],
                    "confidence": row[2],
                    "created_at": row[3]
                }
        return None

    def cache_result(self, image_hash: str, task_type: str, prompt: str,
                     response: str, tier_used: int, confidence: float):
        """Cache a vision result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO vision_cache
                   (image_hash, task_type, prompt, response, tier_used, confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (image_hash, task_type, prompt, response, tier_used, confidence,
                 datetime.now().isoformat())
            )

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*), SUM(access_count) FROM vision_cache")
            count, accesses = cursor.fetchone()
            return {
                "cached_images": count or 0,
                "total_cache_hits": (accesses or 0) - (count or 0),
                "db_path": str(self.db_path)
            }

# ============================================================================
# TIER 0: ZERO-COST HANDLERS
# ============================================================================

def analyze_image_basic(image_path: str) -> ImageAnalysis:
    """Quick image analysis using PIL (no ML, instant)."""
    from PIL import Image
    import hashlib

    img = Image.open(image_path)

    # Calculate hash
    img_hash = hashlib.md5(img.tobytes()).hexdigest()

    # Get dominant colors (simplified)
    small = img.resize((50, 50)).convert('RGB')
    pixels = list(small.getdata())
    from collections import Counter
    color_counts = Counter(pixels)
    dominant = [c[0] for c in color_counts.most_common(5)]

    # Brightness (average luminance)
    grayscale = img.convert('L')
    brightness = sum(grayscale.getdata()) / (img.width * img.height * 255)

    # Complexity (edge detection proxy)
    try:
        from PIL import ImageFilter
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        complexity = sum(edges.getdata()) / (img.width * img.height * 255)
    except:
        complexity = 0.5

    # Check if likely has text (high contrast, structured)
    has_text = complexity > 0.1 and brightness > 0.3

    return ImageAnalysis(
        width=img.width,
        height=img.height,
        format=img.format or "unknown",
        has_text=has_text,
        dominant_colors=dominant,
        brightness=brightness,
        complexity=complexity,
        hash=img_hash
    )

def get_dominant_color_name(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB to color name."""
    r, g, b = rgb

    # Simple color classification
    if r > 200 and g < 100 and b < 100:
        return "red"
    elif r < 100 and g > 200 and b < 100:
        return "green"
    elif r < 100 and g < 100 and b > 200:
        return "blue"
    elif r > 200 and g > 200 and b < 100:
        return "yellow"
    elif r > 200 and g < 100 and b > 200:
        return "magenta"
    elif r < 100 and g > 200 and b > 200:
        return "cyan"
    elif r > 200 and g > 200 and b > 200:
        return "white"
    elif r < 50 and g < 50 and b < 50:
        return "black"
    elif abs(r - g) < 30 and abs(g - b) < 30:
        return "gray"
    elif r > 200 and g > 100 and b < 100:
        return "orange"
    elif r > 100 and g < 100 and b > 100:
        return "purple"
    else:
        return f"rgb({r},{g},{b})"

def handle_color_analysis(image_path: str, prompt: str) -> VisionResult:
    """Handle color-related queries (Tier 0)."""
    start = datetime.now()
    analysis = analyze_image_basic(image_path)

    colors = [get_dominant_color_name(c) for c in analysis.dominant_colors[:3]]
    unique_colors = list(dict.fromkeys(colors))  # Remove duplicates, keep order

    if len(unique_colors) == 1:
        response = f"The image is primarily {unique_colors[0]}."
    else:
        response = f"The dominant colors are: {', '.join(unique_colors)}."

    return VisionResult(
        success=True,
        response=response,
        tier_used=VisionTier.ZERO_COST,
        task_type=TaskType.COLOR,
        processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
        confidence=0.9,
        metadata={"colors": unique_colors, "analysis": "PIL"}
    )

def handle_ocr(image_path: str, prompt: str) -> VisionResult:
    """Handle OCR using Apple Vision (Tier 0)."""
    start = datetime.now()

    try:
        from apple_ocr import extract_text
        result = extract_text(image_path)

        if result.get("success"):
            text = result.get("text", "")
            response = text if text else "No text found in image."
            return VisionResult(
                success=True,
                response=response,
                tier_used=VisionTier.ZERO_COST,
                task_type=TaskType.OCR,
                processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
                confidence=1.0,
                metadata={"lines": result.get("lines", []), "engine": "apple_vision"}
            )
    except Exception as e:
        logger.warning(f"Apple Vision OCR failed: {e}")

    # Fallback to VLM
    return None  # Signal to try next tier

# ============================================================================
# TIER 1: LIGHTWEIGHT HANDLERS
# ============================================================================

def handle_basic_describe(image_path: str, prompt: str) -> VisionResult:
    """Quick description using basic analysis + heuristics."""
    start = datetime.now()
    analysis = analyze_image_basic(image_path)

    # Build basic description from analysis
    colors = [get_dominant_color_name(c) for c in analysis.dominant_colors[:2]]

    parts = []
    parts.append(f"A {analysis.width}x{analysis.height} image")

    if analysis.has_text:
        parts.append("that appears to contain text")

    if analysis.brightness < 0.3:
        parts.append("with dark tones")
    elif analysis.brightness > 0.7:
        parts.append("with bright/light tones")

    if colors:
        parts.append(f"featuring {colors[0]} as the dominant color")

    response = " ".join(parts) + "."

    # This is a quick estimate - flag for potential VLM followup
    return VisionResult(
        success=True,
        response=response,
        tier_used=VisionTier.LIGHTWEIGHT,
        task_type=TaskType.BASIC_DESCRIBE,
        processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
        confidence=0.5,  # Low confidence - basic analysis only
        metadata={"analysis": analysis.__dict__, "note": "Basic analysis only"}
    )

def handle_face_detection(image_path: str, prompt: str) -> VisionResult:
    """Face detection using CoreML/Vision (Tier 1)."""
    start = datetime.now()

    try:
        import Vision
        import Quartz
        from Foundation import NSURL

        image_url = NSURL.fileURLWithPath_(image_path)
        image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)
        cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)

        request = Vision.VNDetectFaceRectanglesRequest.alloc().init()
        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        handler.performRequests_error_([request], None)

        results = request.results()
        face_count = len(results) if results else 0

        if face_count == 0:
            response = "No faces detected in the image."
        elif face_count == 1:
            response = "1 face detected in the image."
        else:
            response = f"{face_count} faces detected in the image."

        return VisionResult(
            success=True,
            response=response,
            tier_used=VisionTier.LIGHTWEIGHT,
            task_type=TaskType.FACE_DETECT,
            processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
            confidence=0.95,
            metadata={"face_count": face_count, "engine": "apple_vision"}
        )
    except Exception as e:
        logger.warning(f"Face detection failed: {e}")
        return None

# ============================================================================
# TIER 2: LOCAL VLM
# ============================================================================

def handle_vlm(image_path: str, prompt: str, task_type: TaskType) -> VisionResult:
    """Handle with local VLM (nanoLLaVA)."""
    start = datetime.now()

    try:
        # Try vision server first
        import requests
        try:
            health = requests.get("http://localhost:8766/health", timeout=2)
            if health.status_code == 200:
                response = requests.post(
                    "http://localhost:8766/process",
                    json={"image_path": image_path, "prompt": prompt},
                    timeout=120
                )
                result = response.json()
                if result.get("success"):
                    return VisionResult(
                        success=True,
                        response=result.get("response", ""),
                        tier_used=VisionTier.LOCAL_VLM,
                        task_type=task_type,
                        processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
                        confidence=0.75,
                        metadata={"via": "vision_server"}
                    )
        except:
            pass

        # Fallback to CLI
        import subprocess
        cmd = f'''python3 -m mlx_vlm generate \
            --model "mlx-community/nanoLLaVA-1.5-bf16" \
            --image "{image_path}" \
            --prompt '{prompt.replace("'", "'")}' \
            --max-tokens 150'''

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            output = result.stdout
            # Parse response
            if "<|im_start|>assistant" in output:
                response = output.split("<|im_start|>assistant")[1].split("=====")[0].strip()
            else:
                response = output.strip()

            return VisionResult(
                success=True,
                response=response,
                tier_used=VisionTier.LOCAL_VLM,
                task_type=task_type,
                processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
                confidence=0.75,
                metadata={"via": "cli"}
            )
    except Exception as e:
        logger.error(f"VLM failed: {e}")

    return None

# ============================================================================
# TIER 3: CLAUDE ESCALATION
# ============================================================================

def handle_claude_escalation(image_path: str, prompt: str, task_type: TaskType) -> VisionResult:
    """Escalate complex vision tasks to Claude via dual terminal bridge."""
    start = datetime.now()

    try:
        # Import the escalation handler
        from escalation_handler import escalate_to_claude

        # Prepare vision prompt for Claude
        vision_prompt = f"""I'm analyzing an image and need help with a complex vision task.

Image location: {image_path}
Task type: {task_type.value}
User request: {prompt}

Please analyze this image and provide a detailed response. Focus on:
1. What you can see in the image
2. Specific details relevant to the user's question
3. Any insights or observations

Note: The image should be visible in your context."""

        # Escalate via the dual terminal bridge
        result = escalate_to_claude(vision_prompt, include_image=image_path)

        if result.get("success"):
            return VisionResult(
                success=True,
                response=result.get("response", ""),
                tier_used=VisionTier.CLAUDE,
                task_type=task_type,
                processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
                confidence=0.95,
                metadata={"via": "dual_terminal_bridge", "escalated": True}
            )
    except ImportError:
        logger.warning("Escalation handler not available")
    except Exception as e:
        logger.error(f"Claude escalation failed: {e}")

    return None

# ============================================================================
# SMART ROUTER
# ============================================================================

class SmartVisionRouter:
    """Intelligent routing of vision tasks to appropriate tier."""

    def __init__(self):
        self.memory = VisionMemory()

    def classify_task(self, prompt: str) -> TaskType:
        """Classify what type of vision task this is."""
        prompt_lower = prompt.lower()

        # Check keywords for each task type
        scores = {}
        for task_type, keywords in TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scores[task_type] = score

        if scores:
            # Return highest scoring task type
            return max(scores, key=scores.get)

        # Default to basic describe
        return TaskType.BASIC_DESCRIBE

    def get_tier_for_task(self, task_type: TaskType) -> VisionTier:
        """Get the appropriate tier for a task type."""
        return TASK_ROUTING.get(task_type, VisionTier.LOCAL_VLM)

    def process(self, image_path: str, prompt: str,
                force_tier: VisionTier = None,
                skip_cache: bool = False) -> VisionResult:
        """
        Process a vision request with smart routing.

        Args:
            image_path: Path to image
            prompt: User's question/request
            force_tier: Override automatic tier selection
            skip_cache: Bypass cache lookup

        Returns:
            VisionResult with response and metadata
        """
        start = datetime.now()

        # Get image hash for caching
        analysis = analyze_image_basic(image_path)
        image_hash = analysis.hash

        # Classify task
        task_type = self.classify_task(prompt)
        target_tier = force_tier or self.get_tier_for_task(task_type)

        logger.info(f"Task: {task_type.value}, Tier: {target_tier.name}")

        # Check cache
        if not skip_cache:
            cached = self.memory.get_cached(image_hash, task_type.value)
            if cached:
                logger.info("Cache hit!")
                return VisionResult(
                    success=True,
                    response=cached["response"],
                    tier_used=VisionTier(cached["tier_used"]),
                    task_type=task_type,
                    processing_time_ms=1,
                    confidence=cached["confidence"],
                    from_cache=True,
                    metadata={"cached_at": cached["created_at"]}
                )

        # Process through tiers
        result = None

        # Tier 0: Zero-cost handlers
        if target_tier == VisionTier.ZERO_COST or result is None:
            if task_type == TaskType.OCR:
                result = handle_ocr(image_path, prompt)
            elif task_type == TaskType.COLOR:
                result = handle_color_analysis(image_path, prompt)

        # Tier 1: Lightweight handlers
        if target_tier.value >= VisionTier.LIGHTWEIGHT.value and result is None:
            if task_type == TaskType.FACE_DETECT:
                result = handle_face_detection(image_path, prompt)
            elif task_type == TaskType.BASIC_DESCRIBE:
                result = handle_basic_describe(image_path, prompt)

        # Tier 2: Local VLM
        if target_tier.value >= VisionTier.LOCAL_VLM.value and result is None:
            result = handle_vlm(image_path, prompt, task_type)

        # Tier 3: Claude escalation
        if target_tier == VisionTier.CLAUDE and result is None:
            result = handle_claude_escalation(image_path, prompt, task_type)

        # Final fallback
        if result is None:
            result = VisionResult(
                success=False,
                response="Unable to process image with any available tier.",
                tier_used=target_tier,
                task_type=task_type,
                processing_time_ms=int((datetime.now() - start).total_seconds() * 1000),
                confidence=0.0
            )

        # Cache successful results
        if result.success and not result.from_cache:
            self.memory.cache_result(
                image_hash, task_type.value, prompt,
                result.response, result.tier_used.value, result.confidence
            )

        return result

    def progressive_analyze(self, image_path: str, prompt: str) -> Dict:
        """
        Progressive analysis: quick first, detailed on demand.

        Returns initial quick result with option to get detailed analysis.
        """
        # Stage 1: Quick analysis (Tier 0-1)
        quick_result = self.process(image_path, prompt, force_tier=VisionTier.LIGHTWEIGHT)

        return {
            "quick_result": quick_result,
            "quick_confidence": quick_result.confidence,
            "detailed_available": quick_result.confidence < 0.8,
            "get_detailed": lambda: self.process(image_path, prompt, force_tier=VisionTier.LOCAL_VLM)
        }


# ============================================================================
# PUBLIC API
# ============================================================================

# Singleton router
_router: Optional[SmartVisionRouter] = None

def get_router() -> SmartVisionRouter:
    """Get the smart vision router instance."""
    global _router
    if _router is None:
        _router = SmartVisionRouter()
    return _router

def smart_process(image_path: str, prompt: str, **kwargs) -> VisionResult:
    """Process an image with smart routing."""
    return get_router().process(image_path, prompt, **kwargs)

def quick_analyze(image_path: str) -> ImageAnalysis:
    """Get quick analysis of an image (instant, no ML)."""
    return analyze_image_basic(image_path)

def get_vision_stats() -> Dict:
    """Get vision system statistics."""
    router = get_router()
    return {
        "cache": router.memory.get_stats(),
        "tiers": [t.name for t in VisionTier],
        "task_types": [t.value for t in TaskType]
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python smart_vision.py <image_path> <prompt>")
        print("\nExample:")
        print("  python smart_vision.py /tmp/test.png 'What color is this?'")
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = " ".join(sys.argv[2:])

    result = smart_process(image_path, prompt)

    print(f"\nTask Type: {result.task_type.value}")
    print(f"Tier Used: {result.tier_used.name}")
    print(f"Confidence: {result.confidence}")
    print(f"Time: {result.processing_time_ms}ms")
    print(f"From Cache: {result.from_cache}")
    print(f"\nResponse:\n{result.response}")
