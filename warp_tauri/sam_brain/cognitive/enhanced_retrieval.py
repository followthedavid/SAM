"""
Enhanced Retrieval System for SAM Cognitive Architecture

Implements:
1. HyDE (Hypothetical Document Embeddings) - Generate hypothetical answer, embed, search
2. Multi-hop Retrieval - Extract entities, search iteratively
3. Cross-encoder Reranking - Use ms-marco for precise scoring
4. Query Decomposition - Break complex queries into sub-queries

Integrates with existing:
- semantic_memory.py (vector embeddings via Ollama)
- context_manager.py (basic RAG)
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime
import hashlib

# Try to import ML libraries, fall back gracefully
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    np = None

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

# Code indexer integration (Phase 2.2)
try:
    from .code_indexer import get_code_indexer, CodeEntity
    CODE_INDEXER_AVAILABLE = True
except ImportError:
    CODE_INDEXER_AVAILABLE = False
    CodeEntity = None

# Relevance Scorer (Phase 2.2.5) - lightweight MLX-compatible reranking
try:
    import sys
    import os
    # Add parent directory to path if not already there
    _parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)

    from relevance_scorer import (
        RelevanceScorer,
        get_relevance_scorer,
        rerank_code_results,
        rerank_doc_results,
    )
    RELEVANCE_SCORER_AVAILABLE = True
except ImportError:
    RELEVANCE_SCORER_AVAILABLE = False


@dataclass
class RetrievedChunk:
    """A retrieved piece of content"""
    id: str
    content: str
    source: str  # Database/table name
    score: float  # Relevance score (0-1)
    metadata: Dict[str, Any]

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class EmbeddingModel:
    """
    Wrapper for embedding models.
    Uses sentence-transformers if available, falls back to Ollama.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._init_model()

    def _init_model(self):
        """Initialize embedding model"""
        if ML_AVAILABLE:
            try:
                self.model = SentenceTransformer(self.model_name)
                self.backend = "sentence_transformers"
                return
            except Exception as e:
                print(f"Failed to load sentence-transformers: {e}")

        # Fall back to Ollama
        self.backend = "ollama"

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts"""
        if self.backend == "sentence_transformers" and self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Use Ollama
            return self._embed_ollama(texts)

    def _embed_ollama(self, texts: List[str]) -> List[List[float]]:
        """Embed using Ollama's API"""
        import subprocess
        import json

        embeddings = []
        for text in texts:
            try:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:11434/api/embeddings",
                     "-d", json.dumps({"model": "nomic-embed-text", "prompt": text})],
                    capture_output=True, text=True, timeout=30
                )
                data = json.loads(result.stdout)
                embeddings.append(data.get("embedding", []))
            except Exception as e:
                print(f"Ollama embedding failed: {e}")
                embeddings.append([])

        return embeddings

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text"""
        return self.embed([text])[0]


class HyDERetriever:
    """
    Hypothetical Document Embeddings retriever.

    Instead of embedding the query directly:
    1. Generate a hypothetical answer to the query
    2. Embed the hypothetical answer
    3. Search for similar real documents

    This works because the hypothetical answer is closer in embedding
    space to relevant documents than the query itself.
    """

    def __init__(self, embedding_model: Optional[EmbeddingModel] = None,
                 llm_generator: Optional[callable] = None):
        self.embedder = embedding_model or EmbeddingModel()
        self.llm_generator = llm_generator or self._default_generator
        self.cache: Dict[str, List[float]] = {}

    def _default_generator(self, query: str) -> str:
        """Default hypothetical document generator (simple heuristics)"""
        # Without an LLM, we do keyword expansion
        words = query.lower().split()

        # Add common response patterns
        patterns = [
            f"The answer to '{query}' is",
            f"Regarding {' '.join(words[:3])},",
            f"{query.rstrip('?')}.",
        ]

        return " ".join(patterns)

    def generate_hypothetical(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query"""
        return self.llm_generator(query)

    def get_hyde_embedding(self, query: str) -> List[float]:
        """Get HyDE embedding for a query"""
        cache_key = hashlib.md5(query.encode()).hexdigest()

        if cache_key in self.cache:
            return self.cache[cache_key]

        # Generate hypothetical document
        hypothetical = self.generate_hypothetical(query)

        # Combine query + hypothetical for embedding
        combined = f"{query}\n\n{hypothetical}"

        embedding = self.embedder.embed_single(combined)
        self.cache[cache_key] = embedding

        return embedding

    def retrieve(self, query: str, documents: List[Tuple[str, List[float]]],
                 top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Retrieve documents using HyDE.

        Args:
            query: The search query
            documents: List of (content, embedding) tuples
            top_k: Number of results to return

        Returns:
            List of (content, score) tuples
        """
        query_emb = self.get_hyde_embedding(query)

        if not ML_AVAILABLE or np is None:
            # Fall back to keyword matching
            return self._keyword_fallback(query, [d[0] for d in documents], top_k)

        query_emb = np.array(query_emb)
        scores = []

        for content, doc_emb in documents:
            if not doc_emb:
                continue
            doc_emb = np.array(doc_emb)
            # Cosine similarity
            score = np.dot(query_emb, doc_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(doc_emb) + 1e-8
            )
            scores.append((content, float(score)))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _keyword_fallback(self, query: str, documents: List[str],
                          top_k: int) -> List[Tuple[str, float]]:
        """Fallback keyword matching when embeddings unavailable"""
        keywords = set(query.lower().split())
        scores = []

        for doc in documents:
            doc_words = set(doc.lower().split())
            overlap = len(keywords & doc_words)
            score = overlap / (len(keywords) + 1)
            scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class EntityExtractor:
    """
    Extract entities from text for multi-hop retrieval.
    Uses spaCy if available, falls back to regex patterns.
    """

    def __init__(self):
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("spaCy model not found. Install with: python -m spacy download en_core_web_sm")

    def extract(self, text: str) -> List[Dict[str, str]]:
        """Extract entities from text"""
        if self.nlp:
            return self._extract_spacy(text)
        return self._extract_regex(text)

    def _extract_spacy(self, text: str) -> List[Dict[str, str]]:
        """Extract entities using spaCy"""
        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })

        return entities

    def _extract_regex(self, text: str) -> List[Dict[str, str]]:
        """Extract entities using regex patterns"""
        entities = []

        # Capitalized phrases (likely proper nouns)
        for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text):
            entities.append({
                "text": match.group(1),
                "type": "PROPER_NOUN",
                "start": match.start(),
                "end": match.end()
            })

        # Technical terms (camelCase, snake_case)
        for match in re.finditer(r'\b([a-z]+[A-Z][a-zA-Z]*|[a-z]+_[a-z_]+)\b', text):
            entities.append({
                "text": match.group(1),
                "type": "TECHNICAL",
                "start": match.start(),
                "end": match.end()
            })

        # Numbers and measurements
        for match in re.finditer(r'\b(\d+(?:\.\d+)?(?:\s*(?:GB|MB|KB|ms|s|%))?)\b', text):
            entities.append({
                "text": match.group(1),
                "type": "QUANTITY",
                "start": match.start(),
                "end": match.end()
            })

        return entities


class MultiHopRetriever:
    """
    Multi-hop retrieval: iteratively search based on extracted entities.

    Process:
    1. Initial query → retrieve documents
    2. Extract entities from retrieved documents
    3. Search for documents containing those entities
    4. Repeat until saturation or max hops
    5. Merge and deduplicate results
    """

    def __init__(self, base_retriever: HyDERetriever,
                 entity_extractor: Optional[EntityExtractor] = None,
                 max_hops: int = 3):
        self.retriever = base_retriever
        self.extractor = entity_extractor or EntityExtractor()
        self.max_hops = max_hops

    def retrieve(self, query: str,
                 document_store: "DocumentStore",
                 top_k_per_hop: int = 5,
                 top_k_final: int = 10) -> List[RetrievedChunk]:
        """
        Perform multi-hop retrieval.

        Args:
            query: Initial search query
            document_store: Store to search
            top_k_per_hop: Results per hop
            top_k_final: Final number of results

        Returns:
            List of RetrievedChunk objects
        """
        all_results: Dict[str, RetrievedChunk] = {}
        seen_queries: Set[str] = {query.lower()}
        current_queries = [query]

        for hop in range(self.max_hops):
            hop_results = []

            for q in current_queries:
                # Retrieve for this query
                results = document_store.search(q, top_k=top_k_per_hop)
                hop_results.extend(results)

            # Add to all results (higher hop = lower score adjustment)
            hop_penalty = 1.0 - (hop * 0.1)
            for chunk in hop_results:
                if chunk.id not in all_results:
                    chunk.score *= hop_penalty
                    all_results[chunk.id] = chunk
                else:
                    # Boost score if found multiple times
                    all_results[chunk.id].score = min(
                        1.0,
                        all_results[chunk.id].score + chunk.score * 0.2
                    )

            # Extract entities for next hop
            new_queries = []
            for chunk in hop_results:
                entities = self.extractor.extract(chunk.content)
                for ent in entities:
                    ent_text = ent["text"].lower()
                    if ent_text not in seen_queries and len(ent_text) > 2:
                        new_queries.append(ent["text"])
                        seen_queries.add(ent_text)

            if not new_queries:
                break  # Saturated

            current_queries = new_queries[:10]  # Limit queries per hop

        # Sort by final score
        results = sorted(all_results.values(), key=lambda x: x.score, reverse=True)
        return results[:top_k_final]


class CrossEncoderReranker:
    """
    Rerank results using a cross-encoder model or lightweight fallback.

    Cross-encoders are more accurate than bi-encoders for ranking
    because they process query and document together.

    On 8GB RAM systems, falls back to lightweight RelevanceScorer
    which uses MLX embeddings and multi-factor scoring.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 use_lightweight: bool = True):
        """
        Initialize the reranker.

        Args:
            model_name: Cross-encoder model name (if using heavy model)
            use_lightweight: Prefer lightweight RelevanceScorer (recommended for 8GB RAM)
        """
        self.model_name = model_name
        self.model = None
        self.lightweight_scorer = None
        self.use_lightweight = use_lightweight

        if use_lightweight and RELEVANCE_SCORER_AVAILABLE:
            self._init_lightweight()
        else:
            self._init_model()

    def _init_model(self):
        """Initialize cross-encoder model (heavy, ~500MB RAM)"""
        if ML_AVAILABLE:
            try:
                self.model = CrossEncoder(self.model_name)
            except Exception as e:
                print(f"Failed to load cross-encoder: {e}")
                # Fall back to lightweight scorer
                if RELEVANCE_SCORER_AVAILABLE:
                    self._init_lightweight()

    def _init_lightweight(self):
        """Initialize lightweight MLX-based scorer (recommended for 8GB RAM)"""
        if RELEVANCE_SCORER_AVAILABLE:
            try:
                self.lightweight_scorer = get_relevance_scorer()
                self.use_lightweight = True
            except Exception as e:
                print(f"Failed to init lightweight scorer: {e}")

    def rerank(self, query: str, chunks: List[RetrievedChunk],
               top_k: int = 5) -> List[RetrievedChunk]:
        """
        Rerank chunks using cross-encoder or lightweight scorer.

        Args:
            query: The search query
            chunks: List of chunks to rerank
            top_k: Number of results to return

        Returns:
            Reranked list of chunks
        """
        if not chunks:
            return []

        # Try lightweight scorer first (recommended for 8GB RAM)
        if self.use_lightweight and self.lightweight_scorer:
            return self._rerank_lightweight(query, chunks, top_k)

        # Fall back to heavy cross-encoder
        if self.model:
            return self._rerank_crossencoder(query, chunks, top_k)

        # No reranking available - just sort by original score
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]

    def _rerank_lightweight(self, query: str, chunks: List[RetrievedChunk],
                            top_k: int) -> List[RetrievedChunk]:
        """Rerank using lightweight RelevanceScorer."""
        # Convert chunks to format expected by scorer
        results = []
        for chunk in chunks:
            results.append({
                "id": chunk.id,
                "name": chunk.metadata.get("name", chunk.source.split("/")[-1]),
                "type": chunk.metadata.get("type", "unknown"),
                "content": chunk.content,
                "file_path": chunk.metadata.get("file", chunk.source),
                "line_number": chunk.metadata.get("line", 0),
                "original_score": chunk.score,
            })

        # Rerank using multi-factor scoring
        scored = self.lightweight_scorer.rerank(query, results, limit=top_k)

        # Convert back to RetrievedChunk format
        reranked = []
        scored_dict = {s.id: s.final_score for s in scored}

        for chunk in chunks:
            if chunk.id in scored_dict:
                # Update score with reranked score
                chunk.score = (chunk.score + scored_dict[chunk.id]) / 2
                reranked.append(chunk)

        # Sort by updated score
        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:top_k]

    def _rerank_crossencoder(self, query: str, chunks: List[RetrievedChunk],
                             top_k: int) -> List[RetrievedChunk]:
        """Rerank using heavy cross-encoder model."""
        # Prepare pairs for cross-encoder
        pairs = [[query, chunk.content] for chunk in chunks]

        # Get scores
        scores = self.model.predict(pairs)

        # Update chunk scores
        for chunk, score in zip(chunks, scores):
            # Combine original score with rerank score
            chunk.score = (chunk.score + float(score)) / 2

        # Sort by new score
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]


