#!/usr/bin/env python3
"""
SAM Code Indexer - Phase 2.2.7

Indexes code files for intelligent retrieval with semantic search:
- Function signatures and docstrings
- Class definitions and methods
- Module-level documentation
- Import statements
- Supports: Python, Rust, Swift, TypeScript/JavaScript

Integrates with SemanticMemory for MLX-based embeddings.

Phase 2.2.7: Incremental index updates with file watching
- IndexWatcher class monitors directories for changes
- Polling-based detection (30 second intervals)
- Background thread operation
- Callbacks for change notifications

Storage: /Volumes/David External/sam_memory/code_index.db
"""

import ast
import re
import sqlite3
import hashlib
import time
import json
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime


# Database path on external storage
DB_PATH = Path("/Volumes/David External/sam_memory/code_index.db")

# MLX Embeddings - shared with semantic_memory.py
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_mlx_model = None
_mlx_tokenizer = None


def _get_embedding(text: str) -> Optional[np.ndarray]:
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

    except ImportError:
        # Fallback: return None if mlx_embeddings not available
        return None
    except Exception as e:
        print(f"MLX Embedding error: {e}")
        return None


@dataclass
class CodeSymbol:
    """A code symbol (function, class, method, import, etc.)"""
    id: str
    name: str
    symbol_type: str  # function, class, method, module, import, struct, enum, protocol
    signature: str
    docstring: Optional[str]
    file_path: str
    line_number: int
    content: str  # Full content for embedding
    project_id: str
    imports: Optional[str] = None  # JSON list of imports for modules
    embedding: Optional[bytes] = None  # Serialized embedding

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop('embedding', None)
        return d


# =============================================================================
# Language Parsers
# =============================================================================

class PythonParser:
    """Parse Python files using AST for accurate extraction."""

    def parse(self, file_path: Path, project_id: str) -> List[CodeSymbol]:
        """Parse a Python file and extract code symbols."""
        symbols = []

        try:
            content = file_path.read_text(errors='ignore')
            tree = ast.parse(content)
            lines = content.split('\n')
        except Exception as e:
            return symbols

        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

        # Module-level symbol with imports
        if tree.body:
            module_doc = None
            if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
                docstring = tree.body[0].value.value
                if isinstance(docstring, str) and len(docstring) > 10:
                    module_doc = docstring[:1000]

            symbol_id = hashlib.md5(f"{file_path}:module".encode()).hexdigest()[:12]
            symbols.append(CodeSymbol(
                id=symbol_id,
                name=file_path.stem,
                symbol_type="module",
                signature=f"Module: {file_path.name}",
                docstring=module_doc,
                file_path=str(file_path),
                line_number=1,
                content=f"Module {file_path.name}\nImports: {', '.join(imports[:20])}\n{module_doc or ''}",
                project_id=project_id,
                imports=json.dumps(imports) if imports else None
            ))

        # Parse functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append(self._parse_function(node, file_path, lines, project_id))
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.append(self._parse_function(node, file_path, lines, project_id, async_=True))
            elif isinstance(node, ast.ClassDef):
                symbols.append(self._parse_class(node, file_path, lines, project_id))

        return symbols

    def _parse_function(self, node: ast.FunctionDef, file_path: Path,
                        lines: List[str], project_id: str, async_: bool = False) -> CodeSymbol:
        """Parse a function definition."""
        prefix = "async " if async_ else ""

        # Build signature with type annotations
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)

        # Handle *args and **kwargs
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        returns = ""
        if node.returns:
            try:
                returns = f" -> {ast.unparse(node.returns)}"
            except:
                pass

        signature = f"{prefix}def {node.name}({', '.join(args)}){returns}"

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get function body snippet
        start_line = node.lineno - 1
        end_line = min(start_line + 25, len(lines))
        body_snippet = '\n'.join(lines[start_line:end_line])

        symbol_id = hashlib.md5(f"{file_path}:{node.name}:{node.lineno}".encode()).hexdigest()[:12]

        content = f"{signature}\n"
        if docstring:
            content += f'"""{docstring[:400]}"""\n'
        content += body_snippet[:600]

        return CodeSymbol(
            id=symbol_id,
            name=node.name,
            symbol_type="function",
            signature=signature,
            docstring=docstring[:1000] if docstring else None,
            file_path=str(file_path),
            line_number=node.lineno,
            content=content,
            project_id=project_id
        )

    def _parse_class(self, node: ast.ClassDef, file_path: Path,
                     lines: List[str], project_id: str) -> CodeSymbol:
        """Parse a class definition."""
        # Build signature with bases
        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except:
                pass

        signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get method names
        methods = []
        for n in node.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(n.name)

        # Get class attributes
        attributes = []
        for n in node.body:
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                attr = n.target.id
                if n.annotation:
                    try:
                        attr += f": {ast.unparse(n.annotation)}"
                    except:
                        pass
                attributes.append(attr)

        symbol_id = hashlib.md5(f"{file_path}:{node.name}:{node.lineno}".encode()).hexdigest()[:12]

        content = f"{signature}\n"
        if docstring:
            content += f'"""{docstring[:400]}"""\n'
        if attributes:
            content += f"Attributes: {', '.join(attributes[:10])}\n"
        content += f"Methods: {', '.join(methods[:15])}"

        return CodeSymbol(
            id=symbol_id,
            name=node.name,
            symbol_type="class",
            signature=signature,
            docstring=docstring[:1000] if docstring else None,
            file_path=str(file_path),
            line_number=node.lineno,
            content=content,
            project_id=project_id
        )


