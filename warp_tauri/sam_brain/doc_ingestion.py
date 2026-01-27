#!/usr/bin/env python3
"""
SAM Documentation Ingestion - Phase 5.1.6

Ingests documentation and converts to training data:
- Markdown files: Split into Q&A pairs, extract code examples
- Docstrings: Extract with function signatures (Python, JS, Rust)
- README files: Parse sections into instruction/response pairs
- Code examples: Pair with explanations

Supports:
- Markdown (.md)
- reStructuredText (.rst)
- Python docstrings
- JSDoc comments
- Rust doc comments

Storage: /Volumes/David External/sam_training/documentation/
"""

import os
import re
import ast
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass, field, asdict
from enum import Enum


# =============================================================================
# Configuration
# =============================================================================

# Storage on external drive per project rules
DOC_DB = Path("/Volumes/David External/sam_training/documentation/docs.db")
DOC_JSONL = Path("/Volumes/David External/sam_training/documentation/training_examples.jsonl")

# Fallback to local if external not available
LOCAL_FALLBACK = Path.home() / ".sam" / "training_data" / "documentation"


class DocType(Enum):
    """Types of documentation"""
    MARKDOWN = "markdown"
    RST = "restructuredtext"
    PYTHON_DOCSTRING = "python_docstring"
    JSDOC = "jsdoc"
    RUSTDOC = "rustdoc"
    README = "readme"
    API_DOC = "api_doc"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"


class ExtractionType(Enum):
    """Types of extracted content"""
    QA_PAIR = "qa_pair"
    CODE_EXAMPLE = "code_example"
    FUNCTION_DOC = "function_doc"
    CLASS_DOC = "class_doc"
    SECTION = "section"
    DEFINITION = "definition"
    CONCEPT = "concept"


@dataclass
class DocFragment:
    """An extracted documentation fragment"""
    id: str
    doc_type: DocType
    extraction_type: ExtractionType

    # Source info
    source_path: str
    source_name: str
    project: Optional[str]

    # Content
    title: str
    content: str
    code_example: Optional[str]
    language: Optional[str]

    # Training format
    instruction: str
    input_text: str
    output_text: str

    # Metadata
    section_path: List[str]  # Hierarchical path like ["Installation", "Dependencies"]
    quality_score: float
    extracted_at: str

    def to_training_example(self) -> Dict:
        """Convert to JSONL training format"""
        return {
            "instruction": self.instruction,
            "input": self.input_text,
            "output": self.output_text,
            "metadata": {
                "doc_type": self.doc_type.value,
                "extraction_type": self.extraction_type.value,
                "source": self.source_name,
                "quality": self.quality_score,
            }
        }


# =============================================================================
# Markdown Parser
# =============================================================================