class QueryDecomposer:
    """
    Decompose complex queries into simpler sub-queries.

    Patterns:
    - "X and Y" → ["X", "Y"]
    - "X or Y" → ["X", "Y"]
    - "How to X using Y" → ["how to X", "Y"]
    - "What is X in Y" → ["what is X", "Y"]
    """

    def decompose(self, query: str) -> List[str]:
        """Decompose a query into sub-queries"""
        sub_queries = [query]  # Always include original

        # Split on "and"
        if " and " in query.lower():
            parts = re.split(r'\s+and\s+', query, flags=re.IGNORECASE)
            sub_queries.extend(parts)

        # Split on "or"
        if " or " in query.lower():
            parts = re.split(r'\s+or\s+', query, flags=re.IGNORECASE)
            sub_queries.extend(parts)

        # Extract "using X" phrases
        using_match = re.search(r'using\s+([^,?.]+)', query, re.IGNORECASE)
        if using_match:
            sub_queries.append(using_match.group(1).strip())

        # Extract "in X" phrases
        in_match = re.search(r'\bin\s+([^,?.]+)$', query, re.IGNORECASE)
        if in_match:
            sub_queries.append(in_match.group(1).strip())

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for q in sub_queries:
            q_lower = q.lower().strip()
            if q_lower not in seen and len(q_lower) > 2:
                seen.add(q_lower)
                unique.append(q.strip())

        return unique


