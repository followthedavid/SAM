"""
Code Indexer for SAM RAG System (Phase 2.2)

Indexes code files for intelligent retrieval:
- Function signatures and docstrings
- Class definitions and methods
- Module-level documentation
- Supports Python, JavaScript/TypeScript, Rust

Integrates with EnhancedRetrievalSystem.
"""

import ast
import re
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CodeEntity:
    """A code entity (function, class, method, etc.)"""
    id: str
    name: str
    type: str  # function, class, method, module
    signature: str
    docstring: Optional[str]
    file_path: str
    line_number: int
    content: str  # Full content for embedding
    project_id: str


class PythonParser:
    """Parse Python files for code entities."""

    def parse(self, file_path: Path, project_id: str) -> List[CodeEntity]:
        """Parse a Python file and extract code entities."""
        entities = []

        try:
            content = file_path.read_text(errors='ignore')
            tree = ast.parse(content)
            lines = content.split('\n')
        except Exception as e:
            return entities

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                entity = self._parse_function(node, file_path, lines, project_id)
                entities.append(entity)
            elif isinstance(node, ast.AsyncFunctionDef):
                entity = self._parse_function(node, file_path, lines, project_id, async_=True)
                entities.append(entity)
            elif isinstance(node, ast.ClassDef):
                entity = self._parse_class(node, file_path, lines, project_id)
                entities.append(entity)

        # Module docstring
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
            docstring = tree.body[0].value.value
            if isinstance(docstring, str) and len(docstring) > 10:
                entity_id = hashlib.md5(f"{file_path}:module".encode()).hexdigest()[:12]
                entities.append(CodeEntity(
                    id=entity_id,
                    name=file_path.stem,
                    type="module",
                    signature=f"Module: {file_path.name}",
                    docstring=docstring[:1000],
                    file_path=str(file_path),
                    line_number=1,
                    content=f"Module {file_path.name}: {docstring[:500]}",
                    project_id=project_id
                ))

        return entities

    def _parse_function(self, node: ast.FunctionDef, file_path: Path,
                        lines: List[str], project_id: str, async_: bool = False) -> CodeEntity:
        """Parse a function definition."""
        prefix = "async " if async_ else ""

        # Build signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        signature = f"{prefix}def {node.name}({', '.join(args)}){returns}"

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get function body snippet
        start_line = node.lineno - 1
        end_line = min(start_line + 20, len(lines))
        body_snippet = '\n'.join(lines[start_line:end_line])

        entity_id = hashlib.md5(f"{file_path}:{node.name}:{node.lineno}".encode()).hexdigest()[:12]

        content = f"{signature}\n"
        if docstring:
            content += f'"""{docstring[:300]}"""\n'
        content += body_snippet[:500]

        return CodeEntity(
            id=entity_id,
            name=node.name,
            type="function",
            signature=signature,
            docstring=docstring[:1000] if docstring else None,
            file_path=str(file_path),
            line_number=node.lineno,
            content=content,
            project_id=project_id
        )

    def _parse_class(self, node: ast.ClassDef, file_path: Path,
                     lines: List[str], project_id: str) -> CodeEntity:
        """Parse a class definition."""
        # Build signature with bases
        bases = [ast.unparse(b) for b in node.bases]
        signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get method names
        methods = [n.name for n in ast.walk(node)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

        entity_id = hashlib.md5(f"{file_path}:{node.name}:{node.lineno}".encode()).hexdigest()[:12]

        content = f"{signature}\n"
        if docstring:
            content += f'"""{docstring[:300]}"""\n'
        content += f"Methods: {', '.join(methods[:10])}"

        return CodeEntity(
            id=entity_id,
            name=node.name,
            type="class",
            signature=signature,
            docstring=docstring[:1000] if docstring else None,
            file_path=str(file_path),
            line_number=node.lineno,
            content=content,
            project_id=project_id
        )


class JavaScriptParser:
    """Parse JavaScript/TypeScript files for code entities."""

    # Regex patterns for JS/TS
    FUNCTION_PATTERN = re.compile(
        r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE
    )
    ARROW_PATTERN = re.compile(
        r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
        re.MULTILINE
    )
    CLASS_PATTERN = re.compile(
        r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?',
        re.MULTILINE
    )
    JSDOC_PATTERN = re.compile(
        r'/\*\*\s*(.*?)\s*\*/',
        re.DOTALL
    )

    def parse(self, file_path: Path, project_id: str) -> List[CodeEntity]:
        """Parse a JavaScript/TypeScript file."""
        entities = []

        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')
        except Exception:
            return entities

        # Parse functions
        for match in self.FUNCTION_PATTERN.finditer(content):
            name = match.group(1)
            params = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            # Look for preceding JSDoc
            docstring = self._find_jsdoc(content, match.start())

            signature = f"function {name}({params})"
            entity_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 15)

            entities.append(CodeEntity(
                id=entity_id,
                name=name,
                type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:500],
                project_id=project_id
            ))

        # Parse arrow functions
        for match in self.ARROW_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            signature = f"const {name} = () =>"
            entity_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 10)

            entities.append(CodeEntity(
                id=entity_id,
                name=name,
                type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{snippet}"[:500],
                project_id=project_id
            ))

        # Parse classes
        for match in self.CLASS_PATTERN.finditer(content):
            name = match.group(1)
            extends = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            signature = f"class {name}" + (f" extends {extends}" if extends else "")
            entity_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 20)

            entities.append(CodeEntity(
                id=entity_id,
                name=name,
                type="class",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:500],
                project_id=project_id
            ))

        return entities

    def _find_jsdoc(self, content: str, pos: int) -> Optional[str]:
        """Find JSDoc comment before a position."""
        # Look backwards for /**
        search_start = max(0, pos - 500)
        search_area = content[search_start:pos]

        match = self.JSDOC_PATTERN.search(search_area)
        if match:
            # Clean up the JSDoc
            doc = match.group(1)
            doc = re.sub(r'\n\s*\*\s*', '\n', doc)
            return doc.strip()[:500]
        return None

    def _get_snippet(self, lines: List[str], start: int, count: int) -> str:
        """Get a snippet of lines."""
        end = min(start + count, len(lines))
        return '\n'.join(lines[start:end])


