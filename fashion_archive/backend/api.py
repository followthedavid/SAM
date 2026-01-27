#!/usr/bin/env python3
"""
Fashion Archive - FastAPI Backend
Provides REST API for the universal Apple app and SAM integration.
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import FashionArchiveDB, import_all_sources

# ============================================================================
# CONFIGURATION
# ============================================================================

API_HOST = "0.0.0.0"
API_PORT = 8420

# ============================================================================
# MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    source: Optional[str] = None
    category: Optional[str] = None
    year: Optional[int] = None
    limit: int = 50
    offset: int = 0

class TrendRequest(BaseModel):
    terms: List[str]
    by: str = "year"  # year or month

class ContentRequest(BaseModel):
    prompt: str
    context_query: Optional[str] = None
    context_limit: int = 5

class TTSRequest(BaseModel):
    text: str
    voice: str = "Samantha"  # macOS voice
    rate: int = 180

# ============================================================================
# APP SETUP
# ============================================================================

db: FashionArchiveDB = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    db = FashionArchiveDB()
    print(f"Fashion Archive API started on port {API_PORT}")
    yield
    print("Fashion Archive API shutting down")

app = FastAPI(
    title="Fashion Archive API",
    description="API for the Fashion Archive universal app and SAM integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ARTICLE ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API health check and info."""
    stats = db.get_stats()
    return {
        "name": "Fashion Archive API",
        "status": "running",
        "total_articles": stats['total_articles'],
        "sources": [s['name'] for s in stats['by_source']]
    }

@app.get("/articles")
async def list_articles(
    source: Optional[str] = None,
    category: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(50, le=500),
    offset: int = 0
):
    """List articles with optional filters."""
    results = db.search(
        query=None,
        source=source,
        category=category,
        year=year,
        limit=limit,
        offset=offset
    )
    return {"count": len(results), "articles": results}

@app.get("/articles/{article_id}")
async def get_article(article_id: str):
    """Get a single article by ID."""
    article = db.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@app.post("/search")
async def search_articles(request: SearchRequest):
    """Full-text search with filters."""
    results = db.search(
        query=request.query,
        source=request.source,
        category=request.category,
        year=request.year,
        limit=request.limit,
        offset=request.offset
    )
    return {
        "query": request.query,
        "count": len(results),
        "articles": results
    }

@app.get("/search")
async def search_articles_get(
    q: str,
    source: Optional[str] = None,
    category: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(50, le=500),
    offset: int = 0
):
    """Full-text search (GET method for convenience)."""
    results = db.search(
        query=q,
        source=source,
        category=category,
        year=year,
        limit=limit,
        offset=offset
    )
    return {
        "query": q,
        "count": len(results),
        "articles": results
    }

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/stats")
async def get_stats():
    """Get archive statistics."""
    return db.get_stats()

@app.get("/trends/{term}")
async def get_trend(term: str, by: str = "year"):
    """Get trend data for a term over time."""
    return db.get_trends(term, by)

@app.post("/trends/compare")
async def compare_trends(request: TrendRequest):
    """Compare multiple terms over time."""
    return db.compare_terms(request.terms, request.by)

@app.get("/categories/evolution")
async def category_evolution():
    """Track category distribution over time."""
    return db.get_category_evolution()

@app.get("/authors")
async def top_authors(source: Optional[str] = None, limit: int = 50):
    """Get most prolific authors."""
    return db.get_top_authors(source, limit)

@app.get("/years")
async def available_years():
    """Get list of years with article counts."""
    stats = db.get_stats()
    return stats.get('by_year', {})

@app.get("/categories")
async def available_categories():
    """Get list of categories with article counts."""
    stats = db.get_stats()
    return stats.get('top_categories', {})

@app.get("/sources")
async def available_sources():
    """Get list of sources with article counts."""
    stats = db.get_stats()
    return stats.get('by_source', [])

# ============================================================================
# SAM INTEGRATION ENDPOINTS
# ============================================================================

@app.post("/sam/query")
async def sam_query(request: ContentRequest):
    """
    Query the archive with natural language, returns context for SAM.
    SAM can use this to answer questions about fashion history/trends.
    """
    # Search for relevant articles
    results = db.search(
        query=request.context_query or request.prompt,
        limit=request.context_limit
    )

    # Build context for SAM
    context_articles = []
    for article in results:
        context_articles.append({
            "title": article['title'],
            "source": article['source_name'],
            "date": article['publish_date'],
            "excerpt": article['content'][:500] if article.get('content') else "",
            "category": article['category']
        })

    return {
        "prompt": request.prompt,
        "context_articles": context_articles,
        "total_found": len(results),
        "suggested_response_format": "Based on the fashion archive, here's what I found..."
    }

