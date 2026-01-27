"""
Documentation Indexer for SAM RAG System (Phase 2.2.3)

Indexes documentation for intelligent retrieval:
- Markdown files (.md) with smart section chunking
- Code comments (docstrings, inline comments, block comments)
- Generates embeddings for semantic search

Integrates with EnhancedRetrievalSystem and uses same DB as CodeIndexer.
"""

import re
import sqlite3
import hashlib
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# MLX Embeddings - same as semantic_memory.py
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim
_mlx_model = None
_mlx_tokenizer = None


@dataclass
class DocEntity:
    """A documentation entity (section, comment, docstring, etc.)"""
    id: str
    doc_type: str  # markdown, docstring, comment, block_comment
    file_path: str
    section_title: Optional[str]
    content: str
    line_number: int
    project_id: str
    embedding: Optional[List[float]] = None


class MarkdownParser:
    """Parse markdown files into logical sections."""

    # Heading patterns
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.MULTILINE)

    # Max chunk size in characters (reasonable for embeddings)
    MAX_CHUNK_SIZE = 1500
    MIN_CHUNK_SIZE = 100

    def parse(self, file_path: Path, project_id: str) -> List[DocEntity]:
        """Parse a markdown file into sections."""
        entities = []

        try:
            content = file_path.read_text(errors='ignore')
        except Exception:
            return entities

        # Remove code blocks for heading detection (will be preserved in sections)
        content_for_detection = self.CODE_BLOCK_PATTERN.sub('', content)

        # Find all headings
        headings = list(self.HEADING_PATTERN.finditer(content))

        if not headings:
            # No headings - treat as single document
            if len(content.strip()) >= self.MIN_CHUNK_SIZE:
                entity_id = hashlib.md5(f"{file_path}:full".encode()).hexdigest()[:12]
                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="markdown",
                    file_path=str(file_path),
                    section_title=file_path.stem,
                    content=content[:self.MAX_CHUNK_SIZE],
                    line_number=1,
                    project_id=project_id
                ))
            return entities

        # Parse sections between headings
        for i, match in enumerate(headings):
            heading_level = len(match.group(1))
            heading_text = match.group(2).strip()
            start_pos = match.start()

            # Find end of section (next heading of same or higher level, or end of file)
            end_pos = len(content)
            for j in range(i + 1, len(headings)):
                next_level = len(headings[j].group(1))
                if next_level <= heading_level:
                    end_pos = headings[j].start()
                    break

            section_content = content[start_pos:end_pos].strip()
            line_number = content[:start_pos].count('\n') + 1

            # Chunk large sections
            chunks = self._chunk_section(section_content, heading_text)

            for chunk_idx, chunk in enumerate(chunks):
                chunk_title = heading_text if len(chunks) == 1 else f"{heading_text} (part {chunk_idx + 1})"
                entity_id = hashlib.md5(f"{file_path}:{heading_text}:{chunk_idx}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="markdown",
                    file_path=str(file_path),
                    section_title=chunk_title,
                    content=chunk,
                    line_number=line_number,
                    project_id=project_id
                ))

        return entities

    def _chunk_section(self, content: str, heading: str) -> List[str]:
        """Chunk a section if it's too large."""
        if len(content) <= self.MAX_CHUNK_SIZE:
            return [content]

        chunks = []
        current_chunk = ""

        # Split by paragraphs (double newline)
        paragraphs = re.split(r'\n\n+', content)

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.MAX_CHUNK_SIZE:
                current_chunk += para + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # If single paragraph is too long, split by sentences
                if len(para) > self.MAX_CHUNK_SIZE:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 1 <= self.MAX_CHUNK_SIZE:
                            current_chunk += sent + " "
                        else:
                            if current_chunk.strip():
                                chunks.append(current_chunk.strip())
                            current_chunk = sent + " "
                else:
                    current_chunk = para + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [content[:self.MAX_CHUNK_SIZE]]