class MarkdownParser:
    """Parse Markdown files and extract training data"""

    # Patterns
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)
    INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')
    LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    LIST_PATTERN = re.compile(r'^[\-\*]\s+(.+)$', re.MULTILINE)
    NUMBERED_LIST_PATTERN = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)

    def parse(self, content: str, source_path: str,
              project: Optional[str] = None) -> List[DocFragment]:
        """Parse markdown content and extract fragments"""
        fragments = []
        source_name = Path(source_path).name

        # Split into sections by headings
        sections = self._split_into_sections(content)

        for section in sections:
            # Extract Q&A pairs from sections
            qa_fragments = self._extract_qa_pairs(section, source_path, source_name, project)
            fragments.extend(qa_fragments)

            # Extract code examples with explanations
            code_fragments = self._extract_code_examples(section, source_path, source_name, project)
            fragments.extend(code_fragments)

            # Extract concept definitions
            concept_fragments = self._extract_concepts(section, source_path, source_name, project)
            fragments.extend(concept_fragments)

        return fragments

    def _split_into_sections(self, content: str) -> List[Dict]:
        """Split content into sections by headings"""
        sections = []
        current_section = {"level": 0, "title": "Introduction", "content": "", "path": []}

        lines = content.split('\n')
        heading_stack = []

        for line in lines:
            match = self.HEADING_PATTERN.match(line)
            if match:
                # Save current section
                if current_section["content"].strip():
                    sections.append(current_section.copy())

                level = len(match.group(1))
                title = match.group(2).strip()

                # Update heading stack
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))

                current_section = {
                    "level": level,
                    "title": title,
                    "content": "",
                    "path": [h[1] for h in heading_stack]
                }
            else:
                current_section["content"] += line + "\n"

        # Save last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _extract_qa_pairs(self, section: Dict, source_path: str,
                          source_name: str, project: Optional[str]) -> List[DocFragment]:
        """Extract Q&A pairs from a section"""
        fragments = []
        content = section["content"]
        title = section["title"]

        # Skip very short sections
        if len(content) < 50:
            return fragments

        # Generate Q&A based on section title and content
        # The title often implies the question

        # Common patterns that suggest Q&A
        qa_patterns = [
            (r'how\s+to', "How do I"),
            (r'getting\s+started', "How do I get started with"),
            (r'installation', "How do I install"),
            (r'configuration', "How do I configure"),
            (r'usage', "How do I use"),
            (r'example', "Can you show me an example of"),
            (r'troubleshooting', "How do I fix"),
            (r'faq', ""),
            (r'what\s+is', "What is"),
            (r'why', "Why"),
            (r'when', "When should I"),
        ]

        question = None
        for pattern, prefix in qa_patterns:
            if re.search(pattern, title.lower()):
                if prefix:
                    question = f"{prefix} {title.lower().strip('?')}?"
                else:
                    question = title + "?"
                break

        if not question:
            # Generate a generic question
            question = f"Explain the '{title}' section"

        # Clean up the answer
        answer = self._clean_content_for_answer(content)

        if len(answer) > 50:
            fragment_id = hashlib.md5(
                f"{source_path}:{title}:qa".encode()
            ).hexdigest()[:16]

            fragments.append(DocFragment(
                id=fragment_id,
                doc_type=DocType.MARKDOWN,
                extraction_type=ExtractionType.QA_PAIR,
                source_path=source_path,
                source_name=source_name,
                project=project,
                title=title,
                content=content[:2000],
                code_example=None,
                language=None,
                instruction=question,
                input_text="",
                output_text=answer[:3000],
                section_path=section.get("path", []),
                quality_score=self._calculate_quality(question, answer),
                extracted_at=datetime.now().isoformat()
            ))

        return fragments

    def _extract_code_examples(self, section: Dict, source_path: str,
                               source_name: str, project: Optional[str]) -> List[DocFragment]:
        """Extract code examples with their explanations"""
        fragments = []
        content = section["content"]
        title = section["title"]

        # Find all code blocks
        matches = list(self.CODE_BLOCK_PATTERN.finditer(content))

        for i, match in enumerate(matches):
            language = match.group(1) or "text"
            code = match.group(2).strip()

            if len(code) < 10:
                continue

            # Get context around the code block (explanation)
            start_pos = match.start()
            end_pos = match.end()

            # Text before code block is usually the explanation
            text_before = content[:start_pos].strip()
            # Get last paragraph before code
            paragraphs = text_before.split('\n\n')
            explanation = paragraphs[-1].strip() if paragraphs else ""

            # Text after might have more explanation
            text_after = content[end_pos:end_pos+500].strip()
            after_paragraph = text_after.split('\n\n')[0] if text_after else ""

            # Build the instruction
            if explanation:
                instruction = f"Show me code that: {explanation[:200]}"
            else:
                instruction = f"Show me an example of {title}"

            # Build the output
            output = f"Here's an example:\n\n```{language}\n{code}\n```"
            if after_paragraph and len(after_paragraph) > 20:
                output += f"\n\n{after_paragraph}"

            fragment_id = hashlib.md5(
                f"{source_path}:{title}:code:{i}".encode()
            ).hexdigest()[:16]

            fragments.append(DocFragment(
                id=fragment_id,
                doc_type=DocType.MARKDOWN,
                extraction_type=ExtractionType.CODE_EXAMPLE,
                source_path=source_path,
                source_name=source_name,
                project=project,
                title=f"{title} - Example {i+1}",
                content=explanation[:500],
                code_example=code,
                language=language,
                instruction=instruction,
                input_text="",
                output_text=output[:3000],
                section_path=section.get("path", []),
                quality_score=self._calculate_code_quality(code, explanation),
                extracted_at=datetime.now().isoformat()
            ))

        return fragments

    def _extract_concepts(self, section: Dict, source_path: str,
                          source_name: str, project: Optional[str]) -> List[DocFragment]:
        """Extract concept definitions"""
        fragments = []
        content = section["content"]
        title = section["title"]

        # Look for definition patterns
        # "X is Y", "X: Y", "X - Y"
        definition_patterns = [
            r'^\*\*([^*]+)\*\*\s*[-:]\s*(.+)$',  # **Term**: definition
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+(.+)$',  # Term is definition
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*(.+)$',  # Term: definition
        ]

        for pattern in definition_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                term = match.group(1).strip()
                definition = match.group(2).strip()

                if len(definition) < 20 or len(term) < 2:
                    continue

                fragment_id = hashlib.md5(
                    f"{source_path}:{term}:concept".encode()
                ).hexdigest()[:16]

                fragments.append(DocFragment(
                    id=fragment_id,
                    doc_type=DocType.MARKDOWN,
                    extraction_type=ExtractionType.CONCEPT,
                    source_path=source_path,
                    source_name=source_name,
                    project=project,
                    title=term,
                    content=definition[:1000],
                    code_example=None,
                    language=None,
                    instruction=f"What is {term}?",
                    input_text="",
                    output_text=f"{term} is {definition}",
                    section_path=section.get("path", []),
                    quality_score=0.6,
                    extracted_at=datetime.now().isoformat()
                ))

        return fragments

    def _clean_content_for_answer(self, content: str) -> str:
        """Clean markdown content for use as an answer"""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        # Keep code blocks intact
        # Remove link URLs but keep text
        content = self.LINK_PATTERN.sub(r'\1', content)
        return content.strip()

    def _calculate_quality(self, question: str, answer: str) -> float:
        """Calculate quality score for a Q&A pair"""
        score = 0.5

        # Longer answers are generally better
        if len(answer) > 200:
            score += 0.1
        if len(answer) > 500:
            score += 0.1

        # Question should be clear
        if '?' in question:
            score += 0.05

        # Answer should have some structure
        if '\n' in answer:
            score += 0.05

        # Code examples in answer are valuable
        if '```' in answer or '`' in answer:
            score += 0.1

        return min(1.0, score)

    def _calculate_code_quality(self, code: str, explanation: str) -> float:
        """Calculate quality score for a code example"""
        score = 0.5

        # Code length
        lines = code.split('\n')
        if 3 <= len(lines) <= 30:
            score += 0.15
        elif len(lines) > 30:
            score += 0.05

        # Has explanation
        if len(explanation) > 50:
            score += 0.15

        # Code has comments
        if '#' in code or '//' in code or '/*' in code:
            score += 0.1

        # Not just imports
        if not all(line.strip().startswith(('import', 'from', 'use', 'require'))
                   for line in lines if line.strip()):
            score += 0.1

        return min(1.0, score)