class TypeScriptParser:
    """Parse JavaScript/TypeScript files using regex."""

    FUNCTION_PATTERN = re.compile(
        r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(<[^>]*>)?\s*\(([^)]*)\)(?:\s*:\s*([^\{]+))?',
        re.MULTILINE
    )
    ARROW_PATTERN = re.compile(
        r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*([^\=\>]+))?\s*=>',
        re.MULTILINE
    )
    CLASS_PATTERN = re.compile(
        r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:<[^>]*>)?(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?',
        re.MULTILINE
    )
    INTERFACE_PATTERN = re.compile(
        r'(?:export\s+)?interface\s+(\w+)(?:<[^>]*>)?(?:\s+extends\s+([^{]+))?',
        re.MULTILINE
    )
    TYPE_PATTERN = re.compile(
        r'(?:export\s+)?type\s+(\w+)\s*(?:<[^>]*>)?\s*=',
        re.MULTILINE
    )
    IMPORT_PATTERN = re.compile(
        r'import\s+(?:\{[^}]+\}|[\w*]+)\s+from\s+[\'"]([^\'"]+)[\'"]',
        re.MULTILINE
    )
    JSDOC_PATTERN = re.compile(
        r'/\*\*\s*(.*?)\s*\*/',
        re.DOTALL
    )

    def parse(self, file_path: Path, project_id: str) -> List[CodeSymbol]:
        """Parse a JavaScript/TypeScript file."""
        symbols = []

        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')
        except Exception:
            return symbols

        # Extract imports
        imports = [m.group(1) for m in self.IMPORT_PATTERN.finditer(content)]

        # Module symbol with imports
        symbol_id = hashlib.md5(f"{file_path}:module".encode()).hexdigest()[:12]
        symbols.append(CodeSymbol(
            id=symbol_id,
            name=file_path.stem,
            symbol_type="module",
            signature=f"Module: {file_path.name}",
            docstring=None,
            file_path=str(file_path),
            line_number=1,
            content=f"Module {file_path.name}\nImports: {', '.join(imports[:20])}",
            project_id=project_id,
            imports=json.dumps(imports) if imports else None
        ))

        # Parse functions
        for match in self.FUNCTION_PATTERN.finditer(content):
            name = match.group(1)
            generics = match.group(2) or ""
            params = match.group(3)
            return_type = match.group(4) or ""
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            signature = f"function {name}{generics}({params}){': ' + return_type.strip() if return_type.strip() else ''}"
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 15)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse arrow functions
        for match in self.ARROW_PATTERN.finditer(content):
            name = match.group(1)
            params = match.group(2)
            return_type = match.group(3) or ""
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            signature = f"const {name} = ({params}){': ' + return_type.strip() if return_type.strip() else ''} =>"
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 10)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse classes
        for match in self.CLASS_PATTERN.finditer(content):
            name = match.group(1)
            extends = match.group(2)
            implements = match.group(3)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            signature = f"class {name}"
            if extends:
                signature += f" extends {extends}"
            if implements:
                signature += f" implements {implements.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 20)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="class",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse interfaces
        for match in self.INTERFACE_PATTERN.finditer(content):
            name = match.group(1)
            extends = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            signature = f"interface {name}" + (f" extends {extends.strip()}" if extends else "")
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 15)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="interface",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse type aliases
        for match in self.TYPE_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_jsdoc(content, match.start())
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 5)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="type",
                signature=f"type {name}",
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=snippet[:400],
                project_id=project_id
            ))

        return symbols

    def _find_jsdoc(self, content: str, pos: int) -> Optional[str]:
        """Find JSDoc comment before a position."""
        search_start = max(0, pos - 500)
        search_area = content[search_start:pos]

        match = self.JSDOC_PATTERN.search(search_area)
        if match:
            doc = match.group(1)
            doc = re.sub(r'\n\s*\*\s*', '\n', doc)
            return doc.strip()[:500]
        return None

    def _get_snippet(self, lines: List[str], start: int, count: int) -> str:
        """Get a snippet of lines."""
        end = min(start + count, len(lines))
        return '\n'.join(lines[start:end])


class RustParser:
    """Parse Rust files using regex."""

    FUNCTION_PATTERN = re.compile(
        r'(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)\s*(<[^>]*>)?\s*\(([^)]*)\)(?:\s*->\s*([^\{]+))?',
        re.MULTILINE
    )
    STRUCT_PATTERN = re.compile(
        r'(?:pub(?:\([^)]*\))?\s+)?struct\s+(\w+)(?:<[^>]*>)?',
        re.MULTILINE
    )
    ENUM_PATTERN = re.compile(
        r'(?:pub(?:\([^)]*\))?\s+)?enum\s+(\w+)(?:<[^>]*>)?',
        re.MULTILINE
    )
    TRAIT_PATTERN = re.compile(
        r'(?:pub(?:\([^)]*\))?\s+)?trait\s+(\w+)(?:<[^>]*>)?',
        re.MULTILINE
    )
    IMPL_PATTERN = re.compile(
        r'impl(?:<[^>]*>)?\s+(?:(\w+)\s+for\s+)?(\w+)',
        re.MULTILINE
    )
    USE_PATTERN = re.compile(
        r'use\s+([^;]+);',
        re.MULTILINE
    )

    def parse(self, file_path: Path, project_id: str) -> List[CodeSymbol]:
        """Parse a Rust file."""
        symbols = []

        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')
        except Exception:
            return symbols

        # Extract use statements (imports)
        imports = [m.group(1).strip() for m in self.USE_PATTERN.finditer(content)]

        # Module symbol
        symbol_id = hashlib.md5(f"{file_path}:module".encode()).hexdigest()[:12]
        # Get module doc (//! comments at top)
        module_doc = self._find_module_doc(lines)

        symbols.append(CodeSymbol(
            id=symbol_id,
            name=file_path.stem,
            symbol_type="module",
            signature=f"Module: {file_path.name}",
            docstring=module_doc,
            file_path=str(file_path),
            line_number=1,
            content=f"Module {file_path.name}\nImports: {', '.join(imports[:15])}\n{module_doc or ''}",
            project_id=project_id,
            imports=json.dumps(imports) if imports else None
        ))

        # Parse functions
        for match in self.FUNCTION_PATTERN.finditer(content):
            name = match.group(1)
            generics = match.group(2) or ""
            params = match.group(3)
            return_type = match.group(4) or ""
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"fn {name}{generics}({params.strip()})"
            if return_type.strip():
                signature += f" -> {return_type.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 15)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse structs
        for match in self.STRUCT_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"struct {name}"
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 20)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="struct",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse enums
        for match in self.ENUM_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"enum {name}"
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 15)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="enum",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse traits
        for match in self.TRAIT_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"trait {name}"
            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]

            snippet = self._get_snippet(lines, line_num - 1, 20)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="trait",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        return symbols

    def _find_module_doc(self, lines: List[str]) -> Optional[str]:
        """Find //! module documentation at the top of file."""
        docs = []
        for line in lines[:30]:
            stripped = line.strip()
            if stripped.startswith('//!'):
                docs.append(stripped[3:].strip())
            elif stripped and not stripped.startswith('//'):
                break
        return '\n'.join(docs) if docs else None

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


