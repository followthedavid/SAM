#!/usr/bin/env python3
"""
SAM Voice Cache - Cache TTS output for improved performance.

Task 6.2.2: Implement TTS caching with LRU eviction.

Features:
- Cache key: hash(text + voice + settings)
- Storage: ~/.sam/voice_cache/ (WAV/AIFF files)
- LRU eviction when max size exceeded
- Pre-compute SAM's common phrases
- Background cleanup of old entries

Usage:
    from voice_cache import VoiceCache

    cache = VoiceCache()

    # Check for cached audio
    audio_path = cache.get(text, voice="Daniel", rate=180)
    if not audio_path:
        # Generate and cache
        audio_path = generate_tts(text)
        cache.put(text, audio_path, voice="Daniel", rate=180)

    # Precompute common phrases
    cache.precompute_common(tts_function)
"""

import os
import sys
import json
import hashlib
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from collections import OrderedDict


# Default cache location
DEFAULT_CACHE_DIR = Path.home() / ".sam" / "voice_cache"

# Maximum cache size in bytes (500MB default)
DEFAULT_MAX_CACHE_SIZE = 500 * 1024 * 1024

# Cache entry max age (7 days)
DEFAULT_MAX_AGE_DAYS = 7


@dataclass
class CacheEntry:
    """Metadata for a cached audio file."""
    key: str
    text: str
    voice: str
    settings: Dict[str, Any]
    audio_path: str
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "text": self.text,
            "voice": self.voice,
            "settings": self.settings,
            "audio_path": self.audio_path,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        return cls(
            key=data["key"],
            text=data["text"],
            voice=data["voice"],
            settings=data.get("settings", {}),
            audio_path=data["audio_path"],
            size_bytes=data["size_bytes"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 1)
        )


