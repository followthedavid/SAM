#!/usr/bin/env python3
"""
SAM Scraper Dashboard - Standalone Web Interface
Reads from PostgreSQL AND legacy SQLite databases.
Run: python -m scraper_system.dashboard
Open: http://localhost:8080
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import urllib.request

# Import our database
from .storage.database import get_database
from .config.settings import DATA_SOURCES

# All data sources with actual data (SQLite databases)
# Spread across multiple drives due to storage constraints
LEGACY_DATABASES = {
    # === Fiction (David External) ===
    "ao3": {
        "path": "/Volumes/David External/ao3_archive/ao3_index.db",
        "table": "works",
        "count_query": "SELECT COUNT(*) FROM works",
        "downloaded_query": "SELECT COUNT(*) FROM works WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM works",
        "name": "Archive of Our Own",
        "type": "fiction",
        "emoji": "✍️",
    },
    "nifty": {
        "path": "/Volumes/David External/nifty_archive/nifty_index.db",
        "table": "stories",
        "count_query": "SELECT COUNT(*) FROM stories",
        "downloaded_query": "SELECT COUNT(*) FROM stories WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM stories WHERE word_count IS NOT NULL",
        "name": "Nifty Archive",
        "type": "fiction",
        "emoji": "📖",
    },
    "literotica": {
        "path": "/Volumes/David External/literotica_archive/literotica_index.db",
        "table": "stories",
        "count_query": "SELECT COUNT(*) FROM stories",
        "downloaded_query": "SELECT COUNT(*) FROM stories WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM stories WHERE word_count IS NOT NULL",
        "name": "Literotica",
        "type": "fiction",
        "emoji": "📚",
    },
    "ao3_roleplay": {
        "path": "/Volumes/David External/ao3_roleplay/ao3_roleplay_index.db",
        "table": "works",
        "count_query": "SELECT COUNT(*) FROM works",
        "downloaded_query": "SELECT COUNT(*) FROM works WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM works WHERE word_count IS NOT NULL",
        "name": "AO3 Roleplay",
        "type": "roleplay",
        "emoji": "🎭",
    },
    "flist": {
        "path": "/Volumes/David External/flist_archive/flist_index.db",
        "table": "characters",
        "count_query": "SELECT COUNT(*) FROM characters",
        "downloaded_query": "SELECT COUNT(*) FROM characters WHERE downloaded = 1",
        "words_query": "SELECT 0",
        "name": "F-List Characters",
        "type": "profiles",
        "emoji": "👤",
    },

    # === Photos (David External) ===
    "firstview": {
        "path": "/Volumes/David External/firstview_archive/firstview_index.db",
        "table": "photos",
        "count_query": "SELECT COUNT(*) FROM photos",
        "downloaded_query": "SELECT COUNT(*) FROM photos WHERE downloaded = 1",
        "words_query": "SELECT 0",
        "name": "Firstview",
        "type": "photos",
        "emoji": "📸",
    },

    # === Code (David External) ===
    "code": {
        "path": "/Volumes/David External/coding_training/code_collection.db",
        "table": "code_examples",
        "count_query": "SELECT COUNT(*) FROM code_examples",
        "downloaded_query": "SELECT COUNT(*) FROM code_examples",
        "words_query": "SELECT 0",
        "name": "Code Examples (GitHub + SO)",
        "type": "code",
        "emoji": "💻",
    },
    "apple_dev": {
        "path": "/Volumes/David External/apple_dev_archive/apple_dev.db",
        "table": "docs",
        "count_query": "SELECT (SELECT COUNT(*) FROM docs) + (SELECT COUNT(*) FROM github_code) + (SELECT COUNT(*) FROM stackoverflow)",
        "downloaded_query": "SELECT (SELECT COUNT(*) FROM docs) + (SELECT COUNT(*) FROM github_code) + (SELECT COUNT(*) FROM stackoverflow)",
        "words_query": "SELECT 0",
        "name": "Apple Dev (Swift/macOS)",
        "type": "code",
        "emoji": "🍎",
    },

    # === Fashion/Culture (Volume #1) ===
    "wwd": {
        "path": "/Volumes/#1/wwd_archive/wwd_index.db",
        "table": "articles",
        "count_query": "SELECT COUNT(*) FROM articles",
        "downloaded_query": "SELECT COUNT(*) FROM articles WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM articles WHERE word_count IS NOT NULL",
        "name": "Women's Wear Daily",
        "type": "fashion",
        "emoji": "👗",
    },
    "vmag": {
        "path": "/Volumes/#1/vmag_archive/vmag_index.db",
        "table": "articles",
        "count_query": "SELECT COUNT(*) FROM articles",
        "downloaded_query": "SELECT COUNT(*) FROM articles WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM articles WHERE word_count IS NOT NULL",
        "name": "V Magazine",
        "type": "fashion",
        "emoji": "👠",
    },
    "wmag": {
        "path": "/Volumes/#1/wmag_archive/wmag_index.db",
        "table": "articles",
        "count_query": "SELECT COUNT(*) FROM articles",
        "downloaded_query": "SELECT COUNT(*) FROM articles WHERE downloaded = 1",
        "words_query": "SELECT SUM(word_count) FROM articles WHERE word_count IS NOT NULL",
        "name": "W Magazine",
        "type": "fashion",
        "emoji": "👠",
    },
}


class DashboardAPI:
    """API for dashboard data"""

    # Cache settings
    CACHE_TTL = 30  # seconds - stats refresh every 30 seconds

    def __init__(self):
        # Try to connect to PostgreSQL, but don't fail if unavailable
        try:
            self.db = get_database()
        except Exception as e:
            print(f"PostgreSQL not available: {e}")
            print("Dashboard will use SQLite legacy databases only")
            self.db = None

        # Cache for stats
        self._stats_cache = None
        self._cache_time = None

    def _get_legacy_stats(self) -> dict:
        """Read stats from legacy SQLite databases."""
        legacy = {}
        for source_id, config in LEGACY_DATABASES.items():
            db_path = Path(config["path"])
            if not db_path.exists():
                continue
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Get counts
                cursor.execute(config["count_query"])
                total = cursor.fetchone()[0] or 0

                cursor.execute(config["downloaded_query"])
                downloaded = cursor.fetchone()[0] or 0

                cursor.execute(config["words_query"])
                words = cursor.fetchone()[0] or 0

                conn.close()

                legacy[source_id] = {
                    "name": config["name"],
                    "type": config.get("type", "fiction"),
                    "emoji": config.get("emoji", "📦"),
                    "enabled": True,
                    "running": self._check_running(source_id),
                    "indexed": total,
                    "downloaded": downloaded,
                    "processed": downloaded,
                    "pending": max(0, total - downloaded),
                    "bytes": 0,
                    "words": words,
                    "last_scraped": None,
                    "last_page": None,
                }
            except Exception as e:
                print(f"Error reading legacy DB {source_id}: {e}")
        return legacy

    def get_all_stats(self, force_refresh: bool = False) -> dict:
        """Get comprehensive stats for all sources (configured + with data).

        Results are cached for CACHE_TTL seconds to avoid slow external drive queries.
        """
        import time
        now = time.time()

        # Return cached stats if still valid
        if not force_refresh and self._stats_cache and self._cache_time:
            if now - self._cache_time < self.CACHE_TTL:
                return self._stats_cache

        sources = {}

        # First, add all configured scrapers from DATA_SOURCES
        for source_id, config in DATA_SOURCES.items():
            sources[source_id] = {
                "name": config.get("name", source_id),
                "type": config.get("type", "unknown"),
                "emoji": self._get_emoji(source_id),
                "enabled": config.get("enabled", False),
                "running": self._check_running(source_id),
                "indexed": 0,
                "downloaded": 0,
                "processed": 0,
                "pending": 0,
                "bytes": 0,
                "words": 0,
                "last_scraped": None,
                "last_page": None,
                "has_data": False,
            }

        # Then overlay with actual data from legacy databases
        legacy_sources = self._get_legacy_stats()
        for source_id, data in legacy_sources.items():
            if source_id in sources:
                sources[source_id].update(data)
                sources[source_id]["has_data"] = data.get("indexed", 0) > 0
            else:
                data["has_data"] = data.get("indexed", 0) > 0
                sources[source_id] = data

        # Get recent jobs (if PostgreSQL available)
        jobs = self.db.get_job_history(limit=20) if self.db else []

        # Calculate totals (including legacy)
        total_indexed = sum(s["indexed"] for s in sources.values())
        total_downloaded = sum(s["downloaded"] for s in sources.values())
        total_processed = sum(s["processed"] for s in sources.values())
        total_pending = sum(s["pending"] for s in sources.values())
        total_bytes = sum(s["bytes"] for s in sources.values())
        total_words = sum(s.get("words", 0) for s in sources.values())

        # Training estimates - use actual word counts where available
        tokens_per_word = 1.3

        # Use actual word counts if available, else estimate
        actual_words = total_words if total_words > 0 else total_downloaded * 2500

        # Build result
        result = {
            "summary": {
                "total_indexed": total_indexed,
                "total_downloaded": total_downloaded,
                "total_processed": total_processed,
                "total_pending": total_pending,
                "total_bytes": total_bytes,
                "total_words": total_words,
                "total_sources": len([s for s in sources.values() if s["indexed"] > 0]),
                "active_scrapers": len([s for s in sources.values() if s["running"]]),
                "legacy_sources": len([s for s in sources.values() if s.get("is_legacy", False)]),
            },
            "training": {
                "actual_words": total_words,
                "estimated_words": actual_words,
                "estimated_tokens": int(actual_words * tokens_per_word),
                "estimated_size_mb": total_bytes / (1024 * 1024) if total_bytes else actual_words * 6 / (1024 * 1024),
            },
            "sources": sources,
            "recent_jobs": [
                {
                    "source": j.task_name,
                    "status": j.status.value if hasattr(j.status, 'value') else str(j.status),
                    "items": j.items_scraped or 0,
                    "started": j.started_at.isoformat() if j.started_at else None,
                    "completed": j.completed_at.isoformat() if j.completed_at else None,
                    "error": j.error,
                }
                for j in (jobs or [])
            ],
            "generated_at": datetime.now().isoformat(),
            "cache_ttl": self.CACHE_TTL,
        }

        # Save to cache
        self._stats_cache = result
        self._cache_time = now

        return result

    def _check_running(self, source_id: str) -> bool:
        """Check if a scraper is currently running"""
        import subprocess
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"{source_id}"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False

    def _get_emoji(self, source_id: str) -> str:
        """Get emoji for a source."""
        emoji_map = {
            'ao3': '✍️', 'nifty': '📖', 'literotica': '📚', 'dark_psych': '🧠',
            'flist': '👤', 'reddit_rp': '🎭', 'ao3_rp': '💬', 'ao3_roleplay': '🎭',
            'wwd': '👗', 'vogue': '👠', 'wmag': '👠', 'vmag': '👗',
            'gq': '🎩', 'gq_esquire': '🎩', 'esquire': '🎩', 'thecut': '✂️',
            'interview': '🎤',
            'calcareers': '💼', 'resumes': '📄', 'coverletters': '✉️', 'soq': '📝',
            'bias_ratings': '⚖️', 'news': '📰', 'articles': '📑',
            'github': '💻', 'code': '💻', 'books': '📚',
            'firstview': '📸',
        }
        return emoji_map.get(source_id, '📦')


# HTML Dashboard Template
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAM Scraper Dashboard</title>
    <style>
        :root {
            --bg: #0f0f0f;
            --card: rgba(255,255,255,0.03);
            --card-hover: rgba(255,255,255,0.05);
            --border: rgba(255,255,255,0.08);
            --text: #f5f5f7;
            --text-dim: #86868b;
            --accent: #5e5ce6;
            --green: #30d158;
            --red: #ff453a;
            --orange: #ff9f0a;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 24px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }

        .header h1 {
            font-size: 28px;
            font-weight: 600;
        }

        .header .subtitle {
            color: var(--text-dim);
            font-size: 14px;
        }

        .refresh-btn {
            padding: 10px 20px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            cursor: pointer;
            font-size: 14px;
        }

        .refresh-btn:hover { background: var(--card-hover); }

        /* Summary Cards */
        .summary-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }

        .summary-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .summary-card.highlight {
            border-color: rgba(94, 92, 230, 0.3);
        }

        .summary-emoji { font-size: 32px; }
        .summary-value { font-size: 24px; font-weight: 600; }
        .summary-label { font-size: 12px; color: var(--text-dim); text-transform: uppercase; }

        /* Scrapers Grid */
        .scrapers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }

        .scraper-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            transition: all 0.2s;
        }

        .scraper-card:hover {
            background: var(--card-hover);
            transform: translateY(-2px);
        }

        .scraper-card.active {
            border-color: rgba(48, 209, 88, 0.5);
        }

        .scraper-card.disabled {
            opacity: 0.5;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .source-info { display: flex; align-items: center; gap: 12px; }
        .source-emoji { font-size: 28px; }
        .source-name { font-size: 16px; font-weight: 600; }
        .source-type { font-size: 11px; color: var(--text-dim); text-transform: uppercase; }

        .status-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }

        .status-badge.running {
            background: rgba(48, 209, 88, 0.15);
            color: var(--green);
        }

        .status-badge.idle {
            background: rgba(142, 142, 147, 0.15);
            color: var(--text-dim);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 16px;
        }

        .stat-item {
            text-align: center;
            padding: 8px;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
        }

        .stat-number { font-size: 14px; font-weight: 600; }
        .stat-label { font-size: 9px; color: var(--text-dim); text-transform: uppercase; }

        .progress-bar {
            height: 6px;
            background: rgba(255,255,255,0.05);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), #8b5cf6);
            border-radius: 3px;
            transition: width 0.5s;
        }

        /* Training Section */
        .training-section {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 32px;
        }

        .training-section h2 {
            font-size: 18px;
            margin-bottom: 20px;
        }

        .training-cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }

        .training-card {
            text-align: center;
            padding: 20px;
        }

        .training-icon { font-size: 28px; margin-bottom: 8px; }
        .training-value { font-size: 24px; font-weight: 600; color: var(--accent); }
        .training-label { font-size: 12px; color: var(--text-dim); }

        /* Jobs Section */
        .jobs-section {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
        }

        .jobs-section h2 {
            font-size: 18px;
            margin-bottom: 20px;
        }

        .job-item {
            display: flex;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid var(--border);
            gap: 16px;
        }

        .job-item:last-child { border-bottom: none; }

        .job-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .job-status.completed { background: var(--green); }
        .job-status.failed { background: var(--red); }
        .job-status.running { background: var(--orange); animation: pulse 2s infinite; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .job-source { font-weight: 500; min-width: 120px; }
        .job-items { color: var(--text-dim); font-size: 13px; }
        .job-time { color: var(--text-dim); font-size: 12px; margin-left: auto; }

        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-dim);
        }

        .error {
            background: rgba(255, 69, 58, 0.1);
            border: 1px solid rgba(255, 69, 58, 0.3);
            border-radius: 8px;
            padding: 16px;
            color: var(--red);
            margin-bottom: 24px;
        }

        /* Live Status Section */
        .live-status {
            background: linear-gradient(135deg, rgba(94, 92, 230, 0.1), rgba(139, 92, 246, 0.1));
            border: 1px solid rgba(94, 92, 230, 0.3);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 32px;
        }

        .live-status h2 {
            font-size: 18px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .live-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--green);
            animation: pulse 2s infinite;
        }

        .live-indicator.offline {
            background: var(--text-dim);
            animation: none;
        }

        .live-grid {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 20px;
        }

        .active-scrapers {
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 16px;
        }

        .active-scraper-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid var(--border);
        }

        .active-scraper-item:last-child { border-bottom: none; }

        .scraper-info { display: flex; align-items: center; gap: 12px; }
        .scraper-progress { color: var(--text-dim); font-size: 13px; }

        .queue-list {
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 16px;
        }

        .queue-item {
            padding: 8px 12px;
            color: var(--text-dim);
            font-size: 13px;
        }

        .resource-status {
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 16px;
        }

        .resource-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }

        .resource-item:last-child { border-bottom: none; }

        .resource-label { color: var(--text-dim); font-size: 13px; }
        .resource-value { font-size: 14px; font-weight: 500; }

        .daemon-controls {
            margin-top: 16px;
            display: flex;
            gap: 12px;
        }

        .daemon-btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--card);
            color: var(--text);
            cursor: pointer;
            font-size: 13px;
        }

        .daemon-btn:hover { background: var(--card-hover); }
        .daemon-btn.primary { background: var(--accent); border-color: var(--accent); }
        .daemon-btn.primary:hover { background: #7a78f0; }

        /* Responsive */
        @media (max-width: 900px) {
            .summary-row { grid-template-columns: repeat(2, 1fr); }
            .training-cards { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 600px) {
            .summary-row { grid-template-columns: 1fr; }
            .scrapers-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>SAM Scraper Dashboard</h1>
            <p class="subtitle">Training data collection status</p>
        </div>
        <button class="refresh-btn" onclick="loadData()">Refresh</button>
    </div>

    <div id="error" class="error" style="display: none;"></div>

    <div id="live-status" class="live-status" style="display: none;">
        <h2>
            <span class="live-indicator" id="live-dot"></span>
            Live Status
        </h2>
        <div class="live-grid">
            <div class="active-scrapers">
                <strong>Active Scrapers</strong>
                <div id="active-list">-</div>
            </div>
            <div class="queue-list">
                <strong>Queue (<span id="queue-count">0</span>)</strong>
                <div id="queue-list">Empty</div>
            </div>
            <div class="resource-status">
                <strong>Resources</strong>
                <div class="resource-item">
                    <span class="resource-label">RAM</span>
                    <span class="resource-value" id="ram-value">-</span>
                </div>
                <div class="resource-item">
                    <span class="resource-label">CPU</span>
                    <span class="resource-value" id="cpu-value">-</span>
                </div>
                <div class="resource-item">
                    <span class="resource-label">Today</span>
                    <span class="resource-value" id="today-value">-</span>
                </div>
            </div>
        </div>
        <div class="daemon-controls">
            <button class="daemon-btn primary" onclick="addAllToQueue()">Add All Scrapers to Queue</button>
            <button class="daemon-btn" onclick="loadDaemonStatus()">Refresh Status</button>
        </div>
    </div>

    <div id="daemon-offline" class="live-status" style="display: none; opacity: 0.6;">
        <h2>
            <span class="live-indicator offline"></span>
            Scraper Daemon Offline
        </h2>
        <p style="color: var(--text-dim); margin-top: 10px;">
            Start the daemon to enable continuous scraping:<br>
            <code style="background: rgba(0,0,0,0.3); padding: 8px 12px; display: inline-block; margin-top: 10px; border-radius: 6px;">
                python -m scraper_system.daemon
            </code>
        </p>
    </div>

    <div id="content">
        <div class="loading">Loading...</div>
    </div>

    <script>
        const EMOJI_MAP = {
            'ao3': '✍️', 'nifty': '📖', 'literotica': '📚', 'dark_psych': '🧠',
            'flist': '👤', 'reddit_rp': '🎭', 'ao3_rp': '💬',
            'wwd': '📰', 'vogue': '👗', 'wmag': '👠', 'vmag': '👗',
            'gq': '🎩', 'esquire': '🎩', 'thecut': '✂️', 'interview': '🎤',
            'calcareers': '💼', 'resumes': '📄', 'coverletters': '✉️', 'soq': '📝',
            'bias_ratings': '⚖️', 'news': '📰', 'articles': '📑',
            'github': '💻', 'books': '📚',
        };

        function formatNumber(n) {
            if (n >= 1000000000) return (n / 1000000000).toFixed(1) + 'B';
            if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
            if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
            return n.toString();
        }

        function formatBytes(bytes) {
            if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
            if (bytes >= 1048576) return (bytes / 1048576).toFixed(0) + ' MB';
            if (bytes >= 1024) return (bytes / 1024).toFixed(0) + ' KB';
            return bytes + ' B';
        }

        function formatTime(iso) {
            if (!iso) return '-';
            const d = new Date(iso);
            const now = new Date();
            const diff = (now - d) / 1000;
            if (diff < 60) return 'just now';
            if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
            if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
            return Math.floor(diff / 86400) + 'd ago';
        }

        function render(data) {
            const s = data.summary;
            const t = data.training;

            let html = `
                <div class="summary-row">
                    <div class="summary-card">
                        <span class="summary-emoji">📚</span>
                        <div>
                            <div class="summary-value">${formatNumber(s.total_indexed)}</div>
                            <div class="summary-label">Indexed</div>
                        </div>
                    </div>
                    <div class="summary-card">
                        <span class="summary-emoji">⬇️</span>
                        <div>
                            <div class="summary-value">${formatNumber(s.total_downloaded)}</div>
                            <div class="summary-label">Downloaded</div>
                        </div>
                    </div>
                    <div class="summary-card">
                        <span class="summary-emoji">⏳</span>
                        <div>
                            <div class="summary-value">${formatNumber(s.total_pending)}</div>
                            <div class="summary-label">Pending</div>
                        </div>
                    </div>
                    <div class="summary-card highlight">
                        <span class="summary-emoji">🧠</span>
                        <div>
                            <div class="summary-value">${formatNumber(s.total_processed)}</div>
                            <div class="summary-label">Processed</div>
                        </div>
                    </div>
                </div>

                <div class="scrapers-grid">
            `;

            // Sort sources: running first, then by indexed count
            const sortedSources = Object.entries(data.sources)
                .sort((a, b) => {
                    if (a[1].running !== b[1].running) return b[1].running - a[1].running;
                    return b[1].indexed - a[1].indexed;
                });

            for (const [id, src] of sortedSources) {
                const emoji = EMOJI_MAP[id] || '📦';
                const progress = src.indexed > 0 ? (src.downloaded / src.indexed * 100) : 0;
                const cardClass = src.running ? 'active' : (src.enabled ? '' : 'disabled');

                html += `
                    <div class="scraper-card ${cardClass}">
                        <div class="card-header">
                            <div class="source-info">
                                <span class="source-emoji">${emoji}</span>
                                <div>
                                    <div class="source-name">${src.name}</div>
                                    <div class="source-type">${src.type}</div>
                                </div>
                            </div>
                            <span class="status-badge ${src.running ? 'running' : 'idle'}">
                                ${src.running ? '● Active' : 'Idle'}
                            </span>
                        </div>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-number">${formatNumber(src.indexed)}</div>
                                <div class="stat-label">Indexed</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">${formatNumber(src.downloaded)}</div>
                                <div class="stat-label">Downloaded</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">${formatNumber(src.pending)}</div>
                                <div class="stat-label">Pending</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">${formatNumber(src.processed)}</div>
                                <div class="stat-label">Processed</div>
                            </div>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress.toFixed(1)}%"></div>
                        </div>
                    </div>
                `;
            }

            html += `</div>

                <div class="training-section">
                    <h2>🧠 Training Data Estimates</h2>
                    <div class="training-cards">
                        <div class="training-card">
                            <div class="training-icon">📝</div>
                            <div class="training-value">${formatNumber(t.estimated_words)}</div>
                            <div class="training-label">Words</div>
                        </div>
                        <div class="training-card">
                            <div class="training-icon">🎯</div>
                            <div class="training-value">${formatNumber(t.estimated_tokens)}</div>
                            <div class="training-label">Tokens</div>
                        </div>
                        <div class="training-card">
                            <div class="training-icon">💾</div>
                            <div class="training-value">${formatBytes(t.estimated_size_mb * 1048576)}</div>
                            <div class="training-label">Size</div>
                        </div>
                        <div class="training-card">
                            <div class="training-icon">📊</div>
                            <div class="training-value">${s.total_sources}</div>
                            <div class="training-label">Sources</div>
                        </div>
                    </div>
                </div>

                <div class="jobs-section">
                    <h2>📋 Recent Jobs</h2>
            `;

            if (data.recent_jobs.length === 0) {
                html += '<div class="loading">No jobs yet</div>';
            } else {
                for (const job of data.recent_jobs.slice(0, 10)) {
                    const statusClass = job.status === 'completed' ? 'completed' :
                                       job.status === 'failed' ? 'failed' : 'running';
                    html += `
                        <div class="job-item">
                            <div class="job-status ${statusClass}"></div>
                            <div class="job-source">${job.source}</div>
                            <div class="job-items">${job.items || 0} items</div>
                            <div class="job-time">${formatTime(job.completed || job.started)}</div>
                        </div>
                    `;
                }
            }

            html += `</div>`;

            document.getElementById('content').innerHTML = html;
        }

        async function loadData() {
            try {
                const resp = await fetch('/api/stats');
                if (!resp.ok) throw new Error('Failed to load stats');
                const data = await resp.json();
                render(data);
                document.getElementById('error').style.display = 'none';
            } catch (e) {
                document.getElementById('error').textContent = 'Error: ' + e.message;
                document.getElementById('error').style.display = 'block';
            }
        }

        // Daemon status functions
        async function loadDaemonStatus() {
            try {
                const resp = await fetch('/api/daemon');
                const data = await resp.json();

                if (data.running) {
                    document.getElementById('live-status').style.display = 'block';
                    document.getElementById('daemon-offline').style.display = 'none';

                    // Update active scrapers
                    if (data.active_scrapers && data.active_scrapers.length > 0) {
                        let activeHtml = '';
                        for (const scraper of data.active_scrapers) {
                            activeHtml += `
                                <div class="active-scraper-item">
                                    <div class="scraper-info">
                                        <span>${EMOJI_MAP[scraper.id] || '📦'}</span>
                                        <strong>${scraper.id}</strong>
                                    </div>
                                    <div class="scraper-progress">${scraper.status}</div>
                                </div>
                            `;
                        }
                        document.getElementById('active-list').innerHTML = activeHtml;
                    } else {
                        document.getElementById('active-list').innerHTML = '<div class="queue-item">Idle - no scrapers running</div>';
                    }

                    // Update queue
                    document.getElementById('queue-count').textContent = data.queue_length || 0;
                    if (data.queue && data.queue.length > 0) {
                        let queueHtml = '';
                        for (const item of data.queue.slice(0, 5)) {
                            queueHtml += `<div class="queue-item">${EMOJI_MAP[item] || '📦'} ${item}</div>`;
                        }
                        if (data.queue.length > 5) {
                            queueHtml += `<div class="queue-item">... and ${data.queue.length - 5} more</div>`;
                        }
                        document.getElementById('queue-list').innerHTML = queueHtml;
                    } else {
                        document.getElementById('queue-list').innerHTML = '<div class="queue-item">Queue empty</div>';
                    }

                    // Update resources
                    document.getElementById('ram-value').textContent = data.resources.available_ram_gb.toFixed(1) + ' GB free';
                    document.getElementById('cpu-value').textContent = data.resources.cpu_percent + '%';
                    document.getElementById('today-value').textContent = formatNumber(data.today.items) + ' items';

                } else {
                    document.getElementById('live-status').style.display = 'none';
                    document.getElementById('daemon-offline').style.display = 'block';
                }
            } catch (e) {
                document.getElementById('live-status').style.display = 'none';
                document.getElementById('daemon-offline').style.display = 'block';
            }
        }

        async function addAllToQueue() {
            try {
                const resp = await fetch('/api/daemon/add-all');
                const data = await resp.json();
                if (data.success) {
                    alert('Added all scrapers to queue!');
                    loadDaemonStatus();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            } catch (e) {
                alert('Error: ' + e.message);
            }
        }

        // Initial load
        loadData();
        loadDaemonStatus();

        // Auto-refresh
        setInterval(loadData, 30000);
        setInterval(loadDaemonStatus, 5000);  // Daemon status every 5s
    </script>
</body>
</html>
'''


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for dashboard"""

    api = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

        elif parsed.path == '/api/stats':
            try:
                stats = self.api.get_all_stats()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(stats, default=str).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif parsed.path == '/api/daemon':
            # Proxy to daemon status API
            try:
                with urllib.request.urlopen('http://localhost:8089/status', timeout=2) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
            except Exception:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"running": False, "error": "Daemon not running"}).encode())

        elif parsed.path == '/api/daemon/add-all':
            # Add all scrapers to daemon queue
            try:
                with urllib.request.urlopen('http://localhost:8089/add-all', timeout=5) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Quiet logging
        pass


def run_dashboard(port: int = 8080):
    """Run the dashboard server"""
    DashboardHandler.api = DashboardAPI()

    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"Dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        server.shutdown()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_dashboard(port)
