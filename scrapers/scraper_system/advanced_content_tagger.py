#!/usr/bin/env python3
"""
Advanced Content Tagging System - Cutting Edge

Multi-modal, ML-powered content analysis:
1. Transfer learning from AO3 tagged data
2. Scene-level segmentation and analysis
3. Local LLM for nuanced understanding (MLX)
4. Embedding-based semantic similarity
5. Character and relationship extraction
6. Intensity gradient scoring
7. AO3 community tag vocabulary mining

Usage:
    python advanced_content_tagger.py train          # Train classifier on AO3
    python advanced_content_tagger.py analyze nifty  # Analyze Nifty with trained model
    python advanced_content_tagger.py extract-vocab  # Mine AO3 tag vocabulary
    python advanced_content_tagger.py status         # Show stats
"""

import json
import re
import sqlite3
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Generator
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime
import pickle

# Import exhaustive taxonomy
from exhaustive_tag_taxonomy import MASTER_TAXONOMY, CONSENT_TAGS

# MLX for Apple Silicon
try:
    import mlx.core as mx
    import mlx.nn as nn
    from mlx_lm import load, generate
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("Note: MLX not available - some features disabled")

# Sentence embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Note: sentence-transformers not available - using fallback")


# ============================================================================
# Configuration
# ============================================================================

AO3_DB = Path("/Volumes/David External/ao3_archive/ao3_index.db")
AO3_CONTENT = Path("/Volumes/David External/ao3_archive/works")
NIFTY_DB = Path("/Volumes/David External/nifty_archive/nifty_index.db")
NIFTY_CONTENT = Path("/Volumes/David External/nifty_archive/stories")

MODEL_DIR = Path("/Volumes/David External/SAM_training_corpus/tag_models")
TAG_DB = Path.home() / ".sam" / "advanced_tags.db"


# ============================================================================
# AO3 Tag Vocabulary Mining
# ============================================================================

@dataclass
class TagVocabulary:
    """Comprehensive tag vocabulary mined from AO3."""

    # Core AO3 warning categories
    archive_warnings: Set[str] = field(default_factory=set)

    # Relationship tags
    relationships: Set[str] = field(default_factory=set)

    # Freeform tags (the rich community vocabulary)
    freeform_tags: Dict[str, int] = field(default_factory=dict)

    # Categorized tags (our analysis)
    categorized: Dict[str, Set[str]] = field(default_factory=dict)

    # Tag embeddings for similarity matching
    tag_embeddings: Dict[str, np.ndarray] = field(default_factory=dict)