class VoiceCache:
    """
    LRU cache for TTS audio files.

    Stores generated audio to avoid re-synthesis of repeated phrases.
    Uses hash(text + voice + settings) as cache key.
    """

    # SAM's common phrases for precomputation
    SAM_COMMON_PHRASES = [
        # Greetings and acknowledgments
        "Hey there!",
        "Hey David.",
        "Sure thing!",
        "On it.",
        "Done.",
        "Got it.",
        "Understood.",
        "Roger that.",
        "Absolutely.",
        "No problem.",
        "You got it.",
        "Consider it done.",

        # Status updates
        "Let me check.",
        "Working on it.",
        "Almost there.",
        "Here's what I found.",
        "I'm analyzing that now.",
        "Give me a second.",
        "Just a moment.",
        "Processing...",

        # Responses
        "Interesting.",
        "That looks good to me.",
        "I see a few issues here.",
        "Let me dig deeper.",
        "I've got some thoughts on that.",

        # Build/code related
        "The build was successful.",
        "Tests are passing.",
        "All tests passed.",
        "Build failed. Let me check the errors.",
        "Found the issue.",
        "Fixed it.",
        "Pushed the changes.",
        "Ready for review.",

        # Conversation
        "What's up?",
        "How can I help?",
        "Ready when you are.",
        "Need more context on that.",
        "Could you be more specific?",
        "Tell me more.",
        "And then what happened?",

        # SAM personality
        "Trust me, I've got this.",
        "I'm pretty good at this, you know.",
        "Easy.",
        "Piece of cake.",
        "Watch and learn.",
        "That's my specialty.",
    ]

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_size_bytes: int = DEFAULT_MAX_CACHE_SIZE,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS
    ):
        """
        Initialize voice cache.

        Args:
            cache_dir: Directory to store cached audio files
            max_size_bytes: Maximum total cache size in bytes
            max_age_days: Maximum age for cache entries
        """
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.max_size_bytes = max_size_bytes
        self.max_age_days = max_age_days

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache metadata file
        self._metadata_file = self.cache_dir / "cache_metadata.json"

        # LRU ordered dict: key -> CacheEntry
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_size_bytes": 0
        }

        # Load existing cache metadata
        self._load_metadata()

    def _generate_key(
        self,
        text: str,
        voice: str = "default",
        **settings
    ) -> str:
        """
        Generate cache key from text, voice, and settings.

        Args:
            text: The text being synthesized
            voice: Voice name/ID
            **settings: Additional TTS settings (rate, pitch, etc.)

        Returns:
            SHA256 hash as cache key
        """
        # Normalize text (strip whitespace, lowercase for matching)
        normalized_text = text.strip().lower()

        # Build key components
        key_parts = [
            normalized_text,
            voice.lower(),
            json.dumps(settings, sort_keys=True)
        ]
        key_string = "|".join(key_parts)

        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    def get(
        self,
        text: str,
        voice: str = "default",
        **settings
    ) -> Optional[Path]:
        """
        Get cached audio for text.

        Args:
            text: The text to look up
            voice: Voice name/ID
            **settings: TTS settings used when generating

        Returns:
            Path to cached audio file, or None if not cached
        """
        key = self._generate_key(text, voice, **settings)

        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]
            audio_path = Path(entry.audio_path)

            # Verify file still exists
            if not audio_path.exists():
                # Remove stale entry
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            # Update access tracking (LRU)
            entry.last_accessed = datetime.now()
            entry.access_count += 1

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            self._stats["hits"] += 1
            return audio_path

    def put(
        self,
        text: str,
        audio_path: Path,
        voice: str = "default",
        copy_file: bool = True,
        **settings
    ) -> str:
        """
        Cache audio for text.

        Args:
            text: The text that was synthesized
            audio_path: Path to the audio file
            voice: Voice name/ID
            copy_file: If True, copy file to cache dir. If False, assume it's already there
            **settings: TTS settings used when generating

        Returns:
            Cache key
        """
        key = self._generate_key(text, voice, **settings)
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with self._lock:
            # Copy file to cache directory if needed
            if copy_file:
                cache_file = self.cache_dir / f"{key}{audio_path.suffix}"
                shutil.copy2(audio_path, cache_file)
                final_path = cache_file
            else:
                final_path = audio_path

            file_size = final_path.stat().st_size

            # Create cache entry
            entry = CacheEntry(
                key=key,
                text=text,
                voice=voice,
                settings=settings,
                audio_path=str(final_path),
                size_bytes=file_size,
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )

            # Add to cache
            self._cache[key] = entry
            self._cache.move_to_end(key)  # Most recently used
            self._stats["total_size_bytes"] += file_size

            # Evict if necessary
            self._evict_if_needed()

            # Save metadata periodically
            if len(self._cache) % 10 == 0:
                self._save_metadata()

            return key

    def contains(self, text: str, voice: str = "default", **settings) -> bool:
        """Check if text is cached."""
        key = self._generate_key(text, voice, **settings)
        with self._lock:
            if key in self._cache:
                path = Path(self._cache[key].audio_path)
                return path.exists()
            return False

    def remove(self, text: str, voice: str = "default", **settings) -> bool:
        """
        Remove cached audio for text.

        Returns:
            True if entry was removed, False if not found
        """
        key = self._generate_key(text, voice, **settings)

        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            audio_path = Path(entry.audio_path)

            # Remove file
            if audio_path.exists():
                audio_path.unlink()

            # Remove from cache
            self._stats["total_size_bytes"] -= entry.size_bytes
            del self._cache[key]

            return True

    def precompute_common(
        self,
        tts_function: Callable[[str], Path],
        voice: str = "default",
        phrases: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        **settings
    ) -> Dict[str, Any]:
        """
        Pre-compute and cache SAM's common phrases.

        Args:
            tts_function: Function(text) -> audio_path
            voice: Voice to use
            phrases: Custom phrases to precompute (uses default if None)
            progress_callback: Optional callback(current, total, phrase)
            **settings: TTS settings

        Returns:
            Dict with stats about precomputation
        """
        phrases = phrases or self.SAM_COMMON_PHRASES
        total = len(phrases)
        cached = 0
        generated = 0
        errors = 0

        for i, phrase in enumerate(phrases):
            if progress_callback:
                progress_callback(i + 1, total, phrase)

            # Skip if already cached
            if self.contains(phrase, voice, **settings):
                cached += 1
                continue

            try:
                # Generate audio
                audio_path = tts_function(phrase)
                if audio_path and Path(audio_path).exists():
                    self.put(phrase, audio_path, voice, **settings)
                    generated += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                print(f"Error precomputing '{phrase[:30]}...': {e}")

        # Save metadata after batch operation
        self._save_metadata()

        return {
            "total_phrases": total,
            "already_cached": cached,
            "newly_generated": generated,
            "errors": errors,
            "cache_size_bytes": self._stats["total_size_bytes"]
        }

    def cleanup(
        self,
        max_age_days: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Remove old/stale cache entries.

        Args:
            max_age_days: Override default max age
            dry_run: If True, report what would be removed without removing

        Returns:
            Stats about cleanup operation
        """
        max_age = max_age_days or self.max_age_days
        cutoff = datetime.now() - timedelta(days=max_age)

        removed = []
        bytes_freed = 0

        with self._lock:
            # Find entries to remove
            for key, entry in list(self._cache.items()):
                should_remove = False

                # Check age
                if entry.last_accessed < cutoff:
                    should_remove = True

                # Check if file exists
                if not Path(entry.audio_path).exists():
                    should_remove = True

                if should_remove:
                    if not dry_run:
                        audio_path = Path(entry.audio_path)
                        if audio_path.exists():
                            audio_path.unlink()
                        del self._cache[key]
                        self._stats["total_size_bytes"] -= entry.size_bytes

                    removed.append({
                        "key": key,
                        "text": entry.text[:50],
                        "size_bytes": entry.size_bytes,
                        "age_days": (datetime.now() - entry.last_accessed).days
                    })
                    bytes_freed += entry.size_bytes

            if not dry_run:
                self._save_metadata()

        return {
            "entries_removed": len(removed),
            "bytes_freed": bytes_freed,
            "dry_run": dry_run,
            "removed": removed if dry_run else None
        }

    def _evict_if_needed(self):
        """Evict least recently used entries if cache exceeds max size."""
        while self._stats["total_size_bytes"] > self.max_size_bytes and self._cache:
            # Remove least recently used (first item in OrderedDict)
            key, entry = self._cache.popitem(last=False)

            # Remove file
            audio_path = Path(entry.audio_path)
            if audio_path.exists():
                audio_path.unlink()

            self._stats["total_size_bytes"] -= entry.size_bytes
            self._stats["evictions"] += 1

    def _load_metadata(self):
        """Load cache metadata from file."""
        if not self._metadata_file.exists():
            return

        try:
            with open(self._metadata_file) as f:
                data = json.load(f)

            for entry_data in data.get("entries", []):
                try:
                    entry = CacheEntry.from_dict(entry_data)

                    # Verify file exists
                    if Path(entry.audio_path).exists():
                        self._cache[entry.key] = entry
                        self._stats["total_size_bytes"] += entry.size_bytes
                except Exception as e:
                    continue

            self._stats.update(data.get("stats", {}))

        except Exception as e:
            print(f"Warning: Could not load cache metadata: {e}")

    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            data = {
                "entries": [entry.to_dict() for entry in self._cache.values()],
                "stats": self._stats,
                "saved_at": datetime.now().isoformat()
            }

            with open(self._metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save cache metadata: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            hit_rate = 0
            total_requests = self._stats["hits"] + self._stats["misses"]
            if total_requests > 0:
                hit_rate = self._stats["hits"] / total_requests

            return {
                "entries": len(self._cache),
                "total_size_bytes": self._stats["total_size_bytes"],
                "total_size_mb": round(self._stats["total_size_bytes"] / (1024 * 1024), 2),
                "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
                "utilization_percent": round(
                    self._stats["total_size_bytes"] / self.max_size_bytes * 100, 1
                ) if self.max_size_bytes > 0 else 0,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate * 100, 1),
                "evictions": self._stats["evictions"],
                "cache_dir": str(self.cache_dir)
            }

    def list_entries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List cache entries (most recently used first)."""
        with self._lock:
            entries = []
            for key in reversed(list(self._cache.keys())[:limit]):
                entry = self._cache[key]
                entries.append({
                    "key": key,
                    "text": entry.text[:50] + "..." if len(entry.text) > 50 else entry.text,
                    "voice": entry.voice,
                    "size_kb": round(entry.size_bytes / 1024, 1),
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.strftime("%Y-%m-%d %H:%M")
                })
            return entries

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            for entry in self._cache.values():
                audio_path = Path(entry.audio_path)
                if audio_path.exists():
                    audio_path.unlink()

            self._cache.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "total_size_bytes": 0
            }
            self._save_metadata()