class SwiftParser:
    """Parse Swift files using regex."""

    FUNCTION_PATTERN = re.compile(
        r'(?:(?:public|private|internal|fileprivate|open)\s+)?(?:static\s+)?(?:class\s+)?(?:override\s+)?func\s+(\w+)\s*(<[^>]*>)?\s*\(([^)]*)\)(?:\s*(?:throws\s+)?(?:async\s+)?(?:->\s*([^\{]+))?)?',
        re.MULTILINE
    )
    CLASS_PATTERN = re.compile(
        r'(?:(?:public|private|internal|fileprivate|open)\s+)?(?:final\s+)?class\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+))?',
        re.MULTILINE
    )
    STRUCT_PATTERN = re.compile(
        r'(?:(?:public|private|internal|fileprivate|open)\s+)?struct\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+))?',
        re.MULTILINE
    )
    ENUM_PATTERN = re.compile(
        r'(?:(?:public|private|internal|fileprivate|open)\s+)?enum\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+))?',
        re.MULTILINE
    )
    PROTOCOL_PATTERN = re.compile(
        r'(?:(?:public|private|internal|fileprivate|open)\s+)?protocol\s+(\w+)(?:\s*:\s*([^{\n]+))?\s*\{',
        re.MULTILINE
    )
    EXTENSION_PATTERN = re.compile(
        r'extension\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+))?',
        re.MULTILINE
    )
    IMPORT_PATTERN = re.compile(
        r'import\s+(\w+)',
        re.MULTILINE
    )

    def parse(self, file_path: Path, project_id: str) -> List[CodeSymbol]:
        """Parse a Swift file."""
        symbols = []

        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')
        except Exception:
            return symbols

        # Extract imports
        imports = [m.group(1) for m in self.IMPORT_PATTERN.finditer(content)]

        # Module symbol
        symbol_id = hashlib.md5(f"{file_path}:module".encode()).hexdigest()[:12]
        symbols.append(CodeSymbol(
            id=symbol_id,
            name=file_path.stem,
            symbol_type="module",
            signature=f"Module: {file_path.name}",
            docstring=None,
            file_path=str(file_path),
            line_number=1,
            content=f"Module {file_path.name}\nImports: {', '.join(imports[:15])}",
            project_id=project_id,
            imports=json.dumps(imports) if imports else None
        ))

        # Parse functions
        for match in self.FUNCTION_PATTERN.finditer(content):
            name = match.group(1)
            generics = match.group(2) or ""
            params = match.group(3)
            return_type = match.group(4) or ""
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"func {name}{generics}({params.strip()})"
            if return_type.strip():
                signature += f" -> {return_type.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 15)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="function",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse classes
        for match in self.CLASS_PATTERN.finditer(content):
            name = match.group(1)
            conformances = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"class {name}"
            if conformances:
                signature += f": {conformances.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 20)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="class",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse structs
        for match in self.STRUCT_PATTERN.finditer(content):
            name = match.group(1)
            conformances = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"struct {name}"
            if conformances:
                signature += f": {conformances.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 20)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="struct",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse enums
        for match in self.ENUM_PATTERN.finditer(content):
            name = match.group(1)
            conformances = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"enum {name}"
            if conformances:
                signature += f": {conformances.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 15)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="enum",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        # Parse protocols
        for match in self.PROTOCOL_PATTERN.finditer(content):
            name = match.group(1)
            conformances = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            docstring = self._find_doc_comment(lines, line_num - 1)
            signature = f"protocol {name}"
            if conformances:
                signature += f": {conformances.strip()}"

            symbol_id = hashlib.md5(f"{file_path}:{name}:{line_num}".encode()).hexdigest()[:12]
            snippet = self._get_snippet(lines, line_num - 1, 20)

            symbols.append(CodeSymbol(
                id=symbol_id,
                name=name,
                symbol_type="protocol",
                signature=signature,
                docstring=docstring,
                file_path=str(file_path),
                line_number=line_num,
                content=f"{signature}\n{docstring or ''}\n{snippet}"[:600],
                project_id=project_id
            ))

        return symbols

    def _find_doc_comment(self, lines: List[str], line_num: int) -> Optional[str]:
        """Find /// or /** */ doc comments before a line."""
        docs = []
        i = line_num - 1

        # Check for /// style comments
        while i >= 0:
            stripped = lines[i].strip()
            if stripped.startswith('///'):
                docs.insert(0, stripped[3:].strip())
                i -= 1
            elif stripped.startswith('/**'):
                # Multi-line doc comment
                break
            elif stripped:
                break
            else:
                i -= 1

        if docs:
            return '\n'.join(docs)

        # Check for /** */ style comments
        i = line_num - 1
        while i >= 0:
            if '*/' in lines[i]:
                # Found end of block comment, look for start
                end_idx = i
                while i >= 0:
                    if '/**' in lines[i]:
                        block = '\n'.join(lines[i:end_idx + 1])
                        # Clean up the comment
                        block = re.sub(r'/\*\*|\*/', '', block)
                        block = re.sub(r'\n\s*\*\s*', '\n', block)
                        return block.strip()[:500]
                    i -= 1
                break
            elif lines[i].strip():
                break
            i -= 1

        return None

    def _get_snippet(self, lines: List[str], start: int, count: int) -> str:
        """Get a snippet of lines."""
        end = min(start + count, len(lines))
        return '\n'.join(lines[start:end])


# =============================================================================
# Main Code Indexer
# =============================================================================