# =============================================================================
# Python Docstring Parser
# =============================================================================

class PythonDocstringParser:
    """Extract docstrings from Python files"""

    def parse(self, content: str, source_path: str,
              project: Optional[str] = None) -> List[DocFragment]:
        """Parse Python file and extract docstrings"""
        fragments = []
        source_name = Path(source_path).name

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return fragments

        # Module docstring
        if ast.get_docstring(tree):
            doc = ast.get_docstring(tree)
            fragments.append(self._create_module_fragment(
                doc, source_path, source_name, project
            ))

        # Walk the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                doc = ast.get_docstring(node)
                if doc:
                    frag = self._create_function_fragment(
                        node, doc, content, source_path, source_name, project
                    )
                    if frag:
                        fragments.append(frag)

            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                if doc:
                    frag = self._create_class_fragment(
                        node, doc, content, source_path, source_name, project
                    )
                    if frag:
                        fragments.append(frag)

        return fragments

    def _create_module_fragment(self, docstring: str, source_path: str,
                                source_name: str, project: Optional[str]) -> DocFragment:
        """Create fragment from module docstring"""
        fragment_id = hashlib.md5(
            f"{source_path}:module".encode()
        ).hexdigest()[:16]

        module_name = Path(source_path).stem

        return DocFragment(
            id=fragment_id,
            doc_type=DocType.PYTHON_DOCSTRING,
            extraction_type=ExtractionType.SECTION,
            source_path=source_path,
            source_name=source_name,
            project=project,
            title=f"Module: {module_name}",
            content=docstring,
            code_example=None,
            language="python",
            instruction=f"What does the {module_name} module do?",
            input_text="",
            output_text=docstring[:2000],
            section_path=[module_name],
            quality_score=0.7 if len(docstring) > 100 else 0.5,
            extracted_at=datetime.now().isoformat()
        )

    def _create_function_fragment(self, node: ast.FunctionDef, docstring: str,
                                  source_content: str, source_path: str,
                                  source_name: str, project: Optional[str]) -> Optional[DocFragment]:
        """Create fragment from function docstring"""
        func_name = node.name

        # Skip private/magic methods
        if func_name.startswith('_') and not func_name.startswith('__init__'):
            return None

        # Get function signature
        try:
            args = []
            for arg in node.args.args:
                arg_str = arg.arg
                if arg.annotation:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                args.append(arg_str)

            signature = f"def {func_name}({', '.join(args)})"
            if node.returns:
                signature += f" -> {ast.unparse(node.returns)}"
        except:
            signature = f"def {func_name}(...)"

        fragment_id = hashlib.md5(
            f"{source_path}:{func_name}".encode()
        ).hexdigest()[:16]

        instruction = f"How do I use the {func_name} function?"
        output = f"```python\n{signature}\n```\n\n{docstring}"

        return DocFragment(
            id=fragment_id,
            doc_type=DocType.PYTHON_DOCSTRING,
            extraction_type=ExtractionType.FUNCTION_DOC,
            source_path=source_path,
            source_name=source_name,
            project=project,
            title=func_name,
            content=docstring,
            code_example=signature,
            language="python",
            instruction=instruction,
            input_text="",
            output_text=output[:3000],
            section_path=[source_name, func_name],
            quality_score=self._calculate_docstring_quality(docstring),
            extracted_at=datetime.now().isoformat()
        )

    def _create_class_fragment(self, node: ast.ClassDef, docstring: str,
                               source_content: str, source_path: str,
                               source_name: str, project: Optional[str]) -> Optional[DocFragment]:
        """Create fragment from class docstring"""
        class_name = node.name

        # Get methods
        methods = [n.name for n in node.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and not n.name.startswith('_')]

        fragment_id = hashlib.md5(
            f"{source_path}:{class_name}:class".encode()
        ).hexdigest()[:16]

        instruction = f"What is the {class_name} class and how do I use it?"

        output = f"The `{class_name}` class:\n\n{docstring}"
        if methods:
            output += f"\n\nMethods: {', '.join(methods[:10])}"

        return DocFragment(
            id=fragment_id,
            doc_type=DocType.PYTHON_DOCSTRING,
            extraction_type=ExtractionType.CLASS_DOC,
            source_path=source_path,
            source_name=source_name,
            project=project,
            title=class_name,
            content=docstring,
            code_example=f"class {class_name}",
            language="python",
            instruction=instruction,
            input_text="",
            output_text=output[:3000],
            section_path=[source_name, class_name],
            quality_score=self._calculate_docstring_quality(docstring),
            extracted_at=datetime.now().isoformat()
        )

    def _calculate_docstring_quality(self, docstring: str) -> float:
        """Calculate quality score for a docstring"""
        score = 0.5

        # Length
        if len(docstring) > 50:
            score += 0.1
        if len(docstring) > 200:
            score += 0.1

        # Has structure (Args, Returns, etc.)
        if 'Args:' in docstring or 'Parameters:' in docstring:
            score += 0.1
        if 'Returns:' in docstring or 'Return:' in docstring:
            score += 0.1
        if 'Example' in docstring or '>>>' in docstring:
            score += 0.1

        return min(1.0, score)