class CommentParser:
    """Parse code files for comments (inline, block, docstrings)."""

    # Python patterns
    PY_DOCSTRING_PATTERN = re.compile(
        r'^\s*(?:\'\'\'|""")([\s\S]*?)(?:\'\'\'|""")',
        re.MULTILINE
    )
    PY_INLINE_COMMENT_PATTERN = re.compile(r'#\s*(.+)$', re.MULTILINE)

    # JavaScript/TypeScript patterns
    JS_BLOCK_COMMENT_PATTERN = re.compile(
        r'/\*\*?\s*([\s\S]*?)\s*\*/',
        re.MULTILINE
    )
    JS_INLINE_COMMENT_PATTERN = re.compile(r'//\s*(.+)$', re.MULTILINE)

    # Rust patterns
    RS_DOC_COMMENT_PATTERN = re.compile(r'^///\s*(.+)$', re.MULTILINE)
    RS_BLOCK_COMMENT_PATTERN = re.compile(r'/\*!?\s*([\s\S]*?)\s*\*/')

    # Min comment length to index
    MIN_COMMENT_LENGTH = 20

    # Comments to skip (common noise)
    SKIP_PATTERNS = [
        re.compile(r'^TODO:?\s*$', re.IGNORECASE),
        re.compile(r'^FIXME:?\s*$', re.IGNORECASE),
        re.compile(r'^XXX:?\s*$', re.IGNORECASE),
        re.compile(r'^\s*-{3,}\s*$'),  # Divider lines
        re.compile(r'^\s*={3,}\s*$'),
        re.compile(r'^#!'),  # Shebangs
        re.compile(r'^pylint:\s*'),
        re.compile(r'^type:\s*ignore'),
        re.compile(r'^noqa'),
        re.compile(r'^@\w+'),  # Decorators/annotations
    ]

    def parse(self, file_path: Path, project_id: str) -> List[DocEntity]:
        """Parse a code file for comments."""
        entities = []
        suffix = file_path.suffix.lower()

        try:
            content = file_path.read_text(errors='ignore')
        except Exception:
            return entities

        if suffix == '.py':
            entities.extend(self._parse_python(file_path, content, project_id))
        elif suffix in ('.js', '.ts', '.jsx', '.tsx'):
            entities.extend(self._parse_javascript(file_path, content, project_id))
        elif suffix == '.rs':
            entities.extend(self._parse_rust(file_path, content, project_id))

        return entities

    def _parse_python(self, file_path: Path, content: str, project_id: str) -> List[DocEntity]:
        """Parse Python comments."""
        entities = []

        # Docstrings (standalone, not function/class docstrings - those are in code_indexer)
        # We focus on module-level docstrings and explanatory comments
        for match in self.PY_DOCSTRING_PATTERN.finditer(content):
            doc_content = match.group(1).strip()
            if len(doc_content) >= self.MIN_COMMENT_LENGTH and not self._should_skip(doc_content):
                line_num = content[:match.start()].count('\n') + 1
                entity_id = hashlib.md5(f"{file_path}:docstring:{line_num}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="docstring",
                    file_path=str(file_path),
                    section_title=f"Docstring at line {line_num}",
                    content=doc_content[:1500],
                    line_number=line_num,
                    project_id=project_id
                ))

        # Collect consecutive inline comments as blocks
        comment_blocks = self._collect_comment_blocks(content, self.PY_INLINE_COMMENT_PATTERN)
        for block_start, block_content in comment_blocks:
            if len(block_content) >= self.MIN_COMMENT_LENGTH and not self._should_skip(block_content):
                entity_id = hashlib.md5(f"{file_path}:comment:{block_start}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="comment",
                    file_path=str(file_path),
                    section_title=f"Comment block at line {block_start}",
                    content=block_content[:1500],
                    line_number=block_start,
                    project_id=project_id
                ))

        return entities

    def _parse_javascript(self, file_path: Path, content: str, project_id: str) -> List[DocEntity]:
        """Parse JavaScript/TypeScript comments."""
        entities = []

        # Block comments (JSDoc style)
        for match in self.JS_BLOCK_COMMENT_PATTERN.finditer(content):
            doc_content = self._clean_jsdoc(match.group(1))
            if len(doc_content) >= self.MIN_COMMENT_LENGTH and not self._should_skip(doc_content):
                line_num = content[:match.start()].count('\n') + 1
                entity_id = hashlib.md5(f"{file_path}:block:{line_num}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="block_comment",
                    file_path=str(file_path),
                    section_title=f"Block comment at line {line_num}",
                    content=doc_content[:1500],
                    line_number=line_num,
                    project_id=project_id
                ))

        # Inline comments
        comment_blocks = self._collect_comment_blocks(content, self.JS_INLINE_COMMENT_PATTERN)
        for block_start, block_content in comment_blocks:
            if len(block_content) >= self.MIN_COMMENT_LENGTH and not self._should_skip(block_content):
                entity_id = hashlib.md5(f"{file_path}:comment:{block_start}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="comment",
                    file_path=str(file_path),
                    section_title=f"Comment at line {block_start}",
                    content=block_content[:1500],
                    line_number=block_start,
                    project_id=project_id
                ))

        return entities

    def _parse_rust(self, file_path: Path, content: str, project_id: str) -> List[DocEntity]:
        """Parse Rust comments."""
        entities = []

        # Doc comments (///)
        doc_comments = []
        current_block = []
        current_start = None

        for match in self.RS_DOC_COMMENT_PATTERN.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            comment_text = match.group(1)

            if current_start is None:
                current_start = line_num
                current_block = [comment_text]
            elif line_num == current_start + len(current_block):
                # Consecutive line
                current_block.append(comment_text)
            else:
                # New block
                if current_block:
                    doc_comments.append((current_start, '\n'.join(current_block)))
                current_start = line_num
                current_block = [comment_text]

        if current_block:
            doc_comments.append((current_start, '\n'.join(current_block)))

        for line_num, doc_content in doc_comments:
            if len(doc_content) >= self.MIN_COMMENT_LENGTH and not self._should_skip(doc_content):
                entity_id = hashlib.md5(f"{file_path}:doc:{line_num}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="docstring",
                    file_path=str(file_path),
                    section_title=f"Doc comment at line {line_num}",
                    content=doc_content[:1500],
                    line_number=line_num,
                    project_id=project_id
                ))

        # Block comments
        for match in self.RS_BLOCK_COMMENT_PATTERN.finditer(content):
            doc_content = match.group(1).strip()
            if len(doc_content) >= self.MIN_COMMENT_LENGTH and not self._should_skip(doc_content):
                line_num = content[:match.start()].count('\n') + 1
                entity_id = hashlib.md5(f"{file_path}:block:{line_num}".encode()).hexdigest()[:12]

                entities.append(DocEntity(
                    id=entity_id,
                    doc_type="block_comment",
                    file_path=str(file_path),
                    section_title=f"Block comment at line {line_num}",
                    content=doc_content[:1500],
                    line_number=line_num,
                    project_id=project_id
                ))

        return entities

    def _collect_comment_blocks(self, content: str, pattern: re.Pattern) -> List[Tuple[int, str]]:
        """Collect consecutive comments into blocks."""
        blocks = []
        current_block = []
        current_start = None
        last_line = -2

        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            comment_text = match.group(1).strip()

            if line_num <= last_line + 1:
                # Consecutive or same line
                current_block.append(comment_text)
            else:
                # New block
                if current_block:
                    blocks.append((current_start, '\n'.join(current_block)))
                current_start = line_num
                current_block = [comment_text]

            last_line = line_num

        if current_block:
            blocks.append((current_start, '\n'.join(current_block)))

        return blocks

    def _clean_jsdoc(self, content: str) -> str:
        """Clean JSDoc comment content."""
        # Remove leading * from each line
        lines = content.split('\n')
        cleaned = []
        for line in lines:
            line = re.sub(r'^\s*\*\s?', '', line)
            cleaned.append(line)
        return '\n'.join(cleaned).strip()

    def _should_skip(self, content: str) -> bool:
        """Check if comment should be skipped."""
        content_stripped = content.strip()
        for pattern in self.SKIP_PATTERNS:
            if pattern.search(content_stripped):
                return True
        return False


