#!/usr/bin/env python3
"""
SAM Code Pattern Miner - Phase 5.1.5

Extracts high-quality training examples from git history:
- Bug fixes: Before/after code with fix explanation
- Refactoring: Code improvements with rationale
- Feature additions: New functionality implementations
- Documentation: Code + documentation pairs
- Tests: Test code with tested functionality

Multi-language support: Python, JS/TS, Rust, Swift
Incremental mining with commit tracking
Quality filtering to skip noise

Storage: /Volumes/David External/sam_training/code_patterns/
"""

import os
import re
import json
import sqlite3
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import difflib


# =============================================================================
# Configuration
# =============================================================================

# Storage on external drive per project rules
PATTERNS_DB = Path("/Volumes/David External/sam_training/code_patterns/patterns.db")
PATTERNS_JSONL = Path("/Volumes/David External/sam_training/code_patterns/training_examples.jsonl")

# Fallback to local if external not available
LOCAL_FALLBACK = Path.home() / ".sam" / "training_data" / "code_patterns"

SUPPORTED_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.rs': 'rust',
    '.swift': 'swift',
}

# Quality thresholds
MIN_DIFF_LINES = 3
MAX_DIFF_LINES = 200
MIN_COMMIT_MSG_LENGTH = 10
MAX_FILES_PER_COMMIT = 10  # Skip massive commits


class PatternType(Enum):
    """Types of code patterns to mine"""
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    TEST = "test"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CLEANUP = "cleanup"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass
class CommitInfo:
    """Information about a git commit"""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    files_changed: int
    insertions: int
    deletions: int


@dataclass
class FileDiff:
    """A single file diff from a commit"""
    file_path: str
    old_path: Optional[str]  # For renames
    language: str
    additions: List[str]
    deletions: List[str]
    context: List[str]  # Surrounding unchanged lines
    unified_diff: str


@dataclass
class CodePattern:
    """An extracted code pattern for training"""
    id: str
    pattern_type: PatternType
    language: str

    # Source info
    repo_path: str
    repo_name: str
    commit_hash: str
    commit_message: str
    file_path: str

    # The actual pattern
    before_code: str
    after_code: str
    diff: str
    context: str  # Surrounding code for understanding

    # Training format
    instruction: str
    input_text: str
    output_text: str

    # Metadata
    quality_score: float
    extracted_at: str

    def to_training_example(self) -> Dict:
        """Convert to JSONL training format"""
        return {
            "instruction": self.instruction,
            "input": self.input_text,
            "output": self.output_text,
            "metadata": {
                "pattern_type": self.pattern_type.value,
                "language": self.language,
                "repo": self.repo_name,
                "commit": self.commit_hash[:8],
                "quality": self.quality_score,
            }
        }


# =============================================================================
# Commit Analyzer
# =============================================================================