# =============================================================================
# JSDoc Parser
# =============================================================================

class JSDocParser:
    """Extract JSDoc comments from JavaScript/TypeScript files"""

    JSDOC_PATTERN = re.compile(
        r'/\*\*\s*(.*?)\s*\*/\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)|class\s+(\w+))',
        re.DOTALL
    )

    JSDOC_TAG_PATTERN = re.compile(r'@(\w+)\s+(.+?)(?=@\w+|$)', re.DOTALL)

    def parse(self, content: str, source_path: str,
              project: Optional[str] = None) -> List[DocFragment]:
        """Parse JS/TS file and extract JSDoc comments"""
        fragments = []
        source_name = Path(source_path).name

        for match in self.JSDOC_PATTERN.finditer(content):
            doc_content = match.group(1)
            func_name = match.group(2) or match.group(3) or match.group(4)

            if not func_name or len(doc_content) < 20:
                continue

            # Clean up the doc content
            doc_content = re.sub(r'\n\s*\*\s*', '\n', doc_content).strip()

            # Parse tags
            tags = dict(self.JSDOC_TAG_PATTERN.findall(doc_content))

            # Get description (text before first tag)
            description = re.split(r'@\w+', doc_content)[0].strip()

            fragment_id = hashlib.md5(
                f"{source_path}:{func_name}:jsdoc".encode()
            ).hexdigest()[:16]

            instruction = f"How do I use the {func_name} function?"

            output = f"The `{func_name}` function: {description}"
            if 'param' in tags:
                output += f"\n\nParameters:\n{tags['param']}"
            if 'returns' in tags or 'return' in tags:
                ret = tags.get('returns', tags.get('return', ''))
                output += f"\n\nReturns: {ret}"
            if 'example' in tags:
                output += f"\n\nExample:\n```javascript\n{tags['example']}\n```"

            fragments.append(DocFragment(
                id=fragment_id,
                doc_type=DocType.JSDOC,
                extraction_type=ExtractionType.FUNCTION_DOC,
                source_path=source_path,
                source_name=source_name,
                project=project,
                title=func_name,
                content=doc_content,
                code_example=tags.get('example'),
                language="javascript",
                instruction=instruction,
                input_text="",
                output_text=output[:3000],
                section_path=[source_name, func_name],
                quality_score=0.6 if len(description) > 50 else 0.4,
                extracted_at=datetime.now().isoformat()
            ))

        return fragments


