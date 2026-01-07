#!/usr/bin/env python3
"""
SAM Exhaustive Project Analyzer - Deep understanding of all projects.

This runs ONCE and builds complete understanding:
- Deep metadata extraction from every project
- Purpose/description inference from code
- Tech stack detection
- Relationship mapping between projects
- Activity/health scoring
- Auto-categorization and tagging
- Importance ranking
- Generates browsable master inventory

No back-and-forth needed - one comprehensive scan.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "exhaustive_analysis"
DISCOVERED_FILE = SCRIPT_DIR / "projects_discovered.json"
INVENTORY_FILE = OUTPUT_DIR / "master_inventory.json"
REPORT_FILE = OUTPUT_DIR / "MASTER_REPORT.md"
RELATIONSHIPS_FILE = OUTPUT_DIR / "relationships.json"


@dataclass
class ProjectAnalysis:
    """Deep analysis of a single project."""
    path: str
    name: str

    # Basic info
    description: str = ""
    purpose: str = ""  # Inferred from code

    # Tech stack
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)

    # Files
    total_files: int = 0
    code_files: int = 0
    total_lines: int = 0
    has_readme: bool = False
    has_tests: bool = False
    has_ci: bool = False
    has_docker: bool = False

    # Activity
    last_modified: str = ""
    days_since_modified: int = 0
    git_commits: int = 0
    git_last_commit: str = ""

    # Health
    has_todos: int = 0
    has_fixmes: int = 0
    incomplete_features: List[str] = field(default_factory=list)

    # Classification
    project_type: str = ""  # app, library, tool, game, config, etc.
    status: str = ""  # active, stale, abandoned, complete, wip
    complexity: str = ""  # simple, moderate, complex

    # Auto-generated
    tags: List[str] = field(default_factory=list)
    importance_score: float = 0.0
    auto_starred: bool = False
    auto_pinned: bool = False

    # Relationships
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    related_to: List[str] = field(default_factory=list)

    # Raw data
    readme_content: str = ""
    key_files: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)


class ExhaustiveAnalyzer:
    """Performs deep analysis of all projects."""

    # File patterns for detection
    LANG_PATTERNS = {
        ".py": "Python",
        ".rs": "Rust",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".js": "JavaScript",
        ".jsx": "JavaScript/React",
        ".swift": "Swift",
        ".go": "Go",
        ".rb": "Ruby",
        ".java": "Java",
        ".kt": "Kotlin",
        ".c": "C",
        ".cpp": "C++",
        ".cs": "C#",
        ".vue": "Vue",
        ".svelte": "Svelte",
    }

    FRAMEWORK_INDICATORS = {
        "package.json": {
            "react": "React",
            "vue": "Vue",
            "svelte": "Svelte",
            "next": "Next.js",
            "nuxt": "Nuxt",
            "express": "Express",
            "fastify": "Fastify",
            "electron": "Electron",
            "tauri": "Tauri",
        },
        "Cargo.toml": {
            "tauri": "Tauri",
            "actix": "Actix",
            "rocket": "Rocket",
            "tokio": "Tokio",
            "serde": "Serde",
            "clap": "Clap CLI",
        },
        "requirements.txt": {
            "flask": "Flask",
            "django": "Django",
            "fastapi": "FastAPI",
            "torch": "PyTorch",
            "tensorflow": "TensorFlow",
            "transformers": "Hugging Face",
            "langchain": "LangChain",
        },
        "pyproject.toml": {
            "flask": "Flask",
            "django": "Django",
            "fastapi": "FastAPI",
        }
    }

    PROJECT_TYPE_INDICATORS = {
        "app": ["main.py", "main.rs", "index.html", "App.vue", "App.tsx"],
        "library": ["setup.py", "pyproject.toml", "lib.rs", "index.js"],
        "cli": ["cli.py", "cli.rs", "bin/", "clap", "argparse", "click"],
        "api": ["routes/", "api/", "endpoints/", "fastapi", "express", "actix"],
        "game": ["game.py", "game.rs", "unity", "unreal", "godot", "pygame"],
        "ml": ["model.py", "train.py", "inference", "torch", "tensorflow"],
        "automation": ["script", "automation", "cron", "task", "workflow"],
        "config": [".config", "dotfiles", "settings"],
    }

    STATUS_THRESHOLDS = {
        "active": 7,      # Modified within 7 days
        "recent": 30,     # Modified within 30 days
        "stale": 180,     # Modified within 180 days
        "abandoned": 365, # Not modified in a year
    }

    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
        self.projects: Dict[str, ProjectAnalysis] = {}
        self.relationships: Dict[str, Set[str]] = defaultdict(set)
        self.all_imports: Dict[str, Set[str]] = defaultdict(set)  # project -> imports
        self.progress = {"scanned": 0, "total": 0, "current": ""}

    def load_discovered(self) -> List[Dict]:
        """Load previously discovered projects."""
        if DISCOVERED_FILE.exists():
            data = json.load(open(DISCOVERED_FILE))
            return data.get("projects", [])
        return []

    def analyze_project(self, project_path: str) -> ProjectAnalysis:
        """Deep analysis of a single project."""
        path = Path(project_path)
        analysis = ProjectAnalysis(
            path=str(path),
            name=path.name
        )

        if not path.exists():
            analysis.status = "missing"
            return analysis

        # Basic file analysis
        self._analyze_files(path, analysis)

        # README and description
        self._extract_description(path, analysis)

        # Tech stack
        self._detect_tech_stack(path, analysis)

        # Git analysis
        self._analyze_git(path, analysis)

        # Activity and status
        self._analyze_activity(path, analysis)

        # Code analysis (TODOs, structure)
        self._analyze_code(path, analysis)

        # Classify project type
        self._classify_project(path, analysis)

        # Calculate importance
        self._calculate_importance(analysis)

        # Auto-tag
        self._auto_tag(analysis)

        return analysis

    def _analyze_files(self, path: Path, analysis: ProjectAnalysis):
        """Analyze file structure."""
        try:
            all_files = list(path.rglob("*"))
            # Filter out common non-project directories
            ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv",
                         "target", "build", "dist", ".next", ".nuxt", "vendor"}

            files = [f for f in all_files if f.is_file() and
                    not any(d in f.parts for d in ignore_dirs)]

            analysis.total_files = len(files)

            code_extensions = set(self.LANG_PATTERNS.keys())
            code_files = [f for f in files if f.suffix in code_extensions]
            analysis.code_files = len(code_files)

            # Count lines (sample if too many files)
            sample = code_files[:50] if len(code_files) > 50 else code_files
            total_lines = 0
            for f in sample:
                try:
                    total_lines += len(f.read_text(errors='ignore').splitlines())
                except:
                    pass
            if len(code_files) > 50:
                total_lines = int(total_lines * len(code_files) / 50)
            analysis.total_lines = total_lines

            # Key files
            key_file_names = ["README.md", "README", "package.json", "Cargo.toml",
                            "pyproject.toml", "setup.py", "Makefile", "Dockerfile",
                            "docker-compose.yml", ".github/workflows"]
            for kf in key_file_names:
                if (path / kf).exists():
                    analysis.key_files.append(kf)

            analysis.has_readme = any("readme" in kf.lower() for kf in analysis.key_files)
            analysis.has_tests = (path / "tests").exists() or (path / "test").exists() or \
                                (path / "__tests__").exists() or (path / "spec").exists()
            analysis.has_ci = (path / ".github" / "workflows").exists() or \
                             (path / ".gitlab-ci.yml").exists() or (path / ".travis.yml").exists()
            analysis.has_docker = (path / "Dockerfile").exists() or (path / "docker-compose.yml").exists()

            # Entry points
            entry_candidates = ["main.py", "main.rs", "index.js", "index.ts",
                               "app.py", "server.py", "cli.py", "src/main.rs", "src/lib.rs"]
            for entry in entry_candidates:
                if (path / entry).exists():
                    analysis.entry_points.append(entry)

        except Exception as e:
            pass

    def _extract_description(self, path: Path, analysis: ProjectAnalysis):
        """Extract description from README and other sources."""
        # Try README
        for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
            readme_path = path / readme_name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(errors='ignore')[:5000]
                    analysis.readme_content = content

                    # Extract first paragraph as description
                    lines = content.split('\n')
                    desc_lines = []
                    in_description = False
                    for line in lines:
                        line = line.strip()
                        if not line:
                            if in_description and desc_lines:
                                break
                            continue
                        if line.startswith('#'):
                            in_description = True
                            continue
                        if in_description:
                            if line.startswith(('#', '!', '[', '```')):
                                break
                            desc_lines.append(line)

                    analysis.description = ' '.join(desc_lines)[:500]
                    break
                except:
                    pass

        # Try package.json description
        if not analysis.description:
            pkg_json = path / "package.json"
            if pkg_json.exists():
                try:
                    pkg = json.load(open(pkg_json))
                    analysis.description = pkg.get("description", "")[:500]
                except:
                    pass

        # Try Cargo.toml description
        if not analysis.description:
            cargo_toml = path / "Cargo.toml"
            if cargo_toml.exists():
                try:
                    content = cargo_toml.read_text()
                    match = re.search(r'description\s*=\s*"([^"]+)"', content)
                    if match:
                        analysis.description = match.group(1)[:500]
                except:
                    pass

        # Infer purpose from project name and files
        self._infer_purpose(path, analysis)

    def _infer_purpose(self, path: Path, analysis: ProjectAnalysis):
        """Infer project purpose from name and structure."""
        name_lower = analysis.name.lower()

        purpose_keywords = {
            "api": "API service",
            "server": "Server application",
            "client": "Client application",
            "cli": "Command-line tool",
            "bot": "Bot/automation",
            "scraper": "Web scraper",
            "crawler": "Web crawler",
            "pipeline": "Data/processing pipeline",
            "dashboard": "Dashboard/visualization",
            "auth": "Authentication system",
            "proxy": "Proxy service",
            "bridge": "Integration bridge",
            "plugin": "Plugin/extension",
            "theme": "Theme/styling",
            "test": "Testing utilities",
            "mock": "Mock/testing data",
            "demo": "Demo/example",
            "template": "Project template",
            "starter": "Starter template",
            "boilerplate": "Boilerplate code",
            "config": "Configuration",
            "tool": "Development tool",
            "util": "Utilities",
            "helper": "Helper functions",
            "lib": "Library",
            "sdk": "SDK",
            "wrapper": "API wrapper",
            "game": "Game",
            "app": "Application",
            "web": "Web application",
            "mobile": "Mobile application",
            "desktop": "Desktop application",
            "ml": "Machine learning",
            "ai": "AI/ML project",
            "model": "ML model",
            "train": "Training system",
            "data": "Data processing",
            "etl": "ETL pipeline",
            "migration": "Data migration",
            "backup": "Backup system",
            "sync": "Synchronization",
            "monitor": "Monitoring",
            "log": "Logging",
            "metric": "Metrics collection",
            "voice": "Voice/audio processing",
            "video": "Video processing",
            "image": "Image processing",
            "media": "Media processing",
        }

        for keyword, purpose in purpose_keywords.items():
            if keyword in name_lower:
                analysis.purpose = purpose
                break

        if not analysis.purpose and analysis.description:
            analysis.purpose = analysis.description[:100]

    def _detect_tech_stack(self, path: Path, analysis: ProjectAnalysis):
        """Detect languages, frameworks, and tools."""
        # Languages from file extensions
        lang_counts = defaultdict(int)
        try:
            for f in path.rglob("*"):
                if f.is_file() and f.suffix in self.LANG_PATTERNS:
                    lang_counts[self.LANG_PATTERNS[f.suffix]] += 1
        except:
            pass

        # Sort by count, take top languages
        analysis.languages = [lang for lang, _ in
                            sorted(lang_counts.items(), key=lambda x: -x[1])[:5]]

        # Frameworks from config files
        for config_file, indicators in self.FRAMEWORK_INDICATORS.items():
            config_path = path / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text().lower()
                    for indicator, framework in indicators.items():
                        if indicator in content and framework not in analysis.frameworks:
                            analysis.frameworks.append(framework)
                except:
                    pass

        # Tools detection
        if (path / "Dockerfile").exists():
            analysis.tools.append("Docker")
        if (path / "docker-compose.yml").exists() or (path / "docker-compose.yaml").exists():
            analysis.tools.append("Docker Compose")
        if (path / ".github" / "workflows").exists():
            analysis.tools.append("GitHub Actions")
        if (path / "Makefile").exists():
            analysis.tools.append("Make")
        if (path / "justfile").exists():
            analysis.tools.append("Just")
        if (path / ".pre-commit-config.yaml").exists():
            analysis.tools.append("Pre-commit")
        if (path / "pytest.ini").exists() or (path / "pyproject.toml").exists():
            analysis.tools.append("Pytest")

    def _analyze_git(self, path: Path, analysis: ProjectAnalysis):
        """Analyze git history."""
        git_dir = path / ".git"
        if not git_dir.exists():
            return

        try:
            # Commit count
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                analysis.git_commits = int(result.stdout.strip())

            # Last commit date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                analysis.git_last_commit = result.stdout.strip()
        except:
            pass

    def _analyze_activity(self, path: Path, analysis: ProjectAnalysis):
        """Analyze project activity and determine status."""
        # Find most recent file modification
        latest_mtime = 0
        try:
            for f in path.rglob("*"):
                if f.is_file() and ".git" not in f.parts:
                    try:
                        mtime = f.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                    except:
                        pass
        except:
            pass

        if latest_mtime > 0:
            last_mod = datetime.fromtimestamp(latest_mtime)
            analysis.last_modified = last_mod.isoformat()
            analysis.days_since_modified = (datetime.now() - last_mod).days

        # Determine status
        days = analysis.days_since_modified
        if days <= self.STATUS_THRESHOLDS["active"]:
            analysis.status = "active"
        elif days <= self.STATUS_THRESHOLDS["recent"]:
            analysis.status = "recent"
        elif days <= self.STATUS_THRESHOLDS["stale"]:
            analysis.status = "stale"
        else:
            analysis.status = "abandoned"

    def _analyze_code(self, path: Path, analysis: ProjectAnalysis):
        """Analyze code for TODOs, FIXMEs, and incomplete features."""
        todo_pattern = re.compile(r'\b(TODO|FIXME|XXX|HACK|BUG)\b', re.IGNORECASE)
        incomplete_pattern = re.compile(r'(not implemented|stub|placeholder|coming soon)', re.IGNORECASE)

        code_extensions = {'.py', '.rs', '.ts', '.tsx', '.js', '.jsx', '.go', '.swift'}

        try:
            for f in path.rglob("*"):
                if f.is_file() and f.suffix in code_extensions and ".git" not in f.parts:
                    try:
                        content = f.read_text(errors='ignore')

                        # Count TODOs/FIXMEs
                        todos = todo_pattern.findall(content)
                        analysis.has_todos += len([t for t in todos if t.upper() == 'TODO'])
                        analysis.has_fixmes += len([t for t in todos if t.upper() in ('FIXME', 'BUG')])

                        # Find incomplete features
                        for match in incomplete_pattern.finditer(content):
                            # Get surrounding context
                            start = max(0, match.start() - 50)
                            end = min(len(content), match.end() + 50)
                            context = content[start:end].replace('\n', ' ').strip()
                            if len(analysis.incomplete_features) < 10:
                                analysis.incomplete_features.append(context[:100])
                    except:
                        pass
        except:
            pass

    def _classify_project(self, path: Path, analysis: ProjectAnalysis):
        """Classify project type and complexity."""
        # Determine type
        type_scores = defaultdict(int)

        for proj_type, indicators in self.PROJECT_TYPE_INDICATORS.items():
            for indicator in indicators:
                if "/" in indicator:
                    if (path / indicator).exists():
                        type_scores[proj_type] += 2
                elif indicator.startswith("."):
                    if analysis.name.startswith(indicator) or (path / indicator).exists():
                        type_scores[proj_type] += 1
                else:
                    # Check if indicator in any file name or content
                    for kf in analysis.key_files:
                        if indicator in kf.lower():
                            type_scores[proj_type] += 1
                    for lang in analysis.languages:
                        if indicator in lang.lower():
                            type_scores[proj_type] += 1
                    for fw in analysis.frameworks:
                        if indicator in fw.lower():
                            type_scores[proj_type] += 1
                    if indicator in analysis.name.lower():
                        type_scores[proj_type] += 2

        if type_scores:
            analysis.project_type = max(type_scores, key=type_scores.get)
        else:
            analysis.project_type = "unknown"

        # Determine complexity
        if analysis.code_files > 50 or analysis.total_lines > 5000:
            analysis.complexity = "complex"
        elif analysis.code_files > 10 or analysis.total_lines > 1000:
            analysis.complexity = "moderate"
        else:
            analysis.complexity = "simple"

    def _calculate_importance(self, analysis: ProjectAnalysis):
        """Calculate importance score for auto-starring."""
        score = 0.0

        # Activity bonus
        if analysis.status == "active":
            score += 30
        elif analysis.status == "recent":
            score += 20
        elif analysis.status == "stale":
            score += 5

        # Size/complexity bonus
        if analysis.complexity == "complex":
            score += 20
        elif analysis.complexity == "moderate":
            score += 10

        # Code quality indicators
        if analysis.has_tests:
            score += 10
        if analysis.has_ci:
            score += 10
        if analysis.has_readme:
            score += 5
        if analysis.has_docker:
            score += 5

        # Git activity
        if analysis.git_commits > 100:
            score += 15
        elif analysis.git_commits > 20:
            score += 10
        elif analysis.git_commits > 5:
            score += 5

        # Framework/tool sophistication
        score += len(analysis.frameworks) * 3
        score += len(analysis.tools) * 2

        # Penalty for incomplete
        score -= analysis.has_todos * 0.5
        score -= analysis.has_fixmes * 1

        analysis.importance_score = max(0, score)

        # Auto-star threshold
        if score >= 50:
            analysis.auto_starred = True
        if score >= 75:
            analysis.auto_pinned = True

    def _auto_tag(self, analysis: ProjectAnalysis):
        """Auto-generate tags."""
        tags = set()

        # Language tags
        for lang in analysis.languages[:3]:
            tags.add(lang.lower().replace("/", "-"))

        # Framework tags
        for fw in analysis.frameworks[:3]:
            tags.add(fw.lower().replace(" ", "-").replace(".", ""))

        # Type tag
        if analysis.project_type and analysis.project_type != "unknown":
            tags.add(analysis.project_type)

        # Status tag
        if analysis.status:
            tags.add(analysis.status)

        # Special tags
        if analysis.has_tests:
            tags.add("tested")
        if analysis.has_ci:
            tags.add("ci-cd")
        if analysis.has_docker:
            tags.add("containerized")
        if "Tauri" in analysis.frameworks:
            tags.add("desktop-app")
        if any(ml in str(analysis.frameworks) for ml in ["PyTorch", "TensorFlow", "Hugging Face"]):
            tags.add("machine-learning")

        analysis.tags = sorted(tags)

    def find_relationships(self):
        """Find relationships between all projects."""
        print("Finding relationships between projects...")

        # Build import maps
        for proj_path, analysis in self.projects.items():
            path = Path(proj_path)

            # Extract imports from Python files
            for py_file in path.rglob("*.py"):
                if ".git" in py_file.parts or "venv" in py_file.parts:
                    continue
                try:
                    content = py_file.read_text(errors='ignore')
                    # Find imports
                    imports = re.findall(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE)
                    self.all_imports[proj_path].update(imports)
                except:
                    pass

            # Extract dependencies from package.json
            pkg_json = path / "package.json"
            if pkg_json.exists():
                try:
                    pkg = json.load(open(pkg_json))
                    deps = list(pkg.get("dependencies", {}).keys())
                    deps += list(pkg.get("devDependencies", {}).keys())
                    self.all_imports[proj_path].update(deps)
                except:
                    pass

            # Extract dependencies from Cargo.toml
            cargo_toml = path / "Cargo.toml"
            if cargo_toml.exists():
                try:
                    content = cargo_toml.read_text()
                    deps = re.findall(r'^(\w+)\s*=', content, re.MULTILINE)
                    self.all_imports[proj_path].update(deps)
                except:
                    pass

        # Find cross-project dependencies
        project_names = {Path(p).name.lower(): p for p in self.projects.keys()}

        for proj_path, imports in self.all_imports.items():
            for imp in imports:
                imp_lower = imp.lower().split('.')[0]
                if imp_lower in project_names:
                    other_proj = project_names[imp_lower]
                    if other_proj != proj_path:
                        self.projects[proj_path].depends_on.append(other_proj)
                        self.projects[other_proj].depended_by.append(proj_path)

        # Find related projects by name similarity and shared tags
        for proj_path, analysis in self.projects.items():
            name_parts = set(re.split(r'[-_]', analysis.name.lower()))

            for other_path, other_analysis in self.projects.items():
                if other_path == proj_path:
                    continue

                other_name_parts = set(re.split(r'[-_]', other_analysis.name.lower()))

                # Name similarity
                common_parts = name_parts & other_name_parts
                if len(common_parts) >= 2 or (len(common_parts) == 1 and len(list(common_parts)[0]) > 4):
                    if other_path not in analysis.related_to:
                        analysis.related_to.append(other_path)

                # Shared tags (at least 3)
                shared_tags = set(analysis.tags) & set(other_analysis.tags)
                if len(shared_tags) >= 3:
                    if other_path not in analysis.related_to:
                        analysis.related_to.append(other_path)

    def run_full_analysis(self) -> Dict:
        """Run exhaustive analysis on all discovered projects."""
        discovered = self.load_discovered()
        self.progress["total"] = len(discovered)

        print(f"Starting exhaustive analysis of {len(discovered)} projects...")
        print("This will take a while. Progress will be shown.\n")

        for i, proj in enumerate(discovered):
            proj_path = proj.get("path", "")
            self.progress["scanned"] = i + 1
            self.progress["current"] = proj_path

            if i % 50 == 0:
                print(f"Progress: {i}/{len(discovered)} ({i*100//len(discovered)}%)")

            analysis = self.analyze_project(proj_path)
            self.projects[proj_path] = analysis

        # Find relationships after all projects analyzed
        self.find_relationships()

        # Save results
        self.save_results()

        return self.generate_summary()

    def save_results(self):
        """Save all analysis results."""
        # Master inventory
        inventory = {
            "generated_at": datetime.now().isoformat(),
            "total_projects": len(self.projects),
            "projects": {p: asdict(a) for p, a in self.projects.items()}
        }
        json.dump(inventory, open(INVENTORY_FILE, "w"), indent=2)

        # Relationships
        relationships = {
            "dependencies": {p: list(a.depends_on) for p, a in self.projects.items() if a.depends_on},
            "dependents": {p: list(a.depended_by) for p, a in self.projects.items() if a.depended_by},
            "related": {p: list(a.related_to) for p, a in self.projects.items() if a.related_to},
        }
        json.dump(relationships, open(RELATIONSHIPS_FILE, "w"), indent=2)

        # Generate report
        self.generate_report()

        # Update favorites
        self.update_favorites()

    def update_favorites(self):
        """Update project_favorites.json with auto-starred projects."""
        try:
            from project_favorites import FavoritesManager
            manager = FavoritesManager()

            starred = 0
            pinned = 0

            for proj_path, analysis in self.projects.items():
                if analysis.auto_pinned:
                    manager.pin(proj_path)
                    for tag in analysis.tags[:5]:
                        manager.add_tag(proj_path, tag)
                    pinned += 1
                elif analysis.auto_starred:
                    manager.star(proj_path, analysis.name)
                    for tag in analysis.tags[:5]:
                        manager.add_tag(proj_path, tag)
                    starred += 1

            print(f"Updated favorites: {pinned} pinned, {starred} starred")
        except Exception as e:
            print(f"Could not update favorites: {e}")

    def generate_summary(self) -> Dict:
        """Generate analysis summary."""
        analyses = list(self.projects.values())

        # Status breakdown
        status_counts = defaultdict(int)
        for a in analyses:
            status_counts[a.status] += 1

        # Type breakdown
        type_counts = defaultdict(int)
        for a in analyses:
            type_counts[a.project_type] += 1

        # Language breakdown
        lang_counts = defaultdict(int)
        for a in analyses:
            for lang in a.languages:
                lang_counts[lang] += 1

        # Framework breakdown
        fw_counts = defaultdict(int)
        for a in analyses:
            for fw in a.frameworks:
                fw_counts[fw] += 1

        # Top projects by importance
        top_projects = sorted(analyses, key=lambda a: -a.importance_score)[:20]

        return {
            "total_projects": len(analyses),
            "status_breakdown": dict(status_counts),
            "type_breakdown": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
            "language_breakdown": dict(sorted(lang_counts.items(), key=lambda x: -x[1])[:15]),
            "framework_breakdown": dict(sorted(fw_counts.items(), key=lambda x: -x[1])[:15]),
            "auto_starred": len([a for a in analyses if a.auto_starred]),
            "auto_pinned": len([a for a in analyses if a.auto_pinned]),
            "with_tests": len([a for a in analyses if a.has_tests]),
            "with_ci": len([a for a in analyses if a.has_ci]),
            "with_docker": len([a for a in analyses if a.has_docker]),
            "total_code_files": sum(a.code_files for a in analyses),
            "total_lines": sum(a.total_lines for a in analyses),
            "top_projects": [{"name": a.name, "path": a.path, "score": a.importance_score}
                           for a in top_projects],
            "output_files": {
                "inventory": str(INVENTORY_FILE),
                "report": str(REPORT_FILE),
                "relationships": str(RELATIONSHIPS_FILE),
            }
        }

    def generate_report(self):
        """Generate markdown report."""
        analyses = list(self.projects.values())

        # Sort by importance
        by_importance = sorted(analyses, key=lambda a: -a.importance_score)

        # Group by status
        by_status = defaultdict(list)
        for a in analyses:
            by_status[a.status].append(a)

        # Group by type
        by_type = defaultdict(list)
        for a in analyses:
            by_type[a.project_type].append(a)

        report = []
        report.append("# SAM Exhaustive Project Analysis")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"\nTotal Projects Analyzed: **{len(analyses)}**\n")

        # Summary stats
        report.append("## Summary Statistics\n")
        report.append(f"- **Active projects** (modified <7 days): {len(by_status.get('active', []))}")
        report.append(f"- **Recent projects** (modified <30 days): {len(by_status.get('recent', []))}")
        report.append(f"- **Stale projects** (modified <180 days): {len(by_status.get('stale', []))}")
        report.append(f"- **Abandoned projects** (>180 days): {len(by_status.get('abandoned', []))}")
        report.append(f"- **Projects with tests**: {len([a for a in analyses if a.has_tests])}")
        report.append(f"- **Projects with CI/CD**: {len([a for a in analyses if a.has_ci])}")
        report.append(f"- **Total code files**: {sum(a.code_files for a in analyses):,}")
        report.append(f"- **Total lines of code**: {sum(a.total_lines for a in analyses):,}")
        report.append("")

        # Top 30 most important
        report.append("## Top 30 Most Important Projects\n")
        report.append("| Rank | Project | Type | Status | Score | Languages |")
        report.append("|------|---------|------|--------|-------|-----------|")
        for i, a in enumerate(by_importance[:30], 1):
            pin = "📌" if a.auto_pinned else "⭐" if a.auto_starred else ""
            langs = ", ".join(a.languages[:2]) if a.languages else "-"
            report.append(f"| {i} | {pin} **{a.name}** | {a.project_type} | {a.status} | {a.importance_score:.0f} | {langs} |")
        report.append("")

        # By project type
        report.append("## Projects by Type\n")
        for proj_type in sorted(by_type.keys(), key=lambda t: -len(by_type[t])):
            projects = by_type[proj_type]
            report.append(f"### {proj_type.title()} ({len(projects)} projects)\n")
            # Show top 10 for each type
            for a in sorted(projects, key=lambda x: -x.importance_score)[:10]:
                status_emoji = {"active": "🟢", "recent": "🟡", "stale": "🟠", "abandoned": "🔴"}.get(a.status, "⚪")
                report.append(f"- {status_emoji} **{a.name}** - {a.description[:80] if a.description else a.purpose[:80] if a.purpose else 'No description'}")
            if len(projects) > 10:
                report.append(f"- ... and {len(projects) - 10} more")
            report.append("")

        # Active projects detail
        report.append("## Active Projects (Detail)\n")
        for a in sorted(by_status.get('active', []), key=lambda x: -x.importance_score):
            report.append(f"### {a.name}\n")
            report.append(f"- **Path**: `{a.path}`")
            report.append(f"- **Type**: {a.project_type} | **Complexity**: {a.complexity}")
            report.append(f"- **Languages**: {', '.join(a.languages) if a.languages else 'Unknown'}")
            report.append(f"- **Frameworks**: {', '.join(a.frameworks) if a.frameworks else 'None detected'}")
            if a.description:
                report.append(f"- **Description**: {a.description[:200]}")
            report.append(f"- **Files**: {a.code_files} code files, {a.total_lines:,} lines")
            if a.depends_on:
                report.append(f"- **Depends on**: {', '.join(Path(p).name for p in a.depends_on[:5])}")
            if a.tags:
                report.append(f"- **Tags**: {', '.join(a.tags)}")
            report.append("")

        # Relationships section
        report.append("## Project Relationships\n")
        deps = [(p, a) for p, a in self.projects.items() if a.depends_on or a.depended_by]
        if deps:
            report.append("Projects with detected dependencies:\n")
            for proj_path, analysis in sorted(deps, key=lambda x: -len(x[1].depended_by)):
                if analysis.depended_by:
                    report.append(f"- **{analysis.name}** is used by: {', '.join(Path(p).name for p in analysis.depended_by[:5])}")
        report.append("")

        # Write report
        REPORT_FILE.write_text('\n'.join(report))
        print(f"Report written to: {REPORT_FILE}")


def main():
    import sys

    analyzer = ExhaustiveAnalyzer()

    if len(sys.argv) < 2:
        print("SAM Exhaustive Project Analyzer")
        print("-" * 40)
        print("\nThis tool performs deep analysis of ALL discovered projects.")
        print("It will:")
        print("  - Analyze tech stack, purpose, and health of each project")
        print("  - Find relationships between projects")
        print("  - Auto-categorize and tag everything")
        print("  - Auto-star important projects")
        print("  - Generate a comprehensive report")
        print("\nCommands:")
        print("  run     - Run full exhaustive analysis (takes a while)")
        print("  summary - Show summary of last analysis")
        print("  report  - Open the generated report")
        return

    cmd = sys.argv[1]

    if cmd == "run":
        summary = analyzer.run_full_analysis()
        print("\n" + "=" * 60)
        print("EXHAUSTIVE ANALYSIS COMPLETE")
        print("=" * 60)
        print(json.dumps(summary, indent=2))

    elif cmd == "summary":
        if INVENTORY_FILE.exists():
            inventory = json.load(open(INVENTORY_FILE))
            print(f"Last analysis: {inventory.get('generated_at', 'unknown')}")
            print(f"Total projects: {inventory.get('total_projects', 0)}")
        else:
            print("No analysis found. Run 'exhaustive_analyzer.py run' first.")

    elif cmd == "report":
        if REPORT_FILE.exists():
            import subprocess
            subprocess.run(["open", str(REPORT_FILE)])
        else:
            print("No report found. Run 'exhaustive_analyzer.py run' first.")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