class CommitAnalyzer:
    """Analyzes git commits to classify pattern types"""

    # Keywords for pattern classification
    PATTERN_KEYWORDS = {
        PatternType.BUG_FIX: [
            'fix', 'bug', 'issue', 'error', 'crash', 'broken', 'problem',
            'resolve', 'patch', 'hotfix', 'correct', 'typo', 'mistake',
            'handle', 'catch', 'null', 'undefined', 'exception'
        ],
        PatternType.REFACTORING: [
            'refactor', 'cleanup', 'clean up', 'reorganize', 'restructure',
            'rename', 'move', 'extract', 'inline', 'simplify', 'improve',
            'modernize', 'update', 'upgrade', 'migrate'
        ],
        PatternType.FEATURE: [
            'add', 'implement', 'create', 'new', 'feature', 'introduce',
            'support', 'enable', 'allow', 'extend', 'enhance', 'capability'
        ],
        PatternType.DOCUMENTATION: [
            'doc', 'comment', 'readme', 'documentation', 'docstring',
            'jsdoc', 'rustdoc', 'explain', 'describe', 'annotate'
        ],
        PatternType.TEST: [
            'test', 'spec', 'unittest', 'integration', 'e2e', 'coverage',
            'assert', 'expect', 'mock', 'fixture', 'pytest', 'jest'
        ],
        PatternType.PERFORMANCE: [
            'performance', 'optimize', 'speed', 'fast', 'slow', 'memory',
            'cache', 'lazy', 'async', 'parallel', 'concurrent', 'efficiency'
        ],
        PatternType.SECURITY: [
            'security', 'secure', 'auth', 'permission', 'credential',
            'vulnerability', 'sanitize', 'validate', 'escape', 'xss', 'sql'
        ],
        PatternType.CLEANUP: [
            'remove', 'delete', 'unused', 'dead', 'deprecated', 'obsolete',
            'lint', 'format', 'style', 'whitespace', 'trailing'
        ],
        PatternType.CONFIG: [
            'config', 'configuration', 'setting', 'option', 'env', 'environment',
            'variable', 'constant', 'parameter', 'flag'
        ],
    }

    def __init__(self):
        self._keyword_map = {}
        for pattern_type, keywords in self.PATTERN_KEYWORDS.items():
            for keyword in keywords:
                self._keyword_map[keyword.lower()] = pattern_type

    def classify_commit(self, message: str, files: List[str] = None) -> PatternType:
        """Classify a commit message into a pattern type"""
        message_lower = message.lower()

        # Count keyword matches
        scores = {pt: 0 for pt in PatternType}

        for keyword, pattern_type in self._keyword_map.items():
            if keyword in message_lower:
                scores[pattern_type] += 1

        # File-based hints
        if files:
            for f in files:
                f_lower = f.lower()
                if 'test' in f_lower or 'spec' in f_lower:
                    scores[PatternType.TEST] += 2
                if 'readme' in f_lower or 'doc' in f_lower:
                    scores[PatternType.DOCUMENTATION] += 2
                if 'config' in f_lower or '.env' in f_lower:
                    scores[PatternType.CONFIG] += 2

        # Get highest score
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type

        return PatternType.UNKNOWN

    def calculate_quality_score(self, commit: CommitInfo, diff: FileDiff,
                                pattern_type: PatternType) -> float:
        """Calculate quality score for a pattern (0.0 - 1.0)"""
        score = 0.5  # Base score

        # Good commit message adds quality
        msg_len = len(commit.message)
        if msg_len > 50:
            score += 0.1
        if msg_len > 100:
            score += 0.05

        # Known pattern type is better
        if pattern_type != PatternType.UNKNOWN:
            score += 0.1

        # Right-sized diffs are better
        diff_lines = len(diff.additions) + len(diff.deletions)
        if 5 <= diff_lines <= 50:
            score += 0.15
        elif 50 < diff_lines <= 100:
            score += 0.05

        # Having context is good
        if diff.context:
            score += 0.1

        # Balanced changes (not pure additions/deletions)
        if diff.additions and diff.deletions:
            ratio = min(len(diff.additions), len(diff.deletions)) / max(len(diff.additions), len(diff.deletions))
            score += ratio * 0.1

        # Bug fixes and features are more valuable
        if pattern_type in [PatternType.BUG_FIX, PatternType.FEATURE]:
            score += 0.05

        return min(1.0, max(0.0, score))

    def generate_instruction(self, pattern_type: PatternType, language: str,
                            commit_message: str) -> str:
        """Generate a training instruction based on pattern type"""

        base_instructions = {
            PatternType.BUG_FIX: f"Fix this bug in the {language} code",
            PatternType.REFACTORING: f"Refactor this {language} code to improve its quality",
            PatternType.FEATURE: f"Implement this feature in {language}",
            PatternType.DOCUMENTATION: f"Add documentation to this {language} code",
            PatternType.TEST: f"Write tests for this {language} code",
            PatternType.PERFORMANCE: f"Optimize this {language} code for better performance",
            PatternType.SECURITY: f"Fix the security issue in this {language} code",
            PatternType.CLEANUP: f"Clean up this {language} code",
            PatternType.CONFIG: f"Update the configuration for this {language} project",
            PatternType.UNKNOWN: f"Improve this {language} code",
        }

        base = base_instructions.get(pattern_type, f"Modify this {language} code")

        # Add context from commit message if it's descriptive
        if len(commit_message) > 20 and not commit_message.startswith('Merge'):
            # Clean up the message
            clean_msg = commit_message.split('\n')[0].strip()
            if len(clean_msg) < 80:
                return f"{base}: {clean_msg}"

        return base


# =============================================================================
# Quality Filter
# =============================================================================

