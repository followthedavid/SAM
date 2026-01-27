#!/usr/bin/env python3
"""
SAM Image Preprocessor - Memory-efficient image preprocessing for vision models

Optimizes images before analysis:
- Resizes large images (>2048px) to save memory
- Converts formats if needed
- Creates temp processed versions (preserves originals)
- Estimates memory requirements

Designed for 8GB M2 Mac Mini constraint.

Created: 2026-01-25
Version: 1.0.0
"""

import os
import sys
import hashlib
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, Union
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_preprocessor")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default max dimension for images (width or height)
DEFAULT_MAX_SIZE = 2048

# Vision model memory estimates (bytes per pixel for different processing stages)
# These are conservative estimates for 8GB RAM constraint
MEMORY_ESTIMATES = {
    "raw_pixels": 3,           # RGB bytes per pixel
    "rgba_pixels": 4,          # RGBA bytes per pixel
    "float_tensor": 12,        # 3 channels * 4 bytes/float
    "model_overhead": 1.5,     # Additional overhead multiplier for model processing
    "batch_overhead": 2.0,     # Extra for batched operations
}

# Supported input formats
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

# Output format for processed images (JPEG for smaller size, PNG for quality)
DEFAULT_OUTPUT_FORMAT = "JPEG"
LOSSLESS_OUTPUT_FORMAT = "PNG"

# JPEG quality for compressed output
JPEG_QUALITY = 85

# Temp directory for processed images
TEMP_DIR = Path(tempfile.gettempdir()) / "sam_vision"


# ============================================================================
# DATA MODELS
# ============================================================================

class ImageFormat(Enum):
    """Supported image formats"""
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"
    TIFF = "tiff"
    UNKNOWN = "unknown"


@dataclass
class ImageInfo:
    """Information about an image file"""
    path: str
    width: int
    height: int
    format: ImageFormat
    mode: str  # PIL mode: RGB, RGBA, L, etc.
    file_size_bytes: int
    has_alpha: bool
    needs_resize: bool
    estimated_memory_bytes: int

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "format": self.format.value,
            "mode": self.mode,
            "file_size_bytes": self.file_size_bytes,
            "has_alpha": self.has_alpha,
            "needs_resize": self.needs_resize,
            "estimated_memory_bytes": self.estimated_memory_bytes,
            "estimated_memory_mb": round(self.estimated_memory_bytes / (1024 * 1024), 2),
        }


@dataclass
class PreprocessResult:
    """Result from image preprocessing"""
    original_path: str
    processed_path: str
    original_size: Tuple[int, int]  # (width, height)
    processed_size: Tuple[int, int]
    was_resized: bool
    was_converted: bool
    original_format: ImageFormat
    output_format: str
    processing_time_ms: int
    memory_saved_bytes: int

    def to_dict(self) -> Dict:
        return {
            "original_path": self.original_path,
            "processed_path": self.processed_path,
            "original_size": self.original_size,
            "processed_size": self.processed_size,
            "was_resized": self.was_resized,
            "was_converted": self.was_converted,
            "original_format": self.original_format.value,
            "output_format": self.output_format,
            "processing_time_ms": self.processing_time_ms,
            "memory_saved_bytes": self.memory_saved_bytes,
            "memory_saved_mb": round(self.memory_saved_bytes / (1024 * 1024), 2),
        }


# ============================================================================
# IMAGE PREPROCESSOR
# ============================================================================

