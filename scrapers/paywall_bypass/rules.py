"""
Rule Database - Site-specific bypass rules and community contributions.
"""

import os
import json
import sqlite3
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urlparse


@dataclass
class SiteRule:
    """Site-specific bypass rule."""
    domain: str
    method: str  # Primary bypass method
    params: Dict[str, Any]  # Method-specific parameters
    content_selector: Optional[str] = None  # CSS selector for content
    title_selector: Optional[str] = None
    author_selector: Optional[str] = None
    date_selector: Optional[str] = None
    remove_selectors: List[str] = None  # Elements to remove
    notes: Optional[str] = None
    success_rate: float = 0.0
    last_verified: Optional[str] = None
    added_by: str = "system"
    enabled: bool = True


class RuleDatabase:
    """
    Site-specific bypass rules management.

    Features:
    - SQLite storage for rules
    - Rule lookup by domain/subdomain
    - Success rate tracking
    - Community rule sharing (future)
    - Auto-learning from successful bypasses
    """

    # Built-in rules for major sites
    BUILTIN_RULES = {
        # Major US newspapers
        "nytimes.com": SiteRule(
            domain="nytimes.com",
            method="archive",
            params={"services": ["archive_today", "wayback"]},
            content_selector="section[name='articleBody']",
            notes="NYT has metered paywall, archives work well"
        ),
        "wsj.com": SiteRule(
            domain="wsj.com",
            method="googlebot",
            params={"fallback": "archive"},
            content_selector="article",
            notes="WSJ hard paywall, Googlebot sometimes works"
        ),
        "washingtonpost.com": SiteRule(
            domain="washingtonpost.com",
            method="archive",
            params={"services": ["archive_today", "google_cache"]},
            content_selector="article",
            notes="WaPo metered, archives reliable"
        ),
        "latimes.com": SiteRule(
            domain="latimes.com",
            method="cookies",
            params={},
            content_selector=".page-article-body",
            notes="LA Times uses cookie-based metering"
        ),

        # Tech/Business
        "bloomberg.com": SiteRule(
            domain="bloomberg.com",
            method="archive",
            params={"services": ["archive_today", "wayback"]},
            content_selector="article",
            notes="Bloomberg hard paywall"
        ),
        "businessinsider.com": SiteRule(
            domain="businessinsider.com",
            method="amp",
            params={"fallback": "archive"},
            content_selector=".content-lock-content",
            notes="BI uses AMP version"
        ),
        "techcrunch.com": SiteRule(
            domain="techcrunch.com",
            method="reader",
            params={},
            content_selector="article",
            notes="TC mostly free, reader mode works"
        ),
        "wired.com": SiteRule(
            domain="wired.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Wired has metered paywall"
        ),
        "arstechnica.com": SiteRule(
            domain="arstechnica.com",
            method="cookies",
            params={},
            content_selector="article",
            notes="Ars uses cookie metering"
        ),

        # Financial
        "ft.com": SiteRule(
            domain="ft.com",
            method="archive",
            params={"services": ["archive_today"]},
            content_selector="article",
            notes="FT hard paywall, archive.today best"
        ),
        "economist.com": SiteRule(
            domain="economist.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Economist hard paywall"
        ),
        "seekingalpha.com": SiteRule(
            domain="seekingalpha.com",
            method="googlebot",
            params={},
            content_selector="[data-test-id='article-content']",
            notes="SA uses registration wall, Googlebot works"
        ),
        "reuters.com": SiteRule(
            domain="reuters.com",
            method="reader",
            params={},
            content_selector="article",
            notes="Reuters mostly free"
        ),

        # UK Publications
        "thetimes.co.uk": SiteRule(
            domain="thetimes.co.uk",
            method="archive",
            params={},
            content_selector="article",
            notes="Times UK hard paywall"
        ),
        "telegraph.co.uk": SiteRule(
            domain="telegraph.co.uk",
            method="amp",
            params={"fallback": "archive"},
            content_selector="article",
            notes="Telegraph uses registration"
        ),
        "theguardian.com": SiteRule(
            domain="theguardian.com",
            method="reader",
            params={},
            content_selector="article",
            notes="Guardian free with contribution asks"
        ),

        # Entertainment/Culture
        "medium.com": SiteRule(
            domain="medium.com",
            method="archive",
            params={"services": ["archive_today", "google_cache"]},
            content_selector="article",
            notes="Medium metered, archives work"
        ),
        "theatlantic.com": SiteRule(
            domain="theatlantic.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Atlantic metered"
        ),
        "newyorker.com": SiteRule(
            domain="newyorker.com",
            method="archive",
            params={},
            content_selector="article",
            notes="New Yorker metered"
        ),
        "rollingstone.com": SiteRule(
            domain="rollingstone.com",
            method="amp",
            params={},
            content_selector="article",
            notes="RS uses AMP"
        ),

        # News aggregators
        "news.google.com": SiteRule(
            domain="news.google.com",
            method="reader",
            params={"follow_redirect": True},
            notes="Google News redirects to source"
        ),
        "apple.news": SiteRule(
            domain="apple.news",
            method="reader",
            params={"follow_redirect": True},
            notes="Apple News redirects to source"
        ),

        # Academic/Research
        "nature.com": SiteRule(
            domain="nature.com",
            method="archive",
            params={"services": ["wayback"]},
            content_selector="article",
            notes="Nature paywall for some articles"
        ),
        "sciencedirect.com": SiteRule(
            domain="sciencedirect.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Elsevier paywall"
        ),
        "ieee.org": SiteRule(
            domain="ieee.org",
            method="archive",
            params={},
            notes="IEEE paywall"
        ),

        # Regional US
        "chicagotribune.com": SiteRule(
            domain="chicagotribune.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Tribune metered"
        ),
        "bostonglobe.com": SiteRule(
            domain="bostonglobe.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Globe metered"
        ),
        "sfchronicle.com": SiteRule(
            domain="sfchronicle.com",
            method="archive",
            params={},
            content_selector="article",
            notes="Chronicle metered"
        ),

        # International
        "spiegel.de": SiteRule(
            domain="spiegel.de",
            method="archive",
            params={},
            content_selector="article",
            notes="Spiegel German news"
        ),
        "lemonde.fr": SiteRule(
            domain="lemonde.fr",
            method="archive",
            params={},
            content_selector="article",
            notes="Le Monde French news"
        ),
        "nikkei.com": SiteRule(
            domain="nikkei.com",
            method="googlebot",
            params={},
            content_selector="article",
            notes="Nikkei Japanese business"
        ),
    }

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "/tmp/paywall_rules.db"
        self._init_db()
        self._load_builtin_rules()

    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    domain TEXT PRIMARY KEY,
                    method TEXT,
                    params TEXT,
                    content_selector TEXT,
                    title_selector TEXT,
                    author_selector TEXT,
                    date_selector TEXT,
                    remove_selectors TEXT,
                    notes TEXT,
                    success_rate REAL DEFAULT 0.0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_verified TEXT,
                    added_by TEXT DEFAULT 'system',
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    url TEXT,
                    method_used TEXT,
                    success INTEGER,
                    content_length INTEGER,
                    latency_ms INTEGER,
                    timestamp TEXT,
                    error TEXT
                )
            """)

    def _load_builtin_rules(self):
        """Load built-in rules into database if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            for domain, rule in self.BUILTIN_RULES.items():
                # Check if rule exists
                cursor = conn.execute(
                    "SELECT domain FROM rules WHERE domain = ?",
                    (domain,)
                )
                if cursor.fetchone() is None:
                    self._insert_rule(conn, rule)

    def _insert_rule(self, conn: sqlite3.Connection, rule: SiteRule):
        """Insert rule into database."""
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO rules (
                domain, method, params, content_selector, title_selector,
                author_selector, date_selector, remove_selectors, notes,
                success_rate, added_by, enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.domain,
            rule.method,
            json.dumps(rule.params),
            rule.content_selector,
            rule.title_selector,
            rule.author_selector,
            rule.date_selector,
            json.dumps(rule.remove_selectors or []),
            rule.notes,
            rule.success_rate,
            rule.added_by,
            1 if rule.enabled else 0,
            now,
            now
        ))

    def get_rule(self, domain: str) -> Optional[Dict]:
        """
        Get rule for domain.

        Handles subdomain matching (e.g., 'www.nytimes.com' matches 'nytimes.com')
        """
        # Normalize domain
        domain = domain.lower().replace("www.", "")

        with sqlite3.connect(self.db_path) as conn:
            # Try exact match first
            cursor = conn.execute(
                "SELECT * FROM rules WHERE domain = ? AND enabled = 1",
                (domain,)
            )
            row = cursor.fetchone()

            if not row:
                # Try parent domain
                parts = domain.split(".")
                if len(parts) > 2:
                    parent = ".".join(parts[-2:])
                    cursor = conn.execute(
                        "SELECT * FROM rules WHERE domain = ? AND enabled = 1",
                        (parent,)
                    )
                    row = cursor.fetchone()

            if row:
                return self._row_to_dict(cursor, row)

        return None

    def _row_to_dict(self, cursor, row) -> Dict:
        """Convert database row to dictionary."""
        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))

        # Parse JSON fields
        if data.get("params"):
            data["params"] = json.loads(data["params"])
        if data.get("remove_selectors"):
            data["remove_selectors"] = json.loads(data["remove_selectors"])

        return data

    def add_rule(self, rule: SiteRule) -> bool:
        """Add or update a rule."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if exists
                cursor = conn.execute(
                    "SELECT domain FROM rules WHERE domain = ?",
                    (rule.domain,)
                )

                now = datetime.now().isoformat()

                if cursor.fetchone():
                    # Update existing
                    conn.execute("""
                        UPDATE rules SET
                            method = ?, params = ?, content_selector = ?,
                            title_selector = ?, author_selector = ?, date_selector = ?,
                            remove_selectors = ?, notes = ?, enabled = ?, updated_at = ?
                        WHERE domain = ?
                    """, (
                        rule.method,
                        json.dumps(rule.params),
                        rule.content_selector,
                        rule.title_selector,
                        rule.author_selector,
                        rule.date_selector,
                        json.dumps(rule.remove_selectors or []),
                        rule.notes,
                        1 if rule.enabled else 0,
                        now,
                        rule.domain
                    ))
                else:
                    self._insert_rule(conn, rule)

                return True
        except Exception:
            return False

    def record_attempt(
        self,
        domain: str,
        url: str,
        method: str,
        success: bool,
        content_length: int = 0,
        latency_ms: int = 0,
        error: Optional[str] = None
    ):
        """Record bypass attempt for rule learning."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Record history
                conn.execute("""
                    INSERT INTO rule_history (
                        domain, url, method_used, success, content_length,
                        latency_ms, timestamp, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    domain, url, method, 1 if success else 0,
                    content_length, latency_ms, datetime.now().isoformat(), error
                ))

                # Update rule success rate
                cursor = conn.execute("""
                    SELECT success_count, fail_count FROM rules WHERE domain = ?
                """, (domain,))
                row = cursor.fetchone()

                if row:
                    success_count, fail_count = row
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                    total = success_count + fail_count
                    rate = success_count / total if total > 0 else 0

                    conn.execute("""
                        UPDATE rules SET
                            success_count = ?, fail_count = ?, success_rate = ?,
                            last_verified = ?
                        WHERE domain = ?
                    """, (
                        success_count, fail_count, rate,
                        datetime.now().isoformat(), domain
                    ))
        except Exception:
            pass

    def learn_from_success(
        self,
        url: str,
        method: str,
        content_selector: Optional[str] = None
    ):
        """
        Learn from successful bypass to create/update rules.

        Called automatically when a bypass succeeds.
        """
        domain = urlparse(url).netloc.lower().replace("www.", "")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT domain FROM rules WHERE domain = ?",
                    (domain,)
                )

                now = datetime.now().isoformat()

                if cursor.fetchone() is None:
                    # Create new rule from successful bypass
                    conn.execute("""
                        INSERT INTO rules (
                            domain, method, params, content_selector,
                            success_rate, success_count, added_by,
                            enabled, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        domain, method, "{}", content_selector,
                        1.0, 1, "auto_learned",
                        1, now, now
                    ))
        except Exception:
            pass

    def get_all_rules(self, enabled_only: bool = True) -> List[Dict]:
        """Get all rules."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM rules"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY success_rate DESC"

            cursor = conn.execute(query)
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Get rule database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total rules
            cursor = conn.execute("SELECT COUNT(*) FROM rules")
            total_rules = cursor.fetchone()[0]

            # Enabled rules
            cursor = conn.execute("SELECT COUNT(*) FROM rules WHERE enabled = 1")
            enabled_rules = cursor.fetchone()[0]

            # Total attempts
            cursor = conn.execute("SELECT COUNT(*) FROM rule_history")
            total_attempts = cursor.fetchone()[0]

            # Successful attempts
            cursor = conn.execute("SELECT COUNT(*) FROM rule_history WHERE success = 1")
            successful = cursor.fetchone()[0]

            # Top methods
            cursor = conn.execute("""
                SELECT method, COUNT(*) as count, AVG(success) as rate
                FROM rule_history
                GROUP BY method
                ORDER BY count DESC
                LIMIT 10
            """)
            top_methods = [
                {"method": row[0], "attempts": row[1], "success_rate": row[2]}
                for row in cursor.fetchall()
            ]

            # Top domains
            cursor = conn.execute("""
                SELECT domain, success_rate, success_count + fail_count as total
                FROM rules
                WHERE total > 0
                ORDER BY total DESC
                LIMIT 10
            """)
            top_domains = [
                {"domain": row[0], "success_rate": row[1], "total_attempts": row[2]}
                for row in cursor.fetchall()
            ]

            return {
                "total_rules": total_rules,
                "enabled_rules": enabled_rules,
                "total_attempts": total_attempts,
                "successful_attempts": successful,
                "overall_success_rate": successful / total_attempts if total_attempts > 0 else 0,
                "top_methods": top_methods,
                "top_domains": top_domains,
            }

    def disable_rule(self, domain: str) -> bool:
        """Disable a rule."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE rules SET enabled = 0, updated_at = ? WHERE domain = ?",
                    (datetime.now().isoformat(), domain)
                )
                return True
        except Exception:
            return False

    def export_rules(self, filepath: str) -> bool:
        """Export all rules to JSON file."""
        try:
            rules = self.get_all_rules(enabled_only=False)
            with open(filepath, "w") as f:
                json.dump(rules, f, indent=2)
            return True
        except Exception:
            return False

    def import_rules(self, filepath: str, overwrite: bool = False) -> int:
        """
        Import rules from JSON file.

        Returns number of rules imported.
        """
        try:
            with open(filepath) as f:
                rules = json.load(f)

            imported = 0
            for rule_data in rules:
                rule = SiteRule(
                    domain=rule_data["domain"],
                    method=rule_data["method"],
                    params=rule_data.get("params", {}),
                    content_selector=rule_data.get("content_selector"),
                    title_selector=rule_data.get("title_selector"),
                    author_selector=rule_data.get("author_selector"),
                    date_selector=rule_data.get("date_selector"),
                    remove_selectors=rule_data.get("remove_selectors"),
                    notes=rule_data.get("notes"),
                    added_by="imported"
                )

                # Check if should overwrite
                existing = self.get_rule(rule.domain)
                if existing and not overwrite:
                    continue

                if self.add_rule(rule):
                    imported += 1

            return imported
        except Exception:
            return 0