class AO3TagMiner:
    """Mines and categorizes the full AO3 tag vocabulary."""

    # Tag category patterns for auto-classification
    CATEGORY_PATTERNS = {
        "consent": [
            r"non.?con", r"dub.?con", r"rape", r"assault", r"forced", r"coercion",
            r"blackmail", r"manipulation", r"consent", r"willing", r"consensual"
        ],
        "power_dynamics": [
            r"dom[/\s]sub", r"dominant", r"submissive", r"master", r"slave",
            r"power.?play", r"control", r"authority", r"boss", r"teacher",
            r"coach", r"daddy", r"age.?gap", r"power.?imbalance"
        ],
        "kink": [
            r"bdsm", r"bondage", r"spanking", r"humiliation", r"degradation",
            r"worship", r"foot", r"leather", r"uniform", r"size.?kink",
            r"breeding", r"rough", r"pain", r"masochism", r"sadism"
        ],
        "emotional": [
            r"angst", r"fluff", r"hurt.?comfort", r"dark", r"romantic",
            r"tragedy", r"happy.?ending", r"slow.?burn", r"pining"
        ],
        "relationship": [
            r"first.?time", r"friends.?to.?lovers", r"enemies", r"strangers",
            r"established", r"secret.?relationship", r"affair", r"cheating"
        ],
        "identity": [
            r"coming.?out", r"closeted", r"internalized", r"homophobia",
            r"gay", r"bisexual", r"questioning", r"straight.?guy"
        ],
        "setting": [
            r"school", r"college", r"military", r"prison", r"office",
            r"sports", r"locker.?room", r"public", r"outdoor"
        ],
        "character_type": [
            r"jock", r"nerd", r"bully", r"twink", r"bear", r"daddy",
            r"muscle", r"innocent", r"experienced", r"virgin"
        ],
        "explicit_acts": [
            r"oral", r"anal", r"rimming", r"fingering", r"handjob",
            r"blowjob", r"threesome", r"gangbang", r"voyeur", r"exhib"
        ],
    }

    def __init__(self):
        self.vocab = TagVocabulary()
        self.embedder = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                pass

    def mine_ao3_tags(self) -> TagVocabulary:
        """Extract all tags from AO3 database."""
        conn = sqlite3.connect(AO3_DB)

        # Get all works with tags
        cursor = conn.execute("""
            SELECT warnings, tags, relationships FROM works WHERE downloaded = 1
        """)

        all_freeform = Counter()

        for warnings_json, tags_json, rels_json in cursor:
            # Parse warnings
            if warnings_json:
                try:
                    warnings = json.loads(warnings_json)
                    for w in warnings:
                        self.vocab.archive_warnings.add(w)
                except:
                    pass

            # Parse freeform tags
            if tags_json:
                try:
                    tags = json.loads(tags_json)
                    for t in tags:
                        all_freeform[t.lower().strip()] += 1
                except:
                    pass

            # Parse relationships
            if rels_json:
                try:
                    rels = json.loads(rels_json)
                    for r in rels:
                        self.vocab.relationships.add(r)
                except:
                    pass

        conn.close()

        # Filter to tags appearing 2+ times
        self.vocab.freeform_tags = {k: v for k, v in all_freeform.items() if v >= 2}

        # Auto-categorize tags
        self._categorize_tags()

        # Generate embeddings for similarity matching
        if self.embedder:
            self._generate_tag_embeddings()

        return self.vocab

    def _categorize_tags(self):
        """Categorize freeform tags using patterns."""
        for category, patterns in self.CATEGORY_PATTERNS.items():
            self.vocab.categorized[category] = set()

            combined_pattern = '|'.join(patterns)
            regex = re.compile(combined_pattern, re.IGNORECASE)

            for tag in self.vocab.freeform_tags:
                if regex.search(tag):
                    self.vocab.categorized[category].add(tag)

    def _generate_tag_embeddings(self):
        """Generate embeddings for all tags."""
        if not self.embedder:
            return

        tags = list(self.vocab.freeform_tags.keys())

        # Batch embed
        batch_size = 100
        for i in range(0, len(tags), batch_size):
            batch = tags[i:i+batch_size]
            embeddings = self.embedder.encode(batch)
            for tag, emb in zip(batch, embeddings):
                self.vocab.tag_embeddings[tag] = emb

    def save_vocab(self, path: Path = None):
        """Save vocabulary to disk."""
        path = path or MODEL_DIR / "tag_vocabulary.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            pickle.dump(self.vocab, f)

        print(f"Saved vocabulary to {path}")
        print(f"  Archive warnings: {len(self.vocab.archive_warnings)}")
        print(f"  Freeform tags: {len(self.vocab.freeform_tags)}")
        print(f"  Categorized tags: {sum(len(v) for v in self.vocab.categorized.values())}")

    def load_vocab(self, path: Path = None) -> TagVocabulary:
        """Load vocabulary from disk."""
        path = path or MODEL_DIR / "tag_vocabulary.pkl"

        with open(path, 'rb') as f:
            self.vocab = pickle.load(f)

        return self.vocab


# ============================================================================
# Scene Segmentation
# ============================================================================

class SceneSegmenter:
    """Segments stories into discrete scenes for granular analysis."""

    # Scene break patterns
    BREAK_PATTERNS = [
        r'\n\s*\*\s*\*\s*\*\s*\n',  # * * *
        r'\n\s*~+\s*\n',            # ~~~
        r'\n\s*-{3,}\s*\n',         # ---
        r'\n\s*#{3,}\s*\n',         # ###
        r'\n\s*\.\s*\.\s*\.\s*\n',  # . . .
        r'\n{3,}',                   # Multiple blank lines
    ]

    COMBINED_PATTERN = re.compile('|'.join(BREAK_PATTERNS))

    @dataclass
    class Scene:
        index: int
        text: str
        word_count: int
        char_start: int
        char_end: int

        # Analysis results (filled later)
        tags: Dict[str, float] = field(default_factory=dict)
        intensity: float = 0.0
        characters: List[str] = field(default_factory=list)
        pov: str = ""

    def segment(self, text: str, min_words: int = 100) -> List['SceneSegmenter.Scene']:
        """Segment text into scenes."""
        # Split by scene break patterns
        parts = self.COMBINED_PATTERN.split(text)

        scenes = []
        char_pos = 0

        for i, part in enumerate(parts):
            part = part.strip()
            word_count = len(part.split())

            if word_count >= min_words:
                scenes.append(self.Scene(
                    index=len(scenes),
                    text=part,
                    word_count=word_count,
                    char_start=char_pos,
                    char_end=char_pos + len(part)
                ))

            char_pos += len(part)

        # If no breaks found, treat whole text as one scene
        if not scenes and len(text.split()) >= min_words:
            scenes.append(self.Scene(
                index=0,
                text=text,
                word_count=len(text.split()),
                char_start=0,
                char_end=len(text)
            ))

        return scenes


# ============================================================================
# Character & Relationship Extraction
# ============================================================================

