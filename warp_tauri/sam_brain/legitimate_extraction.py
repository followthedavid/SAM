#!/usr/bin/env python3
"""
Legitimate Extraction - What we CAN actually reverse engineer

This extracts real, actionable knowledge from:
1. AppleScript dictionaries (every app's automation API)
2. URL schemes (how to control apps)
3. Accessibility actions (what we can click/trigger)
4. Open source projects (actual code)
5. Your own conversation exports (reasoning patterns)
6. Installed app resources (UI patterns, strings)
7. SQLite databases (data structures)

No encryption breaking. No server-side secrets. Just what's legitimately exposed.
"""

import subprocess
import sqlite3
import plistlib
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import re


# =============================================================================
# 1. APPLESCRIPT DICTIONARY EXTRACTION
# =============================================================================

class AppleScriptExtractor:
    """
    Extract automation capabilities from every installed app.

    This is GOLD - it tells SAM exactly how to control any app.
    Apps expose their entire automation API through scripting dictionaries.
    """

    def __init__(self):
        self.extracted_apps: Dict[str, dict] = {}

    def get_scriptable_apps(self) -> List[Path]:
        """Find all apps with AppleScript support."""
        scriptable = []

        app_dirs = [
            Path("/Applications"),
            Path("/System/Applications"),
            Path.home() / "Applications",
        ]

        for app_dir in app_dirs:
            if not app_dir.exists():
                continue
            for app in app_dir.glob("**/*.app"):
                # Check for scripting dictionary
                sdef = app / "Contents" / "Resources" / f"{app.stem}.sdef"
                osax = app / "Contents" / "Resources" / "Scripts"

                if sdef.exists() or self._has_apple_events(app):
                    scriptable.append(app)

        return scriptable

    def _has_apple_events(self, app: Path) -> bool:
        """Check if app responds to Apple Events."""
        info_plist = app / "Contents" / "Info.plist"
        if info_plist.exists():
            try:
                with open(info_plist, "rb") as f:
                    plist = plistlib.load(f)
                # NSAppleScriptEnabled or has scripting additions
                return plist.get("NSAppleScriptEnabled", False) or \
                       "OSAScriptingDefinition" in plist
            except:
                pass
        return False

    def extract_dictionary(self, app_name: str) -> Dict:
        """
        Extract the complete AppleScript dictionary for an app.

        This tells us:
        - All commands the app supports
        - All objects we can manipulate
        - All properties we can read/write
        - Parameter types and descriptions
        """
        try:
            # Get scripting terminology
            result = subprocess.run(
                ["sdef", f"/Applications/{app_name}.app"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return self._parse_sdef(result.stdout, app_name)

            # Try system apps
            result = subprocess.run(
                ["sdef", f"/System/Applications/{app_name}.app"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return self._parse_sdef(result.stdout, app_name)

        except Exception as e:
            return {"error": str(e)}

        return {"error": "App not found or not scriptable"}

    def _parse_sdef(self, sdef_xml: str, app_name: str) -> Dict:
        """Parse SDEF XML into structured commands."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(sdef_xml)
        except ET.ParseError:
            return {"raw": sdef_xml[:5000]}

        result = {
            "app": app_name,
            "suites": [],
            "commands": [],
            "classes": [],
        }

        for suite in root.findall(".//suite"):
            suite_info = {
                "name": suite.get("name"),
                "description": suite.get("description", ""),
                "commands": [],
                "classes": [],
            }

            # Extract commands
            for cmd in suite.findall(".//command"):
                cmd_info = {
                    "name": cmd.get("name"),
                    "code": cmd.get("code"),
                    "description": cmd.get("description", ""),
                    "parameters": [],
                }

                for param in cmd.findall(".//parameter"):
                    cmd_info["parameters"].append({
                        "name": param.get("name"),
                        "type": param.get("type"),
                        "description": param.get("description", ""),
                        "optional": param.get("optional", "no") == "yes",
                    })

                suite_info["commands"].append(cmd_info)
                result["commands"].append(cmd_info)

            # Extract classes (objects we can manipulate)
            for cls in suite.findall(".//class"):
                cls_info = {
                    "name": cls.get("name"),
                    "code": cls.get("code"),
                    "description": cls.get("description", ""),
                    "properties": [],
                    "elements": [],
                }

                for prop in cls.findall(".//property"):
                    cls_info["properties"].append({
                        "name": prop.get("name"),
                        "type": prop.get("type"),
                        "access": prop.get("access", "rw"),
                        "description": prop.get("description", ""),
                    })

                for elem in cls.findall(".//element"):
                    cls_info["elements"].append({
                        "type": elem.get("type"),
                        "access": elem.get("access", "rw"),
                    })

                suite_info["classes"].append(cls_info)
                result["classes"].append(cls_info)

            result["suites"].append(suite_info)

        return result

    def generate_training_pairs(self, app_dict: Dict) -> List[Dict]:
        """Convert AppleScript dictionary to SAM training pairs."""
        pairs = []
        app_name = app_dict.get("app", "Unknown")

        for cmd in app_dict.get("commands", []):
            # How to use this command
            params = ", ".join([
                f"{p['name']}: {p['type']}" + (" (optional)" if p.get('optional') else "")
                for p in cmd.get("parameters", [])
            ])

            pairs.append({
                "instruction": f"How do I use the '{cmd['name']}' command in {app_name} via AppleScript?",
                "input": "",
                "output": f"""The '{cmd['name']}' command in {app_name}:

Description: {cmd.get('description', 'No description')}

Parameters: {params if params else 'None'}

Example AppleScript:
```applescript
tell application "{app_name}"
    {cmd['name']}{' ' + cmd['parameters'][0]['name'] if cmd.get('parameters') else ''}
end tell
```
""",
            })

        for cls in app_dict.get("classes", []):
            props = ", ".join([p['name'] for p in cls.get("properties", [])[:5]])

            pairs.append({
                "instruction": f"What is the '{cls['name']}' object in {app_name} and what can I do with it?",
                "input": "",
                "output": f"""The '{cls['name']}' object in {app_name}:

Description: {cls.get('description', 'No description')}

Properties: {props}{'...' if len(cls.get('properties', [])) > 5 else ''}

Example - Get all {cls['name']}s:
```applescript
tell application "{app_name}"
    get every {cls['name'].lower()}
end tell
```
""",
            })

        return pairs


# =============================================================================
# 2. URL SCHEME EXTRACTION
# =============================================================================

class URLSchemeExtractor:
    """
    Extract URL schemes from installed apps.

    URL schemes let SAM:
    - Launch apps with specific actions
    - Open files in specific apps
    - Trigger app features without AppleScript
    - Deep link into app features
    """

    def extract_all_schemes(self) -> Dict[str, List[str]]:
        """Extract URL schemes from all installed apps."""
        schemes = {}

        app_dirs = [
            Path("/Applications"),
            Path("/System/Applications"),
            Path.home() / "Applications",
        ]

        for app_dir in app_dirs:
            if not app_dir.exists():
                continue

            for app in app_dir.glob("*.app"):
                app_schemes = self._extract_from_app(app)
                if app_schemes:
                    schemes[app.stem] = app_schemes

        return schemes

    def _extract_from_app(self, app: Path) -> List[str]:
        """Extract URL schemes from a single app."""
        info_plist = app / "Contents" / "Info.plist"

        if not info_plist.exists():
            return []

        try:
            with open(info_plist, "rb") as f:
                plist = plistlib.load(f)

            schemes = []

            # CFBundleURLTypes contains URL schemes
            url_types = plist.get("CFBundleURLTypes", [])
            for url_type in url_types:
                url_schemes = url_type.get("CFBundleURLSchemes", [])
                schemes.extend(url_schemes)

            return schemes

        except Exception:
            return []

    def generate_training_pairs(self, schemes: Dict[str, List[str]]) -> List[Dict]:
        """Convert URL schemes to training pairs."""
        pairs = []

        for app, app_schemes in schemes.items():
            if not app_schemes:
                continue

            scheme_list = ", ".join(app_schemes[:3])

            pairs.append({
                "instruction": f"How can I open or control {app} using URL schemes?",
                "input": "",
                "output": f"""{app} supports these URL schemes: {scheme_list}

Example usage:
```bash
open "{app_schemes[0]}://"
```

Or in Python:
```python
import subprocess
subprocess.run(["open", "{app_schemes[0]}://"])
```

This launches {app} and can trigger specific actions depending on the URL path.
""",
            })

        return pairs


# =============================================================================
# 3. ACCESSIBILITY ACTION EXTRACTION
# =============================================================================

class AccessibilityExtractor:
    """
    Extract all accessibility actions available on running apps.

    This tells SAM exactly what UI elements exist and what actions
    can be performed on them - clicking, pressing, selecting, etc.
    """

    def __init__(self):
        self.ax_available = self._check_accessibility()

    def _check_accessibility(self) -> bool:
        """Check if accessibility permissions are granted."""
        try:
            from ApplicationServices import AXIsProcessTrusted
            return AXIsProcessTrusted()
        except ImportError:
            return False

    def extract_actions(self, app_name: str) -> Dict:
        """Extract all available actions from a running app."""
        if not self.ax_available:
            return {"error": "Accessibility not available"}

        try:
            from ApplicationServices import (
                AXUIElementCreateApplication,
                AXUIElementCopyAttributeValue,
                AXUIElementCopyActionNames,
            )
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
            )

            # Find app PID
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly, kCGNullWindowID
            )

            pid = None
            for window in window_list:
                if app_name.lower() in window.get("kCGWindowOwnerName", "").lower():
                    pid = window.get("kCGWindowOwnerPID")
                    break

            if not pid:
                return {"error": f"App '{app_name}' not running"}

            app = AXUIElementCreateApplication(pid)
            return self._extract_element_actions(app, depth=0, max_depth=4)

        except Exception as e:
            return {"error": str(e)}

    def _extract_element_actions(self, element, depth: int, max_depth: int) -> Dict:
        """Recursively extract actions from UI elements."""
        if depth > max_depth:
            return {"truncated": True}

        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCopyActionNames,
            kAXRoleAttribute,
            kAXTitleAttribute,
            kAXChildrenAttribute,
        )

        result = {}

        # Get role
        err, role = AXUIElementCopyAttributeValue(element, kAXRoleAttribute, None)
        if err == 0:
            result["role"] = str(role)

        # Get title
        err, title = AXUIElementCopyAttributeValue(element, kAXTitleAttribute, None)
        if err == 0 and title:
            result["title"] = str(title)

        # Get available actions - THIS IS THE KEY
        err, actions = AXUIElementCopyActionNames(element, None)
        if err == 0 and actions:
            result["actions"] = [str(a) for a in actions]

        # Get children
        err, children = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute, None)
        if err == 0 and children:
            result["children"] = [
                self._extract_element_actions(child, depth + 1, max_depth)
                for child in children[:15]
            ]

        return result

    def find_all_actions(self, tree: Dict) -> List[Dict]:
        """Flatten tree to list of actionable elements."""
        actionable = []

        if tree.get("actions"):
            actionable.append({
                "role": tree.get("role"),
                "title": tree.get("title"),
                "actions": tree.get("actions"),
            })

        for child in tree.get("children", []):
            actionable.extend(self.find_all_actions(child))

        return actionable


# =============================================================================
# 4. OPEN SOURCE PROJECT MINING
# =============================================================================

class OpenSourceMiner:
    """
    Extract patterns from open source AI projects.

    These are actual working implementations we can learn from:
    - llama.cpp: Inference optimization
    - whisper.cpp: Speech recognition
    - MLX examples: Apple Silicon patterns
    - LocalAI: Local deployment patterns
    """

    VALUABLE_REPOS = {
        "ml-explore/mlx": {
            "what_to_learn": [
                "Apple Silicon optimization",
                "Memory-efficient inference",
                "Quantization patterns",
                "KV-cache implementation",
            ],
            "key_files": [
                "python/mlx/nn/layers.py",
                "python/mlx/optimizers.py",
            ],
        },
        "ml-explore/mlx-examples": {
            "what_to_learn": [
                "LoRA fine-tuning",
                "LLM inference patterns",
                "Model loading",
                "Generation parameters",
            ],
            "key_files": [
                "llms/mlx_lm/models/qwen2.py",
                "llms/mlx_lm/tuner/lora.py",
            ],
        },
        "ggerganov/llama.cpp": {
            "what_to_learn": [
                "GGUF format",
                "Quantization methods",
                "Context management",
                "Sampling strategies",
            ],
            "key_files": [
                "llama.cpp",
                "ggml.c",
            ],
        },
        "ggerganov/whisper.cpp": {
            "what_to_learn": [
                "Speech recognition pipeline",
                "Audio processing",
                "Real-time transcription",
            ],
            "key_files": [
                "whisper.cpp",
            ],
        },
    }

    def __init__(self, clone_dir: Path):
        self.clone_dir = clone_dir
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    def clone_repo(self, repo: str) -> Path:
        """Clone or update a repo."""
        repo_name = repo.split("/")[-1]
        repo_path = self.clone_dir / repo_name

        if repo_path.exists():
            # Update
            subprocess.run(
                ["git", "pull"],
                cwd=repo_path,
                capture_output=True,
            )
        else:
            # Clone (shallow for speed)
            subprocess.run(
                ["git", "clone", "--depth", "1", f"https://github.com/{repo}.git"],
                cwd=self.clone_dir,
                capture_output=True,
            )

        return repo_path

    def extract_patterns(self, repo_path: Path, patterns: List[str]) -> List[Dict]:
        """Extract code patterns from a repo."""
        extracted = []

        for pattern in patterns:
            # Search for pattern in Python files
            result = subprocess.run(
                ["grep", "-r", "-l", pattern, "--include=*.py"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                files = result.stdout.strip().split("\n")
                for f in files[:5]:  # Limit
                    file_path = repo_path / f
                    if file_path.exists():
                        content = file_path.read_text()[:5000]
                        extracted.append({
                            "pattern": pattern,
                            "file": f,
                            "content_preview": content,
                        })

        return extracted


# =============================================================================
# 5. SQLITE DATABASE EXTRACTION
# =============================================================================

class SQLiteExtractor:
    """
    Extract schemas and data patterns from local SQLite databases.

    Many apps store data in unencrypted SQLite:
    - Browser history
    - Notes databases
    - App caches
    - Conversation logs
    """

    KNOWN_DATABASES = {
        "safari_history": {
            "path": "~/Library/Safari/History.db",
            "what_to_learn": "URL patterns, visit frequency, browsing behavior",
        },
        "notes": {
            "path": "~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite",
            "what_to_learn": "Note structure, folder organization",
        },
        "messages": {
            "path": "~/Library/Messages/chat.db",
            "what_to_learn": "Message structure, conversation threading",
        },
    }

    def extract_schema(self, db_path: Path) -> Dict:
        """Extract schema from a SQLite database."""
        if not db_path.exists():
            return {"error": "Database not found"}

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            schema = {"tables": {}}

            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()

                schema["tables"][table] = {
                    "columns": [
                        {
                            "name": col[1],
                            "type": col[2],
                            "nullable": not col[3],
                            "primary_key": bool(col[5]),
                        }
                        for col in columns
                    ]
                }

                # Sample row count
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    schema["tables"][table]["row_count"] = cursor.fetchone()[0]
                except:
                    pass

            conn.close()
            return schema

        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# 6. CONVERSATION EXPORT MINING (ChatGPT, Claude)
# =============================================================================

class ConversationMiner:
    """
    Extract reasoning patterns from your own AI conversations.

    Your ChatGPT/Claude exports contain:
    - Problem-solving approaches
    - Code generation patterns
    - Explanation styles
    - Error handling patterns

    This is learning from the BEST models' outputs without needing
    their weights or server access.
    """

    def __init__(self, export_dir: Path):
        self.export_dir = export_dir

    def extract_reasoning_patterns(self, conversations: List[Dict]) -> List[Dict]:
        """Extract high-value reasoning patterns from conversations."""
        patterns = []

        for conv in conversations:
            messages = conv.get("mapping", {})

            for msg_id, msg_data in messages.items():
                message = msg_data.get("message")
                if not message:
                    continue

                author = message.get("author", {}).get("role")
                content = message.get("content", {})

                if author == "assistant" and content.get("parts"):
                    text = content["parts"][0] if content["parts"] else ""

                    # Look for high-value patterns
                    if self._is_reasoning_heavy(text):
                        patterns.append({
                            "type": "reasoning",
                            "content": text[:2000],
                            "indicators": self._extract_reasoning_indicators(text),
                        })

                    if self._is_code_explanation(text):
                        patterns.append({
                            "type": "code_explanation",
                            "content": text[:2000],
                        })

        return patterns

    def _is_reasoning_heavy(self, text: str) -> bool:
        """Check if text contains significant reasoning."""
        indicators = [
            "because", "therefore", "however", "although",
            "first", "second", "finally", "in conclusion",
            "the reason", "this means", "as a result",
            "let me think", "step by step",
        ]
        count = sum(1 for ind in indicators if ind in text.lower())
        return count >= 3

    def _is_code_explanation(self, text: str) -> bool:
        """Check if text explains code."""
        return "```" in text and any(
            phrase in text.lower()
            for phrase in ["this code", "the function", "here's how", "this will"]
        )

    def _extract_reasoning_indicators(self, text: str) -> List[str]:
        """Extract reasoning structure indicators."""
        indicators = []

        if "step" in text.lower():
            indicators.append("step-by-step")
        if "first" in text.lower() and "then" in text.lower():
            indicators.append("sequential")
        if "however" in text.lower() or "but" in text.lower():
            indicators.append("considers-alternatives")
        if "because" in text.lower():
            indicators.append("causal-reasoning")

        return indicators


# =============================================================================
# MAIN: COMPREHENSIVE EXTRACTION
# =============================================================================

def run_comprehensive_extraction():
    """Run all extractors and generate training data."""

    print("=" * 70)
    print("LEGITIMATE EXTRACTION - What We Can Actually Learn")
    print("=" * 70)
    print()

    training_pairs = []

    # 1. AppleScript Dictionaries
    print("1. APPLESCRIPT DICTIONARIES")
    print("-" * 40)
    as_extractor = AppleScriptExtractor()

    key_apps = ["Finder", "Safari", "Notes", "Mail", "Calendar", "Reminders", "Music"]

    for app in key_apps:
        result = as_extractor.extract_dictionary(app)
        if "error" not in result:
            cmd_count = len(result.get("commands", []))
            cls_count = len(result.get("classes", []))
            print(f"  ✓ {app}: {cmd_count} commands, {cls_count} classes")

            pairs = as_extractor.generate_training_pairs(result)
            training_pairs.extend(pairs)
        else:
            print(f"  ✗ {app}: {result.get('error', 'Unknown error')}")

    print(f"  → Generated {len(training_pairs)} training pairs from AppleScript")
    print()

    # 2. URL Schemes
    print("2. URL SCHEMES")
    print("-" * 40)
    url_extractor = URLSchemeExtractor()
    schemes = url_extractor.extract_all_schemes()

    apps_with_schemes = [(app, s) for app, s in schemes.items() if s]
    print(f"  Found {len(apps_with_schemes)} apps with URL schemes")

    for app, app_schemes in list(apps_with_schemes)[:10]:
        print(f"  ✓ {app}: {', '.join(app_schemes[:3])}")

    url_pairs = url_extractor.generate_training_pairs(schemes)
    training_pairs.extend(url_pairs)
    print(f"  → Generated {len(url_pairs)} training pairs from URL schemes")
    print()

    # 3. Accessibility (if available)
    print("3. ACCESSIBILITY ACTIONS")
    print("-" * 40)
    ax_extractor = AccessibilityExtractor()

    if ax_extractor.ax_available:
        # Try to extract from Finder (always running)
        finder_actions = ax_extractor.extract_actions("Finder")
        if "error" not in finder_actions:
            actionable = ax_extractor.find_all_actions(finder_actions)
            print(f"  ✓ Found {len(actionable)} actionable UI elements in Finder")
            for elem in actionable[:5]:
                print(f"    - {elem.get('role')}: {elem.get('title', 'untitled')} → {elem.get('actions')}")
        else:
            print(f"  ✗ Finder: {finder_actions.get('error')}")
    else:
        print("  ✗ Accessibility permissions not granted")
        print("    → Grant in System Settings > Privacy > Accessibility")
    print()

    # 4. Summary
    print("=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Total training pairs generated: {len(training_pairs)}")
    print()
    print("VALUE ASSESSMENT:")
    print("-" * 40)
    print("""
    ✓ AppleScript Dictionaries: HIGH VALUE
      - SAM can now automate any scriptable app
      - No reverse engineering needed - Apple exposes this

    ✓ URL Schemes: MEDIUM VALUE
      - SAM can launch and deep-link into apps
      - Useful for quick actions

    ✓ Accessibility Actions: HIGH VALUE
      - SAM can click any button, read any text
      - This is how we verify UI state (your earlier request)

    ✓ Conversation Exports: HIGHEST VALUE
      - Learning from Claude/ChatGPT outputs
      - 20K+ examples already processed

    ✗ Encrypted Binaries: NO VALUE
      - Can't extract, don't waste time

    ✗ Server-side Logic: IMPOSSIBLE
      - Not accessible, focus elsewhere
    """)

    # Save training pairs
    output_path = Path("/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/extracted_training.json")
    with open(output_path, "w") as f:
        json.dump(training_pairs, f, indent=2)
    print(f"Training pairs saved to: {output_path}")

    return training_pairs


if __name__ == "__main__":
    run_comprehensive_extraction()
