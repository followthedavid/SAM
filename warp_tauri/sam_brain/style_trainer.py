#!/usr/bin/env python3
"""
SAM Style Trainer - Learn from user's coding patterns.

Extracts patterns from starred/active projects to create training data
for fine-tuning or LoRA adaptation.
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
INVENTORY_FILE = SCRIPT_DIR / "exhaustive_analysis" / "master_inventory.json"
TRAINING_DIR = SCRIPT_DIR / "training_data"
TRAINING_DIR.mkdir(exist_ok=True)

class StyleExtractor:
    """Extract coding style patterns from projects."""

    def __init__(self):
        self.inventory = json.load(open(INVENTORY_FILE))
        self.projects = self.inventory["projects"]
        self.patterns = defaultdict(list)
        self.samples = []

    def get_active_projects(self):
        """Get projects worth learning from (starred, active, high score)."""
        worthy = []
        for path, data in self.projects.items():
            # Skip vendor/node_modules
            if "node_modules" in path or "vendor" in path or ".venv" in path:
                continue

            score = data.get("importance_score", 0)
            status = data.get("status", "")
            starred = data.get("starred", False)

            # Include if: starred, active, recent, or high score
            if starred or status in ["active", "recent"] or score >= 50:
                worthy.append((path, data))

        return sorted(worthy, key=lambda x: -x[1].get("importance_score", 0))

    def extract_python_patterns(self, file_path):
        """Extract Python coding patterns."""
        try:
            content = Path(file_path).read_text(errors='ignore')
            lines = content.split('\n')
        except:
            return None

        patterns = {
            "file": str(file_path),
            "docstrings": [],
            "function_defs": [],
            "class_defs": [],
            "imports": [],
            "comments": [],
            "type_hints": False,
            "f_strings": False,
            "list_comprehensions": 0,
            "error_handling": 0,
            "decorators": [],
        }

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Imports
            if stripped.startswith(("import ", "from ")):
                patterns["imports"].append(stripped)

            # Function definitions with context
            if stripped.startswith("def "):
                # Get docstring if present
                func_lines = [stripped]
                if i + 1 < len(lines) and '"""' in lines[i + 1]:
                    j = i + 1
                    doc_lines = []
                    while j < len(lines) and j < i + 10:
                        doc_lines.append(lines[j].strip())
                        if j > i + 1 and '"""' in lines[j]:
                            break
                        j += 1
                    func_lines.extend(doc_lines)
                patterns["function_defs"].append('\n'.join(func_lines))

            # Class definitions
            if stripped.startswith("class "):
                patterns["class_defs"].append(stripped)

            # Comments (non-docstring)
            if stripped.startswith("#") and not stripped.startswith("#!"):
                patterns["comments"].append(stripped)

            # Type hints
            if ": " in stripped and ("-> " in stripped or re.search(r':\s*\w+\s*=', stripped)):
                patterns["type_hints"] = True

            # F-strings
            if 'f"' in stripped or "f'" in stripped:
                patterns["f_strings"] = True

            # List comprehensions
            if re.search(r'\[.*for.*in.*\]', stripped):
                patterns["list_comprehensions"] += 1

            # Error handling
            if stripped.startswith(("try:", "except ", "raise ")):
                patterns["error_handling"] += 1

            # Decorators
            if stripped.startswith("@"):
                patterns["decorators"].append(stripped)

        return patterns

    def extract_rust_patterns(self, file_path):
        """Extract Rust coding patterns."""
        try:
            content = Path(file_path).read_text(errors='ignore')
            lines = content.split('\n')
        except:
            return None

        patterns = {
            "file": str(file_path),
            "function_defs": [],
            "struct_defs": [],
            "impl_blocks": [],
            "uses": [],
            "macros": [],
            "derives": [],
            "error_handling": 0,
        }

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("use "):
                patterns["uses"].append(stripped)
            if stripped.startswith("fn "):
                patterns["function_defs"].append(stripped)
            if stripped.startswith("struct "):
                patterns["struct_defs"].append(stripped)
            if stripped.startswith("impl "):
                patterns["impl_blocks"].append(stripped)
            if stripped.startswith("#[derive"):
                patterns["derives"].append(stripped)
            if re.search(r'\w+!\s*\(', stripped):
                patterns["macros"].append(stripped[:80])
            if "?" in stripped or ".unwrap()" in stripped or "match " in stripped:
                patterns["error_handling"] += 1

        return patterns

    def extract_typescript_patterns(self, file_path):
        """Extract TypeScript/JavaScript patterns."""
        try:
            content = Path(file_path).read_text(errors='ignore')
            lines = content.split('\n')
        except:
            return None

        patterns = {
            "file": str(file_path),
            "function_defs": [],
            "class_defs": [],
            "imports": [],
            "interfaces": [],
            "arrow_functions": 0,
            "async_await": 0,
            "jsx": False,
        }

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("import "):
                patterns["imports"].append(stripped)
            if "function " in stripped:
                patterns["function_defs"].append(stripped[:100])
            if stripped.startswith("class "):
                patterns["class_defs"].append(stripped)
            if stripped.startswith("interface "):
                patterns["interfaces"].append(stripped)
            if "=>" in stripped:
                patterns["arrow_functions"] += 1
            if "async " in stripped or "await " in stripped:
                patterns["async_await"] += 1
            if "</" in stripped or "/>" in stripped:
                patterns["jsx"] = True

        return patterns

    def analyze_project(self, project_path, data):
        """Analyze a single project for coding patterns."""
        path = Path(project_path)
        if not path.exists():
            return None

        result = {
            "project": project_path,
            "name": data.get("name", path.name),
            "languages": data.get("languages", []),
            "python_patterns": [],
            "rust_patterns": [],
            "ts_patterns": [],
        }

        # Find code files (limit to prevent OOM)
        files_checked = 0
        max_files = 50

        for ext, extractor, key in [
            (".py", self.extract_python_patterns, "python_patterns"),
            (".rs", self.extract_rust_patterns, "rust_patterns"),
            (".ts", self.extract_typescript_patterns, "ts_patterns"),
            (".tsx", self.extract_typescript_patterns, "ts_patterns"),
        ]:
            for f in path.rglob(f"*{ext}"):
                if files_checked >= max_files:
                    break
                if "node_modules" in str(f) or ".git" in str(f) or "venv" in str(f):
                    continue

                patterns = extractor(f)
                if patterns:
                    result[key].append(patterns)
                    files_checked += 1

        return result

    def generate_training_samples(self):
        """Generate training samples for model fine-tuning."""
        projects = self.get_active_projects()
        print(f"Analyzing {len(projects)} worthy projects...")

        all_patterns = []
        samples = []

        for i, (path, data) in enumerate(projects[:100]):  # Top 100
            if i % 10 == 0:
                print(f"Progress: {i}/{min(len(projects), 100)}")

            result = self.analyze_project(path, data)
            if result:
                all_patterns.append(result)

                # Generate instruction-following samples
                for py in result.get("python_patterns", []):
                    for func in py.get("function_defs", [])[:3]:
                        if len(func) > 50:  # Meaningful functions
                            samples.append({
                                "instruction": "Write a Python function with proper documentation.",
                                "input": f"Function signature: {func.split('(')[0]}",
                                "output": func,
                                "source": result["name"],
                            })

                for rust in result.get("rust_patterns", []):
                    for func in rust.get("function_defs", [])[:3]:
                        samples.append({
                            "instruction": "Write a Rust function.",
                            "input": f"Function: {func.split('(')[0] if '(' in func else func}",
                            "output": func,
                            "source": result["name"],
                        })

        return all_patterns, samples

    def create_style_profile(self, patterns):
        """Create a coding style profile from extracted patterns."""
        profile = {
            "python": {
                "uses_type_hints": 0,
                "uses_f_strings": 0,
                "avg_docstring_rate": 0,
                "common_decorators": Counter(),
                "common_imports": Counter(),
                "comprehension_heavy": False,
            },
            "rust": {
                "common_derives": Counter(),
                "error_handling_style": "?",  # vs unwrap vs match
                "common_uses": Counter(),
            },
            "typescript": {
                "arrow_vs_function": 0,
                "uses_async": 0,
                "uses_interfaces": 0,
            },
            "general": {
                "prefers_explicit_types": False,
                "comment_density": 0,
                "function_length_avg": 0,
            }
        }

        type_hint_count = 0
        f_string_count = 0
        total_py = 0

        for proj in patterns:
            for py in proj.get("python_patterns", []):
                total_py += 1
                if py.get("type_hints"):
                    type_hint_count += 1
                if py.get("f_strings"):
                    f_string_count += 1
                for dec in py.get("decorators", []):
                    profile["python"]["common_decorators"][dec] += 1
                for imp in py.get("imports", [])[:5]:
                    profile["python"]["common_imports"][imp.split()[1] if len(imp.split()) > 1 else imp] += 1

        if total_py > 0:
            profile["python"]["uses_type_hints"] = type_hint_count / total_py
            profile["python"]["uses_f_strings"] = f_string_count / total_py

        return profile

    def save_training_data(self, patterns, samples, profile):
        """Save all training data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        # Save patterns
        with open(TRAINING_DIR / f"patterns_{timestamp}.json", "w") as f:
            json.dump(patterns, f, indent=2, default=str)

        # Save samples in JSONL format (for training)
        with open(TRAINING_DIR / "training_samples.jsonl", "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")

        # Save style profile
        profile_serializable = {
            "python": {
                "uses_type_hints": profile["python"]["uses_type_hints"],
                "uses_f_strings": profile["python"]["uses_f_strings"],
                "common_decorators": dict(profile["python"]["common_decorators"].most_common(10)),
                "common_imports": dict(profile["python"]["common_imports"].most_common(20)),
            },
            "rust": {
                "common_derives": dict(profile["rust"]["common_derives"].most_common(10)),
                "common_uses": dict(profile["rust"]["common_uses"].most_common(10)),
            },
            "typescript": profile["typescript"],
            "general": profile["general"],
        }

        with open(TRAINING_DIR / "style_profile.json", "w") as f:
            json.dump(profile_serializable, f, indent=2)

        print(f"\nTraining data saved to {TRAINING_DIR}/")
        print(f"  - patterns_{timestamp}.json ({len(patterns)} projects)")
        print(f"  - training_samples.jsonl ({len(samples)} samples)")
        print(f"  - style_profile.json")

        return len(patterns), len(samples)


def main():
    extractor = StyleExtractor()

    print("="*60)
    print("SAM Style Trainer - Extracting Your Coding Patterns")
    print("="*60)

    patterns, samples = extractor.generate_training_samples()
    profile = extractor.create_style_profile(patterns)

    print("\n" + "="*60)
    print("STYLE PROFILE SUMMARY")
    print("="*60)
    print(f"\nPython Style:")
    print(f"  Type hints usage: {profile['python']['uses_type_hints']*100:.1f}%")
    print(f"  F-string usage: {profile['python']['uses_f_strings']*100:.1f}%")
    print(f"  Top decorators: {list(profile['python']['common_decorators'].most_common(5))}")

    extractor.save_training_data(patterns, samples, profile)

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Review training_samples.jsonl for quality")
    print("2. Use samples to fine-tune via Ollama Modelfile")
    print("3. Or create LoRA adapter with the samples")


if __name__ == "__main__":
    main()
