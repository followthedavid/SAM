#!/usr/bin/env python3
"""
SAM Multi-Agent Orchestration - Spawn specialized sub-agents for complex tasks.

When SAM encounters a complex task, it can:
1. Decompose into subtasks
2. Spawn specialized agents for each
3. Coordinate results
4. Synthesize final output

Agent types:
- CodeAgent: Writes and modifies code
- ReviewAgent: Reviews code for issues
- TestAgent: Creates and runs tests
- DocAgent: Writes documentation
- ResearchAgent: Searches codebases and web
- FixAgent: Debugs and fixes errors
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
SCRIPT_DIR = Path(__file__).parent


class AgentType(Enum):
    CODE = "code"
    REVIEW = "review"
    TEST = "test"
    DOC = "doc"
    RESEARCH = "research"
    FIX = "fix"
    GENERAL = "general"


@dataclass
class SubTask:
    id: str
    description: str
    agent_type: AgentType
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TaskPlan:
    task_id: str
    original_task: str
    subtasks: List[SubTask]
    created_at: str
    status: str = "pending"
    final_result: Optional[str] = None


# Agent system prompts
AGENT_PROMPTS = {
    AgentType.CODE: """You are a code writing agent. Your job is to write clean, working code.
Output ONLY the code, no explanations. Use proper formatting and comments.""",

    AgentType.REVIEW: """You are a code review agent. Your job is to find bugs, issues, and improvements.
Be specific about line numbers and provide concrete fixes.""",

    AgentType.TEST: """You are a testing agent. Your job is to write comprehensive tests.
Cover edge cases and use appropriate testing frameworks.""",

    AgentType.DOC: """You are a documentation agent. Your job is to write clear documentation.
Include usage examples and explain complex parts.""",

    AgentType.RESEARCH: """You are a research agent. Your job is to find relevant information.
Search codebases, find patterns, and summarize findings.""",

    AgentType.FIX: """You are a debugging agent. Your job is to find and fix errors.
Analyze error messages and provide working fixes.""",

    AgentType.GENERAL: """You are a helpful AI assistant. Complete the task thoroughly."""
}


class Agent:
    """Individual agent that can execute tasks."""

    def __init__(self, agent_type: AgentType, model: str = "qwen2.5-coder:1.5b"):
        self.agent_type = agent_type
        self.model = model
        self.system_prompt = AGENT_PROMPTS[agent_type]

    def execute(self, task: str, context: str = "") -> str:
        """Execute a task and return result."""
        prompt = f"{context}\n\nTask: {task}" if context else task

        try:
            data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "system": self.system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2000
                }
            }).encode()

            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                return result.get("response", "")

        except Exception as e:
            return f"Error: {e}"


class TaskDecomposer:
    """Decomposes complex tasks into subtasks."""

    def __init__(self):
        self.agent = Agent(AgentType.GENERAL)

    def decompose(self, task: str) -> List[SubTask]:
        """Break down a task into subtasks."""
        prompt = f"""Analyze this task and break it into subtasks.
For each subtask, specify:
- Description (what to do)
- Agent type (code/review/test/doc/research/fix)
- Dependencies (which subtasks must complete first, by number)

Output as JSON array:
[
  {{"description": "...", "agent_type": "code", "dependencies": []}},
  {{"description": "...", "agent_type": "test", "dependencies": [0]}}
]

Task: {task}