class ImagePreprocessor:
    """
    Preprocesses images for optimal vision model performance.

    Features:
    - Resizes large images to save memory
    - Converts unsupported formats
    - Preserves original files
    - Caches processed results
    - Estimates memory requirements
    """

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        jpeg_quality: int = JPEG_QUALITY,
        cache_dir: Optional[Path] = None,
    ):
        """
        Args:
            max_size: Maximum dimension (width or height) for images
            output_format: Output format for processed images (JPEG or PNG)
            jpeg_quality: Quality for JPEG compression (1-100)
            cache_dir: Directory for cached processed images
        """
        self.max_size = max_size
        self.output_format = output_format
        self.jpeg_quality = jpeg_quality
        self.cache_dir = cache_dir or TEMP_DIR

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Track processed files for cleanup
        self._processed_files: Dict[str, str] = {}  # original_hash -> processed_path

        # Lazy load PIL
        self._pil_available: Optional[bool] = None

    @property
    def pil_available(self) -> bool:
        """Check if PIL/Pillow is available"""
        if self._pil_available is None:
            try:
                from PIL import Image
                self._pil_available = True
            except ImportError:
                self._pil_available = False
                logger.warning("PIL/Pillow not available. Install with: pip install Pillow")
        return self._pil_available

    def get_image_info(self, path: Union[str, Path]) -> ImageInfo:
        """
        Get information about an image file.

        Args:
            path: Path to image file

        Returns:
            ImageInfo with size, format, and memory estimates
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        if not self.pil_available:
            raise RuntimeError("PIL/Pillow required for image info")

        from PIL import Image

        file_size = path.stat().st_size

        with Image.open(path) as img:
            width, height = img.size
            mode = img.mode

            # Detect format
            img_format = self._detect_format(path, img.format)

            # Check for alpha channel
            has_alpha = mode in ("RGBA", "LA", "PA") or (
                mode == "P" and "transparency" in img.info
            )

            # Check if resize needed
            needs_resize = width > self.max_size or height > self.max_size

            # Estimate memory for vision model processing
            estimated_memory = self.estimate_memory_needed(path, (width, height), has_alpha)

        return ImageInfo(
            path=str(path),
            width=width,
            height=height,
            format=img_format,
            mode=mode,
            file_size_bytes=file_size,
            has_alpha=has_alpha,
            needs_resize=needs_resize,
            estimated_memory_bytes=estimated_memory,
        )

    def estimate_memory_needed(
        self,
        path: Union[str, Path],
        size: Optional[Tuple[int, int]] = None,
        has_alpha: Optional[bool] = None,
    ) -> int:
        """
        Estimate memory needed for vision model processing.

        Args:
            path: Path to image (used to get size if not provided)
            size: Optional (width, height) tuple
            has_alpha: Whether image has alpha channel

        Returns:
            Estimated memory in bytes
        """
        if size is None:
            if not self.pil_available:
                # Rough estimate without PIL - assume 4K image
                return 4096 * 4096 * 12 * 2  # ~400MB worst case

            from PIL import Image
            with Image.open(path) as img:
                size = img.size
                has_alpha = img.mode in ("RGBA", "LA", "PA")

        width, height = size
        pixels = width * height

        # Calculate memory stages
        bytes_per_pixel = MEMORY_ESTIMATES["rgba_pixels"] if has_alpha else MEMORY_ESTIMATES["raw_pixels"]
        raw_memory = pixels * bytes_per_pixel

        # Float tensor representation (for model input)
        tensor_memory = pixels * MEMORY_ESTIMATES["float_tensor"]

        # Add model overhead
        total_memory = int((raw_memory + tensor_memory) * MEMORY_ESTIMATES["model_overhead"])

        return total_memory

    def preprocess_image(
        self,
        path: Union[str, Path],
        max_size: Optional[int] = None,
        force_format: Optional[str] = None,
        preserve_alpha: bool = False,
    ) -> str:
        """
        Preprocess an image for vision model input.

        Args:
            path: Path to original image
            max_size: Override default max size
            force_format: Force specific output format
            preserve_alpha: Keep alpha channel (uses PNG output)

        Returns:
            Path to processed image (may be same as input if no changes needed)
        """
        result = self.preprocess_image_detailed(path, max_size, force_format, preserve_alpha)
        return result.processed_path

    def preprocess_image_detailed(
        self,
        path: Union[str, Path],
        max_size: Optional[int] = None,
        force_format: Optional[str] = None,
        preserve_alpha: bool = False,
    ) -> PreprocessResult:
        """
        Preprocess an image with detailed result information.

        Args:
            path: Path to original image
            max_size: Override default max size
            force_format: Force specific output format
            preserve_alpha: Keep alpha channel (uses PNG output)

        Returns:
            PreprocessResult with details about processing
        """
        from datetime import datetime
        start_time = datetime.now()

        path = Path(path)
        max_size = max_size or self.max_size

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        if not self.pil_available:
            raise RuntimeError("PIL/Pillow required for preprocessing")

        from PIL import Image

        # Check cache
        cache_key = self._get_cache_key(path, max_size, force_format, preserve_alpha)
        if cache_key in self._processed_files:
            cached_path = self._processed_files[cache_key]
            if Path(cached_path).exists():
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                with Image.open(path) as orig:
                    orig_size = orig.size
                with Image.open(cached_path) as proc:
                    proc_size = proc.size
                return PreprocessResult(
                    original_path=str(path),
                    processed_path=cached_path,
                    original_size=orig_size,
                    processed_size=proc_size,
                    was_resized=orig_size != proc_size,
                    was_converted=True,
                    original_format=self._detect_format(path),
                    output_format=force_format or self.output_format,
                    processing_time_ms=processing_time,
                    memory_saved_bytes=self._calc_memory_saved(orig_size, proc_size),
                )

        with Image.open(path) as img:
            original_size = img.size
            original_format = self._detect_format(path, img.format)
            original_mode = img.mode

            width, height = img.size
            needs_resize = width > max_size or height > max_size

            # Determine output format
            if force_format:
                output_format = force_format.upper()
            elif preserve_alpha and img.mode in ("RGBA", "LA", "PA"):
                output_format = LOSSLESS_OUTPUT_FORMAT
            else:
                output_format = self.output_format

            # Check if we need to process at all
            needs_conversion = self._needs_format_conversion(path, output_format, img.mode)

            if not needs_resize and not needs_conversion:
                # No processing needed - return original
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return PreprocessResult(
                    original_path=str(path),
                    processed_path=str(path),
                    original_size=original_size,
                    processed_size=original_size,
                    was_resized=False,
                    was_converted=False,
                    original_format=original_format,
                    output_format=original_format.value.upper(),
                    processing_time_ms=processing_time,
                    memory_saved_bytes=0,
                )

            # Process the image
            processed_img = img.copy()

            # Resize if needed
            if needs_resize:
                processed_img = self._resize_image(processed_img, max_size)

            # Convert mode if needed for output format
            if output_format == "JPEG" and processed_img.mode in ("RGBA", "LA", "PA", "P"):
                # JPEG doesn't support alpha - convert to RGB
                if processed_img.mode == "P":
                    processed_img = processed_img.convert("RGBA")
                if processed_img.mode in ("RGBA", "LA"):
                    # Composite onto white background
                    background = Image.new("RGB", processed_img.size, (255, 255, 255))
                    if processed_img.mode == "RGBA":
                        background.paste(processed_img, mask=processed_img.split()[3])
                    else:
                        background.paste(processed_img.convert("RGBA"),
                                       mask=processed_img.split()[1])
                    processed_img = background
                elif processed_img.mode != "RGB":
                    processed_img = processed_img.convert("RGB")

            # Generate output path
            output_ext = ".jpg" if output_format == "JPEG" else ".png"
            output_path = self.cache_dir / f"processed_{cache_key}{output_ext}"

            # Save processed image
            save_kwargs = {}
            if output_format == "JPEG":
                save_kwargs["quality"] = self.jpeg_quality
                save_kwargs["optimize"] = True
            elif output_format == "PNG":
                save_kwargs["optimize"] = True

            processed_img.save(output_path, format=output_format, **save_kwargs)
            processed_size = processed_img.size

            # Cache the result
            self._processed_files[cache_key] = str(output_path)

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        memory_saved = self._calc_memory_saved(original_size, processed_size)

        logger.info(
            f"Preprocessed {path.name}: {original_size} -> {processed_size}, "
            f"saved ~{memory_saved // (1024*1024)}MB memory"
        )

        return PreprocessResult(
            original_path=str(path),
            processed_path=str(output_path),
            original_size=original_size,
            processed_size=processed_size,
            was_resized=needs_resize,
            was_converted=True,
            original_format=original_format,
            output_format=output_format,
            processing_time_ms=processing_time,
            memory_saved_bytes=memory_saved,
        )

    def _resize_image(self, img, max_size: int):
        """Resize image while maintaining aspect ratio"""
        from PIL import Image

        width, height = img.size

        # Calculate new size maintaining aspect ratio
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))

        # Use high-quality resampling
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _detect_format(self, path: Path, pil_format: Optional[str] = None) -> ImageFormat:
        """Detect image format from file extension or PIL format"""
        if pil_format:
            fmt_lower = pil_format.lower()
            if fmt_lower in ("jpeg", "jpg"):
                return ImageFormat.JPEG
            elif fmt_lower == "png":
                return ImageFormat.PNG
            elif fmt_lower == "gif":
                return ImageFormat.GIF
            elif fmt_lower == "bmp":
                return ImageFormat.BMP
            elif fmt_lower == "webp":
                return ImageFormat.WEBP
            elif fmt_lower in ("tiff", "tif"):
                return ImageFormat.TIFF

        # Fall back to extension
        ext = Path(path).suffix.lower()
        if ext in (".jpg", ".jpeg"):
            return ImageFormat.JPEG
        elif ext == ".png":
            return ImageFormat.PNG
        elif ext == ".gif":
            return ImageFormat.GIF
        elif ext == ".bmp":
            return ImageFormat.BMP
        elif ext == ".webp":
            return ImageFormat.WEBP
        elif ext in (".tiff", ".tif"):
            return ImageFormat.TIFF

        return ImageFormat.UNKNOWN

    def _needs_format_conversion(self, path: Path, output_format: str, mode: str) -> bool:
        """Check if format conversion is needed"""
        current_format = self._detect_format(path)

        # Check if format matches
        if output_format == "JPEG" and current_format == ImageFormat.JPEG:
            # Already JPEG, but might need mode conversion
            return mode not in ("RGB", "L")
        elif output_format == "PNG" and current_format == ImageFormat.PNG:
            return False

        return True

    def _get_cache_key(
        self,
        path: Path,
        max_size: int,
        force_format: Optional[str],
        preserve_alpha: bool,
    ) -> str:
        """Generate cache key for processed image"""
        # Use file path + mtime + processing params for cache key
        stat = path.stat()
        key_data = f"{path}:{stat.st_mtime}:{max_size}:{force_format}:{preserve_alpha}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]

    def _calc_memory_saved(
        self,
        original_size: Tuple[int, int],
        processed_size: Tuple[int, int],
    ) -> int:
        """Calculate estimated memory saved by resizing"""
        orig_pixels = original_size[0] * original_size[1]
        proc_pixels = processed_size[0] * processed_size[1]

        # Estimate using float tensor memory (main memory consumer)
        orig_memory = orig_pixels * MEMORY_ESTIMATES["float_tensor"] * MEMORY_ESTIMATES["model_overhead"]
        proc_memory = proc_pixels * MEMORY_ESTIMATES["float_tensor"] * MEMORY_ESTIMATES["model_overhead"]

        return int(orig_memory - proc_memory)

    def cleanup_cache(self, max_age_hours: int = 24):
        """
        Clean up old cached files.

        Args:
            max_age_hours: Remove files older than this
        """
        import time

        cutoff = time.time() - (max_age_hours * 3600)
        removed_count = 0

        for file_path in self.cache_dir.glob("processed_*"):
            if file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                    removed_count += 1
                except OSError as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")

        # Clear stale cache entries
        self._processed_files = {
            k: v for k, v in self._processed_files.items()
            if Path(v).exists()
        }

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} cached images")

    def clear_cache(self):
        """Clear all cached processed images"""
        for file_path in self.cache_dir.glob("processed_*"):
            try:
                file_path.unlink()
            except OSError:
                pass
        self._processed_files.clear()
        logger.info("Cache cleared")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global preprocessor instance
_preprocessor: Optional[ImagePreprocessor] = None


def get_preprocessor() -> ImagePreprocessor:
    """Get global preprocessor instance (lazy initialization)"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = ImagePreprocessor()
    return _preprocessor