class RustParser:
    """Parse Rust files for code entities."""

    FUNCTION_PATTERN = re.compile(
        r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]([^{]*)',
        re.MULTILINE
    )
    STRUCT_PATTERN = re.compile(
        r'(?:pub\s+)?struct\s+(\w+)',
        re.MULTILINE
    )
    IMPL_PATTERN = re.compile(
        r'impl(?:\s*<[^>]*>)?\s+(\w+)',
        re.MULTILINE
    )

    def parse(self, file_path: Path, project_id: str) -> List[CodeEntity]:
        """Parse a Rust file."""
        entities = []

        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')
        except Exception:
            return entities

        # Parse functions
        for match in self.FUNCTION_PATTERN.finditer(content):
            name = match.group(1)
            params = match.group(2).strip()
            line_num = content[:match.start()].count('\n') + 1

            # Look for /// doc comments
            docstring = self._find_doc_comment(lines, line_num - 1)

            signature = f"fn {name}({params.split(')')[0]})"
            entity_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 15)

            entities.append(CodeEntity(
                id=entity_id,
                name=name,
                type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:500],
                project_id=project_id
            ))

        # Parse structs
        for match in self.STRUCT_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"struct {name}"
            entity_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 15)

            entities.append(CodeEntity(
                id=entity_id,
                name=name,
                type="struct",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:500],
                project_id=project_id
            ))

        return entities

    def _find_doc_comment(self, lines: List[str], line_num: int) -> Optional[str]:
        """Find /// doc comments before a line."""
        docs = []
        i = line_num - 1
        while i >= 0 and lines[i].strip().startswith('///'):
            docs.insert(0, lines[i].strip()[3:].strip())
            i -= 1
        return '\n'.join(docs) if docs else None

    def _get_snippet(self, lines: List[str], start: int, count: int) -> str:
        """Get a snippet of lines."""
        end = min(start + count, len(lines))
        return '\n'.join(lines[start:end])