class DocumentStore:
    """
    Unified interface to multiple document sources.
    Wraps SQLite databases for retrieval.
    """

    def __init__(self, db_paths: List[str],
                 embedding_model: Optional[EmbeddingModel] = None):
        self.db_paths = [Path(p) for p in db_paths if Path(p).exists()]
        self.embedder = embedding_model or EmbeddingModel()
        self._embedding_cache: Dict[str, List[float]] = {}

    def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        """Search across all document sources"""
        all_chunks = []

        for db_path in self.db_paths:
            chunks = self._search_db(db_path, query, top_k)
            all_chunks.extend(chunks)

        # Sort by score
        all_chunks.sort(key=lambda x: x.score, reverse=True)
        return all_chunks[:top_k]

    def _search_db(self, db_path: Path, query: str,
                   top_k: int) -> List[RetrievedChunk]:
        """Search a single SQLite database"""
        chunks = []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                # Find text columns
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                text_cols = [col[1] for col in columns if 'text' in col[1].lower()
                             or col[2].upper() == 'TEXT']

                if not text_cols:
                    continue

                # Keyword search
                keywords = query.lower().split()[:5]
                for col in text_cols:
                    for kw in keywords:
                        if len(kw) < 3:
                            continue
                        try:
                            cursor.execute(
                                f"SELECT rowid, {col} FROM {table} WHERE {col} LIKE ? LIMIT ?",
                                (f"%{kw}%", top_k)
                            )
                            for row in cursor.fetchall():
                                content = str(row[1])[:500]
                                chunk_id = f"{db_path.name}:{table}:{row[0]}"

                                # Simple keyword score
                                score = sum(1 for k in keywords if k in content.lower())
                                score = min(1.0, score / len(keywords))

                                chunks.append(RetrievedChunk(
                                    id=chunk_id,
                                    content=content,
                                    source=f"{db_path.name}/{table}",
                                    score=score,
                                    metadata={"table": table, "db": db_path.name}
                                ))
                        except Exception:
                            continue

            conn.close()

        except Exception as e:
            print(f"Error searching {db_path}: {e}")

        return chunks