JSON:"""

        response = self.agent.execute(prompt)

        # Parse response
        try:
            # Find JSON in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                subtasks_data = json.loads(response[start:end])
                subtasks = []
                for i, st in enumerate(subtasks_data):
                    subtasks.append(SubTask(
                        id=f"subtask_{i}",
                        description=st.get("description", ""),
                        agent_type=AgentType(st.get("agent_type", "general")),
                        dependencies=[f"subtask_{d}" for d in st.get("dependencies", [])]
                    ))
                return subtasks
        except:
            pass

        # Fallback: single task
        return [SubTask(
            id="subtask_0",
            description=task,
            agent_type=AgentType.GENERAL
        )]


class Orchestrator:
    """Orchestrates multiple agents to complete complex tasks."""

    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.agents = {t: Agent(t) for t in AgentType}
        self.plans: Dict[str, TaskPlan] = {}
        self.max_workers = 3

    def create_plan(self, task: str) -> TaskPlan:
        """Create an execution plan for a task."""
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        subtasks = self.decomposer.decompose(task)

        plan = TaskPlan(
            task_id=task_id,
            original_task=task,
            subtasks=subtasks,
            created_at=datetime.now().isoformat()
        )

        self.plans[task_id] = plan
        return plan

    def _can_execute(self, subtask: SubTask, completed: set) -> bool:
        """Check if subtask's dependencies are met."""
        return all(dep in completed for dep in subtask.dependencies)

    def _execute_subtask(self, subtask: SubTask, context: Dict[str, str]) -> SubTask:
        """Execute a single subtask."""
        subtask.status = "running"

        # Build context from dependencies
        dep_context = ""
        for dep_id in subtask.dependencies:
            if dep_id in context:
                dep_context += f"\n--- Result from {dep_id} ---\n{context[dep_id]}\n"

        agent = self.agents[subtask.agent_type]

        try:
            result = agent.execute(subtask.description, dep_context)
            subtask.result = result
            subtask.status = "completed"
        except Exception as e:
            subtask.error = str(e)
            subtask.status = "failed"

        return subtask

    def execute_plan(self, plan: TaskPlan) -> TaskPlan:
        """Execute a task plan."""
        plan.status = "running"
        completed = set()
        context = {}

        # Execute in dependency order
        while len(completed) < len(plan.subtasks):
            # Find ready tasks
            ready = [
                st for st in plan.subtasks
                if st.id not in completed and self._can_execute(st, completed)
            ]

            if not ready:
                # Deadlock or all done
                break

            # Execute ready tasks in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._execute_subtask, st, context): st
                    for st in ready
                }

                for future in as_completed(futures):
                    subtask = future.result()
                    completed.add(subtask.id)
                    if subtask.result:
                        context[subtask.id] = subtask.result

        # Synthesize final result
        plan.final_result = self._synthesize_results(plan, context)
        plan.status = "completed" if all(
            st.status == "completed" for st in plan.subtasks
        ) else "partial"

        return plan

    def _synthesize_results(self, plan: TaskPlan, context: Dict[str, str]) -> str:
        """Synthesize all subtask results into final output."""
        parts = [f"# Results for: {plan.original_task}\n"]

        for subtask in plan.subtasks:
            parts.append(f"\n## {subtask.agent_type.value.title()}: {subtask.description}")
            if subtask.result:
                parts.append(subtask.result)
            elif subtask.error:
                parts.append(f"Error: {subtask.error}")

        return "\n".join(parts)

    def run(self, task: str) -> str:
        """Main entry point: decompose and execute a task."""
        # Check if task is complex enough for multi-agent
        if self._is_simple_task(task):
            # Just run with single agent
            return self.agents[AgentType.GENERAL].execute(task)

        # Create and execute plan
        plan = self.create_plan(task)
        plan = self.execute_plan(plan)

        return plan.final_result

    def _is_simple_task(self, task: str) -> bool:
        """Check if task is simple enough for single agent."""
        simple_patterns = [
            "list", "show", "display", "read", "cat", "head",
            "git status", "git diff", "what is", "explain"
        ]
        task_lower = task.lower()
        return any(p in task_lower for p in simple_patterns)


# Global orchestrator
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Get global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def run_multi_agent(task: str) -> str:
    """Run a task with multi-agent orchestration."""
    return get_orchestrator().run(task)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Multi-Agent Orchestrator")
        print("-" * 40)
        print("Usage: multi_agent.py <task>")
        print("\nExample:")
        print('  multi_agent.py "Create a Python function to parse JSON files with error handling and tests"')
        sys.exit(0)

    task = " ".join(sys.argv[1:])

    print(f"Task: {task}")
    print("-" * 40)

    orchestrator = Orchestrator()
    plan = orchestrator.create_plan(task)

    print(f"\nPlan created with {len(plan.subtasks)} subtasks:")
    for st in plan.subtasks:
        deps = f" (depends on: {', '.join(st.dependencies)})" if st.dependencies else ""
        print(f"  [{st.agent_type.value}] {st.description}{deps}")

    print("\nExecuting...")
    plan = orchestrator.execute_plan(plan)

    print("\n" + "=" * 40)
    print(plan.final_result)
