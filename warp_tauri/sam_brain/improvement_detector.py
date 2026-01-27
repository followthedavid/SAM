#!/usr/bin/env python3
"""
SAM Improvement Detector - Scans for improvement opportunities across all projects.

Detects:
- Code quality issues (TODO, FIXME, HACK)
- Missing documentation and tests
- Integration gaps between projects
- Performance degradation patterns
- Reverse engineering opportunities
- Duplicate code across projects

Designed for exponential project growth with autonomous detection.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from evolution_tracker import (
    EvolutionTracker, Improvement, IMPROVEMENT_TYPES,
    generate_improvement_id, PROJECT_CATEGORIES
)

# Scan locations
PROJECT_ROOTS = [
    Path("/Users/davidquinton/ReverseLab/SAM"),
    Path("/Volumes/Plex/SSOT"),
    Path("/Volumes/Plex/SSOT/salvaged"),
]

SSOT_PATH = Path("/Volumes/Plex/SSOT")
OVERLAPS_FILE = SSOT_PATH / "PROJECT_OVERLAPS.md"

# File patterns to scan
CODE_EXTENSIONS = {".py", ".rs", ".swift", ".ts", ".js", ".sh", ".zsh"}
DOC_EXTENSIONS = {".md", ".txt", ".rst"}


@dataclass
class DetectedImprovement:
    """Raw detected improvement before being added to tracker."""
    project_id: str
    type: str
    priority: int
    description: str
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    context: Optional[str] = None
    auto_approve: bool = False


@dataclass
class ScanResult:
    """Result of a scan operation."""
    improvements: List[DetectedImprovement] = field(default_factory=list)
    projects_scanned: int = 0
    files_scanned: int = 0
    scan_duration: float = 0.0


class ImprovementDetector:
    """Scans for improvement opportunities across projects."""

    def __init__(self, tracker: EvolutionTracker = None):
        self.tracker = tracker or EvolutionTracker()
        self.seen_hashes: Set[str] = set()
        self._load_existing_improvements()

    def _load_existing_improvements(self):
        """Load hashes of existing improvements to avoid duplicates."""
        for status in ["detected", "validated", "queued", "implementing"]:
            for imp in self.tracker.get_improvements_by_status(status):
                self.seen_hashes.add(self._hash_improvement(imp.project_id, imp.description))

    def _hash_improvement(self, project_id: str, description: str) -> str:
        """Generate hash for deduplication."""
        return hashlib.md5(f"{project_id}:{description}".encode()).hexdigest()

    # =====================
    # MAIN SCAN METHODS
    # =====================

    def full_scan(self) -> ScanResult:
        """Run all detection scans."""
        start = datetime.now()
        result = ScanResult()

        # Run all detectors
        result.improvements.extend(self.scan_code_quality())
        result.improvements.extend(self.scan_integration_gaps())
        result.improvements.extend(self.scan_documentation_gaps())
        result.improvements.extend(self.scan_test_coverage())
        result.improvements.extend(self.scan_performance_patterns())
        result.improvements.extend(self.scan_reverse_engineering_opportunities())
        result.improvements.extend(self.scan_semantic_memory_patterns())

        # Deduplicate
        unique_improvements = self._deduplicate(result.improvements)

        # Add to tracker
        for imp in unique_improvements:
            self._add_improvement(imp)

        result.improvements = unique_improvements
        result.scan_duration = (datetime.now() - start).total_seconds()

        return result

    def _deduplicate(self, improvements: List[DetectedImprovement]) -> List[DetectedImprovement]:
        """Remove duplicate improvements."""
        unique = []
        for imp in improvements:
            hash_key = self._hash_improvement(imp.project_id, imp.description)
            if hash_key not in self.seen_hashes:
                self.seen_hashes.add(hash_key)
                unique.append(imp)
        return unique

    def _add_improvement(self, detected: DetectedImprovement):
        """Add detected improvement to tracker."""
        imp = Improvement(
            id=generate_improvement_id(detected.project_id, detected.description),
            project_id=detected.project_id,
            type=detected.type,
            priority=detected.priority,
            status="detected" if not detected.auto_approve else "queued",
            description=detected.description,
            detected_at=datetime.now().isoformat()
        )
        self.tracker.add_improvement(imp)

    # =====================
    # CODE QUALITY SCAN
    # =====================

    def scan_code_quality(self) -> List[DetectedImprovement]:
        """Scan for TODO, FIXME, HACK comments and code issues."""
        improvements = []

        patterns = {
            r"#\s*TODO[:\s]+(.+)": ("feature", 3, "TODO"),
            r"#\s*FIXME[:\s]+(.+)": ("reliability", 2, "FIXME"),
            r"#\s*HACK[:\s]+(.+)": ("efficiency", 2, "HACK"),
            r"#\s*XXX[:\s]+(.+)": ("reliability", 2, "XXX"),
            r"#\s*BUG[:\s]+(.+)": ("reliability", 1, "BUG"),
            r"//\s*TODO[:\s]+(.+)": ("feature", 3, "TODO"),
            r"//\s*FIXME[:\s]+(.+)": ("reliability", 2, "FIXME"),
        }

        for root in PROJECT_ROOTS:
            if not root.exists():
                continue

            for file_path in self._iter_code_files(root):
                project_id = self._detect_project(file_path)
                if not project_id:
                    continue

                try:
                    content = file_path.read_text(errors='ignore')
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for pattern, (imp_type, priority, label) in patterns.items():
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                description = f"[{label}] {match.group(1).strip()}"
                                improvements.append(DetectedImprovement(
                                    project_id=project_id,
                                    type=imp_type,
                                    priority=priority,
                                    description=description,
                                    source_file=str(file_path),
                                    line_number=line_num,
                                    context=line.strip()
                                ))
                except Exception:
                    continue

        return improvements

    # =====================
    # INTEGRATION GAPS SCAN
    # =====================

    def scan_integration_gaps(self) -> List[DetectedImprovement]:
        """Scan PROJECT_OVERLAPS.md for missing connections."""
        improvements = []

        if not OVERLAPS_FILE.exists():
            return improvements

        content = OVERLAPS_FILE.read_text()

        # Look for "Planned" or "Missing" integrations
        patterns = [
            (r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*Planned\s*\|", "integration"),
            (r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*Missing\s*\|", "integration"),
            (r"Missing Connection[s]?:?\s*([^\n]+)", "integration"),
        ]

        for pattern, imp_type in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                if len(match.groups()) >= 2:
                    source = match.group(1).strip()
                    target = match.group(2).strip()
                    description = f"Connect {source} to {target}"
                else:
                    description = f"Missing: {match.group(1).strip()}"

                # Determine project from context
                project_id = self._extract_project_from_text(description)

                improvements.append(DetectedImprovement(
                    project_id=project_id or "ORCHESTRATOR",
                    type=imp_type,
                    priority=2,
                    description=description,
                    source_file=str(OVERLAPS_FILE)
                ))

        return improvements

    # =====================
    # DOCUMENTATION GAPS
    # =====================

    def scan_documentation_gaps(self) -> List[DetectedImprovement]:
        """Detect missing documentation."""
        improvements = []

        for root in PROJECT_ROOTS:
            if not root.exists():
                continue

            for file_path in self._iter_code_files(root):
                project_id = self._detect_project(file_path)
                if not project_id:
                    continue

                if file_path.suffix == ".py":
                    improvements.extend(self._check_python_docs(file_path, project_id))

        return improvements

    def _check_python_docs(self, file_path: Path, project_id: str) -> List[DetectedImprovement]:
        """Check Python file for missing docstrings."""
        improvements = []

        try:
            content = file_path.read_text(errors='ignore')

            # Check for classes/functions without docstrings
            # Simple heuristic: def/class followed by line without quotes
            pattern = r'(def|class)\s+(\w+)[^:]+:\s*\n\s*(?!["\'])'
            for match in re.finditer(pattern, content):
                item_type = match.group(1)
                name = match.group(2)

                # Skip private/dunder methods
                if name.startswith('_') and not name.startswith('__'):
                    continue

                improvements.append(DetectedImprovement(
                    project_id=project_id,
                    type="documentation",
                    priority=3,
                    description=f"Missing docstring for {item_type} '{name}'",
                    source_file=str(file_path),
                    auto_approve=True
                ))
        except Exception:
            pass

        return improvements

    # =====================
    # TEST COVERAGE SCAN
    # =====================

    def scan_test_coverage(self) -> List[DetectedImprovement]:
        """Detect modules without tests."""
        improvements = []

        for root in PROJECT_ROOTS:
            if not root.exists():
                continue

            # Find Python files without corresponding test files
            for file_path in root.rglob("*.py"):
                if "test" in file_path.name.lower() or "tests" in str(file_path):
                    continue

                project_id = self._detect_project(file_path)
                if not project_id:
                    continue

                # Check if test file exists
                test_patterns = [
                    file_path.parent / f"test_{file_path.name}",
                    file_path.parent / "tests" / f"test_{file_path.name}",
                    file_path.parent.parent / "tests" / f"test_{file_path.name}",
                ]

                has_tests = any(p.exists() for p in test_patterns)

                if not has_tests:
                    improvements.append(DetectedImprovement(
                        project_id=project_id,
                        type="reliability",
                        priority=3,
                        description=f"No tests for {file_path.name}",
                        source_file=str(file_path),
                        auto_approve=True
                    ))

        return improvements

    # =====================
    # PERFORMANCE PATTERNS
    # =====================

    def scan_performance_patterns(self) -> List[DetectedImprovement]:
        """Detect potential performance issues."""
        improvements = []

        # Patterns that suggest performance issues
        perf_patterns = {
            r"for\s+\w+\s+in\s+\w+\s*:\s*\n\s*for\s+\w+\s+in": ("Nested loops detected", 3),
            r"\.append\([^)]+\)\s*$": ("Consider list comprehension", 3),
            r"import\s+\*": ("Wildcard import may slow startup", 3),
            r"time\.sleep\(\d{2,}\)": ("Long sleep detected", 2),
            r"while\s+True\s*:": ("Infinite loop - ensure exit condition", 2),
        }

        for root in PROJECT_ROOTS:
            if not root.exists():
                continue

            for file_path in self._iter_code_files(root):
                project_id = self._detect_project(file_path)
                if not project_id:
                    continue

                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern, (desc, priority) in perf_patterns.items():
                        if re.search(pattern, content):
                            improvements.append(DetectedImprovement(
                                project_id=project_id,
                                type="efficiency",
                                priority=priority,
                                description=f"{desc} in {file_path.name}",
                                source_file=str(file_path)
                            ))
                except Exception:
                    continue

        return improvements

    # =====================
    # REVERSE ENGINEERING SCAN
    # =====================

    def scan_reverse_engineering_opportunities(self) -> List[DetectedImprovement]:
        """Detect opportunities for reverse engineering improvements."""
        improvements = []

        # Look for binary files that could be analyzed
        binary_extensions = {".dylib", ".so", ".dll", ".exe", ".app", ".framework"}

        for root in PROJECT_ROOTS:
            if not root.exists():
                continue

            # Check for TODO comments mentioning reverse engineering
            for file_path in self._iter_code_files(root):
                try:
                    content = file_path.read_text(errors='ignore')

                    # Look for reverse engineering hints
                    re_patterns = [
                        r"#.*reverse\s*engineer",
                        r"#.*decompile",
                        r"#.*binary.*analysis",
                        r"#.*hook.*function",
                        r"#.*patch.*binary",
                        r"#.*inject",
                    ]

                    for pattern in re_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            project_id = self._detect_project(file_path)
                            improvements.append(DetectedImprovement(
                                project_id=project_id or "REVERSELAB",
                                type="feature",
                                priority=2,
                                description=f"RE opportunity noted in {file_path.name}",
                                source_file=str(file_path)
                            ))
                            break
                except Exception:
                    continue

        # Check ReverseLab for documented targets
        reverselab = Path("/Users/davidquinton/ReverseLab")
        if reverselab.exists():
            for target_file in reverselab.rglob("TARGETS.md"):
                try:
                    content = target_file.read_text()
                    # Look for uncompleted targets
                    for match in re.finditer(r"- \[ \]\s+(.+)", content):
                        improvements.append(DetectedImprovement(
                            project_id="REVERSELAB",
                            type="feature",
                            priority=2,
                            description=f"RE target: {match.group(1).strip()}",
                            source_file=str(target_file)
                        ))
                except Exception:
                    continue

        return improvements

    # =====================
    # SEMANTIC MEMORY PATTERNS
    # =====================

    def scan_semantic_memory_patterns(self) -> List[DetectedImprovement]:
        """Analyze semantic memory for repeated issues."""
        improvements = []

        try:
            from semantic_memory import SemanticMemory
            memory = SemanticMemory()

            # Look for error patterns
            error_results = memory.search("error failed exception", limit=20)
            error_counts = defaultdict(int)

            for entry, score in error_results:
                if score > 0.5:
                    # Extract project from metadata
                    project = entry.metadata.get("project", "ORCHESTRATOR")
                    error_counts[project] += 1

            # Projects with many errors need reliability improvements
            for project_id, count in error_counts.items():
                if count >= 3:
                    improvements.append(DetectedImprovement(
                        project_id=project_id,
                        type="reliability",
                        priority=2,
                        description=f"Repeated errors detected ({count} occurrences)",
                        context=f"Analyze semantic memory for error patterns"
                    ))

            # Look for repeated questions (might need documentation)
            question_results = memory.search("how to what is where", limit=20)
            question_topics = defaultdict(int)

            for entry, score in question_results:
                if score > 0.4 and "?" in entry.content:
                    # Count similar questions
                    key = entry.content[:50]
                    question_topics[key] += 1

            for topic, count in question_topics.items():
                if count >= 2:
                    improvements.append(DetectedImprovement(
                        project_id="SSOT_SYSTEM",
                        type="documentation",
                        priority=3,
                        description=f"FAQ needed: {topic[:40]}...",
                        auto_approve=True
                    ))

        except ImportError:
            pass  # Semantic memory not available

        return improvements

    # =====================
    # UTILITY METHODS
    # =====================

    def _iter_code_files(self, root: Path):
        """Iterate over code files in a directory."""
        for ext in CODE_EXTENSIONS:
            yield from root.rglob(f"*{ext}")

    def _detect_project(self, file_path: Path) -> Optional[str]:
        """Detect project ID from file path."""
        path_str = str(file_path).upper()

        # Check known project paths
        for project_id in PROJECT_CATEGORIES:
            if project_id.replace("_", "") in path_str.replace("_", ""):
                return project_id

        # Check for sam_brain specifically
        if "SAM_BRAIN" in path_str or "SAM/WARP_TAURI" in path_str:
            return "SAM_BRAIN"

        # Check salvaged folder
        if "SALVAGED" in path_str:
            return "SSOT_SYSTEM"

        return None

    def _extract_project_from_text(self, text: str) -> Optional[str]:
        """Extract project ID from description text."""
        text_upper = text.upper()
        for project_id in PROJECT_CATEGORIES:
            if project_id in text_upper:
                return project_id
        return None

    # =====================
    # REPORTING
    # =====================

    def get_top_improvements(self, limit: int = 10) -> List[Tuple[Improvement, float]]:
        """Get top prioritized improvements."""
        return self.tracker.get_queued_improvements(limit=limit)

    def summary(self, result: ScanResult = None) -> str:
        """Generate scan summary."""
        lines = [
            "Improvement Detector Summary",
            "=" * 40,
        ]

        if result:
            lines.extend([
                f"Scan Duration: {result.scan_duration:.1f}s",
                f"Files Scanned: {result.files_scanned}",
                f"New Improvements: {len(result.improvements)}",
                "",
            ])

        # Group by type
        queued = self.tracker.get_improvements_by_status("queued")
        detected = self.tracker.get_improvements_by_status("detected")

        by_type = defaultdict(int)
        for imp in queued + detected:
            by_type[imp.type] += 1

        lines.append("By Type:")
        for imp_type, count in sorted(by_type.items()):
            lines.append(f"  {imp_type}: {count}")

        lines.append("")
        lines.append(f"Total Pending: {len(queued) + len(detected)}")

        return "\n".join(lines)


def seed_test_data():
    """Seed some test improvements for verification."""
    tracker = EvolutionTracker()

    # Sync projects first
    tracker.sync_from_ssot()

    test_improvements = [
        DetectedImprovement(
            project_id="SAM_BRAIN",
            type="feature",
            priority=2,
            description="Add auto-training trigger after 100 successful interactions"
        ),
        DetectedImprovement(
            project_id="CHARACTER_PIPELINE",
            type="integration",
            priority=2,
            description="Connect to ComfyUI for texture generation"
        ),
        DetectedImprovement(
            project_id="ORCHESTRATOR",
            type="reliability",
            priority=1,
            description="Add circuit breaker for model loading failures"
        ),
    ]

    detector = ImprovementDetector(tracker)
    for imp in test_improvements:
        detector._add_improvement(imp)

    print(f"Seeded {len(test_improvements)} test improvements")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed_test_data()
        sys.exit(0)

    print("Running full improvement scan...")
    detector = ImprovementDetector()
    result = detector.full_scan()

    print(detector.summary(result))
    print()

    print("Top 5 improvements:")
    for imp, score in detector.get_top_improvements(5):
        print(f"  [{score:.1f}] {imp.project_id}: {imp.description[:50]}...")