class DocIndexer:
    """
    Documentation indexer that scans projects and builds a searchable index.
    Uses same database as CodeIndexer for unified retrieval.
    """

    DB_PATH = Path("/Volumes/David External/sam_memory/code_index.db")

    DOC_EXTENSIONS = {'.md', '.markdown', '.rst', '.txt'}
    CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs'}

    SKIP_DIRS = {
        'node_modules', '.git', 'target', 'dist', 'build',
        '__pycache__', '.venv', 'venv', 'site-packages',
        '.next', '.nuxt', 'coverage', '.mypy_cache'
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.markdown_parser = MarkdownParser()
        self.comment_parser = CommentParser()

    def _init_db(self):
        """Initialize the database schema for documents."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Documents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                doc_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                section_title TEXT,
                content TEXT NOT NULL,
                line_number INTEGER,
                project_id TEXT,
                indexed_at REAL
            )
        """)

        # Embeddings table for semantic search
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doc_embeddings (
                doc_id TEXT PRIMARY KEY,
                embedding BLOB,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_project ON documents(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_file ON documents(file_path)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_title ON documents(section_title)")

        # Track indexed doc files
        cur.execute("""
            CREATE TABLE IF NOT EXISTS indexed_doc_files (
                file_path TEXT PRIMARY KEY,
                project_id TEXT,
                mtime REAL,
                indexed_at REAL
            )
        """)

        conn.commit()
        conn.close()

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

    def index_docs(self, path: str, project_id: str = "default",
                   force: bool = False, with_embeddings: bool = True) -> Dict[str, int]:
        """
        Index all documentation in a path.

        Args:
            path: Path to project root or specific file
            project_id: Unique project identifier
            force: Re-index even if files haven't changed
            with_embeddings: Generate embeddings for semantic search

        Returns:
            Stats dict with counts
        """
        path = Path(path)
        if not path.exists():
            return {"error": "Path not found", "indexed": 0}

        stats = {
            "files_scanned": 0,
            "docs_indexed": 0,
            "comments_indexed": 0,
            "embeddings_generated": 0,
            "skipped": 0
        }

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Get files to process
        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob('*'))

        for file_path in files:
            if not file_path.is_file():
                continue
            if any(skip in file_path.parts for skip in self.SKIP_DIRS):
                stats["skipped"] += 1
                continue

            suffix = file_path.suffix.lower()
            if suffix not in self.DOC_EXTENSIONS and suffix not in self.CODE_EXTENSIONS:
                continue

            stats["files_scanned"] += 1

            # Check if file needs re-indexing
            mtime = file_path.stat().st_mtime
            cur.execute(
                "SELECT mtime FROM indexed_doc_files WHERE file_path = ?",
                (str(file_path),)
            )
            row = cur.fetchone()

            if row and row[0] >= mtime and not force:
                continue

            # Parse and index
            entities = []

            if suffix in self.DOC_EXTENSIONS:
                entities = self.markdown_parser.parse(file_path, project_id)
                stats["docs_indexed"] += len(entities)
            elif suffix in self.CODE_EXTENSIONS:
                entities = self.comment_parser.parse(file_path, project_id)
                stats["comments_indexed"] += len(entities)

            for entity in entities:
                cur.execute("""
                    INSERT OR REPLACE INTO documents
                    (id, doc_type, file_path, section_title, content, line_number, project_id, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.id, entity.doc_type, entity.file_path, entity.section_title,
                    entity.content, entity.line_number, entity.project_id, time.time()
                ))

                # Generate embedding
                if with_embeddings:
                    embedding = self._get_embedding(entity.content)
                    if embedding is not None:
                        cur.execute("""
                            INSERT OR REPLACE INTO doc_embeddings (doc_id, embedding)
                            VALUES (?, ?)
                        """, (entity.id, embedding.tobytes()))
                        stats["embeddings_generated"] += 1

            # Update file tracking
            cur.execute("""
                INSERT OR REPLACE INTO indexed_doc_files (file_path, project_id, mtime, indexed_at)
                VALUES (?, ?, ?, ?)
            """, (str(file_path), project_id, mtime, time.time()))

        conn.commit()
        conn.close()

        return stats

    def search_docs(self, query: str, limit: int = 10,
                    doc_type: Optional[str] = None,
                    project_id: Optional[str] = None,
                    use_semantic: bool = True) -> List[Tuple[DocEntity, float]]:
        """
        Search indexed documents.

        Args:
            query: Search query
            limit: Maximum results
            doc_type: Filter by type (markdown, docstring, comment, block_comment)
            project_id: Filter by project
            use_semantic: Use semantic (embedding) search if available

        Returns:
            List of (DocEntity, score) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        results = []

        if use_semantic:
            # Try semantic search first
            query_embedding = self._get_embedding(query)
            if query_embedding is not None:
                results = self._semantic_search(cur, query_embedding, limit, doc_type, project_id)

        # Fall back to keyword search if no semantic results
        if not results:
            results = self._keyword_search(cur, query, limit, doc_type, project_id)

        conn.close()
        return results

    def _semantic_search(self, cur: sqlite3.Cursor, query_embedding: np.ndarray,
                         limit: int, doc_type: Optional[str],
                         project_id: Optional[str]) -> List[Tuple[DocEntity, float]]:
        """Perform semantic search using embeddings."""
        # Build base query
        sql = """
            SELECT d.id, d.doc_type, d.file_path, d.section_title, d.content, d.line_number, d.project_id, e.embedding
            FROM documents d
            JOIN doc_embeddings e ON d.id = e.doc_id
            WHERE 1=1
        """
        params = []

        if doc_type:
            sql += " AND d.doc_type = ?"
            params.append(doc_type)

        if project_id:
            sql += " AND d.project_id = ?"
            params.append(project_id)

        cur.execute(sql, params)

        results = []
        for row in cur.fetchall():
            entity = DocEntity(
                id=row[0],
                doc_type=row[1],
                file_path=row[2],
                section_title=row[3],
                content=row[4],
                line_number=row[5],
                project_id=row[6]
            )

            # Calculate cosine similarity
            doc_embedding = np.frombuffer(row[7], dtype=np.float32)
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )

            results.append((entity, float(similarity)))

        # Sort by similarity and limit
        results.sort(key=lambda x: -x[1])
        return results[:limit]

    def _keyword_search(self, cur: sqlite3.Cursor, query: str,
                        limit: int, doc_type: Optional[str],
                        project_id: Optional[str]) -> List[Tuple[DocEntity, float]]:
        """Perform keyword search."""
        sql = """
            SELECT id, doc_type, file_path, section_title, content, line_number, project_id
            FROM documents
            WHERE (content LIKE ? OR section_title LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]

        if doc_type:
            sql += " AND doc_type = ?"
            params.append(doc_type)

        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)

        sql += " LIMIT ?"
        params.append(limit)

        cur.execute(sql, params)

        results = []
        for row in cur.fetchall():
            entity = DocEntity(
                id=row[0],
                doc_type=row[1],
                file_path=row[2],
                section_title=row[3],
                content=row[4],
                line_number=row[5],
                project_id=row[6]
            )
            # Simple relevance score based on match count
            score = (row[4].lower().count(query.lower()) +
                     (row[3] or '').lower().count(query.lower()) * 2)
            score = min(score / 10, 1.0)  # Normalize
            results.append((entity, score))

        results.sort(key=lambda x: -x[1])
        return results

    def get_doc_context(self, file_path: str) -> List[DocEntity]:
        """
        Get all documentation context for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of DocEntity objects for the file
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, doc_type, file_path, section_title, content, line_number, project_id
            FROM documents
            WHERE file_path = ?
            ORDER BY line_number
        """, (file_path,))

        results = []
        for row in cur.fetchall():
            results.append(DocEntity(
                id=row[0],
                doc_type=row[1],
                file_path=row[2],
                section_title=row[3],
                content=row[4],
                line_number=row[5],
                project_id=row[6]
            ))

        conn.close()
        return results

    def get_stats(self, project_id: Optional[str] = None) -> Dict:
        """Get indexing statistics."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        base_query = "SELECT COUNT(*) FROM documents"
        params = []

        if project_id:
            base_query += " WHERE project_id = ?"
            params = [project_id]

        cur.execute(base_query, params)
        total_docs = cur.fetchone()[0]

        # Count by type
        type_query = "SELECT doc_type, COUNT(*) FROM documents"
        if project_id:
            type_query += " WHERE project_id = ?"
        type_query += " GROUP BY doc_type"

        cur.execute(type_query, params)
        by_type = {row[0]: row[1] for row in cur.fetchall()}

        # Count embeddings
        emb_query = "SELECT COUNT(*) FROM doc_embeddings"
        cur.execute(emb_query)
        embeddings_count = cur.fetchone()[0]

        # Files indexed
        file_query = "SELECT COUNT(*) FROM indexed_doc_files"
        if project_id:
            file_query += " WHERE project_id = ?"
        cur.execute(file_query, params)
        files_indexed = cur.fetchone()[0]

        conn.close()

        return {
            "total_documents": total_docs,
            "by_type": by_type,
            "embeddings_count": embeddings_count,
            "files_indexed": files_indexed
        }

    def clear_project(self, project_id: str):
        """Remove all indexed documentation for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Get doc IDs for the project
        cur.execute("SELECT id FROM documents WHERE project_id = ?", (project_id,))
        doc_ids = [row[0] for row in cur.fetchall()]

        # Delete embeddings
        for doc_id in doc_ids:
            cur.execute("DELETE FROM doc_embeddings WHERE doc_id = ?", (doc_id,))

        # Delete documents
        cur.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM indexed_doc_files WHERE project_id = ?", (project_id,))

        conn.commit()
        conn.close()


# Singleton
_doc_indexer = None

def get_doc_indexer() -> DocIndexer:
    """Get singleton doc indexer."""
    global _doc_indexer
    if _doc_indexer is None:
        _doc_indexer = DocIndexer()
    return _doc_indexer


# CLI
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="SAM Documentation Indexer")
    parser.add_argument("command", choices=["index", "search", "context", "stats", "clear"])
    parser.add_argument("--path", "-p", default=".")
    parser.add_argument("--project", default="default")
    parser.add_argument("--query", "-q", default="")
    parser.add_argument("--type", "-t", choices=["markdown", "docstring", "comment", "block_comment"])
    parser.add_argument("--limit", "-l", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding generation")
    args = parser.parse_args()

    indexer = get_doc_indexer()

    if args.command == "index":
        import os
        print(f"Indexing documentation in {os.path.abspath(args.path)}...")
        stats = indexer.index_docs(
            os.path.abspath(args.path),
            args.project,
            args.force,
            with_embeddings=not args.no_embeddings
        )
        print(f"Indexing complete:")
        print(f"  Files scanned: {stats['files_scanned']}")
        print(f"  Docs indexed: {stats['docs_indexed']}")
        print(f"  Comments indexed: {stats['comments_indexed']}")
        print(f"  Embeddings generated: {stats['embeddings_generated']}")
        print(f"  Skipped: {stats['skipped']}")

    elif args.command == "search":
        if not args.query:
            print("Please provide a query with --query")
        else:
            results = indexer.search_docs(
                args.query,
                limit=args.limit,
                doc_type=args.type,
                project_id=args.project if args.project != "default" else None
            )
            print(f"Found {len(results)} results for '{args.query}':")
            for entity, score in results:
                print(f"\n  [{entity.doc_type}] {entity.section_title or 'Untitled'}")
                print(f"  File: {entity.file_path}:{entity.line_number}")
                print(f"  Score: {score:.3f}")
                preview = entity.content[:150].replace('\n', ' ')
                print(f"  Preview: {preview}...")

    elif args.command == "context":
        if not args.path or args.path == ".":
            print("Please provide a file path with --path")
        else:
            import os
            results = indexer.get_doc_context(os.path.abspath(args.path))
            print(f"Documentation context for {args.path}:")
            for entity in results:
                print(f"\n  [{entity.doc_type}] Line {entity.line_number}: {entity.section_title or 'Untitled'}")
                preview = entity.content[:200].replace('\n', ' ')
                print(f"  {preview}...")

    elif args.command == "stats":
        stats = indexer.get_stats(args.project if args.project != "default" else None)
        print(json.dumps(stats, indent=2))

    elif args.command == "clear":
        indexer.clear_project(args.project)
        print(f"Cleared documentation index for project: {args.project}")