class CharacterExtractor:
    """Extracts characters and their relationships from text."""

    # Common character role indicators
    ROLE_PATTERNS = {
        "dominant": [
            r"pushed .+ down", r"grabbed .+ by", r"forced .+ to",
            r"ordered", r"commanded", r"made .+ kneel", r"controlled"
        ],
        "submissive": [
            r"was pushed", r"was forced", r"had to obey", r"knelt",
            r"begged", r"pleaded", r"submitted", r"gave in"
        ],
        "aggressor": [
            r"attacked", r"cornered", r"trapped", r"threatened",
            r"bullied", r"tormented", r"humiliated"
        ],
        "victim": [
            r"was attacked", r"was cornered", r"was trapped",
            r"was threatened", r"was bullied", r"couldn't escape"
        ],
        "seducer": [
            r"seduced", r"tempted", r"lured", r"charmed", r"flirted"
        ],
        "innocent": [
            r"didn't understand", r"confused", r"naive", r"first time",
            r"never done", r"inexperienced"
        ],
    }

    # POV indicators
    POV_PATTERNS = {
        "first_person": [r"\bI\b", r"\bme\b", r"\bmy\b", r"\bmyself\b"],
        "second_person": [r"\byou\b", r"\byour\b", r"\byourself\b"],
        "third_person": [r"\bhe\b", r"\bhis\b", r"\bshe\b", r"\bher\b", r"\bthey\b"],
    }

    def detect_pov(self, text: str) -> str:
        """Detect narrative point of view."""
        # Sample first 1000 chars
        sample = text[:1000].lower()

        counts = {}
        for pov, patterns in self.POV_PATTERNS.items():
            count = sum(len(re.findall(p, sample, re.IGNORECASE)) for p in patterns)
            counts[pov] = count

        # First person pronouns are less common, so weight them
        counts["first_person"] *= 2

        return max(counts, key=counts.get)

    def extract_roles(self, text: str) -> Dict[str, float]:
        """Extract character role dynamics from text."""
        roles = {}
        word_count = len(text.split())

        for role, patterns in self.ROLE_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                matches += len(re.findall(pattern, text, re.IGNORECASE))

            if matches > 0:
                # Normalize by text length
                roles[role] = round(matches / word_count * 1000, 2)

        return roles


# ============================================================================
# Intensity Scoring
# ============================================================================

class IntensityScorer:
    """Scores intensity/explicitness of content on multiple dimensions."""

    INTENSITY_MARKERS = {
        "graphic_sexual": {
            "low": ["kissed", "touched", "caressed", "held"],
            "medium": ["stroked", "rubbed", "groped", "moaned"],
            "high": ["fucked", "pounded", "slammed", "rammed", "destroyed"],
            "extreme": ["brutally", "relentlessly", "mercilessly", "violently"]
        },
        "emotional_intensity": {
            "low": ["felt", "thought", "wondered"],
            "medium": ["needed", "wanted", "craved"],
            "high": ["desperate", "aching", "burning", "consumed"],
            "extreme": ["shattered", "destroyed", "broken", "ruined"]
        },
        "power_intensity": {
            "low": ["asked", "suggested", "guided"],
            "medium": ["told", "directed", "instructed"],
            "high": ["ordered", "commanded", "demanded", "forced"],
            "extreme": ["dominated", "controlled", "owned", "enslaved"]
        },
        "pain_intensity": {
            "low": ["uncomfortable", "ached", "sore"],
            "medium": ["hurt", "painful", "stung"],
            "high": ["agony", "screamed", "cried out", "tore"],
            "extreme": ["tortured", "excruciating", "unbearable"]
        },
        "degradation_intensity": {
            "low": ["embarrassed", "blushing"],
            "medium": ["humiliated", "ashamed", "degraded"],
            "high": ["worthless", "pathetic", "disgusting"],
            "extreme": ["subhuman", "nothing", "trash", "garbage"]
        }
    }

    LEVEL_SCORES = {"low": 0.25, "medium": 0.5, "high": 0.75, "extreme": 1.0}

    def score_intensity(self, text: str) -> Dict[str, float]:
        """Score text intensity across dimensions."""
        text_lower = text.lower()
        word_count = len(text.split())

        scores = {}

        for dimension, levels in self.INTENSITY_MARKERS.items():
            dimension_score = 0
            max_level = 0

            for level, markers in levels.items():
                level_score = self.LEVEL_SCORES[level]

                for marker in markers:
                    if marker in text_lower:
                        if level_score > max_level:
                            max_level = level_score
                        dimension_score += level_score

            # Use max level found, weighted by frequency
            if dimension_score > 0:
                scores[dimension] = round(min(1.0, max_level * 0.7 + dimension_score * 0.001), 2)

        # Overall intensity
        if scores:
            scores["overall"] = round(sum(scores.values()) / len(scores), 2)

        return scores