class QualityFilter:
    """Filters out low-quality patterns"""

    # Skip patterns
    SKIP_MESSAGE_PATTERNS = [
        r'^merge\s',
        r'^revert\s',
        r'^wip\b',
        r'^temp\b',
        r'^fixup\b',
        r'^squash\b',
        r'^auto[- ]?commit',
        r'^\s*$',
    ]

    SKIP_FILE_PATTERNS = [
        r'\.lock$',
        r'package-lock\.json$',
        r'yarn\.lock$',
        r'Cargo\.lock$',
        r'\.min\.(js|css)$',
        r'\.generated\.',
        r'__pycache__',
        r'node_modules',
        r'\.git/',
        r'dist/',
        r'build/',
    ]

    def __init__(self):
        self.skip_msg_re = [re.compile(p, re.IGNORECASE) for p in self.SKIP_MESSAGE_PATTERNS]
        self.skip_file_re = [re.compile(p) for p in self.SKIP_FILE_PATTERNS]

    def should_skip_commit(self, commit: CommitInfo) -> Tuple[bool, str]:
        """Check if a commit should be skipped"""
        # Too many files
        if commit.files_changed > MAX_FILES_PER_COMMIT:
            return True, "too many files"

        # Empty or short message
        if len(commit.message.strip()) < MIN_COMMIT_MSG_LENGTH:
            return True, "message too short"

        # Skip patterns
        for pattern in self.skip_msg_re:
            if pattern.search(commit.message):
                return True, f"matches skip pattern"

        return False, ""

    def should_skip_file(self, file_path: str) -> Tuple[bool, str]:
        """Check if a file should be skipped"""
        for pattern in self.skip_file_re:
            if pattern.search(file_path):
                return True, "matches skip pattern"

        # Check extension
        ext = Path(file_path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return True, "unsupported extension"

        return False, ""

    def should_skip_diff(self, diff: FileDiff) -> Tuple[bool, str]:
        """Check if a diff should be skipped"""
        total_lines = len(diff.additions) + len(diff.deletions)

        if total_lines < MIN_DIFF_LINES:
            return True, "diff too small"

        if total_lines > MAX_DIFF_LINES:
            return True, "diff too large"

        # Skip if it's mostly whitespace changes
        non_whitespace = sum(1 for line in diff.additions + diff.deletions
                           if line.strip())
        if non_whitespace < MIN_DIFF_LINES:
            return True, "mostly whitespace"

        return False, ""


# =============================================================================
# Code Pattern Miner
# =============================================================================

class CodePatternMiner:
    """
    Main class for mining code patterns from git repositories.

    Features:
    - Incremental mining (tracks processed commits)
    - Multi-language support
    - Pattern classification
    - Quality filtering
    - Training data generation
    """

    def __init__(self, db_path: Optional[Path] = None):
        # Use external storage if available, fallback to local
        if db_path:
            self.db_path = db_path
        elif PATTERNS_DB.parent.exists():
            self.db_path = PATTERNS_DB
            self.output_jsonl = PATTERNS_JSONL
        else:
            LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
            self.db_path = LOCAL_FALLBACK / "patterns.db"
            self.output_jsonl = LOCAL_FALLBACK / "training_examples.jsonl"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self.analyzer = CommitAnalyzer()
        self.quality_filter = QualityFilter()
        self._stats = {
            "commits_processed": 0,
            "commits_skipped": 0,
            "patterns_extracted": 0,
            "patterns_filtered": 0,
        }

    def _init_db(self):
        """Initialize SQLite database for pattern storage"""
        with sqlite3.connect(self.db_path) as conn:
            # Processed commits tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_commits (
                    commit_hash TEXT PRIMARY KEY,
                    repo_path TEXT,
                    processed_at TEXT,
                    patterns_extracted INTEGER
                )
            """)

            # Patterns table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT,
                    language TEXT,
                    repo_path TEXT,
                    repo_name TEXT,
                    commit_hash TEXT,
                    commit_message TEXT,
                    file_path TEXT,
                    before_code TEXT,
                    after_code TEXT,
                    diff TEXT,
                    context TEXT,
                    instruction TEXT,
                    input_text TEXT,
                    output_text TEXT,
                    quality_score REAL,
                    extracted_at TEXT
                )
            """)

            # Stats table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mining_stats (
                    id INTEGER PRIMARY KEY,
                    repo_path TEXT,
                    mined_at TEXT,
                    commits_processed INTEGER,
                    commits_skipped INTEGER,
                    patterns_extracted INTEGER,
                    patterns_filtered INTEGER
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_lang ON patterns(language)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_repo ON patterns(repo_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_quality ON patterns(quality_score)")

    def _is_commit_processed(self, commit_hash: str, repo_path: str) -> bool:
        """Check if a commit has already been processed"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT 1 FROM processed_commits WHERE commit_hash = ? AND repo_path = ?",
                (commit_hash, repo_path)
            ).fetchone()
            return result is not None

    def _mark_commit_processed(self, commit_hash: str, repo_path: str, patterns_count: int):
        """Mark a commit as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_commits
                (commit_hash, repo_path, processed_at, patterns_extracted)
                VALUES (?, ?, ?, ?)
            """, (commit_hash, repo_path, datetime.now().isoformat(), patterns_count))

    def _store_pattern(self, pattern: CodePattern):
        """Store a pattern in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO patterns
                (id, pattern_type, language, repo_path, repo_name, commit_hash,
                 commit_message, file_path, before_code, after_code, diff, context,
                 instruction, input_text, output_text, quality_score, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.id, pattern.pattern_type.value, pattern.language,
                pattern.repo_path, pattern.repo_name, pattern.commit_hash,
                pattern.commit_message, pattern.file_path,
                pattern.before_code, pattern.after_code, pattern.diff, pattern.context,
                pattern.instruction, pattern.input_text, pattern.output_text,
                pattern.quality_score, pattern.extracted_at
            ))

    def _get_commits(self, repo_path: Path, limit: int = 500,
                     since: Optional[str] = None) -> Generator[CommitInfo, None, None]:
        """Get commits from a git repository"""
        cmd = [
            "git", "log",
            "--pretty=format:%H|%h|%s|%an|%ai",
            "--shortstat",
            f"-n{limit}"
        ]

        if since:
            cmd.append(f"--since={since}")

        try:
            result = subprocess.run(
                cmd, cwd=repo_path, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                return

            lines = result.stdout.strip().split('\n')
            i = 0

            while i < len(lines):
                line = lines[i].strip()
                if not line or '|' not in line:
                    i += 1
                    continue

                parts = line.split('|', 4)
                if len(parts) < 5:
                    i += 1
                    continue

                commit_hash, short_hash, message, author, date = parts

                # Parse stats from next line
                files_changed = insertions = deletions = 0
                if i + 1 < len(lines):
                    stats_line = lines[i + 1].strip()
                    # Parse: "3 files changed, 45 insertions(+), 12 deletions(-)"
                    if 'file' in stats_line:
                        match = re.search(r'(\d+) file', stats_line)
                        if match:
                            files_changed = int(match.group(1))
                        match = re.search(r'(\d+) insertion', stats_line)
                        if match:
                            insertions = int(match.group(1))
                        match = re.search(r'(\d+) deletion', stats_line)
                        if match:
                            deletions = int(match.group(1))
                        i += 1

                yield CommitInfo(
                    hash=commit_hash,
                    short_hash=short_hash,
                    message=message,
                    author=author,
                    date=date,
                    files_changed=files_changed,
                    insertions=insertions,
                    deletions=deletions
                )

                i += 1

        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"Error getting commits: {e}")

    def _get_commit_files(self, repo_path: Path, commit_hash: str) -> List[str]:
        """Get list of files changed in a commit"""
        try:
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                cwd=repo_path, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except:
            pass
        return []

    def _get_file_diff(self, repo_path: Path, commit_hash: str,
                       file_path: str) -> Optional[FileDiff]:
        """Get the diff for a specific file in a commit"""
        ext = Path(file_path).suffix.lower()
        language = SUPPORTED_EXTENSIONS.get(ext, 'unknown')

        try:
            # Get unified diff
            result = subprocess.run(
                ["git", "show", "--no-color", "-U5", f"{commit_hash}", "--", file_path],
                cwd=repo_path, capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return None

            unified_diff = result.stdout

            # Parse additions and deletions
            additions = []
            deletions = []
            context = []

            in_diff = False
            for line in unified_diff.split('\n'):
                if line.startswith('@@'):
                    in_diff = True
                    continue

                if in_diff:
                    if line.startswith('+') and not line.startswith('+++'):
                        additions.append(line[1:])
                    elif line.startswith('-') and not line.startswith('---'):
                        deletions.append(line[1:])
                    elif line.startswith(' '):
                        context.append(line[1:])

            return FileDiff(
                file_path=file_path,
                old_path=None,
                language=language,
                additions=additions,
                deletions=deletions,
                context=context,
                unified_diff=unified_diff
            )

        except:
            return None

    def _get_file_content_at_commit(self, repo_path: Path, commit_hash: str,
                                    file_path: str, before: bool = False) -> str:
        """Get file content at a specific commit"""
        ref = f"{commit_hash}^" if before else commit_hash

        try:
            result = subprocess.run(
                ["git", "show", f"{ref}:{file_path}"],
                cwd=repo_path, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout
        except:
            pass

        return ""

    def mine_repository(self, repo_path: str, limit: int = 500,
                        since: Optional[str] = None,
                        incremental: bool = True) -> Dict:
        """
        Mine a git repository for code patterns.

        Args:
            repo_path: Path to git repository
            limit: Maximum commits to process
            since: Only process commits after this date (e.g., "2024-01-01")
            incremental: Skip already processed commits

        Returns:
            Mining statistics
        """
        repo_path = Path(repo_path)
        repo_name = repo_path.name

        if not (repo_path / ".git").exists():
            return {"error": f"Not a git repository: {repo_path}"}

        self._stats = {
            "commits_processed": 0,
            "commits_skipped": 0,
            "patterns_extracted": 0,
            "patterns_filtered": 0,
        }

        patterns_extracted = []

        for commit in self._get_commits(repo_path, limit, since):
            # Skip if already processed (incremental mode)
            if incremental and self._is_commit_processed(commit.hash, str(repo_path)):
                self._stats["commits_skipped"] += 1
                continue

            # Quality check commit
            should_skip, reason = self.quality_filter.should_skip_commit(commit)
            if should_skip:
                self._stats["commits_skipped"] += 1
                self._mark_commit_processed(commit.hash, str(repo_path), 0)
                continue

            # Get files changed
            files = self._get_commit_files(repo_path, commit.hash)

            # Classify the commit
            pattern_type = self.analyzer.classify_commit(commit.message, files)

            commit_patterns = 0

            for file_path in files:
                # Quality check file
                should_skip, reason = self.quality_filter.should_skip_file(file_path)
                if should_skip:
                    continue

                # Get diff
                diff = self._get_file_diff(repo_path, commit.hash, file_path)
                if not diff:
                    continue

                # Quality check diff
                should_skip, reason = self.quality_filter.should_skip_diff(diff)
                if should_skip:
                    self._stats["patterns_filtered"] += 1
                    continue

                # Calculate quality score
                quality = self.analyzer.calculate_quality_score(commit, diff, pattern_type)

                # Skip low quality patterns
                if quality < 0.4:
                    self._stats["patterns_filtered"] += 1
                    continue

                # Get before/after code
                before_code = self._get_file_content_at_commit(
                    repo_path, commit.hash, file_path, before=True
                )
                after_code = self._get_file_content_at_commit(
                    repo_path, commit.hash, file_path, before=False
                )

                # Generate training data
                instruction = self.analyzer.generate_instruction(
                    pattern_type, diff.language, commit.message
                )

                # Create input/output for training
                # Input: The problem description + before code
                # Output: The solution (after code or diff)
                if before_code:
                    input_text = f"Current code:\n```{diff.language}\n{before_code[:2000]}\n```"
                else:
                    input_text = f"Files to modify: {file_path}"

                output_text = f"```{diff.language}\n{after_code[:3000]}\n```"

                # Create pattern ID
                pattern_id = hashlib.md5(
                    f"{repo_name}:{commit.hash}:{file_path}".encode()
                ).hexdigest()[:16]

                pattern = CodePattern(
                    id=pattern_id,
                    pattern_type=pattern_type,
                    language=diff.language,
                    repo_path=str(repo_path),
                    repo_name=repo_name,
                    commit_hash=commit.hash,
                    commit_message=commit.message,
                    file_path=file_path,
                    before_code=before_code[:5000] if before_code else "",
                    after_code=after_code[:5000] if after_code else "",
                    diff=diff.unified_diff[:5000],
                    context='\n'.join(diff.context[:50]),
                    instruction=instruction,
                    input_text=input_text,
                    output_text=output_text,
                    quality_score=quality,
                    extracted_at=datetime.now().isoformat()
                )

                self._store_pattern(pattern)
                patterns_extracted.append(pattern)
                commit_patterns += 1
                self._stats["patterns_extracted"] += 1

            self._mark_commit_processed(commit.hash, str(repo_path), commit_patterns)
            self._stats["commits_processed"] += 1

        # Log stats
        self._log_mining_run(str(repo_path))

        return {
            "repo": repo_name,
            "repo_path": str(repo_path),
            **self._stats
        }

    def _log_mining_run(self, repo_path: str):
        """Log mining run statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO mining_stats
                (repo_path, mined_at, commits_processed, commits_skipped,
                 patterns_extracted, patterns_filtered)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                repo_path, datetime.now().isoformat(),
                self._stats["commits_processed"], self._stats["commits_skipped"],
                self._stats["patterns_extracted"], self._stats["patterns_filtered"]
            ))

    def mine_multiple_repos(self, repo_paths: List[str], **kwargs) -> Dict:
        """Mine multiple repositories"""
        results = {}
        for repo_path in repo_paths:
            print(f"Mining {repo_path}...")
            result = self.mine_repository(repo_path, **kwargs)
            results[repo_path] = result

        return {
            "repos": len(repo_paths),
            "results": results,
            "total_patterns": sum(r.get("patterns_extracted", 0) for r in results.values())
        }

    def export_training_data(self, output_path: Optional[Path] = None,
                            min_quality: float = 0.5,
                            pattern_types: Optional[List[PatternType]] = None,
                            languages: Optional[List[str]] = None) -> Dict:
        """
        Export patterns as JSONL training data.

        Args:
            output_path: Output file path (defaults to configured path)
            min_quality: Minimum quality score (0.0-1.0)
            pattern_types: Filter by pattern types
            languages: Filter by languages

        Returns:
            Export statistics
        """
        output_path = output_path or self.output_jsonl
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build query
        query = "SELECT * FROM patterns WHERE quality_score >= ?"
        params = [min_quality]

        if pattern_types:
            placeholders = ','.join('?' * len(pattern_types))
            query += f" AND pattern_type IN ({placeholders})"
            params.extend([pt.value for pt in pattern_types])

        if languages:
            placeholders = ','.join('?' * len(languages))
            query += f" AND language IN ({placeholders})"
            params.extend(languages)

        query += " ORDER BY quality_score DESC"

        exported = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            with open(output_path, 'w') as f:
                for row in rows:
                    example = {
                        "instruction": row["instruction"],
                        "input": row["input_text"],
                        "output": row["output_text"],
                        "metadata": {
                            "pattern_type": row["pattern_type"],
                            "language": row["language"],
                            "repo": row["repo_name"],
                            "commit": row["commit_hash"][:8],
                            "quality": row["quality_score"],
                        }
                    }
                    f.write(json.dumps(example) + '\n')
                    exported += 1

        return {
            "exported": exported,
            "output_path": str(output_path),
            "min_quality": min_quality,
            "file_size_kb": round(output_path.stat().st_size / 1024, 1)
        }

    def get_stats(self) -> Dict:
        """Get mining statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total_patterns = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]

            by_type = dict(conn.execute("""
                SELECT pattern_type, COUNT(*) FROM patterns GROUP BY pattern_type
            """).fetchall())

            by_language = dict(conn.execute("""
                SELECT language, COUNT(*) FROM patterns GROUP BY language
            """).fetchall())

            by_repo = dict(conn.execute("""
                SELECT repo_name, COUNT(*) FROM patterns GROUP BY repo_name
            """).fetchall())

            avg_quality = conn.execute(
                "SELECT AVG(quality_score) FROM patterns"
            ).fetchone()[0] or 0

            processed_commits = conn.execute(
                "SELECT COUNT(*) FROM processed_commits"
            ).fetchone()[0]

            return {
                "total_patterns": total_patterns,
                "by_type": by_type,
                "by_language": by_language,
                "by_repo": by_repo,
                "avg_quality": round(avg_quality, 3),
                "processed_commits": processed_commits,
                "db_path": str(self.db_path),
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
            }

    def search_patterns(self, query: str, limit: int = 20) -> List[Dict]:
        """Search patterns by commit message or file path"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, pattern_type, language, repo_name, commit_message,
                       file_path, quality_score, instruction
                FROM patterns
                WHERE commit_message LIKE ? OR file_path LIKE ?
                ORDER BY quality_score DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()

            return [dict(r) for r in rows]

    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        """Get a specific pattern by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM patterns WHERE id = ?", (pattern_id,)
            ).fetchone()

            return dict(row) if row else None


