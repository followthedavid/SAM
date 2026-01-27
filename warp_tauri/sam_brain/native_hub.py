#!/usr/bin/env python3
"""
SAM Native Hub
==============
The cohesive native macOS system that unifies all SAM capabilities.
This is the master entry point for the entire SAM ecosystem.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time

# Import all SAM systems
sys.path.insert(0, str(Path(__file__).parent))

from unified_orchestrator import UnifiedOrchestrator, ProjectStatus, ProjectCategory
from parity_system import CapabilityRouter, Capability, EscalationLearner
try:
    from auto_learner import AutoLearner
    HAS_AUTO_LEARNER = True
except ImportError:
    HAS_AUTO_LEARNER = False
    AutoLearner = None
from tool_system import ToolRegistry


class ParityManager:
    """Wrapper that provides parity stats from CapabilityRouter."""

    def __init__(self):
        self.router = CapabilityRouter()
        data_dir = Path(__file__).parent / "data" / "escalations"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.learner = EscalationLearner(data_dir)
        self.capabilities = self._build_capability_map()

    def _build_capability_map(self) -> Dict[str, Dict]:
        """Build capability map with SAM handling status."""
        cap_map = {}
        # SAM handles these locally
        sam_handles_caps = {
            Capability.FILE_READ, Capability.FILE_WRITE, Capability.FILE_EDIT,
            Capability.GLOB_SEARCH, Capability.GREP_SEARCH, Capability.BASH_EXECUTE,
            Capability.GIT_OPERATIONS, Capability.WEB_FETCH, Capability.CONVERSATION,
            Capability.VOICE_INTERACTION
        }
        for cap in Capability:
            sam_handles = cap in sam_handles_caps
            cap_map[cap.value] = {
                "sam_handles": sam_handles,
                "escalation_reason": "complex reasoning required" if not sam_handles else None
            }
        return cap_map

    def detect_capabilities(self, request: str) -> List[str]:
        """Detect what capabilities a request needs."""
        return [cap.value for cap in self.router.detect_capabilities(request)]

    def record_escalation(self, request: str, capabilities: List[str]):
        """Record an escalation for learning."""
        self.learner.record_escalation(request, "claude", None, {"capabilities": capabilities})

    def get_parity_stats(self) -> Dict:
        """Get parity statistics."""
        total = len(self.capabilities)
        sam_handles = sum(1 for c in self.capabilities.values() if c.get("sam_handles", False))
        return {
            "total": total,
            "sam_handles": sam_handles,
            "needs_escalation": total - sam_handles,
            "parity_pct": round(sam_handles / total * 100) if total else 0
        }


@dataclass
class SystemStatus:
    """Status of all SAM subsystems."""
    orchestrator: bool = False
    auto_learner: bool = False
    api_server: bool = False
    voice_pipeline: bool = False
    vision_server: bool = False
    memory_db: bool = False


class NativeHub:
    """
    Master hub that unifies all SAM systems into one cohesive native setup.

    This is the single entry point for:
    - Project orchestration (what to work on)
    - Capability routing (how to handle requests)
    - Automatic learning (continuous improvement)
    - Tool execution (Claude Code equivalent)
    - System monitoring (health checks)
    """

    def __init__(self):
        self.brain_path = Path(__file__).parent
        self.config_path = Path.home() / ".sam" / "hub_config.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize subsystems
        self.orchestrator = UnifiedOrchestrator()
        self.parity = ParityManager()
        self.tools = ToolRegistry()
        self.auto_learner = None  # Lazy load

        # State
        self.status = SystemStatus()
        self.startup_time = datetime.now()
        self._check_systems()

    def _check_systems(self):
        """Check status of all subsystems."""
        # Check orchestrator (always available)
        self.status.orchestrator = True

        # Check auto-learner daemon
        result = subprocess.run(
            ["launchctl", "list", "com.sam.autolearner"],
            capture_output=True, text=True
        )
        self.status.auto_learner = result.returncode == 0

        # Check API server (port 8765)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 8765))
            self.status.api_server = result == 0
            sock.close()
        except:
            self.status.api_server = False

        # Check vision server (port 8766)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 8766))
            self.status.vision_server = result == 0
            sock.close()
        except:
            self.status.vision_server = False

        # Check memory database
        memory_db = Path("/Volumes/David External/sam_memory/semantic_memory.db")
        self.status.memory_db = memory_db.exists()

    def process_request(self, request: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process any request through the unified SAM system.
        Routes to the appropriate handler based on capability detection.
        """
        context = context or {}

        # Detect what capabilities are needed
        capabilities = self.parity.detect_capabilities(request)

        # Check if SAM can handle locally
        can_handle_locally = all(
            self.parity.capabilities.get(cap, {}).get("sam_handles", False)
            for cap in capabilities
        )

        if can_handle_locally:
            return self._handle_locally(request, capabilities, context)
        else:
            return self._escalate_to_claude(request, capabilities, context)

    def _handle_locally(self, request: str, capabilities: List[str], context: Dict) -> Dict:
        """Handle request using local SAM capabilities."""
        results = []

        for cap in capabilities:
            handler = self._get_local_handler(cap)
            if handler:
                result = handler(request, context)
                results.append({"capability": cap, "result": result})

        return {
            "handled_by": "sam_local",
            "capabilities": capabilities,
            "results": results,
            "success": True
        }

    def _get_local_handler(self, capability: str):
        """Get the local handler for a capability."""
        handlers = {
            "file_read": lambda r, c: self.tools.execute("read", {"file_path": c.get("file_path", "")}),
            "file_write": lambda r, c: self.tools.execute("write", c),
            "file_edit": lambda r, c: self.tools.execute("edit", c),
            "code_search": lambda r, c: self.tools.execute("grep", c),
            "bash_command": lambda r, c: self.tools.execute("bash", c),
            "git_operation": lambda r, c: self.tools.execute("git", c),
        }
        return handlers.get(capability)

    def _escalate_to_claude(self, request: str, capabilities: List[str], context: Dict) -> Dict:
        """Escalate to Claude Code via terminal."""
        # Record escalation for learning
        self.parity.record_escalation(request, capabilities)

        return {
            "handled_by": "claude_escalation",
            "capabilities": capabilities,
            "message": "This request requires Claude Code escalation",
            "escalation_reason": [cap for cap in capabilities if not self.parity.capabilities.get(cap, {}).get("sam_handles", False)],
            "success": False,
            "action_required": "Run in Claude Code terminal"
        }

    def get_dashboard(self) -> str:
        """Get a comprehensive dashboard of the entire SAM ecosystem."""
        self._check_systems()

        lines = [
            "",
            "=" * 70,
            "SAM NATIVE HUB - UNIFIED ECOSYSTEM DASHBOARD",
            "=" * 70,
            "",
            "SYSTEM STATUS",
            "-" * 40,
        ]

        status_icons = {True: "[OK]", False: "[--]"}
        lines.append(f"  {status_icons[self.status.orchestrator]} Project Orchestrator")
        lines.append(f"  {status_icons[self.status.auto_learner]} Auto-Learner Daemon")
        lines.append(f"  {status_icons[self.status.api_server]} SAM API Server (8765)")
        lines.append(f"  {status_icons[self.status.vision_server]} Vision Server (8766)")
        lines.append(f"  {status_icons[self.status.memory_db]} Memory Database")

        # Parity status
        parity_stats = self.parity.get_parity_stats()
        lines.extend([
            "",
            "CAPABILITY PARITY",
            "-" * 40,
            f"  Total Capabilities: {parity_stats['total']}",
            f"  SAM Handles: {parity_stats['sam_handles']} ({parity_stats['parity_pct']}%)",
            f"  Needs Escalation: {parity_stats['needs_escalation']}",
        ])

        # Project overview
        proj_dash = self.orchestrator.get_dashboard()
        lines.extend([
            "",
            "PROJECT OVERVIEW",
            "-" * 40,
            f"  Total Projects: {proj_dash['total_projects']}",
            f"  SAM Can Handle: {proj_dash['sam_can_handle']} ({proj_dash['sam_parity_pct']}%)",
            f"  In Progress: {proj_dash['in_progress']}",
            f"  Completed: {proj_dash['completed']}",
        ])

        # Training stats
        lines.extend([
            "",
            "TRAINING STATUS",
            "-" * 40,
        ])

        training_runs = self.brain_path / "training_runs.json"
        if training_runs.exists():
            with open(training_runs) as f:
                runs = json.load(f)
            if runs:
                latest = runs[-1]
                lines.append(f"  Latest Run: {latest['run_id']}")
                lines.append(f"  Samples: {latest['samples_count']}")
                lines.append(f"  Improvement: {latest['metrics'].get('improvement', 'N/A')}")
        else:
            lines.append("  No training runs yet")

        # Next suggested action
        next_proj = self.orchestrator.suggest_next_project()
        if next_proj:
            lines.extend([
                "",
                "SUGGESTED NEXT ACTION",
                "-" * 40,
                f"  Project: {next_proj.name}",
                f"  Category: {next_proj.category.value}",
                f"  Status: {next_proj.status.value} ({next_proj.progress_pct}%)",
            ])
            if next_proj.next_action:
                lines.append(f"  Action: {next_proj.next_action}")

        lines.extend(["", "=" * 70, ""])

        return "\n".join(lines)

    def start_all_services(self):
        """Start all SAM services."""
        print("Starting SAM services...")

        # Start API server if not running
        if not self.status.api_server:
            subprocess.Popen(
                ["python3", str(self.brain_path / "sam_api.py"), "server", "8765"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("  Started SAM API server")

        # Start auto-learner daemon if not running
        if not self.status.auto_learner:
            subprocess.run(["launchctl", "load", str(Path.home() / "Library/LaunchAgents/com.sam.autolearner.plist")],
                         capture_output=True)
            print("  Started auto-learner daemon")

        print("Services started.")

    def stop_all_services(self):
        """Stop all SAM services."""
        print("Stopping SAM services...")

        # Stop API server
        subprocess.run(["pkill", "-f", "sam_api.py"], capture_output=True)

        # Stop auto-learner
        subprocess.run(["launchctl", "unload", str(Path.home() / "Library/LaunchAgents/com.sam.autolearner.plist")],
                      capture_output=True)

        print("Services stopped.")

    def query_projects(self, query: str) -> List[Dict]:
        """Query projects using natural language."""
        all_projects = self.orchestrator.db.get_all_projects()

        # Simple keyword matching (SAM would use embeddings)
        query_lower = query.lower()
        matches = []

        for proj in all_projects:
            score = 0
            if query_lower in proj.name.lower():
                score += 10
            if query_lower in proj.description.lower():
                score += 5
            for tag in proj.tags:
                if query_lower in tag.lower():
                    score += 3
            if proj.category.value in query_lower:
                score += 5

            if score > 0:
                matches.append((score, proj))

        matches.sort(key=lambda x: -x[0])
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status.value,
                "score": s
            }
            for s, p in matches[:10]
        ]

    def execute_tool(self, tool_name: str, params: Dict) -> Dict:
        """Execute a tool (Claude Code equivalent functionality)."""
        return self.tools.execute(tool_name, params)

    def learn_from_interaction(self, user_input: str, response: str, metadata: Dict = None):
        """Record an interaction for learning."""
        if self.auto_learner is None:
            self.auto_learner = AutoLearner()

        # This would add to the learning queue
        example = {
            "instruction": user_input,
            "response": response,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        # Save to learning queue
        queue_path = self.brain_path / "data" / "learning_queue.jsonl"
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        with open(queue_path, 'a') as f:
            f.write(json.dumps(example) + '\n')

    def export_ecosystem_state(self) -> Dict:
        """Export the complete ecosystem state for backup/analysis."""
        return {
            "timestamp": datetime.now().isoformat(),
            "status": {
                "orchestrator": self.status.orchestrator,
                "auto_learner": self.status.auto_learner,
                "api_server": self.status.api_server,
                "vision_server": self.status.vision_server,
                "memory_db": self.status.memory_db
            },
            "parity": self.parity.get_parity_stats(),
            "projects": self.orchestrator.get_dashboard(),
            "capabilities": list(self.parity.capabilities.keys())
        }


class NativeHubCLI:
    """Command-line interface for the Native Hub."""

    def __init__(self):
        self.hub = NativeHub()

    def run(self, args: List[str]):
        if not args:
            print(self.hub.get_dashboard())
            return

        command = args[0]

        if command == "dashboard":
            print(self.hub.get_dashboard())

        elif command == "start":
            self.hub.start_all_services()

        elif command == "stop":
            self.hub.stop_all_services()

        elif command == "status":
            self.hub._check_systems()
            print("\nSystem Status:")
            for attr, val in vars(self.hub.status).items():
                icon = "[OK]" if val else "[--]"
                print(f"  {icon} {attr}")

        elif command == "projects":
            if len(args) > 1:
                # Query projects
                query = " ".join(args[1:])
                results = self.hub.query_projects(query)
                print(f"\nProjects matching '{query}':")
                for r in results:
                    print(f"  [{r['status']}] {r['name']}")
                    print(f"      {r['description'][:60]}...")
            else:
                # List all
                self.hub.orchestrator.print_dashboard()

        elif command == "suggest":
            proj = self.hub.orchestrator.suggest_next_project()
            if proj:
                print(f"\nSuggested: {proj.name}")
                print(f"Category: {proj.category.value}")
                print(f"Status: {proj.status.value} ({proj.progress_pct}%)")
                print(f"Description: {proj.description}")
                if proj.next_action:
                    print(f"Next Action: {proj.next_action}")
                if proj.path:
                    print(f"Path: {proj.path}")
            else:
                print("No projects need attention right now.")

        elif command == "parity":
            stats = self.hub.parity.get_parity_stats()
            print("\nCapability Parity Status:")
            print(f"  Total: {stats['total']}")
            print(f"  SAM Handles: {stats['sam_handles']} ({stats['parity_pct']}%)")
            print(f"  Needs Escalation: {stats['needs_escalation']}")

            print("\nEscalation Needed For:")
            for cap, info in self.hub.parity.capabilities.items():
                if not info.get("sam_handles", False):
                    print(f"  - {cap}: {info.get('escalation_reason', 'complex task')}")

        elif command == "tool":
            if len(args) < 2:
                print("Available tools:", ", ".join(self.hub.tools.list_tools()))
                return
            tool_name = args[1]
            # Parse remaining args as JSON
            params = {}
            if len(args) > 2:
                try:
                    params = json.loads(" ".join(args[2:]))
                except:
                    print("Error: params must be valid JSON")
                    return
            result = self.hub.execute_tool(tool_name, params)
            print(json.dumps(result, indent=2))

        elif command == "export":
            state = self.hub.export_ecosystem_state()
            output_path = Path.home() / ".sam" / f"ecosystem_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_path, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"Exported to: {output_path}")

        elif command == "help":
            print("""
SAM Native Hub - Unified Ecosystem Control

Commands:
  dashboard    Show full ecosystem dashboard
  status       Check status of all services
  start        Start all SAM services
  stop         Stop all SAM services
  projects     List all projects or query with keywords
  suggest      Get suggested next project to work on
  parity       Show capability parity status
  tool <name>  Execute a tool (Claude Code equivalent)
  export       Export ecosystem state to JSON
  help         Show this help

Examples:
  sam dashboard
  sam projects media
  sam suggest
  sam tool read '{"file_path": "/path/to/file"}'
""")

        else:
            print(f"Unknown command: {command}")
            print("Run 'sam help' for available commands")


def main():
    cli = NativeHubCLI()
    cli.run(sys.argv[1:])


if __name__ == "__main__":
    main()