# Global instance
_cache: Optional[VoiceCache] = None


def get_cache() -> VoiceCache:
    """Get global voice cache instance."""
    global _cache
    if _cache is None:
        _cache = VoiceCache()
    return _cache


# CLI
def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Voice Cache")
    subparsers = parser.add_subparsers(dest="command")

    # stats command
    subparsers.add_parser("stats", help="Show cache statistics")

    # list command
    list_parser = subparsers.add_parser("list", help="List cache entries")
    list_parser.add_argument("--limit", "-n", type=int, default=20)

    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old entries")
    cleanup_parser.add_argument("--max-age", type=int, default=7, help="Max age in days")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed")

    # clear command
    subparsers.add_parser("clear", help="Clear all cache entries")

    # precompute command
    precompute_parser = subparsers.add_parser("precompute", help="Precompute common phrases")
    precompute_parser.add_argument("--voice", "-v", default="Daniel", help="Voice to use")

    args = parser.parse_args()

    cache = VoiceCache()

    if args.command == "stats":
        stats = cache.get_stats()
        print("Voice Cache Statistics")
        print("-" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif args.command == "list":
        entries = cache.list_entries(args.limit)
        print(f"Cache Entries ({len(entries)} shown):")
        print("-" * 60)
        for entry in entries:
            print(f"  {entry['text']}")
            print(f"    Voice: {entry['voice']} | Size: {entry['size_kb']}KB | "
                  f"Accesses: {entry['access_count']} | Last: {entry['last_accessed']}")

    elif args.command == "cleanup":
        result = cache.cleanup(max_age_days=args.max_age, dry_run=args.dry_run)
        print("Cleanup Results")
        print("-" * 40)
        print(f"  Entries removed: {result['entries_removed']}")
        print(f"  Bytes freed: {result['bytes_freed']} ({result['bytes_freed'] / 1024:.1f} KB)")
        if args.dry_run:
            print("\n  (Dry run - no files actually removed)")

    elif args.command == "clear":
        response = input("Are you sure you want to clear the cache? [y/N] ")
        if response.lower() == "y":
            cache.clear()
            print("Cache cleared.")
        else:
            print("Cancelled.")

    elif args.command == "precompute":
        import subprocess

        def tts_func(text: str) -> Path:
            import tempfile
            output = Path(tempfile.mktemp(suffix=".aiff"))
            subprocess.run(["say", "-v", args.voice, "-o", str(output), text],
                          capture_output=True, check=True)
            return output

        def progress(current, total, phrase):
            print(f"[{current}/{total}] {phrase[:40]}...")

        print(f"Precomputing common phrases with voice: {args.voice}")
        result = cache.precompute_common(tts_func, voice=args.voice, progress_callback=progress)
        print("\nResults:")
        print(f"  Already cached: {result['already_cached']}")
        print(f"  Newly generated: {result['newly_generated']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Cache size: {result['cache_size_bytes'] / 1024 / 1024:.1f} MB")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