class CodeIndexer:
    """
    Main code indexer that scans projects and builds a searchable index.
    """

    DB_PATH = Path("/Volumes/David External/sam_memory/code_index.db")

    EXTENSION_PARSERS = {
        '.py': PythonParser,
        '.js': JavaScriptParser,
        '.ts': JavaScriptParser,
        '.jsx': JavaScriptParser,
        '.tsx': JavaScriptParser,
        '.rs': RustParser,
    }

    SKIP_DIRS = {
        'node_modules', '.git', 'target', 'dist', 'build',
        '__pycache__', '.venv', 'venv', 'site-packages',
        '.next', '.nuxt', 'coverage', '.mypy_cache'
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._parsers = {ext: parser() for ext, parser in self.EXTENSION_PARSERS.items()}

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS code_entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                signature TEXT,
                docstring TEXT,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                content TEXT,
                project_id TEXT,
                indexed_at REAL
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_code_name ON code_entities(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_code_type ON code_entities(type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_code_project ON code_entities(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_code_file ON code_entities(file_path)")

        # Track indexed files
        cur.execute("""
            CREATE TABLE IF NOT EXISTS indexed_files (
                file_path TEXT PRIMARY KEY,
                project_id TEXT,
                mtime REAL,
                indexed_at REAL
            )
        """)

        conn.commit()
        conn.close()

    def index_project(self, project_path: str, project_id: str,
                      force: bool = False) -> Dict[str, int]:
        """
        Index all code files in a project.

        Args:
            project_path: Path to project root
            project_id: Unique project identifier
            force: Re-index even if files haven't changed

        Returns:
            Stats dict with counts
        """
        project_path = Path(project_path)
        if not project_path.exists():
            return {"error": "Path not found", "indexed": 0}

        stats = {"files_scanned": 0, "entities_indexed": 0, "skipped": 0}

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for file_path in project_path.rglob('*'):
            if not file_path.is_file():
                continue
            if any(skip in file_path.parts for skip in self.SKIP_DIRS):
                stats["skipped"] += 1
                continue
            if file_path.suffix not in self._parsers:
                continue

            stats["files_scanned"] += 1

            # Check if file needs re-indexing
            mtime = file_path.stat().st_mtime
            cur.execute(
                "SELECT mtime FROM indexed_files WHERE file_path = ?",
                (str(file_path),)
            )
            row = cur.fetchone()

            if row and row[0] >= mtime and not force:
                continue

            # Parse and index
            parser = self._parsers[file_path.suffix]
            entities = parser.parse(file_path, project_id)

            for entity in entities:
                cur.execute("""
                    INSERT OR REPLACE INTO code_entities
                    (id, name, type, signature, docstring, file_path, line_number, content, project_id, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.id, entity.name, entity.type, entity.signature,
                    entity.docstring, entity.file_path, entity.line_number,
                    entity.content, entity.project_id, time.time()
                ))
                stats["entities_indexed"] += 1

            # Update file tracking
            cur.execute("""
                INSERT OR REPLACE INTO indexed_files (file_path, project_id, mtime, indexed_at)
                VALUES (?, ?, ?, ?)
            """, (str(file_path), project_id, mtime, time.time()))

        conn.commit()
        conn.close()

        return stats

    def search(self, query: str, project_id: Optional[str] = None,
               entity_type: Optional[str] = None,
               limit: int = 10) -> List[CodeEntity]:
        """
        Search indexed code entities.

        Args:
            query: Search query
            project_id: Limit to specific project
            entity_type: Limit to specific type (function, class, etc.)
            limit: Maximum results

        Returns:
            List of matching CodeEntity objects
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Build query
        sql = """
            SELECT id, name, type, signature, docstring, file_path, line_number, content, project_id
            FROM code_entities
            WHERE (name LIKE ? OR signature LIKE ? OR content LIKE ? OR docstring LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]

        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)

        if entity_type:
            sql += " AND type = ?"
            params.append(entity_type)

        sql += " LIMIT ?"
        params.append(limit)

        cur.execute(sql, params)

        results = []
        for row in cur.fetchall():
            results.append(CodeEntity(
                id=row[0],
                name=row[1],
                type=row[2],
                signature=row[3],
                docstring=row[4],
                file_path=row[5],
                line_number=row[6],
                content=row[7],
                project_id=row[8]
            ))

        conn.close()
        return results

    def get_stats(self, project_id: Optional[str] = None) -> Dict:
        """Get indexing statistics."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        base_query = "SELECT COUNT(*) FROM code_entities"
        params = []

        if project_id:
            base_query += " WHERE project_id = ?"
            params = [project_id]

        cur.execute(base_query, params)
        total_entities = cur.fetchone()[0]

        # Count by type
        type_query = "SELECT type, COUNT(*) FROM code_entities"
        if project_id:
            type_query += " WHERE project_id = ?"
        type_query += " GROUP BY type"

        cur.execute(type_query, params)
        by_type = {row[0]: row[1] for row in cur.fetchall()}

        # Files indexed
        file_query = "SELECT COUNT(*) FROM indexed_files"
        if project_id:
            file_query += " WHERE project_id = ?"
        cur.execute(file_query, params)
        files_indexed = cur.fetchone()[0]

        conn.close()

        return {
            "total_entities": total_entities,
            "by_type": by_type,
            "files_indexed": files_indexed
        }

    def clear_project(self, project_id: str):
        """Remove all indexed data for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("DELETE FROM code_entities WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM indexed_files WHERE project_id = ?", (project_id,))

        conn.commit()
        conn.close()


# Singleton
_code_indexer = None

def get_code_indexer() -> CodeIndexer:
    """Get singleton code indexer."""
    global _code_indexer
    if _code_indexer is None:
        _code_indexer = CodeIndexer()
    return _code_indexer


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Code Indexer")
    parser.add_argument("command", choices=["index", "search", "stats", "clear"])
    parser.add_argument("--path", default=".")
    parser.add_argument("--project", default="default")
    parser.add_argument("--query", "-q", default="")
    parser.add_argument("--type", "-t", choices=["function", "class", "method", "module", "struct"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    indexer = get_code_indexer()

    if args.command == "index":
        import os
        stats = indexer.index_project(os.path.abspath(args.path), args.project, args.force)
        print(f"Indexing complete:")
        print(f"  Files scanned: {stats['files_scanned']}")
        print(f"  Entities indexed: {stats['entities_indexed']}")
        print(f"  Skipped: {stats['skipped']}")

    elif args.command == "search":
        if not args.query:
            print("Please provide a query with --query")
        else:
            results = indexer.search(args.query, args.project if args.project != "default" else None, args.type)
            print(f"Found {len(results)} results:")
            for r in results:
                print(f"  [{r.type}] {r.name} @ {r.file_path}:{r.line_number}")
                if r.docstring:
                    print(f"       {r.docstring[:80]}...")

    elif args.command == "stats":
        stats = indexer.get_stats(args.project if args.project != "default" else None)
        import json
        print(json.dumps(stats, indent=2))

    elif args.command == "clear":
        indexer.clear_project(args.project)
        print(f"Cleared index for project: {args.project}")