@app.get("/sam/context/{topic}")
async def sam_context(topic: str, limit: int = 5):
    """Get context articles for a topic (simplified endpoint for SAM)."""
    results = db.search(query=topic, limit=limit)
    return {
        "topic": topic,
        "articles": [
            {
                "title": a['title'],
                "source": a['source_name'],
                "date": a['publish_date'],
                "excerpt": a['content'][:300] if a.get('content') else ""
            }
            for a in results
        ]
    }

@app.get("/sam/summary")
async def sam_summary():
    """Get archive summary for SAM's general knowledge."""
    stats = db.get_stats()
    return {
        "description": "Fashion Archive containing articles from major fashion publications",
        "total_articles": stats['total_articles'],
        "total_words": stats['total_words'],
        "sources": [s['name'] for s in stats['by_source']],
        "year_range": f"{min(stats['by_year'].keys()) if stats['by_year'] else 'N/A'} - {max(stats['by_year'].keys()) if stats['by_year'] else 'N/A'}",
        "top_categories": list(stats['top_categories'].keys())[:10],
        "capabilities": [
            "Full-text search across all articles",
            "Trend analysis by term over time",
            "Category evolution tracking",
            "Author analytics",
            "Cross-source comparison"
        ]
    }

# ============================================================================
# TEXT-TO-SPEECH ENDPOINT (macOS)
# ============================================================================

@app.post("/tts/speak")
async def speak_text(request: TTSRequest):
    """
    Use macOS 'say' command to read text aloud.
    Only works when API is running on macOS.
    """
    try:
        # Use macOS say command
        cmd = ["say", "-v", request.voice, "-r", str(request.rate), request.text[:5000]]
        subprocess.Popen(cmd)
        return {"status": "speaking", "voice": request.voice, "text_length": len(request.text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

@app.get("/tts/voices")
async def list_voices():
    """List available macOS voices."""
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
        voices = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split()
            if parts:
                voices.append(parts[0])
        return {"voices": voices}
    except Exception as e:
        return {"voices": ["Samantha", "Alex", "Victoria"], "error": str(e)}

@app.post("/tts/stop")
async def stop_speaking():
    """Stop any current speech."""
    try:
        subprocess.run(["killall", "say"], capture_output=True)
        return {"status": "stopped"}
    except:
        return {"status": "no_speech_running"}

# ============================================================================
# CONTENT GENERATION ENDPOINTS
# ============================================================================

@app.post("/generate/summary")
async def generate_summary(
    topic: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
):
    """
    Generate a summary of articles on a topic.
    Returns structured data that SAM can use to write content.
    """
    # Get relevant articles
    results = db.search(query=topic, limit=20)

    # Filter by year if specified
    if start_year or end_year:
        results = [
            r for r in results
            if r.get('publish_year') and
               (not start_year or r['publish_year'] >= start_year) and
               (not end_year or r['publish_year'] <= end_year)
        ]

    # Get trend data
    trend = db.get_trends(topic)

    return {
        "topic": topic,
        "article_count": len(results),
        "trend_data": trend,
        "key_articles": [
            {
                "title": a['title'],
                "source": a['source_name'],
                "date": a['publish_date'],
                "excerpt": a['content'][:200] if a.get('content') else ""
            }
            for a in results[:5]
        ],
        "sources_represented": list(set(a['source'] for a in results)),
        "suggested_outline": [
            f"Overview of {topic} in fashion",
            "Historical context and evolution",
            "Key moments and articles",
            "Current state and trends",
            "Analysis and insights"
        ]
    }

@app.get("/generate/report/{report_type}")
async def generate_report(report_type: str, year: Optional[int] = None):
    """
    Generate data for various report types.
    report_type: yearly, category, source, trend
    """
    stats = db.get_stats()

    if report_type == "yearly":
        return {
            "type": "yearly",
            "year": year or max(stats['by_year'].keys()) if stats['by_year'] else None,
            "data": stats['by_year'],
            "categories": db.get_category_evolution()
        }

    elif report_type == "category":
        return {
            "type": "category",
            "categories": stats['top_categories'],
            "evolution": db.get_category_evolution()
        }

    elif report_type == "source":
        return {
            "type": "source",
            "sources": stats['by_source'],
            "total_articles": stats['total_articles'],
            "total_words": stats['total_words']
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {report_type}")

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/admin/import")
async def import_articles(source: Optional[str] = None):
    """Trigger article import from scraper directories."""
    if source:
        from database import import_from_scraper, CONFIG
        config = CONFIG["sources"].get(source)
        if not config:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
        count = import_from_scraper(db, source, config["articles_path"])
        return {"source": source, "imported": count}
    else:
        results = import_all_sources(db)
        return {"imported": results, "total": sum(results.values())}

@app.post("/admin/rebuild-fts")
async def rebuild_fts():
    """Rebuild full-text search index."""
    try:
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            conn.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")
        return {"status": "rebuilt"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