# =============================================================================
# Singleton
# =============================================================================

_miner = None


def get_miner() -> CodePatternMiner:
    """Get singleton pattern miner"""
    global _miner
    if _miner is None:
        _miner = CodePatternMiner()
    return _miner


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Code Pattern Miner - Phase 5.1.5")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Mine command
    mine_parser = subparsers.add_parser("mine", help="Mine a repository")
    mine_parser.add_argument("path", nargs="?", default=".", help="Repository path")
    mine_parser.add_argument("--limit", "-l", type=int, default=500, help="Max commits")
    mine_parser.add_argument("--since", "-s", help="Since date (YYYY-MM-DD)")
    mine_parser.add_argument("--full", action="store_true", help="Process all commits (not incremental)")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export training data")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.add_argument("--min-quality", "-q", type=float, default=0.5)
    export_parser.add_argument("--types", "-t", nargs="+", help="Pattern types to include")
    export_parser.add_argument("--languages", "-l", nargs="+", help="Languages to include")

    # Stats command
    subparsers.add_parser("stats", help="Show statistics")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search patterns")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", "-l", type=int, default=20)

    # Show command
    show_parser = subparsers.add_parser("show", help="Show a pattern")
    show_parser.add_argument("id", help="Pattern ID")

    args = parser.parse_args()
    miner = get_miner()

    if args.command == "mine":
        import os
        path = os.path.abspath(args.path)
        print(f"\nMining {path}...")
        print(f"Limit: {args.limit} commits")
        if args.since:
            print(f"Since: {args.since}")
        print()

        result = miner.mine_repository(
            path, limit=args.limit, since=args.since,
            incremental=not args.full
        )

        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Commits processed: {result['commits_processed']}")
            print(f"Commits skipped: {result['commits_skipped']}")
            print(f"Patterns extracted: {result['patterns_extracted']}")
            print(f"Patterns filtered: {result['patterns_filtered']}")

    elif args.command == "export":
        pattern_types = None
        if args.types:
            pattern_types = [PatternType(t) for t in args.types]

        output_path = Path(args.output) if args.output else None

        print(f"\nExporting training data...")
        result = miner.export_training_data(
            output_path=output_path,
            min_quality=args.min_quality,
            pattern_types=pattern_types,
            languages=args.languages
        )

        print(f"Exported: {result['exported']} examples")
        print(f"Output: {result['output_path']}")
        print(f"Size: {result['file_size_kb']} KB")

    elif args.command == "stats":
        stats = miner.get_stats()
        print("\nCode Pattern Mining Statistics\n")
        print(f"Total patterns: {stats['total_patterns']}")
        print(f"Processed commits: {stats['processed_commits']}")
        print(f"Average quality: {stats['avg_quality']}")
        print(f"Database: {stats['db_path']} ({stats['db_size_mb']} MB)")

        print("\nBy pattern type:")
        for ptype, count in stats['by_type'].items():
            print(f"  {ptype}: {count}")

        print("\nBy language:")
        for lang, count in stats['by_language'].items():
            print(f"  {lang}: {count}")

        print("\nBy repository:")
        for repo, count in stats['by_repo'].items():
            print(f"  {repo}: {count}")

    elif args.command == "search":
        results = miner.search_patterns(args.query, args.limit)
        print(f"\nSearch results for '{args.query}': {len(results)}\n")
        for r in results:
            print(f"  [{r['pattern_type']}] {r['commit_message'][:50]}")
            print(f"    {r['file_path']} (quality: {r['quality_score']:.2f})")
            print()

    elif args.command == "show":
        pattern = miner.get_pattern(args.id)
        if pattern:
            print(f"\nPattern: {pattern['id']}")
            print(f"Type: {pattern['pattern_type']}")
            print(f"Language: {pattern['language']}")
            print(f"Repo: {pattern['repo_name']}")
            print(f"Commit: {pattern['commit_hash'][:8]}")
            print(f"Message: {pattern['commit_message']}")
            print(f"File: {pattern['file_path']}")
            print(f"Quality: {pattern['quality_score']:.2f}")
            print(f"\nInstruction: {pattern['instruction']}")
            print(f"\nDiff:\n{pattern['diff'][:1000]}")
        else:
            print(f"Pattern not found: {args.id}")

    else:
        parser.print_help()
