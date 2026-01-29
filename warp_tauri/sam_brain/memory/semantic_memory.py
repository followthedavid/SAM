#!/usr/bin/env python3
"""
SAM Semantic Memory - Vector embeddings for intelligent recall.

Uses MLX embeddings (native M2 Silicon) for searchable memory of:
- Past interactions
- Project contexts
- Code snippets
- Solutions to problems

Enables SAM to recall relevant past experiences when facing similar tasks.

Migration Note (2026-01-18):
  Switched from Ollama API to native MLX embeddings for:
  - 73% faster embedding generation (local vs network)
  - No background process required
  - Better memory efficiency on 8GB Mac
"""

import os
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# MLX Embeddings - Native M2 Silicon
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, fast
_mlx_model = None
_mlx_tokenizer = None

MEMORY_DIR = Path(__file__).parent / "memory"
EMBEDDINGS_FILE = MEMORY_DIR / "embeddings.json"
INDEX_FILE = MEMORY_DIR / "index.npy"


@dataclass
class MemoryEntry:
    id: str
    content: str
    entry_type: str  # interaction, code, solution, project, note
    timestamp: str
    metadata: Dict
    embedding: Optional[List[float]] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Don't store embedding in JSON, keep in numpy
        d.pop('embedding', None)
        return d


class SemanticMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(exist_ok=True)
        self.entries: Dict[str, MemoryEntry] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self._load()

    def _load(self):
        """Load existing memories."""
        if EMBEDDINGS_FILE.exists():
            data = json.load(open(EMBEDDINGS_FILE))
            for entry_data in data.get("entries", []):
                entry = MemoryEntry(**entry_data)
                self.entries[entry.id] = entry

        if INDEX_FILE.exists():
            index_data = np.load(INDEX_FILE, allow_pickle=True).item()
            self.embeddings = {k: np.array(v) for k, v in index_data.items()}

    def _save(self):
        """Save memories to disk."""
        # Save entries (without embeddings)
        data = {
            "entries": [e.to_dict() for e in self.entries.values()],
            "updated_at": datetime.now().isoformat()
        }
        json.dump(data, open(EMBEDDINGS_FILE, "w"), indent=2)

        # Save embeddings as numpy
        if self.embeddings:
            np.save(INDEX_FILE, self.embeddings)

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding using MLX (native M2 Silicon)."""
        global _mlx_model, _mlx_tokenizer

        try:
            import mlx_embeddings

            # Lazy load model on first use
            if _mlx_model is None:
                _mlx_model, _mlx_tokenizer = mlx_embeddings.load(EMBEDDING_MODEL)

            # Generate embedding
            output = mlx_embeddings.generate(
                _mlx_model,
                _mlx_tokenizer,
                text[:2000]  # Limit text length
            )

            # Extract the text embedding (384-dim for MiniLM)
            embedding = np.array(output.text_embeds[0])
            return embedding

        except Exception as e:
            print(f"MLX Embedding error: {e}")
            return None

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content."""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def add(self, content: str, entry_type: str, metadata: Dict = None) -> str:
        """Add a memory entry."""
        entry_id = self._generate_id(content + str(datetime.now()))

        entry = MemoryEntry(
            id=entry_id,
            content=content,
            entry_type=entry_type,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        # Get embedding
        embedding = self._get_embedding(content)
        if embedding is not None:
            self.embeddings[entry_id] = embedding

        self.entries[entry_id] = entry
        self._save()

        return entry_id

    def add_interaction(self, query: str, response: str, project: str = None, success: bool = True):
        """Add an interaction to memory."""
        content = f"Query: {query}\nResponse: {response}"
        metadata = {
            "project": project,
            "success": success,
            "query": query[:200],
            "response_preview": response[:200]
        }
        return self.add(content, "interaction", metadata)

    def add_code(self, code: str, language: str, description: str, file_path: str = None):
        """Add a code snippet to memory."""
        content = f"Description: {description}\nLanguage: {language}\n\n{code}"
        metadata = {
            "language": language,
            "file_path": file_path,
            "description": description
        }
        return self.add(content, "code", metadata)

    def add_solution(self, problem: str, solution: str, tags: List[str] = None):
        """Add a problem/solution pair."""
        content = f"Problem: {problem}\n\nSolution: {solution}"
        metadata = {
            "problem": problem[:200],
            "tags": tags or []
        }
        return self.add(content, "solution", metadata)

    def add_note(self, note: str, category: str = "general"):
        """Add a general note."""
        return self.add(note, "note", {"category": category})

    # ===== Evolution Feedback Loop =====

    def add_improvement_feedback(
        self,
        improvement_id: str,
        project_id: str,
        improvement_type: str,
        description: str,
        outcome: str,
        success: bool,
        impact_score: float = 0.0,
        lessons_learned: str = ""
    ) -> str:
        """
        Add feedback from a completed improvement to memory.
        This enables SAM to learn from past improvement attempts.
        """
        content = f"""Improvement Feedback:
Project: {project_id}
Type: {improvement_type}
Description: {description}
Outcome: {outcome}
Success: {success}
Impact Score: {impact_score}
Lessons Learned: {lessons_learned}"""

        metadata = {
            "improvement_id": improvement_id,
            "project_id": project_id,
            "improvement_type": improvement_type,
            "success": success,
            "impact_score": impact_score,
            "lessons_learned": lessons_learned
        }
        return self.add(content, "improvement_feedback", metadata)

    def add_pattern(self, pattern_name: str, pattern_description: str, examples: List[str], category: str):
        """
        Add a recognized pattern to memory for future reference.
        Patterns help SAM recognize similar situations.
        """
        examples_text = "\n- ".join(examples) if examples else "None"
        content = f"""Pattern: {pattern_name}
Category: {category}
Description: {pattern_description}
Examples:
- {examples_text}"""

        metadata = {
            "pattern_name": pattern_name,
            "category": category,
            "example_count": len(examples)
        }
        return self.add(content, "pattern", metadata)

    def search_similar_improvements(self, improvement_type: str, project_category: str = None, limit: int = 5) -> List[Tuple[MemoryEntry, float]]:
        """
        Find similar past improvements to learn from.
        Returns improvements that worked well in similar contexts.
        """
        query = f"improvement {improvement_type}"
        if project_category:
            query += f" {project_category} project"

        results = self.search(query, limit=limit * 2, entry_type="improvement_feedback")

        # Filter to successful improvements and sort by impact
        successful = []
        for entry, similarity in results:
            if entry.metadata.get("success", False):
                impact = entry.metadata.get("impact_score", 0)
                # Combine similarity and impact for ranking
                combined_score = similarity * 0.6 + impact * 0.4
                successful.append((entry, combined_score))

        successful.sort(key=lambda x: -x[1])
        return successful[:limit]

    def get_improvement_context(self, improvement_type: str, project_id: str) -> str:
        """
        Get relevant context for a proposed improvement.
        Returns lessons learned from similar past improvements.
        """
        # Search for similar improvements
        similar = self.search_similar_improvements(improvement_type, limit=3)

        if not similar:
            return ""

        context_parts = ["## Lessons from Similar Improvements:\n"]
        for entry, score in similar:
            meta = entry.metadata
            context_parts.append(f"### {meta.get('project_id', 'Unknown')} - {meta.get('improvement_type', 'Unknown')}")
            context_parts.append(f"Impact: {meta.get('impact_score', 0):.1f}/1.0")
            lessons = meta.get('lessons_learned', '')
            if lessons:
                context_parts.append(f"Lessons: {lessons}")
            context_parts.append("")

        return "\n".join(context_parts)

    def get_success_rate_for_type(self, improvement_type: str) -> Dict:
        """
        Calculate success rate for a specific improvement type.
        Helps prioritize improvement types that historically work well.
        """
        feedback_entries = [
            e for e in self.entries.values()
            if e.entry_type == "improvement_feedback"
            and e.metadata.get("improvement_type") == improvement_type
        ]

        if not feedback_entries:
            return {"type": improvement_type, "attempts": 0, "success_rate": 0.0, "avg_impact": 0.0}

        successes = sum(1 for e in feedback_entries if e.metadata.get("success", False))
        impacts = [e.metadata.get("impact_score", 0) for e in feedback_entries]

        return {
            "type": improvement_type,
            "attempts": len(feedback_entries),
            "successes": successes,
            "success_rate": successes / len(feedback_entries) if feedback_entries else 0,
            "avg_impact": sum(impacts) / len(impacts) if impacts else 0
        }

    def get_all_improvement_stats(self) -> Dict:
        """
        Get comprehensive statistics on improvement feedback.
        """
        feedback_entries = [
            e for e in self.entries.values()
            if e.entry_type == "improvement_feedback"
        ]

        if not feedback_entries:
            return {"total": 0, "by_type": {}, "by_project": {}}

        # Stats by type
        by_type = {}
        for e in feedback_entries:
            imp_type = e.metadata.get("improvement_type", "unknown")
            if imp_type not in by_type:
                by_type[imp_type] = {"attempts": 0, "successes": 0, "total_impact": 0}
            by_type[imp_type]["attempts"] += 1
            if e.metadata.get("success", False):
                by_type[imp_type]["successes"] += 1
            by_type[imp_type]["total_impact"] += e.metadata.get("impact_score", 0)

        # Calculate rates
        for imp_type, stats in by_type.items():
            stats["success_rate"] = stats["successes"] / stats["attempts"] if stats["attempts"] > 0 else 0
            stats["avg_impact"] = stats["total_impact"] / stats["attempts"] if stats["attempts"] > 0 else 0

        # Stats by project
        by_project = {}
        for e in feedback_entries:
            proj = e.metadata.get("project_id", "unknown")
            if proj not in by_project:
                by_project[proj] = {"attempts": 0, "successes": 0}
            by_project[proj]["attempts"] += 1
            if e.metadata.get("success", False):
                by_project[proj]["successes"] += 1

        return {
            "total": len(feedback_entries),
            "total_successes": sum(1 for e in feedback_entries if e.metadata.get("success", False)),
            "by_type": by_type,
            "by_project": by_project
        }

    def search(self, query: str, limit: int = 5, entry_type: str = None) -> List[Tuple[MemoryEntry, float]]:
        """Search memories by semantic similarity."""
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return []

        results = []
        for entry_id, entry in self.entries.items():
            # Filter by type if specified
            if entry_type and entry.entry_type != entry_type:
                continue

            # Get embedding
            if entry_id not in self.embeddings:
                continue

            entry_embedding = self.embeddings[entry_id]

            # Cosine similarity
            similarity = np.dot(query_embedding, entry_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(entry_embedding)
            )

            results.append((entry, float(similarity)))

        # Sort by similarity
        results.sort(key=lambda x: -x[1])
        return results[:limit]

    def search_similar_problems(self, problem: str, limit: int = 3) -> List[Tuple[MemoryEntry, float]]:
        """Find similar problems we've solved before."""
        return self.search(problem, limit=limit, entry_type="solution")

    def search_relevant_code(self, description: str, limit: int = 5) -> List[Tuple[MemoryEntry, float]]:
        """Find relevant code snippets."""
        return self.search(description, limit=limit, entry_type="code")

    def get_context_for_query(self, query: str, max_entries: int = 3) -> str:
        """Get relevant context from memory for a query."""
        results = self.search(query, limit=max_entries)

        if not results:
            return ""

        context_parts = ["## Relevant memories:\n"]
        for entry, similarity in results:
            if similarity < 0.5:  # Skip low-relevance
                continue

            context_parts.append(f"### {entry.entry_type.title()} (relevance: {similarity:.2f})")
            context_parts.append(entry.content[:500])
            context_parts.append("")

        return "\n".join(context_parts)

    def stats(self) -> Dict:
        """Get memory statistics."""
        type_counts = {}
        for entry in self.entries.values():
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1

        return {
            "total_entries": len(self.entries),
            "embedded_entries": len(self.embeddings),
            "by_type": type_counts,
            "memory_file": str(EMBEDDINGS_FILE),
            "index_file": str(INDEX_FILE)
        }

    def import_from_memory_json(self, memory_file: Path):
        """Import interactions from existing memory.json."""
        if not memory_file.exists():
            return 0

        data = json.load(open(memory_file))
        count = 0

        for interaction in data.get("interactions", []):
            query = interaction.get("query", "")
            response = interaction.get("response", "")
            project = interaction.get("project")

            if query and response:
                self.add_interaction(query, response, project)
                count += 1

        return count

    def import_from_training_data(self, training_file: Path):
        """Import from training_data.jsonl."""
        if not training_file.exists():
            return 0

        count = 0
        for line in training_file.read_text().strip().split("\n"):
            try:
                data = json.loads(line)
                query = data.get("input", "")
                response = data.get("output", "")
                if query and response:
                    self.add_interaction(query, response)
                    count += 1
            except:
                pass

        return count


# Global instance
_memory = None

def get_memory() -> SemanticMemory:
    """Get global memory instance."""
    global _memory
    if _memory is None:
        _memory = SemanticMemory()
    return _memory


def search(query: str, limit: int = 5) -> List[Tuple[MemoryEntry, float]]:
    """Search semantic memory."""
    return get_memory().search(query, limit)


def add_interaction(query: str, response: str, project: str = None):
    """Add interaction to memory."""
    return get_memory().add_interaction(query, response, project)


def get_context(query: str) -> str:
    """Get relevant context for a query."""
    return get_memory().get_context_for_query(query)


# ===== Feedback Loop Convenience Functions =====

def add_improvement_feedback(
    improvement_id: str,
    project_id: str,
    improvement_type: str,
    description: str,
    outcome: str,
    success: bool,
    impact_score: float = 0.0,
    lessons_learned: str = ""
) -> str:
    """Add improvement feedback to memory."""
    return get_memory().add_improvement_feedback(
        improvement_id, project_id, improvement_type,
        description, outcome, success, impact_score, lessons_learned
    )


def get_improvement_context(improvement_type: str, project_id: str) -> str:
    """Get context from past similar improvements."""
    return get_memory().get_improvement_context(improvement_type, project_id)


def get_improvement_stats() -> Dict:
    """Get improvement feedback statistics."""
    return get_memory().get_all_improvement_stats()


if __name__ == "__main__":
    import sys

    memory = SemanticMemory()

    if len(sys.argv) < 2:
        print("SAM Semantic Memory")
        print("-" * 40)
        stats = memory.stats()
        print(f"Total entries: {stats['total_entries']}")
        print(f"Embedded: {stats['embedded_entries']}")
        print(f"By type: {stats['by_type']}")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "import":
        # Import from existing files
        script_dir = Path(__file__).parent

        count = memory.import_from_memory_json(script_dir / "memory.json")
        print(f"Imported {count} from memory.json")

        count = memory.import_from_training_data(script_dir / "training_data.jsonl")
        print(f"Imported {count} from training_data.jsonl")

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        results = memory.search(query)

        print(f"Search: {query}")
        print("-" * 40)
        for entry, similarity in results:
            print(f"\n[{entry.entry_type}] Similarity: {similarity:.3f}")
            print(entry.content[:200])

    elif cmd == "add":
        content = " ".join(sys.argv[2:])
        entry_id = memory.add(content, "note")
        print(f"Added: {entry_id}")

    elif cmd == "stats":
        stats = memory.stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "improvement-stats":
        stats = memory.get_all_improvement_stats()
        print("Improvement Feedback Statistics")
        print("-" * 40)
        print(f"Total feedback entries: {stats['total']}")
        print(f"Total successes: {stats.get('total_successes', 0)}")

        if stats.get('by_type'):
            print("\nBy improvement type:")
            for imp_type, type_stats in stats['by_type'].items():
                rate = type_stats.get('success_rate', 0) * 100
                impact = type_stats.get('avg_impact', 0)
                print(f"  {imp_type}: {type_stats['attempts']} attempts, {rate:.1f}% success, {impact:.2f} avg impact")

        if stats.get('by_project'):
            print("\nBy project:")
            for proj, proj_stats in stats['by_project'].items():
                print(f"  {proj}: {proj_stats['successes']}/{proj_stats['attempts']} successful")

    elif cmd == "add-feedback":
        # Example: semantic_memory.py add-feedback PROJECT TYPE DESC OUTCOME SUCCESS IMPACT LESSONS
        if len(sys.argv) < 7:
            print("Usage: semantic_memory.py add-feedback <project_id> <type> <description> <outcome> <success:true/false> [impact:0.0-1.0] [lessons]")
            sys.exit(1)

        project_id = sys.argv[2]
        imp_type = sys.argv[3]
        description = sys.argv[4]
        outcome = sys.argv[5]
        success = sys.argv[6].lower() in ('true', '1', 'yes')
        impact = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5
        lessons = sys.argv[8] if len(sys.argv) > 8 else ""

        entry_id = memory.add_improvement_feedback(
            improvement_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            project_id=project_id,
            improvement_type=imp_type,
            description=description,
            outcome=outcome,
            success=success,
            impact_score=impact,
            lessons_learned=lessons
        )
        print(f"Added feedback: {entry_id}")

    elif cmd == "similar-improvements":
        if len(sys.argv) < 3:
            print("Usage: semantic_memory.py similar-improvements <type> [category]")
            sys.exit(1)

        imp_type = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else None

        results = memory.search_similar_improvements(imp_type, category)
        print(f"Similar successful improvements for '{imp_type}':")
        print("-" * 40)
        for entry, score in results:
            meta = entry.metadata
            print(f"\n[{meta.get('project_id', 'Unknown')}] Score: {score:.3f}")
            print(f"  Type: {meta.get('improvement_type')}")
            print(f"  Impact: {meta.get('impact_score', 0):.2f}")
            if meta.get('lessons_learned'):
                print(f"  Lessons: {meta.get('lessons_learned')[:100]}")

    else:
        print(f"Unknown command: {cmd}")
        print("\nUsage: semantic_memory.py [command]")
        print("\nBasic commands:")
        print("  import                  - Import from memory.json and training_data.jsonl")
        print("  search <query>          - Search memories")
        print("  add <note>              - Add a note")
        print("  stats                   - Show memory statistics")
        print("\nFeedback commands:")
        print("  improvement-stats       - Show improvement feedback statistics")
        print("  add-feedback <args>     - Add improvement feedback")
        print("  similar-improvements    - Find similar successful improvements")