# ============================================================================
# Exhaustive Taxonomy Tagger
# ============================================================================

class ExhaustiveTagger:
    """
    Uses the complete 259-tag, 1168-keyword taxonomy for comprehensive tagging.
    """

    def __init__(self):
        # Compile all patterns for efficiency
        self.compiled_patterns = {}

        for category, tags in MASTER_TAXONOMY.items():
            self.compiled_patterns[category] = {}

            for tag_name, tag_data in tags.items():
                # Handle both dict format (with keywords key) and list format
                if isinstance(tag_data, dict) and "keywords" in tag_data:
                    keywords = tag_data["keywords"]
                elif isinstance(tag_data, list):
                    keywords = tag_data
                else:
                    continue

                # Create compiled regex pattern
                pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
                self.compiled_patterns[category][tag_name] = re.compile(pattern, re.IGNORECASE)

    def tag_content(self, text: str) -> Dict[str, Dict[str, float]]:
        """
        Apply exhaustive taxonomy to text.
        Returns: {category: {tag: score, ...}, ...}
        """
        results = {}
        word_count = len(text.split())

        if word_count < 50:
            return results

        for category, patterns in self.compiled_patterns.items():
            category_results = {}

            for tag_name, pattern in patterns.items():
                matches = pattern.findall(text)

                if matches:
                    # Score based on frequency normalized by length
                    raw_score = len(matches) / word_count * 1000
                    # Also factor in unique keyword matches
                    unique_matches = len(set(m.lower() for m in matches))
                    score = min(1.0, (raw_score * 0.5) + (unique_matches * 0.1))

                    if score > 0.05:  # Threshold
                        category_results[tag_name] = round(score, 3)

            if category_results:
                # Sort by score
                results[category] = dict(sorted(
                    category_results.items(),
                    key=lambda x: x[1],
                    reverse=True
                ))

        return results

    def get_top_tags(self, text: str, n: int = 50) -> List[Tuple[str, str, float]]:
        """Get top N tags across all categories."""
        all_results = self.tag_content(text)

        flat_tags = []
        for category, tags in all_results.items():
            for tag, score in tags.items():
                flat_tags.append((category, tag, score))

        # Sort by score
        flat_tags.sort(key=lambda x: x[2], reverse=True)

        return flat_tags[:n]

    def get_consent_analysis(self, text: str) -> Dict[str, any]:
        """Detailed consent analysis using the consent taxonomy."""
        results = {"detected": [], "primary": None, "score": 0.0}

        word_count = len(text.split())
        if word_count < 50:
            return results

        consent_scores = {}

        for consent_type, data in CONSENT_TAGS.items():
            keywords = data["keywords"]
            pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
            matches = re.findall(pattern, text, re.IGNORECASE)

            if matches:
                score = len(matches) / word_count * 1000
                consent_scores[consent_type] = {
                    "score": round(score, 3),
                    "matches": len(matches),
                    "description": data["description"]
                }

        if consent_scores:
            results["detected"] = consent_scores
            # Primary is highest scoring
            primary = max(consent_scores.items(), key=lambda x: x[1]["score"])
            results["primary"] = primary[0]
            results["score"] = primary[1]["score"]

        return results


# ============================================================================
# ML-Based Tag Classifier (Transfer Learning from AO3)
# ============================================================================

