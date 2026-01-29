#!/usr/bin/env python3
"""
Apple Vision OCR - Fast, accurate text extraction using macOS built-in Vision framework.
Zero additional RAM, uses Apple Neural Engine via pyobjc.
"""

import json
from pathlib import Path


def extract_text(image_path: str) -> dict:
    """
    Extract text from image using Apple's Vision framework.
    Returns dict with success, text, confidence, and lines.
    """
    try:
        import Vision
        import Quartz
        from Foundation import NSURL

        image_path = str(Path(image_path).resolve())

        # Load image
        image_url = NSURL.fileURLWithPath_(image_path)
        image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)

        if not image_source:
            return {"success": False, "error": "Could not load image"}

        cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)

        if not cg_image:
            return {"success": False, "error": "Could not create CGImage"}

        # Create text recognition request
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)

        # Process image
        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        success = handler.performRequests_error_([request], None)

        if not success:
            return {"success": False, "error": "Vision request failed"}

        # Extract results
        results = request.results()
        if not results:
            return {"success": True, "text": "", "lines": [], "line_count": 0}

        lines = []
        full_text = []

        for observation in results:
            candidates = observation.topCandidates_(1)
            if candidates:
                text = candidates[0].string()
                confidence = candidates[0].confidence()
                lines.append({"text": text, "confidence": float(confidence)})
                full_text.append(text)

        return {
            "success": True,
            "text": "\n".join(full_text),
            "lines": lines,
            "line_count": len(lines)
        }

    except ImportError as e:
        return {"success": False, "error": f"Missing dependency: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_text_simple(image_path: str) -> str:
    """Simple wrapper that just returns the text or empty string."""
    result = extract_text(image_path)
    return result.get("text", "") if result.get("success") else ""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_text(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python3 apple_ocr.py <image_path>")
