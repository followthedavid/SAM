#!/usr/bin/env python3
"""
SAM Environmental Impact Tracker

Tracks and accumulates the environmental impact of LLM usage over time.
Compares local (SAM) vs cloud (Claude) usage with verifiable metrics.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Environmental cost estimates (conservative, research-based)
IMPACT_ESTIMATES = {
    "claude": {
        "energy_wh_per_1k_tokens": 1.5,      # Datacenter GPU inference
        "co2_g_per_1k_tokens": 0.75,         # Average grid mix
        "water_ml_per_1k_tokens": 0.75,      # Datacenter cooling
    },
    "local": {
        "energy_wh_per_1k_tokens": 0.1,      # Apple Silicon efficiency
        "co2_g_per_1k_tokens": 0.05,         # Much lower
        "water_ml_per_1k_tokens": 0.0,       # No water cooling
    }
}

DB_PATH = Path.home() / ".sam" / "impact_tracker.db"


@dataclass
class ImpactRecord:
    id: int
    timestamp: str
    source: str  # "claude" or "local"
    tokens: int
    energy_wh: float
    co2_g: float
    water_ml: float
    query_type: str
    query_hash: str  # For deduplication tracking


class ImpactTracker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS impact_records (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tokens INTEGER NOT NULL,
                    energy_wh REAL NOT NULL,
                    co2_g REAL NOT NULL,
                    water_ml REAL NOT NULL,
                    query_type TEXT,
                    query_hash TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON impact_records(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source ON impact_records(source)
            """)

    def record_interaction(
        self,
        source: str,
        tokens: int,
        query_type: str = "unknown",
        query_hash: str = ""
    ) -> ImpactRecord:
        """Record an LLM interaction and its environmental impact."""
        estimates = IMPACT_ESTIMATES.get(source, IMPACT_ESTIMATES["local"])

        # Calculate impact
        tokens_k = tokens / 1000
        energy_wh = tokens_k * estimates["energy_wh_per_1k_tokens"]
        co2_g = tokens_k * estimates["co2_g_per_1k_tokens"]
        water_ml = tokens_k * estimates["water_ml_per_1k_tokens"]

        timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO impact_records
                (timestamp, source, tokens, energy_wh, co2_g, water_ml, query_type, query_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, source, tokens, energy_wh, co2_g, water_ml, query_type, query_hash))

            return ImpactRecord(
                id=cursor.lastrowid,
                timestamp=timestamp,
                source=source,
                tokens=tokens,
                energy_wh=energy_wh,
                co2_g=co2_g,
                water_ml=water_ml,
                query_type=query_type,
                query_hash=query_hash
            )

    def get_totals(self, since: Optional[datetime] = None) -> dict:
        """Get cumulative impact totals."""
        query = """
            SELECT
                source,
                COUNT(*) as count,
                SUM(tokens) as total_tokens,
                SUM(energy_wh) as total_energy,
                SUM(co2_g) as total_co2,
                SUM(water_ml) as total_water
            FROM impact_records
        """
        params = []

        if since:
            query += " WHERE timestamp >= ?"
            params.append(since.isoformat())

        query += " GROUP BY source"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        result = {
            "claude": {"count": 0, "tokens": 0, "energy_wh": 0, "co2_g": 0, "water_ml": 0},
            "local": {"count": 0, "tokens": 0, "energy_wh": 0, "co2_g": 0, "water_ml": 0},
        }

        for row in rows:
            source = row["source"]
            if source in result:
                result[source] = {
                    "count": row["count"],
                    "tokens": row["total_tokens"],
                    "energy_wh": round(row["total_energy"], 2),
                    "co2_g": round(row["total_co2"], 2),
                    "water_ml": round(row["total_water"], 2),
                }

        return result

    def get_savings(self, since: Optional[datetime] = None) -> dict:
        """Calculate what was saved by using local vs Claude."""
        totals = self.get_totals(since)

        # What would the local queries have cost if sent to Claude?
        local = totals["local"]
        hypothetical_claude_tokens = local["tokens"]
        tokens_k = hypothetical_claude_tokens / 1000

        hypothetical = {
            "energy_wh": tokens_k * IMPACT_ESTIMATES["claude"]["energy_wh_per_1k_tokens"],
            "co2_g": tokens_k * IMPACT_ESTIMATES["claude"]["co2_g_per_1k_tokens"],
            "water_ml": tokens_k * IMPACT_ESTIMATES["claude"]["water_ml_per_1k_tokens"],
        }

        actual_local = {
            "energy_wh": local["energy_wh"],
            "co2_g": local["co2_g"],
            "water_ml": local["water_ml"],
        }

        return {
            "queries_handled_locally": local["count"],
            "tokens_processed_locally": local["tokens"],
            "energy_saved_wh": round(hypothetical["energy_wh"] - actual_local["energy_wh"], 2),
            "co2_saved_g": round(hypothetical["co2_g"] - actual_local["co2_g"], 2),
            "water_saved_ml": round(hypothetical["water_ml"] - actual_local["water_ml"], 2),
        }

    def get_today_summary(self) -> dict:
        """Get today's impact summary."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        totals = self.get_totals(since=today)
        savings = self.get_savings(since=today)

        return {
            "date": today.strftime("%Y-%m-%d"),
            "local_queries": totals["local"]["count"],
            "claude_queries": totals["claude"]["count"],
            "local_rate": self._calc_rate(totals),
            "totals": totals,
            "savings": savings,
        }

    def get_all_time_summary(self) -> dict:
        """Get all-time impact summary."""
        totals = self.get_totals()
        savings = self.get_savings()

        # Get date range
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT MIN(timestamp) as first, MAX(timestamp) as last, COUNT(*) as total
                FROM impact_records
            """).fetchone()

        return {
            "first_record": row[0],
            "last_record": row[1],
            "total_interactions": row[2],
            "local_queries": totals["local"]["count"],
            "claude_queries": totals["claude"]["count"],
            "local_rate": self._calc_rate(totals),
            "totals": totals,
            "savings": savings,
            "environmental_equivalents": self._get_equivalents(savings),
        }

    def _calc_rate(self, totals: dict) -> float:
        """Calculate local handling rate."""
        total = totals["local"]["count"] + totals["claude"]["count"]
        if total == 0:
            return 0.0
        return round(totals["local"]["count"] / total * 100, 1)

    def _get_equivalents(self, savings: dict) -> dict:
        """Convert savings to real-world equivalents."""
        energy_kwh = savings["energy_saved_wh"] / 1000
        co2_kg = savings["co2_saved_g"] / 1000
        water_l = savings["water_saved_ml"] / 1000

        return {
            "smartphone_charges": round(energy_kwh * 10, 1),  # ~0.1 kWh per charge
            "led_hours": round(energy_kwh * 100, 1),          # ~0.01 kWh per hour
            "driving_km_avoided": round(co2_kg / 0.12, 1),    # ~0.12 kg CO2/km
            "water_bottles": round(water_l * 2, 1),           # 500ml bottles
        }

    def export_data(self, filepath: Path) -> None:
        """Export all data to JSON for verification."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM impact_records ORDER BY timestamp").fetchall()

        data = {
            "export_date": datetime.now().isoformat(),
            "methodology": IMPACT_ESTIMATES,
            "records": [dict(row) for row in rows],
            "summary": self.get_all_time_summary(),
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def format_summary(summary: dict) -> str:
    """Format summary for display."""
    lines = [
        "=" * 50,
        "SAM Environmental Impact Summary",
        "=" * 50,
        "",
        f"Period: {summary.get('date', 'All Time')}",
        f"Local queries: {summary['local_queries']}",
        f"Claude queries: {summary['claude_queries']}",
        f"Local handling rate: {summary['local_rate']}%",
        "",
        "--- Resources Used ---",
        f"  Energy: {summary['totals']['local']['energy_wh'] + summary['totals']['claude']['energy_wh']:.1f} Wh",
        f"  CO2: {summary['totals']['local']['co2_g'] + summary['totals']['claude']['co2_g']:.1f} g",
        f"  Water: {summary['totals']['claude']['water_ml']:.1f} mL",
        "",
        "--- Saved by Using SAM ---",
        f"  Energy: {summary['savings']['energy_saved_wh']:.1f} Wh",
        f"  CO2: {summary['savings']['co2_saved_g']:.1f} g",
        f"  Water: {summary['savings']['water_saved_ml']:.1f} mL",
    ]

    if "environmental_equivalents" in summary:
        eq = summary["environmental_equivalents"]
        lines.extend([
            "",
            "--- Real-World Equivalents ---",
            f"  Smartphone charges saved: {eq['smartphone_charges']}",
            f"  LED bulb hours: {eq['led_hours']}",
            f"  Driving km avoided: {eq['driving_km_avoided']}",
            f"  Water bottles saved: {eq['water_bottles']}",
        ])

    lines.append("=" * 50)
    return "\n".join(lines)


# CLI interface
if __name__ == "__main__":
    import sys

    tracker = ImpactTracker()

    if len(sys.argv) < 2:
        print("Usage: python impact_tracker.py [today|all|record|export]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "today":
        summary = tracker.get_today_summary()
        print(format_summary(summary))

    elif cmd == "all":
        summary = tracker.get_all_time_summary()
        print(format_summary(summary))

    elif cmd == "record":
        if len(sys.argv) < 4:
            print("Usage: python impact_tracker.py record <source> <tokens>")
            print("  source: 'claude' or 'local'")
            print("  tokens: number of tokens")
            sys.exit(1)

        source = sys.argv[2]
        tokens = int(sys.argv[3])
        record = tracker.record_interaction(source, tokens)
        print(f"Recorded: {source}, {tokens} tokens")
        print(f"  Energy: {record.energy_wh:.3f} Wh")
        print(f"  CO2: {record.co2_g:.3f} g")
        print(f"  Water: {record.water_ml:.3f} mL")

    elif cmd == "export":
        filepath = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("impact_export.json")
        tracker.export_data(filepath)
        print(f"Exported to {filepath}")

    else:
        print(f"Unknown command: {cmd}")