class TagClassifier:
    """
    Multi-label classifier trained on AO3 tagged data.
    Uses embedding similarity + learned thresholds.
    """

    def __init__(self):
        self.vocab: Optional[TagVocabulary] = None
        self.embedder = None
        self.tag_centroids: Dict[str, np.ndarray] = {}
        self.tag_thresholds: Dict[str, float] = {}

        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                pass

    def train(self, vocab: TagVocabulary):
        """Train classifier on AO3 data."""
        self.vocab = vocab

        if not self.embedder:
            print("No embedder available - using keyword fallback")
            return

        print("Training tag classifier on AO3 data...")

        conn = sqlite3.connect(AO3_DB)
        cursor = conn.execute("""
            SELECT ao3_id, tags, file_path FROM works
            WHERE downloaded = 1 AND tags IS NOT NULL
        """)

        # Collect embeddings for each tag
        tag_examples: Dict[str, List[np.ndarray]] = defaultdict(list)

        processed = 0
        for ao3_id, tags_json, file_path in cursor:
            try:
                tags = json.loads(tags_json)

                # Load content
                content = self._load_ao3_content(ao3_id)
                if not content or len(content) < 500:
                    continue

                # Get content embedding (sample for efficiency)
                sample = content[:3000]
                embedding = self.embedder.encode(sample)

                # Associate with each tag
                for tag in tags:
                    tag_lower = tag.lower().strip()
                    if tag_lower in vocab.freeform_tags:
                        tag_examples[tag_lower].append(embedding)

                processed += 1
                if processed % 100 == 0:
                    print(f"  Processed {processed} works...")

            except Exception as e:
                continue

        conn.close()

        # Compute centroids for tags with enough examples
        print(f"\nComputing tag centroids...")
        for tag, embeddings in tag_examples.items():
            if len(embeddings) >= 3:  # Need at least 3 examples
                self.tag_centroids[tag] = np.mean(embeddings, axis=0)
                # Set threshold based on variance
                distances = [np.linalg.norm(e - self.tag_centroids[tag]) for e in embeddings]
                self.tag_thresholds[tag] = np.mean(distances) + np.std(distances)

        print(f"Trained centroids for {len(self.tag_centroids)} tags")

    def _load_ao3_content(self, ao3_id: int) -> Optional[str]:
        """Load content for an AO3 work."""
        content_dir = AO3_CONTENT

        # Try common patterns
        for pattern in [f"{ao3_id}.txt", f"{ao3_id}.html", f"{ao3_id}/*"]:
            matches = list(content_dir.glob(pattern))
            if matches:
                try:
                    return matches[0].read_text(errors='ignore')
                except:
                    pass

        return None

    def predict(self, text: str, top_k: int = 20) -> Dict[str, float]:
        """Predict tags for text with confidence scores."""
        if not self.embedder or not self.tag_centroids:
            return {}

        # Get text embedding
        sample = text[:3000]
        text_embedding = self.embedder.encode(sample)

        # Compute similarity to all tag centroids
        scores = {}
        for tag, centroid in self.tag_centroids.items():
            distance = np.linalg.norm(text_embedding - centroid)
            threshold = self.tag_thresholds.get(tag, 1.0)

            # Convert distance to similarity score
            if distance < threshold:
                scores[tag] = round(1 - (distance / threshold), 3)

        # Return top-k
        sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:top_k])

    def save(self, path: Path = None):
        """Save trained model."""
        path = path or MODEL_DIR / "tag_classifier.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            pickle.dump({
                'centroids': self.tag_centroids,
                'thresholds': self.tag_thresholds
            }, f)

        print(f"Saved classifier to {path}")

    def load(self, path: Path = None):
        """Load trained model."""
        path = path or MODEL_DIR / "tag_classifier.pkl"

        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.tag_centroids = data['centroids']
            self.tag_thresholds = data['thresholds']


# ============================================================================
# LLM-Based Scene Analysis (MLX)
# ============================================================================

class LLMSceneAnalyzer:
    """Uses local LLM for nuanced scene analysis."""

    ANALYSIS_PROMPT = """Analyze this scene from erotic fiction. Provide a JSON response with:
{
    "themes": ["list", "of", "themes"],
    "intensity": 0.0-1.0,
    "consent_level": "enthusiastic/willing/reluctant/dubious/non-consensual",
    "power_dynamic": "equal/dominant-submissive/authority/coercion",
    "emotional_tone": "romantic/playful/dark/intense/degrading",
    "character_roles": {"character1": "role", "character2": "role"}
}

Scene:
{scene}

JSON analysis:"""

    def __init__(self, model_path: str = None):
        self.model = None
        self.tokenizer = None

        if MLX_AVAILABLE and model_path:
            try:
                self.model, self.tokenizer = load(model_path)
                print(f"Loaded LLM for scene analysis: {model_path}")
            except Exception as e:
                print(f"Could not load LLM: {e}")

    def analyze_scene(self, scene_text: str) -> Dict:
        """Analyze a scene using LLM."""
        if not self.model:
            return {}

        # Truncate scene for prompt
        scene_sample = scene_text[:2000]
        prompt = self.ANALYSIS_PROMPT.format(scene=scene_sample)

        try:
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=500
            )

            # Parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            pass

        return {}


# ============================================================================
# Master Tagger - Combines All Systems
# ============================================================================

@dataclass
class ComprehensiveTagResult:
    """Complete analysis result for a piece of content."""

    item_id: str
    source: str

    # Document-level
    word_count: int = 0
    scene_count: int = 0
    pov: str = ""

    # All tags (exhaustive taxonomy + ML)
    predicted_tags: Dict[str, float] = field(default_factory=dict)

    # Categorized tags (12 categories, 259 tags)
    categories: Dict[str, List[str]] = field(default_factory=dict)

    # Intensity scores (5 dimensions + overall)
    intensity: Dict[str, float] = field(default_factory=dict)

    # Character dynamics
    character_roles: Dict[str, float] = field(default_factory=dict)

    # Consent analysis (detailed)
    consent_analysis: Dict[str, any] = field(default_factory=dict)

    # Scene-level analysis
    scenes: List[Dict] = field(default_factory=list)

    # Archive warnings (if applicable)
    archive_warnings: List[str] = field(default_factory=list)

    # Tag counts for quick filtering
    tag_count: int = 0

    def to_json(self) -> str:
        return json.dumps({
            "item_id": self.item_id,
            "source": self.source,
            "word_count": self.word_count,
            "scene_count": self.scene_count,
            "pov": self.pov,
            "tag_count": len(self.predicted_tags),
            "predicted_tags": self.predicted_tags,
            "categories": self.categories,
            "intensity": self.intensity,
            "character_roles": self.character_roles,
            "consent_analysis": self.consent_analysis,
            "archive_warnings": self.archive_warnings,
            "scenes": self.scenes[:5]  # Limit for storage
        })