# =============================================================================
# Rust Doc Parser
# =============================================================================

class RustDocParser:
    """Extract Rust doc comments"""

    DOC_COMMENT_PATTERN = re.compile(
        r'((?://!\s*.*\n)+|(?:///\s*.*\n)+)\s*(?:pub(?:\([^)]*\))?\s+)?(?:fn|struct|enum|trait|impl|type)\s+(\w+)',
        re.MULTILINE
    )

    def parse(self, content: str, source_path: str,
              project: Optional[str] = None) -> List[DocFragment]:
        """Parse Rust file and extract doc comments"""
        fragments = []
        source_name = Path(source_path).name

        for match in self.DOC_COMMENT_PATTERN.finditer(content):
            doc_lines = match.group(1)
            item_name = match.group(2)

            # Clean up doc lines
            lines = []
            for line in doc_lines.split('\n'):
                line = line.strip()
                if line.startswith('///'):
                    lines.append(line[3:].strip())
                elif line.startswith('//!'):
                    lines.append(line[3:].strip())

            doc_content = '\n'.join(lines)

            if len(doc_content) < 20:
                continue

            fragment_id = hashlib.md5(
                f"{source_path}:{item_name}:rustdoc".encode()
            ).hexdigest()[:16]

            # Determine if it's a function, struct, etc.
            item_type = "item"
            if 'fn ' in match.group(0):
                item_type = "function"
            elif 'struct ' in match.group(0):
                item_type = "struct"
            elif 'enum ' in match.group(0):
                item_type = "enum"
            elif 'trait ' in match.group(0):
                item_type = "trait"

            instruction = f"What is the {item_name} {item_type} in Rust?"

            fragments.append(DocFragment(
                id=fragment_id,
                doc_type=DocType.RUSTDOC,
                extraction_type=ExtractionType.FUNCTION_DOC if item_type == "function" else ExtractionType.CLASS_DOC,
                source_path=source_path,
                source_name=source_name,
                project=project,
                title=item_name,
                content=doc_content,
                code_example=None,
                language="rust",
                instruction=instruction,
                input_text="",
                output_text=f"The `{item_name}` {item_type}: {doc_content}",
                section_path=[source_name, item_name],
                quality_score=0.6 if len(doc_content) > 100 else 0.4,
                extracted_at=datetime.now().isoformat()
            ))

        return fragments


# =============================================================================
# README Parser
# =============================================================================

class ReadmeParser:
    """Special parsing for README files"""

    def __init__(self):
        self.md_parser = MarkdownParser()

    def parse(self, content: str, source_path: str,
              project: Optional[str] = None) -> List[DocFragment]:
        """Parse README with project context"""
        fragments = []

        # Try to extract project name from path
        if not project:
            project = Path(source_path).parent.name

        # Use markdown parser for base extraction
        md_fragments = self.md_parser.parse(content, source_path, project)

        # Enhance with README-specific extraction
        for frag in md_fragments:
            # Update project context
            frag.project = project

            # Enhance instructions for common sections
            title_lower = frag.title.lower()

            if 'install' in title_lower:
                frag.instruction = f"How do I install {project}?"
            elif 'usage' in title_lower or 'getting started' in title_lower:
                frag.instruction = f"How do I use {project}?"
            elif 'api' in title_lower:
                frag.instruction = f"What is the API for {project}?"
            elif 'config' in title_lower:
                frag.instruction = f"How do I configure {project}?"
            elif 'feature' in title_lower:
                frag.instruction = f"What are the features of {project}?"
            elif 'require' in title_lower or 'depend' in title_lower:
                frag.instruction = f"What are the requirements for {project}?"
            elif 'contribut' in title_lower:
                frag.instruction = f"How do I contribute to {project}?"

            fragments.append(frag)

        # Add a "What is X" fragment for the first section
        if fragments:
            first_frag = fragments[0]
            intro_frag = DocFragment(
                id=hashlib.md5(f"{source_path}:intro".encode()).hexdigest()[:16],
                doc_type=DocType.README,
                extraction_type=ExtractionType.CONCEPT,
                source_path=source_path,
                source_name=Path(source_path).name,
                project=project,
                title=f"What is {project}",
                content=first_frag.content[:1000],
                code_example=None,
                language=None,
                instruction=f"What is {project}?",
                input_text="",
                output_text=first_frag.content[:2000],
                section_path=[project],
                quality_score=0.7,
                extracted_at=datetime.now().isoformat()
            )
            fragments.insert(0, intro_frag)

        return fragments