class CodeIndexer:
    """
    Main code indexer that scans projects and builds a searchable index
    with semantic embeddings for intelligent retrieval.
    """

    EXTENSION_PARSERS = {
        '.py': PythonParser,
        '.js': TypeScriptParser,
        '.ts': TypeScriptParser,
        '.jsx': TypeScriptParser,
        '.tsx': TypeScriptParser,
        '.mjs': TypeScriptParser,
        '.rs': RustParser,
        '.swift': SwiftParser,
    }

    SKIP_DIRS = {
        'node_modules', '.git', 'target', 'dist', 'build',
        '__pycache__', '.venv', 'venv', 'site-packages',
        '.next', '.nuxt', 'coverage', '.mypy_cache',
        'Pods', 'DerivedData', '.build', 'Packages',
        'vendor', 'bower_components', '.cargo'
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._parsers = {ext: parser() for ext, parser in self.EXTENSION_PARSERS.items()}

    def _init_db(self):
        """Initialize the database schema with embeddings support."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS code_symbols (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                symbol_type TEXT NOT NULL,
                signature TEXT,
                docstring TEXT,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                content TEXT,
                project_id TEXT,
                imports TEXT,
                embedding BLOB,
                indexed_at REAL
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol_name ON code_symbols(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol_type ON code_symbols(symbol_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol_project ON code_symbols(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol_file ON code_symbols(file_path)")

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

    def index_project(self, project_path: str, project_id: Optional[str] = None,
                      force: bool = False, generate_embeddings: bool = True) -> Dict[str, int]:
        """
        Index all code files in a project.

        Args:
            project_path: Path to project root
            project_id: Unique project identifier (defaults to directory name)
            force: Re-index even if files haven't changed
            generate_embeddings: Generate MLX embeddings for semantic search

        Returns:
            Stats dict with counts
        """
        project_path = Path(project_path)
        if not project_path.exists():
            return {"error": "Path not found", "indexed": 0}

        if project_id is None:
            project_id = project_path.name

        stats = {"files_scanned": 0, "symbols_indexed": 0, "skipped": 0, "embeddings": 0}

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
            try:
                mtime = file_path.stat().st_mtime
            except:
                continue

            cur.execute(
                "SELECT mtime FROM indexed_files WHERE file_path = ?",
                (str(file_path),)
            )
            row = cur.fetchone()

            if row and row[0] >= mtime and not force:
                continue

            # Parse and index
            parser = self._parsers[file_path.suffix]
            symbols = parser.parse(file_path, project_id)

            for symbol in symbols:
                # Generate embedding if requested
                embedding_blob = None
                if generate_embeddings and symbol.content:
                    embedding = _get_embedding(symbol.content)
                    if embedding is not None:
                        embedding_blob = embedding.tobytes()
                        stats["embeddings"] += 1

                cur.execute("""
                    INSERT OR REPLACE INTO code_symbols
                    (id, name, symbol_type, signature, docstring, file_path, line_number,
                     content, project_id, imports, embedding, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol.id, symbol.name, symbol.symbol_type, symbol.signature,
                    symbol.docstring, symbol.file_path, symbol.line_number,
                    symbol.content, symbol.project_id, symbol.imports,
                    embedding_blob, time.time()
                ))
                stats["symbols_indexed"] += 1

            # Update file tracking
            cur.execute("""
                INSERT OR REPLACE INTO indexed_files (file_path, project_id, mtime, indexed_at)
                VALUES (?, ?, ?, ?)
            """, (str(file_path), project_id, mtime, time.time()))

        conn.commit()
        conn.close()

        return stats

    def search(self, query: str, project_id: Optional[str] = None,
               symbol_type: Optional[str] = None,
               limit: int = 10) -> List[Tuple[CodeSymbol, float]]:
        """
        Search indexed code symbols using semantic similarity.

        Args:
            query: Search query
            project_id: Limit to specific project
            symbol_type: Limit to specific type (function, class, etc.)
            limit: Maximum results

        Returns:
            List of (CodeSymbol, similarity_score) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Try semantic search first
        query_embedding = _get_embedding(query)

        if query_embedding is not None:
            # Semantic search with embeddings
            sql = """
                SELECT id, name, symbol_type, signature, docstring, file_path,
                       line_number, content, project_id, imports, embedding
                FROM code_symbols
                WHERE embedding IS NOT NULL
            """
            params = []

            if project_id:
                sql += " AND project_id = ?"
                params.append(project_id)

            if symbol_type:
                sql += " AND symbol_type = ?"
                params.append(symbol_type)

            cur.execute(sql, params)

            results = []
            for row in cur.fetchall():
                if row[10]:  # embedding exists
                    stored_embedding = np.frombuffer(row[10], dtype=np.float32)
                    # Cosine similarity
                    similarity = float(np.dot(query_embedding, stored_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding) + 1e-8
                    ))

                    results.append((CodeSymbol(
                        id=row[0],
                        name=row[1],
                        symbol_type=row[2],
                        signature=row[3],
                        docstring=row[4],
                        file_path=row[5],
                        line_number=row[6],
                        content=row[7],
                        project_id=row[8],
                        imports=row[9]
                    ), similarity))

            # Sort by similarity
            results.sort(key=lambda x: -x[1])
            conn.close()
            return results[:limit]

        # Fallback to text search
        sql = """
            SELECT id, name, symbol_type, signature, docstring, file_path,
                   line_number, content, project_id, imports
            FROM code_symbols
            WHERE (name LIKE ? OR signature LIKE ? OR content LIKE ? OR docstring LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]

        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)

        if symbol_type:
            sql += " AND symbol_type = ?"
            params.append(symbol_type)

        sql += " LIMIT ?"
        params.append(limit)

        cur.execute(sql, params)

        results = []
        for row in cur.fetchall():
            results.append((CodeSymbol(
                id=row[0],
                name=row[1],
                symbol_type=row[2],
                signature=row[3],
                docstring=row[4],
                file_path=row[5],
                line_number=row[6],
                content=row[7],
                project_id=row[8],
                imports=row[9]
            ), 1.0))  # No similarity score for text search

        conn.close()
        return results

    def get_symbol_context(self, symbol_name: str, project_id: Optional[str] = None) -> Dict:
        """
        Get detailed context for a symbol including related symbols.

        Args:
            symbol_name: Name of the symbol to look up
            project_id: Limit to specific project

        Returns:
            Dict with symbol info and related context
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Find the symbol
        sql = """
            SELECT id, name, symbol_type, signature, docstring, file_path,
                   line_number, content, project_id, imports
            FROM code_symbols
            WHERE name = ?
        """
        params = [symbol_name]

        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)

        cur.execute(sql, params)
        row = cur.fetchone()

        if not row:
            conn.close()
            return {"error": f"Symbol '{symbol_name}' not found"}

        symbol = CodeSymbol(
            id=row[0],
            name=row[1],
            symbol_type=row[2],
            signature=row[3],
            docstring=row[4],
            file_path=row[5],
            line_number=row[6],
            content=row[7],
            project_id=row[8],
            imports=row[9]
        )

        # Find related symbols in the same file
        cur.execute("""
            SELECT name, symbol_type, signature, line_number
            FROM code_symbols
            WHERE file_path = ? AND id != ?
            ORDER BY line_number
        """, (symbol.file_path, symbol.id))

        related_in_file = [
            {"name": r[0], "type": r[1], "signature": r[2], "line": r[3]}
            for r in cur.fetchall()
        ]

        # Find symbols with similar names across the project
        cur.execute("""
            SELECT name, symbol_type, signature, file_path, line_number
            FROM code_symbols
            WHERE name LIKE ? AND id != ? AND project_id = ?
            LIMIT 10
        """, (f"%{symbol_name}%", symbol.id, symbol.project_id))

        similar_names = [
            {"name": r[0], "type": r[1], "signature": r[2], "file": r[3], "line": r[4]}
            for r in cur.fetchall()
        ]

        conn.close()

        return {
            "symbol": symbol.to_dict(),
            "file_path": symbol.file_path,
            "line_number": symbol.line_number,
            "related_in_file": related_in_file,
            "similar_symbols": similar_names,
            "imports": json.loads(symbol.imports) if symbol.imports else []
        }

    def get_stats(self, project_id: Optional[str] = None) -> Dict:
        """Get indexing statistics."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        base_query = "SELECT COUNT(*) FROM code_symbols"
        params = []

        if project_id:
            base_query += " WHERE project_id = ?"
            params = [project_id]

        cur.execute(base_query, params)
        total_symbols = cur.fetchone()[0]

        # Count by type
        type_query = "SELECT symbol_type, COUNT(*) FROM code_symbols"
        if project_id:
            type_query += " WHERE project_id = ?"
        type_query += " GROUP BY symbol_type"

        cur.execute(type_query, params)
        by_type = {row[0]: row[1] for row in cur.fetchall()}

        # Files indexed
        file_query = "SELECT COUNT(*) FROM indexed_files"
        if project_id:
            file_query += " WHERE project_id = ?"
        cur.execute(file_query, params)
        files_indexed = cur.fetchone()[0]

        # Count embeddings
        embed_query = "SELECT COUNT(*) FROM code_symbols WHERE embedding IS NOT NULL"
        if project_id:
            embed_query = embed_query.replace("WHERE", "WHERE project_id = ? AND")
        cur.execute(embed_query, params if project_id else [])
        with_embeddings = cur.fetchone()[0]

        # Projects
        cur.execute("SELECT DISTINCT project_id FROM code_symbols")
        projects = [row[0] for row in cur.fetchall()]

        conn.close()

        return {
            "total_symbols": total_symbols,
            "by_type": by_type,
            "files_indexed": files_indexed,
            "with_embeddings": with_embeddings,
            "projects": projects
        }

    def clear_project(self, project_id: str):
        """Remove all indexed data for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("DELETE FROM code_symbols WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM indexed_files WHERE project_id = ?", (project_id,))

        conn.commit()
        conn.close()

    def list_projects(self) -> List[Dict]:
        """List all indexed projects with stats."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT project_id, COUNT(*) as symbols,
                   COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded
            FROM code_symbols
            GROUP BY project_id
        """)

        projects = []
        for row in cur.fetchall():
            cur.execute(
                "SELECT COUNT(*) FROM indexed_files WHERE project_id = ?",
                (row[0],)
            )
            files = cur.fetchone()[0]

            projects.append({
                "project_id": row[0],
                "symbols": row[1],
                "embedded": row[2],
                "files": files
            })

        conn.close()
        return projects

    def get_file_mtime(self, file_path: str) -> Optional[float]:
        """Get the stored modification time for a file."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT mtime FROM indexed_files WHERE file_path = ?",
            (file_path,)
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def get_indexed_files(self, project_id: str) -> Dict[str, float]:
        """Get all indexed files and their modification times for a project."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT file_path, mtime FROM indexed_files WHERE project_id = ?",
            (project_id,)
        )
        files = {row[0]: row[1] for row in cur.fetchall()}
        conn.close()
        return files

    def remove_file(self, file_path: str):
        """Remove a file and its symbols from the index."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM code_symbols WHERE file_path = ?", (file_path,))
        cur.execute("DELETE FROM indexed_files WHERE file_path = ?", (file_path,))
        conn.commit()
        conn.close()

    def index_file(self, file_path: str, project_id: str,
                   generate_embeddings: bool = True) -> Dict[str, int]:
        """
        Index a single file.

        Args:
            file_path: Path to the file
            project_id: Project identifier
            generate_embeddings: Generate MLX embeddings

        Returns:
            Stats dict with counts
        """
        file_path = Path(file_path)
        stats = {"symbols_indexed": 0, "embeddings": 0}

        if not file_path.exists():
            return {"error": "File not found", **stats}

        if file_path.suffix not in self._parsers:
            return {"error": "Unsupported file type", **stats}

        try:
            mtime = file_path.stat().st_mtime
        except Exception as e:
            return {"error": str(e), **stats}

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Remove old symbols for this file first
        cur.execute("DELETE FROM code_symbols WHERE file_path = ?", (str(file_path),))

        # Parse and index
        parser = self._parsers[file_path.suffix]
        symbols = parser.parse(file_path, project_id)

        for symbol in symbols:
            embedding_blob = None
            if generate_embeddings and symbol.content:
                embedding = _get_embedding(symbol.content)
                if embedding is not None:
                    embedding_blob = embedding.tobytes()
                    stats["embeddings"] += 1

            cur.execute("""
                INSERT OR REPLACE INTO code_symbols
                (id, name, symbol_type, signature, docstring, file_path, line_number,
                 content, project_id, imports, embedding, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol.id, symbol.name, symbol.symbol_type, symbol.signature,
                symbol.docstring, symbol.file_path, symbol.line_number,
                symbol.content, symbol.project_id, symbol.imports,
                embedding_blob, time.time()
            ))
            stats["symbols_indexed"] += 1

        # Update file tracking
        cur.execute("""
            INSERT OR REPLACE INTO indexed_files (file_path, project_id, mtime, indexed_at)
            VALUES (?, ?, ?, ?)
        """, (str(file_path), project_id, mtime, time.time()))

        conn.commit()
        conn.close()

        return stats


# =============================================================================
# Index Watcher - Phase 2.2.7
# =============================================================================

@dataclass
class FileChange:
    """Represents a detected file change."""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    mtime: Optional[float]


class IndexWatcher:
    """
    Monitors project directories for file changes and triggers incremental updates.

    Uses polling (every 30 seconds by default) rather than filesystem events
    for simplicity and cross-platform compatibility.

    Usage:
        watcher = IndexWatcher(indexer)
        watcher.on_file_change(lambda change: print(f"Changed: {change.file_path}"))
        watcher.start("/path/to/project", "my_project")
        # ... later ...
        watcher.stop()
    """

    def __init__(self, indexer: Optional[CodeIndexer] = None,
                 poll_interval: float = 30.0,
                 auto_index: bool = True,
                 generate_embeddings: bool = True):
        """
        Initialize the index watcher.

        Args:
            indexer: CodeIndexer instance (uses singleton if not provided)
            poll_interval: Seconds between directory scans (default: 30)
            auto_index: Automatically update index on changes (default: True)
            generate_embeddings: Generate embeddings on auto-index (default: True)
        """
        self.indexer = indexer
        self.poll_interval = poll_interval
        self.auto_index = auto_index
        self.generate_embeddings = generate_embeddings

        self._project_path: Optional[Path] = None
        self._project_id: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[FileChange], None]] = []
        self._pending_updates: List[str] = []
        self._last_scan_time: float = 0
        self._stats = {
            "scans": 0,
            "changes_detected": 0,
            "files_indexed": 0,
            "errors": 0
        }

    def _get_indexer(self) -> CodeIndexer:
        """Get the indexer instance."""
        if self.indexer is None:
            self.indexer = get_indexer()
        return self.indexer

    def start(self, project_path: str, project_id: Optional[str] = None):
        """
        Start watching a project directory for changes.

        Args:
            project_path: Path to project root directory
            project_id: Unique project identifier (defaults to directory name)
        """
        with self._lock:
            if self._running:
                raise RuntimeError("Watcher is already running. Call stop() first.")

            self._project_path = Path(project_path)
            if not self._project_path.exists():
                raise ValueError(f"Project path does not exist: {project_path}")

            self._project_id = project_id or self._project_path.name
            self._running = True
            self._pending_updates = []

            self._thread = threading.Thread(
                target=self._watch_loop,
                name=f"IndexWatcher-{self._project_id}",
                daemon=True
            )
            self._thread.start()

    def stop(self):
        """Stop watching for changes."""
        with self._lock:
            self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            self._thread = None

    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running

    def on_file_change(self, callback: Callable[[FileChange], None]):
        """
        Register a callback to be called when a file change is detected.

        Args:
            callback: Function that takes a FileChange object
        """
        self._callbacks.append(callback)

    def get_pending_updates(self) -> List[str]:
        """
        Get list of files with pending updates.

        Returns:
            List of file paths that have changed but not yet been indexed
        """
        with self._lock:
            return list(self._pending_updates)

    def get_stats(self) -> Dict:
        """Get watcher statistics."""
        return {
            **self._stats,
            "running": self._running,
            "project_path": str(self._project_path) if self._project_path else None,
            "project_id": self._project_id,
            "poll_interval": self.poll_interval,
            "pending_updates": len(self._pending_updates),
            "last_scan": self._last_scan_time
        }

    def force_scan(self) -> List[FileChange]:
        """
        Force an immediate scan for changes.

        Returns:
            List of detected changes
        """
        if not self._project_path or not self._project_id:
            return []

        return self._scan_for_changes()

    def _watch_loop(self):
        """Main watching loop - runs in background thread."""
        while self._running:
            try:
                changes = self._scan_for_changes()

                if changes:
                    self._stats["changes_detected"] += len(changes)

                    # Notify callbacks
                    for change in changes:
                        for callback in self._callbacks:
                            try:
                                callback(change)
                            except Exception as e:
                                print(f"IndexWatcher callback error: {e}")

                    # Auto-index if enabled
                    if self.auto_index:
                        self._process_changes(changes)

            except Exception as e:
                self._stats["errors"] += 1
                print(f"IndexWatcher error: {e}")

            # Sleep in small increments to allow faster shutdown
            sleep_time = self.poll_interval
            while sleep_time > 0 and self._running:
                time.sleep(min(1.0, sleep_time))
                sleep_time -= 1.0

    def _scan_for_changes(self) -> List[FileChange]:
        """
        Scan project directory for file changes.

        Returns:
            List of detected file changes
        """
        if not self._project_path or not self._project_id:
            return []

        self._stats["scans"] += 1
        self._last_scan_time = time.time()

        indexer = self._get_indexer()
        changes: List[FileChange] = []

        # Get currently indexed files
        indexed_files = indexer.get_indexed_files(self._project_id)
        current_files: Set[str] = set()

        # Scan project directory
        for file_path in self._project_path.rglob('*'):
            if not file_path.is_file():
                continue

            # Skip excluded directories
            if any(skip in file_path.parts for skip in CodeIndexer.SKIP_DIRS):
                continue

            # Skip unsupported file types
            if file_path.suffix not in CodeIndexer.EXTENSION_PARSERS:
                continue

            file_str = str(file_path)
            current_files.add(file_str)

            try:
                mtime = file_path.stat().st_mtime
            except Exception:
                continue

            # Check if file is new or modified
            if file_str not in indexed_files:
                changes.append(FileChange(
                    file_path=file_str,
                    change_type='added',
                    mtime=mtime
                ))
            elif indexed_files[file_str] < mtime:
                changes.append(FileChange(
                    file_path=file_str,
                    change_type='modified',
                    mtime=mtime
                ))

        # Check for deleted files
        for indexed_file in indexed_files:
            if indexed_file not in current_files:
                changes.append(FileChange(
                    file_path=indexed_file,
                    change_type='deleted',
                    mtime=None
                ))

        return changes

    def _process_changes(self, changes: List[FileChange]):
        """
        Process detected changes by updating the index.

        Args:
            changes: List of file changes to process
        """
        indexer = self._get_indexer()

        for change in changes:
            try:
                if change.change_type == 'deleted':
                    indexer.remove_file(change.file_path)
                    with self._lock:
                        if change.file_path in self._pending_updates:
                            self._pending_updates.remove(change.file_path)
                else:
                    # Added or modified
                    stats = indexer.index_file(
                        change.file_path,
                        self._project_id,
                        generate_embeddings=self.generate_embeddings
                    )
                    if "error" not in stats:
                        self._stats["files_indexed"] += 1
                        with self._lock:
                            if change.file_path in self._pending_updates:
                                self._pending_updates.remove(change.file_path)
                    else:
                        # Mark as pending if indexing failed
                        with self._lock:
                            if change.file_path not in self._pending_updates:
                                self._pending_updates.append(change.file_path)

            except Exception as e:
                self._stats["errors"] += 1
                print(f"IndexWatcher: Error processing {change.file_path}: {e}")
                with self._lock:
                    if change.file_path not in self._pending_updates:
                        self._pending_updates.append(change.file_path)


# =============================================================================
# Singleton and Convenience Functions
# =============================================================================

_indexer = None
_watcher = None


def get_indexer() -> CodeIndexer:
    """Get singleton code indexer."""
    global _indexer
    if _indexer is None:
        _indexer = CodeIndexer()
    return _indexer


def get_watcher() -> IndexWatcher:
    """Get singleton index watcher."""
    global _watcher
    if _watcher is None:
        _watcher = IndexWatcher()
    return _watcher


def index_project(project_path: str, project_id: Optional[str] = None) -> Dict:
    """Index a project."""
    return get_indexer().index_project(project_path, project_id)


def search(query: str, limit: int = 10) -> List[Tuple[CodeSymbol, float]]:
    """Search for symbols."""
    return get_indexer().search(query, limit=limit)


def smart_search(query: str, project_id: Optional[str] = None,
                 symbol_type: Optional[str] = None, limit: int = 10) -> List[Tuple[CodeSymbol, float]]:
    """
    Search with automatic query decomposition for complex queries.

    This intelligently detects multi-part queries and decomposes them
    into sub-searches, combining and deduplicating results.

    Examples:
        "memory system and storage location"
        -> searches for memory system AND storage location separately

        "Python auth, logging, database"
        -> searches for each topic and combines results

    Args:
        query: Search query (can be simple or complex)
        project_id: Limit to specific project
        symbol_type: Limit to specific symbol type
        limit: Maximum results to return

    Returns:
        List of (CodeSymbol, score) tuples
    """
    try:
        from query_decomposer import search_with_decomposition
        return search_with_decomposition(
            query, get_indexer(), project_id, symbol_type, limit
        )
    except ImportError:
        # Fallback to regular search if decomposer not available
        return get_indexer().search(query, project_id, symbol_type, limit)


def get_symbol_context(symbol_name: str) -> Dict:
    """Get context for a symbol."""
    return get_indexer().get_symbol_context(symbol_name)


def start_watching(project_path: str, project_id: Optional[str] = None,
                   poll_interval: float = 30.0) -> IndexWatcher:
    """
    Start watching a project for changes.

    Args:
        project_path: Path to project root
        project_id: Unique project identifier
        poll_interval: Seconds between scans

    Returns:
        The IndexWatcher instance
    """
    watcher = get_watcher()
    if watcher.is_running():
        watcher.stop()
    watcher.poll_interval = poll_interval
    watcher.start(project_path, project_id)
    return watcher


def stop_watching():
    """Stop watching for changes."""
    watcher = get_watcher()
    if watcher.is_running():
        watcher.stop()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    import os
    import signal

    parser = argparse.ArgumentParser(description="SAM Code Indexer - Phase 2.2.7")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index a project")
    index_parser.add_argument("path", nargs="?", default=".", help="Project path")
    index_parser.add_argument("--project", "-p", help="Project ID (default: directory name)")
    index_parser.add_argument("--force", "-f", action="store_true", help="Force re-index")
    index_parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding generation")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch project for changes")
    watch_parser.add_argument("path", nargs="?", default=".", help="Project path")
    watch_parser.add_argument("--project", "-p", help="Project ID (default: directory name)")
    watch_parser.add_argument("--interval", "-i", type=float, default=30.0,
                              help="Poll interval in seconds (default: 30)")
    watch_parser.add_argument("--no-auto-index", action="store_true",
                              help="Don't auto-index on changes (just report)")
    watch_parser.add_argument("--no-embeddings", action="store_true",
                              help="Skip embedding generation on auto-index")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search symbols")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--project", "-p", help="Limit to project")
    search_parser.add_argument("--type", "-t", choices=[
        "function", "class", "method", "module", "struct", "enum",
        "trait", "protocol", "interface", "type"
    ])
    search_parser.add_argument("--limit", "-l", type=int, default=10)
    search_parser.add_argument("--smart", "-s", action="store_true",
                               help="Use smart query decomposition for complex queries")

    # Context command
    context_parser = subparsers.add_parser("context", help="Get symbol context")
    context_parser.add_argument("symbol", help="Symbol name")
    context_parser.add_argument("--project", "-p", help="Limit to project")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--project", "-p", help="Limit to project")

    # List command
    subparsers.add_parser("list", help="List indexed projects")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear project index")
    clear_parser.add_argument("project", help="Project ID to clear")

    args = parser.parse_args()
    indexer = get_indexer()

    if args.command == "index":
        path = os.path.abspath(args.path)
        project_id = args.project or os.path.basename(path)
        print(f"Indexing {path} as '{project_id}'...")

        stats = indexer.index_project(
            path, project_id,
            force=args.force,
            generate_embeddings=not args.no_embeddings
        )

        print(f"\nIndexing complete:")
        print(f"  Files scanned: {stats['files_scanned']}")
        print(f"  Symbols indexed: {stats['symbols_indexed']}")
        print(f"  Embeddings generated: {stats.get('embeddings', 0)}")
        print(f"  Skipped: {stats['skipped']}")

    elif args.command == "watch":
        path = os.path.abspath(args.path)
        project_id = args.project or os.path.basename(path)

        # Create watcher with settings
        watcher = IndexWatcher(
            indexer=indexer,
            poll_interval=args.interval,
            auto_index=not args.no_auto_index,
            generate_embeddings=not args.no_embeddings
        )

        # Register callback to print changes
        def on_change(change: FileChange):
            timestamp = datetime.now().strftime("%H:%M:%S")
            action = "indexed" if watcher.auto_index else "detected"
            print(f"[{timestamp}] {change.change_type.upper()}: {change.file_path} ({action})")

        watcher.on_file_change(on_change)

        # Handle Ctrl+C gracefully
        stop_event = threading.Event()

        def signal_handler(sig, frame):
            print("\n\nStopping watcher...")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)

        print(f"Watching {path} as '{project_id}'")
        print(f"  Poll interval: {args.interval}s")
        print(f"  Auto-index: {'yes' if not args.no_auto_index else 'no'}")
        print(f"  Embeddings: {'yes' if not args.no_embeddings else 'no'}")
        print("\nPress Ctrl+C to stop.\n")

        # Do initial index if needed
        initial_stats = indexer.get_stats(project_id)
        if initial_stats['total_symbols'] == 0:
            print("No existing index found. Running initial indexing...")
            init_stats = indexer.index_project(
                path, project_id,
                generate_embeddings=not args.no_embeddings
            )
            print(f"  Initial index: {init_stats['symbols_indexed']} symbols from {init_stats['files_scanned']} files\n")

        # Start watching
        watcher.start(path, project_id)

        # Wait until interrupted
        while not stop_event.is_set():
            stop_event.wait(1.0)

        watcher.stop()

        # Print final stats
        stats = watcher.get_stats()
        print(f"\nWatcher stats:")
        print(f"  Scans: {stats['scans']}")
        print(f"  Changes detected: {stats['changes_detected']}")
        print(f"  Files indexed: {stats['files_indexed']}")
        print(f"  Errors: {stats['errors']}")

    elif args.command == "search":
        if args.smart:
            # Use smart search with query decomposition
            results = smart_search(
                args.query,
                project_id=args.project,
                symbol_type=args.type,
                limit=args.limit
            )
            # Show decomposition info if query was complex
            try:
                from query_decomposer import get_decomposer
                decomposer = get_decomposer()
                if decomposer.is_complex_query(args.query):
                    decomposed = decomposer.decompose(args.query)
                    if len(decomposed.sub_queries) > 1:
                        print(f"Query decomposed into {len(decomposed.sub_queries)} sub-queries:")
                        for sq in decomposed.sub_queries:
                            print(f"  - {sq}")
                        print()
            except ImportError:
                pass
        else:
            results = indexer.search(
                args.query,
                project_id=args.project,
                symbol_type=args.type,
                limit=args.limit
            )

        print(f"Found {len(results)} results for '{args.query}':\n")
        for symbol, score in results:
            print(f"  [{symbol.symbol_type}] {symbol.name} (score: {score:.3f})")
            print(f"      {symbol.signature}")
            print(f"      @ {symbol.file_path}:{symbol.line_number}")
            if symbol.docstring:
                print(f"      {symbol.docstring[:80]}...")
            print()

    elif args.command == "context":
        context = indexer.get_symbol_context(args.symbol, args.project)

        if "error" in context:
            print(context["error"])
        else:
            print(f"Symbol: {context['symbol']['name']}")
            print(f"Type: {context['symbol']['symbol_type']}")
            print(f"Signature: {context['symbol']['signature']}")
            print(f"File: {context['file_path']}:{context['line_number']}")

            if context['symbol'].get('docstring'):
                print(f"\nDocstring:\n{context['symbol']['docstring'][:500]}")

            if context.get('imports'):
                print(f"\nImports: {', '.join(context['imports'][:10])}")

            if context.get('related_in_file'):
                print(f"\nRelated symbols in file:")
                for r in context['related_in_file'][:10]:
                    print(f"  [{r['type']}] {r['name']} @ line {r['line']}")

            if context.get('similar_symbols'):
                print(f"\nSimilar symbols in project:")
                for s in context['similar_symbols'][:5]:
                    print(f"  [{s['type']}] {s['name']} @ {s['file']}")

    elif args.command == "stats":
        stats = indexer.get_stats(args.project)
        print(json.dumps(stats, indent=2))

    elif args.command == "list":
        projects = indexer.list_projects()
        print(f"Indexed projects ({len(projects)}):\n")
        for p in projects:
            print(f"  {p['project_id']}")
            print(f"      Symbols: {p['symbols']} ({p['embedded']} with embeddings)")
            print(f"      Files: {p['files']}")

    elif args.command == "clear":
        indexer.clear_project(args.project)
        print(f"Cleared index for project: {args.project}")

    else:
        parser.print_help()