class AdvancedContentTagger:
    """
    Master tagger combining all analysis systems.
    Uses 259 tags across 12 categories with 1168 keywords.
    """

    def __init__(self, use_llm: bool = False, llm_model_path: str = None):
        self.vocab: Optional[TagVocabulary] = None
        self.classifier = TagClassifier()
        self.segmenter = SceneSegmenter()
        self.character_extractor = CharacterExtractor()
        self.intensity_scorer = IntensityScorer()
        self.exhaustive_tagger = ExhaustiveTagger()  # 259 tags, 1168 keywords
        self.llm_analyzer = None

        if use_llm and llm_model_path:
            self.llm_analyzer = LLMSceneAnalyzer(llm_model_path)

        self._init_db()

    def _init_db(self):
        """Initialize results database."""
        TAG_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(TAG_DB)

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS analyzed_content (
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                analysis_json TEXT,
                word_count INTEGER,
                scene_count INTEGER,
                overall_intensity REAL,
                analyzed_at TEXT,
                PRIMARY KEY (source, item_id)
            );

            CREATE TABLE IF NOT EXISTS tag_associations (
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                confidence REAL,
                category TEXT,
                PRIMARY KEY (source, item_id, tag)
            );

            CREATE INDEX IF NOT EXISTS idx_tag ON tag_associations(tag);
            CREATE INDEX IF NOT EXISTS idx_category ON tag_associations(category);
            CREATE INDEX IF NOT EXISTS idx_confidence ON tag_associations(confidence);
        """)

        conn.commit()
        conn.close()

    def load_models(self):
        """Load trained models."""
        vocab_path = MODEL_DIR / "tag_vocabulary.pkl"
        classifier_path = MODEL_DIR / "tag_classifier.pkl"

        if vocab_path.exists():
            miner = AO3TagMiner()
            self.vocab = miner.load_vocab(vocab_path)
            print(f"Loaded vocabulary: {len(self.vocab.freeform_tags)} tags")

        if classifier_path.exists():
            self.classifier.load(classifier_path)
            print(f"Loaded classifier: {len(self.classifier.tag_centroids)} tag centroids")

    def analyze(self, text: str, item_id: str, source: str) -> ComprehensiveTagResult:
        """Perform comprehensive analysis on text using all 259 tags."""
        result = ComprehensiveTagResult(item_id=item_id, source=source)
        result.word_count = len(text.split())

        # Segment into scenes
        scenes = self.segmenter.segment(text)
        result.scene_count = len(scenes)

        # Detect POV
        result.pov = self.character_extractor.detect_pov(text)

        # EXHAUSTIVE TAXONOMY TAGGING (259 tags, 1168 keywords)
        exhaustive_results = self.exhaustive_tagger.tag_content(text)
        for category, tags in exhaustive_results.items():
            if category not in result.categories:
                result.categories[category] = []
            for tag, score in tags.items():
                result.categories[category].append(tag)
                result.predicted_tags[f"{category}:{tag}"] = score

        # Detailed consent analysis
        consent_analysis = self.exhaustive_tagger.get_consent_analysis(text)
        result.consent_analysis = consent_analysis
        if consent_analysis.get("primary"):
            result.categories["consent_primary"] = [consent_analysis["primary"]]

        # ML-based tag prediction (if trained)
        if self.classifier.tag_centroids:
            ml_tags = self.classifier.predict(text, top_k=30)
            for tag, score in ml_tags.items():
                if tag not in result.predicted_tags:
                    result.predicted_tags[tag] = score

        # Intensity scoring
        result.intensity = self.intensity_scorer.score_intensity(text)

        # Character role extraction
        result.character_roles = self.character_extractor.extract_roles(text)

        # Categorize predicted tags
        if self.vocab:
            for tag in result.predicted_tags:
                for category, tags in self.vocab.categorized.items():
                    if tag in tags:
                        if category not in result.categories:
                            result.categories[category] = []
                        result.categories[category].append(tag)

        # Scene-level analysis (sample for efficiency)
        for scene in scenes[:10]:  # Analyze up to 10 scenes
            scene_analysis = {
                "index": scene.index,
                "word_count": scene.word_count,
                "intensity": self.intensity_scorer.score_intensity(scene.text),
                "roles": self.character_extractor.extract_roles(scene.text)
            }

            # LLM analysis if available
            if self.llm_analyzer and scene.word_count > 200:
                llm_result = self.llm_analyzer.analyze_scene(scene.text)
                if llm_result:
                    scene_analysis["llm"] = llm_result

            result.scenes.append(scene_analysis)

        return result

    def save_result(self, result: ComprehensiveTagResult):
        """Save analysis result to database."""
        conn = sqlite3.connect(TAG_DB)

        # Save main record
        conn.execute("""
            INSERT OR REPLACE INTO analyzed_content
            (source, item_id, analysis_json, word_count, scene_count, overall_intensity, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result.source,
            result.item_id,
            result.to_json(),
            result.word_count,
            result.scene_count,
            result.intensity.get("overall", 0),
            datetime.now().isoformat()
        ))

        # Save tag associations
        conn.execute(
            "DELETE FROM tag_associations WHERE source = ? AND item_id = ?",
            (result.source, result.item_id)
        )

        for tag, confidence in result.predicted_tags.items():
            # Find category
            category = "uncategorized"
            for cat, tags in result.categories.items():
                if tag in tags:
                    category = cat
                    break

            conn.execute("""
                INSERT INTO tag_associations (source, item_id, tag, confidence, category)
                VALUES (?, ?, ?, ?, ?)
            """, (result.source, result.item_id, tag, confidence, category))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get analysis statistics."""
        conn = sqlite3.connect(TAG_DB)

        stats = {}

        # Total analyzed
        cursor = conn.execute("SELECT COUNT(*) FROM analyzed_content")
        stats["total_analyzed"] = cursor.fetchone()[0]

        # By source
        cursor = conn.execute("""
            SELECT source, COUNT(*), AVG(overall_intensity)
            FROM analyzed_content GROUP BY source
        """)
        stats["by_source"] = {
            row[0]: {"count": row[1], "avg_intensity": round(row[2] or 0, 2)}
            for row in cursor
        }

        # Top tags
        cursor = conn.execute("""
            SELECT tag, COUNT(*), AVG(confidence)
            FROM tag_associations
            GROUP BY tag
            ORDER BY COUNT(*) DESC
            LIMIT 50
        """)
        stats["top_tags"] = [
            {"tag": row[0], "count": row[1], "avg_confidence": round(row[2], 2)}
            for row in cursor
        ]

        # By category
        cursor = conn.execute("""
            SELECT category, COUNT(DISTINCT source || ':' || item_id)
            FROM tag_associations
            GROUP BY category
        """)
        stats["by_category"] = {row[0]: row[1] for row in cursor}

        conn.close()
        return stats


# ============================================================================
# CLI
# ============================================================================

def train_system():
    """Train the complete tagging system on AO3 data."""
    print("=" * 70)
    print("Training Advanced Content Tagging System")
    print("=" * 70)

    # Step 1: Mine AO3 vocabulary
    print("\n[1/3] Mining AO3 tag vocabulary...")
    miner = AO3TagMiner()
    vocab = miner.mine_ao3_tags()
    miner.save_vocab()

    print(f"\nVocabulary statistics:")
    print(f"  Archive warnings: {len(vocab.archive_warnings)}")
    print(f"  Freeform tags: {len(vocab.freeform_tags)}")
    for cat, tags in vocab.categorized.items():
        print(f"  {cat}: {len(tags)} tags")

    # Step 2: Train classifier
    print("\n[2/3] Training tag classifier...")
    classifier = TagClassifier()
    classifier.train(vocab)
    classifier.save()

    # Step 3: Test on sample
    print("\n[3/3] Testing on sample content...")
    tagger = AdvancedContentTagger()
    tagger.load_models()

    # Load a sample work
    conn = sqlite3.connect(AO3_DB)
    cursor = conn.execute("SELECT ao3_id FROM works WHERE downloaded = 1 LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        ao3_id = row[0]
        for f in AO3_CONTENT.glob(f"{ao3_id}*"):
            try:
                content = f.read_text(errors='ignore')
                result = tagger.analyze(content, str(ao3_id), "ao3")

                print(f"\nSample analysis for work {ao3_id}:")
                print(f"  Word count: {result.word_count}")
                print(f"  Scenes: {result.scene_count}")
                print(f"  POV: {result.pov}")
                print(f"  Top predicted tags: {list(result.predicted_tags.keys())[:10]}")
                print(f"  Intensity: {result.intensity}")
                break
            except:
                pass

    print("\n" + "=" * 70)
    print("Training complete!")
    print("=" * 70)


def analyze_source(source: str, limit: int = None):
    """Analyze content from a source."""
    print(f"Analyzing {source}...")

    tagger = AdvancedContentTagger()
    tagger.load_models()

    if source == "nifty":
        conn = sqlite3.connect(NIFTY_DB)
        cursor = conn.execute("""
            SELECT id, category FROM stories WHERE downloaded = 1
        """)
        items = cursor.fetchall()
        conn.close()

        analyzed = 0
        errors = 0

        for item_id, category in items:
            if limit and analyzed >= limit:
                break

            # Check if already analyzed
            tag_conn = sqlite3.connect(TAG_DB)
            cursor = tag_conn.execute(
                "SELECT 1 FROM analyzed_content WHERE source = 'nifty' AND item_id = ?",
                (item_id,)
            )
            if cursor.fetchone():
                tag_conn.close()
                continue
            tag_conn.close()

            # Find and load content
            try:
                content = None
                category_dir = NIFTY_CONTENT / category if category else NIFTY_CONTENT

                for f in category_dir.glob(f"{item_id}_*.json"):
                    data = json.loads(f.read_text(errors='ignore'))
                    content = data.get("content", data.get("text", ""))
                    break

                if not content:
                    for f in NIFTY_CONTENT.glob(f"*/{item_id}_*.json"):
                        data = json.loads(f.read_text(errors='ignore'))
                        content = data.get("content", data.get("text", ""))
                        break

                if content and len(content) > 500:
                    result = tagger.analyze(content, item_id, "nifty")
                    tagger.save_result(result)
                    analyzed += 1

                    if analyzed % 50 == 0:
                        print(f"  Analyzed {analyzed} stories...")

            except Exception as e:
                errors += 1

        print(f"\nComplete: {analyzed} analyzed, {errors} errors")

    elif source == "ao3":
        conn = sqlite3.connect(AO3_DB)
        cursor = conn.execute("""
            SELECT ao3_id, warnings FROM works WHERE downloaded = 1
        """)
        items = cursor.fetchall()
        conn.close()

        analyzed = 0

        for ao3_id, warnings_json in items:
            if limit and analyzed >= limit:
                break

            # Check if already analyzed
            tag_conn = sqlite3.connect(TAG_DB)
            cursor = tag_conn.execute(
                "SELECT 1 FROM analyzed_content WHERE source = 'ao3' AND item_id = ?",
                (str(ao3_id),)
            )
            if cursor.fetchone():
                tag_conn.close()
                continue
            tag_conn.close()

            # Load content
            try:
                content = None
                for f in AO3_CONTENT.glob(f"{ao3_id}*"):
                    content = f.read_text(errors='ignore')
                    break

                if content and len(content) > 500:
                    result = tagger.analyze(content, str(ao3_id), "ao3")

                    # Add archive warnings
                    if warnings_json:
                        try:
                            result.archive_warnings = json.loads(warnings_json)
                        except:
                            pass

                    tagger.save_result(result)
                    analyzed += 1

                    if analyzed % 50 == 0:
                        print(f"  Analyzed {analyzed} works...")

            except:
                pass

        print(f"\nComplete: {analyzed} analyzed")


def show_status():
    """Show analysis status."""
    tagger = AdvancedContentTagger()
    stats = tagger.get_stats()

    print("=" * 70)
    print("Advanced Content Tagger Status")
    print("=" * 70)

    print(f"\nTotal analyzed: {stats['total_analyzed']}")

    print("\nBy source:")
    for source, info in stats.get("by_source", {}).items():
        print(f"  {source}: {info['count']} items, avg intensity: {info['avg_intensity']}")

    print("\nBy category:")
    for cat, count in sorted(stats.get("by_category", {}).items()):
        print(f"  {cat}: {count}")

    print("\nTop 20 tags:")
    for tag_info in stats.get("top_tags", [])[:20]:
        print(f"  {tag_info['tag']}: {tag_info['count']} (conf: {tag_info['avg_confidence']})")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Advanced Content Tagger - Cutting Edge ML-Powered Analysis")
        print()
        print("Usage:")
        print("  python advanced_content_tagger.py train              # Train on AO3 data")
        print("  python advanced_content_tagger.py analyze <source>   # Analyze content")
        print("  python advanced_content_tagger.py status             # Show stats")
        print("  python advanced_content_tagger.py extract-vocab      # Just mine vocabulary")
        return

    cmd = sys.argv[1]

    if cmd == "train":
        train_system()
    elif cmd == "analyze":
        source = sys.argv[2] if len(sys.argv) > 2 else "nifty"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        analyze_source(source, limit)
    elif cmd == "status":
        show_status()
    elif cmd == "extract-vocab":
        miner = AO3TagMiner()
        vocab = miner.mine_ao3_tags()
        miner.save_vocab()

        print("\nTop 50 freeform tags:")
        for tag, count in sorted(vocab.freeform_tags.items(), key=lambda x: -x[1])[:50]:
            print(f"  {tag}: {count}")
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