# =============================================================================
# Documentation Ingester
# =============================================================================

class DocumentationIngester:
    """
    Main class for ingesting documentation into training data.

    Features:
    - Multi-format support (MD, RST, docstrings)
    - Q&A pair extraction
    - Code example extraction
    - Quality scoring
    - Training data export
    """

    EXTENSION_PARSERS = {
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.rst': 'rst',
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.rs': 'rust',
    }

    def __init__(self, db_path: Optional[Path] = None):
        # Use external storage if available
        if db_path:
            self.db_path = db_path
        elif DOC_DB.parent.exists():
            self.db_path = DOC_DB
            self.output_jsonl = DOC_JSONL
        else:
            LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
            self.db_path = LOCAL_FALLBACK / "docs.db"
            self.output_jsonl = LOCAL_FALLBACK / "training_examples.jsonl"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Parsers
        self.md_parser = MarkdownParser()
        self.py_parser = PythonDocstringParser()
        self.jsdoc_parser = JSDocParser()
        self.rust_parser = RustDocParser()
        self.readme_parser = ReadmeParser()

        self._stats = {
            "files_processed": 0,
            "fragments_extracted": 0,
            "fragments_stored": 0,
        }

    def _init_db(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            # Fragments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fragments (
                    id TEXT PRIMARY KEY,
                    doc_type TEXT,
                    extraction_type TEXT,
                    source_path TEXT,
                    source_name TEXT,
                    project TEXT,
                    title TEXT,
                    content TEXT,
                    code_example TEXT,
                    language TEXT,
                    instruction TEXT,
                    input_text TEXT,
                    output_text TEXT,
                    section_path TEXT,
                    quality_score REAL,
                    extracted_at TEXT
                )
            """)

            # Processed files tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    processed_at TEXT,
                    fragments_extracted INTEGER
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_type ON fragments(doc_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_project ON fragments(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_quality ON fragments(quality_score)")

    def _get_file_hash(self, content: str) -> str:
        """Get hash of file content"""
        return hashlib.md5(content.encode()).hexdigest()

    def _is_file_processed(self, file_path: str, content_hash: str) -> bool:
        """Check if file has already been processed"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT file_hash FROM processed_files WHERE file_path = ?",
                (file_path,)
            ).fetchone()

            if result and result[0] == content_hash:
                return True
            return False

    def _mark_file_processed(self, file_path: str, content_hash: str, fragments: int):
        """Mark a file as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_files
                (file_path, file_hash, processed_at, fragments_extracted)
                VALUES (?, ?, ?, ?)
            """, (file_path, content_hash, datetime.now().isoformat(), fragments))

    def _store_fragment(self, fragment: DocFragment):
        """Store a fragment in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fragments
                (id, doc_type, extraction_type, source_path, source_name, project,
                 title, content, code_example, language, instruction, input_text,
                 output_text, section_path, quality_score, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fragment.id, fragment.doc_type.value, fragment.extraction_type.value,
                fragment.source_path, fragment.source_name, fragment.project,
                fragment.title, fragment.content, fragment.code_example, fragment.language,
                fragment.instruction, fragment.input_text, fragment.output_text,
                json.dumps(fragment.section_path), fragment.quality_score, fragment.extracted_at
            ))

    def ingest_file(self, file_path: str, project: Optional[str] = None,
                    force: bool = False) -> Dict:
        """
        Ingest a single file.

        Args:
            file_path: Path to the file
            project: Project name (auto-detected if not provided)
            force: Re-process even if already processed

        Returns:
            Ingestion statistics
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

        # Determine parser
        ext = file_path.suffix.lower()
        name = file_path.name.lower()

        if ext not in self.EXTENSION_PARSERS:
            return {"error": f"Unsupported file type: {ext}"}

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

        # Check if already processed
        content_hash = self._get_file_hash(content)
        if not force and self._is_file_processed(str(file_path), content_hash):
            return {"skipped": True, "reason": "already processed"}

        # Parse based on file type
        fragments = []

        if name.startswith('readme'):
            fragments = self.readme_parser.parse(content, str(file_path), project)
        elif ext in ['.md', '.markdown']:
            fragments = self.md_parser.parse(content, str(file_path), project)
        elif ext == '.py':
            fragments = self.py_parser.parse(content, str(file_path), project)
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            fragments = self.jsdoc_parser.parse(content, str(file_path), project)
        elif ext == '.rs':
            fragments = self.rust_parser.parse(content, str(file_path), project)

        # Store fragments
        stored = 0
        for fragment in fragments:
            if fragment.quality_score >= 0.3:  # Skip very low quality
                self._store_fragment(fragment)
                stored += 1

        # Mark file as processed
        self._mark_file_processed(str(file_path), content_hash, stored)

        self._stats["files_processed"] += 1
        self._stats["fragments_extracted"] += len(fragments)
        self._stats["fragments_stored"] += stored

        return {
            "file": str(file_path),
            "fragments_extracted": len(fragments),
            "fragments_stored": stored
        }

    def ingest_markdown(self, file_path: str, project: Optional[str] = None) -> Dict:
        """Ingest a markdown file (convenience method)"""
        return self.ingest_file(file_path, project)

    def ingest_docstrings(self, file_path: str, project: Optional[str] = None) -> Dict:
        """Ingest docstrings from a Python file (convenience method)"""
        return self.ingest_file(file_path, project)

    def ingest_readme(self, file_path: str, project: Optional[str] = None) -> Dict:
        """Ingest a README file (convenience method)"""
        return self.ingest_file(file_path, project)

    def ingest_directory(self, dir_path: str, project: Optional[str] = None,
                         recursive: bool = True, force: bool = False) -> Dict:
        """
        Ingest all documentation files in a directory.

        Args:
            dir_path: Directory path
            project: Project name
            recursive: Scan subdirectories
            force: Re-process already processed files

        Returns:
            Ingestion statistics
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            return {"error": f"Directory not found: {dir_path}"}

        if not project:
            project = dir_path.name

        self._stats = {
            "files_processed": 0,
            "fragments_extracted": 0,
            "fragments_stored": 0,
        }

        results = []

        # Patterns to find
        patterns = ['*.md', '*.py', '*.js', '*.ts', '*.rs', 'README*']

        for pattern in patterns:
            glob_fn = dir_path.rglob if recursive else dir_path.glob
            for file_path in glob_fn(pattern):
                # Skip common non-doc directories
                skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', '.venv',
                            'target', 'dist', 'build', 'site-packages'}
                if any(d in file_path.parts for d in skip_dirs):
                    continue

                result = self.ingest_file(str(file_path), project, force)
                if 'error' not in result and 'skipped' not in result:
                    results.append(result)

        return {
            "directory": str(dir_path),
            "project": project,
            "files_processed": self._stats["files_processed"],
            "fragments_extracted": self._stats["fragments_extracted"],
            "fragments_stored": self._stats["fragments_stored"],
        }

    def export_training_data(self, output_path: Optional[Path] = None,
                            min_quality: float = 0.4,
                            doc_types: Optional[List[DocType]] = None,
                            extraction_types: Optional[List[ExtractionType]] = None) -> Dict:
        """
        Export fragments as JSONL training data.

        Args:
            output_path: Output file path
            min_quality: Minimum quality score
            doc_types: Filter by doc types
            extraction_types: Filter by extraction types

        Returns:
            Export statistics
        """
        output_path = output_path or self.output_jsonl
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build query
        query = "SELECT * FROM fragments WHERE quality_score >= ?"
        params = [min_quality]

        if doc_types:
            placeholders = ','.join('?' * len(doc_types))
            query += f" AND doc_type IN ({placeholders})"
            params.extend([dt.value for dt in doc_types])

        if extraction_types:
            placeholders = ','.join('?' * len(extraction_types))
            query += f" AND extraction_type IN ({placeholders})"
            params.extend([et.value for et in extraction_types])

        query += " ORDER BY quality_score DESC"

        exported = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            with open(output_path, 'w') as f:
                for row in rows:
                    example = {
                        "instruction": row["instruction"],
                        "input": row["input_text"],
                        "output": row["output_text"],
                        "metadata": {
                            "doc_type": row["doc_type"],
                            "extraction_type": row["extraction_type"],
                            "source": row["source_name"],
                            "project": row["project"],
                            "quality": row["quality_score"],
                        }
                    }
                    f.write(json.dumps(example) + '\n')
                    exported += 1

        return {
            "exported": exported,
            "output_path": str(output_path),
            "min_quality": min_quality,
            "file_size_kb": round(output_path.stat().st_size / 1024, 1)
        }

    def get_stats(self) -> Dict:
        """Get ingestion statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total_fragments = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]

            by_doc_type = dict(conn.execute("""
                SELECT doc_type, COUNT(*) FROM fragments GROUP BY doc_type
            """).fetchall())

            by_extraction_type = dict(conn.execute("""
                SELECT extraction_type, COUNT(*) FROM fragments GROUP BY extraction_type
            """).fetchall())

            by_project = dict(conn.execute("""
                SELECT project, COUNT(*) FROM fragments
                WHERE project IS NOT NULL
                GROUP BY project
            """).fetchall())

            avg_quality = conn.execute(
                "SELECT AVG(quality_score) FROM fragments"
            ).fetchone()[0] or 0

            processed_files = conn.execute(
                "SELECT COUNT(*) FROM processed_files"
            ).fetchone()[0]

            return {
                "total_fragments": total_fragments,
                "by_doc_type": by_doc_type,
                "by_extraction_type": by_extraction_type,
                "by_project": by_project,
                "avg_quality": round(avg_quality, 3),
                "processed_files": processed_files,
                "db_path": str(self.db_path),
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
            }

    def search_fragments(self, query: str, limit: int = 20) -> List[Dict]:
        """Search fragments by title or content"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, doc_type, extraction_type, source_name, project,
                       title, instruction, quality_score
                FROM fragments
                WHERE title LIKE ? OR content LIKE ? OR instruction LIKE ?
                ORDER BY quality_score DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()

            return [dict(r) for r in rows]


# =============================================================================
# Singleton
# =============================================================================

_ingester = None


def get_ingester() -> DocumentationIngester:
    """Get singleton documentation ingester"""
    global _ingester
    if _ingester is None:
        _ingester = DocumentationIngester()
    return _ingester


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM Documentation Ingestion - Phase 5.1.6")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Ingest file command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a file or directory")
    ingest_parser.add_argument("path", help="File or directory path")
    ingest_parser.add_argument("--project", "-p", help="Project name")
    ingest_parser.add_argument("--force", "-f", action="store_true", help="Force re-process")
    ingest_parser.add_argument("--no-recursive", action="store_true", help="Don't scan subdirectories")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export training data")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.add_argument("--min-quality", "-q", type=float, default=0.4)

    # Stats command
    subparsers.add_parser("stats", help="Show statistics")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search fragments")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", "-l", type=int, default=20)

    args = parser.parse_args()
    ingester = get_ingester()

    if args.command == "ingest":
        path = Path(args.path)

        if path.is_file():
            print(f"\nIngesting file: {path}")
            result = ingester.ingest_file(str(path), args.project, args.force)
        else:
            print(f"\nIngesting directory: {path}")
            result = ingester.ingest_directory(
                str(path), args.project,
                recursive=not args.no_recursive,
                force=args.force
            )

        if "error" in result:
            print(f"Error: {result['error']}")
        elif "skipped" in result:
            print(f"Skipped: {result['reason']}")
        else:
            print(f"Files processed: {result.get('files_processed', 1)}")
            print(f"Fragments extracted: {result.get('fragments_extracted', 0)}")
            print(f"Fragments stored: {result.get('fragments_stored', 0)}")

    elif args.command == "export":
        output_path = Path(args.output) if args.output else None

        print(f"\nExporting training data...")
        result = ingester.export_training_data(
            output_path=output_path,
            min_quality=args.min_quality
        )

        print(f"Exported: {result['exported']} examples")
        print(f"Output: {result['output_path']}")
        print(f"Size: {result['file_size_kb']} KB")

    elif args.command == "stats":
        stats = ingester.get_stats()
        print("\nDocumentation Ingestion Statistics\n")
        print(f"Total fragments: {stats['total_fragments']}")
        print(f"Processed files: {stats['processed_files']}")
        print(f"Average quality: {stats['avg_quality']}")
        print(f"Database: {stats['db_path']} ({stats['db_size_mb']} MB)")

        print("\nBy document type:")
        for dtype, count in stats['by_doc_type'].items():
            print(f"  {dtype}: {count}")

        print("\nBy extraction type:")
        for etype, count in stats['by_extraction_type'].items():
            print(f"  {etype}: {count}")

        if stats['by_project']:
            print("\nBy project:")
            for proj, count in list(stats['by_project'].items())[:10]:
                print(f"  {proj}: {count}")

    elif args.command == "search":
        results = ingester.search_fragments(args.query, args.limit)
        print(f"\nSearch results for '{args.query}': {len(results)}\n")
        for r in results:
            print(f"  [{r['extraction_type']}] {r['title']}")
            print(f"    {r['instruction'][:60]}...")
            print(f"    Source: {r['source_name']} (quality: {r['quality_score']:.2f})")
            print()

    else:
        parser.print_help()
