#!/usr/bin/env python3
"""
SAM Semantic Memory - Vector embeddings for intelligent recall.

Uses Ollama's embedding API to create searchable memory of:
- Past interactions
- Project contexts
- Code snippets
- Solutions to problems

Enables SAM to recall relevant past experiences when facing similar tasks.
"""

import os
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"  # Fast, good quality embeddings

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
        """Get embedding from Ollama."""
        try:
            data = json.dumps({
                "model": EMBEDDING_MODEL,
                "prompt": text[:2000]  # Limit text length
            }).encode()

            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=data,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return np.array(result["embedding"])
        except Exception as e:
            print(f"Embedding error: {e}")
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

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: semantic_memory.py [import|search <query>|add <note>|stats]")