class EnhancedRetrievalSystem:
    """
    Complete enhanced retrieval system combining all components.

    Pipeline:
    1. Decompose query into sub-queries
    2. For each sub-query:
       a. Use HyDE to generate enhanced embedding
       b. Retrieve initial candidates
    3. Perform multi-hop retrieval for additional context
    4. Rerank all results with cross-encoder
    5. Return top results
    """

    def __init__(self, db_paths: List[str],
                 use_hyde: bool = True,
                 use_multihop: bool = True,
                 use_reranking: bool = True,
                 use_code_index: bool = True):
        self.embedding_model = EmbeddingModel()
        self.document_store = DocumentStore(db_paths, self.embedding_model)
        self.query_decomposer = QueryDecomposer()

        self.hyde_retriever = HyDERetriever(self.embedding_model) if use_hyde else None
        self.entity_extractor = EntityExtractor()
        self.multihop_retriever = MultiHopRetriever(
            self.hyde_retriever or HyDERetriever(self.embedding_model),
            self.entity_extractor
        ) if use_multihop else None
        self.reranker = CrossEncoderReranker() if use_reranking else None

        # Code index integration (Phase 2.2)
        self.code_indexer = None
        self.use_code_index = use_code_index and CODE_INDEXER_AVAILABLE
        if self.use_code_index:
            try:
                self.code_indexer = get_code_indexer()
            except Exception:
                self.use_code_index = False

        self.use_hyde = use_hyde
        self.use_multihop = use_multihop
        self.use_reranking = use_reranking
        self.current_project_id = None  # Set by orchestrator

    def set_project(self, project_id: str):
        """Set current project for code index queries."""
        self.current_project_id = project_id

    def _retrieve_from_code_index(self, query: str, limit: int = 5) -> List[RetrievedChunk]:
        """Retrieve relevant code from the code index."""
        if not self.code_indexer:
            return []

        try:
            results = self.code_indexer.search(
                query,
                project_id=self.current_project_id,
                limit=limit
            )

            chunks = []
            for entity in results:
                # Score based on match quality
                score = 0.7  # Base score for code matches
                if query.lower() in entity.name.lower():
                    score += 0.2
                if entity.docstring and query.lower() in entity.docstring.lower():
                    score += 0.1

                chunks.append(RetrievedChunk(
                    id=f"code:{entity.id}",
                    content=f"[{entity.type}] {entity.signature}\n{entity.content}",
                    source=f"code_index/{entity.file_path.split('/')[-1]}",
                    score=min(1.0, score),
                    metadata={
                        "type": entity.type,
                        "name": entity.name,
                        "file": entity.file_path,
                        "line": entity.line_number
                    }
                ))

            return chunks
        except Exception:
            return []

    def retrieve(self, query: str, top_k: int = 5,
                 include_code: bool = True) -> List[RetrievedChunk]:
        """
        Retrieve documents using the full pipeline.

        Args:
            query: Search query
            top_k: Number of results to return
            include_code: Whether to include code index results

        Returns:
            List of RetrievedChunk objects
        """
        # Step 1: Decompose query
        sub_queries = self.query_decomposer.decompose(query)

        all_chunks: Dict[str, RetrievedChunk] = {}

        # Step 2: Retrieve for each sub-query
        for sq in sub_queries:
            if self.use_multihop and self.multihop_retriever:
                # Multi-hop includes HyDE
                chunks = self.multihop_retriever.retrieve(
                    sq, self.document_store, top_k_per_hop=3, top_k_final=top_k
                )
            else:
                # Simple search
                chunks = self.document_store.search(sq, top_k=top_k)

            # Merge results
            for chunk in chunks:
                if chunk.id not in all_chunks:
                    all_chunks[chunk.id] = chunk
                else:
                    # Boost score for items found by multiple queries
                    all_chunks[chunk.id].score = min(
                        1.0,
                        all_chunks[chunk.id].score + chunk.score * 0.3
                    )

        # Step 2.5: Include code index results (Phase 2.2)
        if include_code and self.use_code_index:
            code_chunks = self._retrieve_from_code_index(query, limit=top_k)
            for chunk in code_chunks:
                if chunk.id not in all_chunks:
                    all_chunks[chunk.id] = chunk

        # Step 3: Rerank
        results = list(all_chunks.values())
        if self.use_reranking and self.reranker:
            results = self.reranker.rerank(query, results, top_k=top_k)
        else:
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k]

        return results

    def retrieve_as_context(self, query: str, max_tokens: int = 150) -> str:
        """
        Retrieve and format as context string.

        Args:
            query: Search query
            max_tokens: Maximum tokens in output

        Returns:
            Formatted context string
        """
        chunks = self.retrieve(query, top_k=10)

        context_parts = []
        token_count = 0

        for chunk in chunks:
            chunk_tokens = len(chunk.content) // 4
            if token_count + chunk_tokens > max_tokens:
                break
            context_parts.append(chunk.content)
            token_count += chunk_tokens

        return "\n---\n".join(context_parts)


# Convenience function
def create_retrieval_system(db_paths: Optional[List[str]] = None) -> EnhancedRetrievalSystem:
    """Create an enhanced retrieval system with default databases"""
    default_paths = [
        "/Volumes/David External/dark_psych_archive/dark_psych.db",
        "/Volumes/David External/coding_training/code_training.db",
        "/Volumes/David External/sam_memory/memory.db"
    ]
    paths = db_paths or default_paths
    return EnhancedRetrievalSystem(paths)


if __name__ == "__main__":
    # Demo
    system = create_retrieval_system()

    query = "How do I implement memory systems in Python?"
    print(f"Query: {query}\n")

    # Decompose
    decomposer = QueryDecomposer()
    sub_queries = decomposer.decompose(query)
    print(f"Sub-queries: {sub_queries}\n")

    # Retrieve
    results = system.retrieve(query, top_k=3)
    print(f"Results ({len(results)}):")
    for r in results:
        print(f"  [{r.score:.2f}] {r.source}: {r.content[:100]}...")