def preprocess_image(
    path: Union[str, Path],
    max_size: int = DEFAULT_MAX_SIZE,
) -> str:
    """
    Preprocess an image for vision model input.

    Args:
        path: Path to original image
        max_size: Maximum dimension (default 2048)

    Returns:
        Path to processed image
    """
    return get_preprocessor().preprocess_image(path, max_size=max_size)


def get_image_info(path: Union[str, Path]) -> Dict:
    """
    Get information about an image.

    Args:
        path: Path to image

    Returns:
        Dict with image info (size, format, memory estimate)
    """
    return get_preprocessor().get_image_info(path).to_dict()


def estimate_memory_needed(path: Union[str, Path]) -> int:
    """
    Estimate memory needed to process an image.

    Args:
        path: Path to image

    Returns:
        Estimated memory in bytes
    """
    return get_preprocessor().estimate_memory_needed(path)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="SAM Image Preprocessor")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get image info")
    info_parser.add_argument("image", help="Path to image")

    # Preprocess command
    preprocess_parser = subparsers.add_parser("preprocess", help="Preprocess image")
    preprocess_parser.add_argument("image", help="Path to image")
    preprocess_parser.add_argument("--max-size", type=int, default=DEFAULT_MAX_SIZE,
                                   help=f"Max dimension (default: {DEFAULT_MAX_SIZE})")
    preprocess_parser.add_argument("--format", choices=["JPEG", "PNG"],
                                   help="Force output format")
    preprocess_parser.add_argument("--preserve-alpha", action="store_true",
                                   help="Preserve alpha channel")

    # Memory estimate command
    memory_parser = subparsers.add_parser("memory", help="Estimate memory needed")
    memory_parser.add_argument("image", help="Path to image")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up cache")
    cleanup_parser.add_argument("--max-age", type=int, default=24,
                               help="Max age in hours (default: 24)")

    args = parser.parse_args()

    if args.command == "info":
        info = get_image_info(args.image)
        print(json.dumps(info, indent=2))

    elif args.command == "preprocess":
        preprocessor = get_preprocessor()
        result = preprocessor.preprocess_image_detailed(
            args.image,
            max_size=args.max_size,
            force_format=args.format,
            preserve_alpha=args.preserve_alpha,
        )
        print(json.dumps(result.to_dict(), indent=2))

    elif args.command == "memory":
        memory = estimate_memory_needed(args.image)
        print(f"Estimated memory: {memory:,} bytes ({memory / (1024*1024):.2f} MB)")

    elif args.command == "cleanup":
        preprocessor = get_preprocessor()
        preprocessor.cleanup_cache(max_age_hours=args.max_age)
        print("Cache cleaned")

    else:
        parser.print_help()
