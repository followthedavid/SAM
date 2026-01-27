#!/usr/bin/env python3
"""
SAM Progress Dashboard - Quick health check for all systems
Run: python3 check_progress.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

def get_escalation_trend():
    """Check if escalation rate is decreasing."""
    db_path = Path.home() / ".sam/escalation_learning.db"
    if not db_path.exists():
        return None, "No escalation data yet"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get last 14 days
    cur.execute("""
        SELECT date, local_handled, escalated
        FROM daily_stats
        ORDER BY date DESC
        LIMIT 14
    """)
    rows = cur.fetchall()
    conn.close()

    if len(rows) < 2:
        return None, "Need more data"

    # Calculate trend
    recent_week = rows[:7]
    older_week = rows[7:14] if len(rows) >= 14 else rows[7:]

    def calc_rate(data):
        total_local = sum(r[1] or 0 for r in data)
        total_escalated = sum(r[2] or 0 for r in data)
        total = total_local + total_escalated
        return total_local / total if total > 0 else 0

    recent_rate = calc_rate(recent_week)
    older_rate = calc_rate(older_week) if older_week else recent_rate

    improvement = recent_rate - older_rate

    return {
        "current_local_rate": recent_rate,
        "previous_local_rate": older_rate,
        "improvement": improvement,
        "trending": "📈 IMPROVING" if improvement > 0.05 else "📊 STABLE" if improvement > -0.05 else "📉 NEEDS ATTENTION"
    }, None

def get_perpetual_daemon_status():
    """Check perpetual daemon learning."""
    db_path = Path.home() / ".sam/perpetual_ladder.db"
    if not db_path.exists():
        return None, "Perpetual daemon not initialized"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'success'")
    successes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
    failures = cur.fetchone()[0]

    cur.execute("SELECT project_id, current_level FROM evolution ORDER BY current_level DESC LIMIT 5")
    levels = cur.fetchall()

    conn.close()

    total = successes + failures
    success_rate = successes / total if total > 0 else 0

    return {
        "total_tasks": total,
        "success_rate": success_rate,
        "top_projects": levels
    }, None

def get_training_data_status():
    """Check training data collection."""
    sources = []

    # Nifty
    nifty_db = Path("/Volumes/David External/nifty_archive/nifty_index.db")
    if nifty_db.exists():
        conn = sqlite3.connect(nifty_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM stories WHERE downloaded = 1")
        downloaded = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM stories")
        total = cur.fetchone()[0]
        conn.close()
        sources.append(("Nifty", downloaded, total))

    # AO3
    ao3_db = Path("/Volumes/David External/ao3_archive/ao3_index.db")
    if ao3_db.exists():
        conn = sqlite3.connect(ao3_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM works WHERE downloaded = 1")
        downloaded = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM works")
        total = cur.fetchone()[0]
        conn.close()
        sources.append(("AO3", downloaded, total))

    # Escalation training data
    esc_training = Path.home() / ".sam/escalation_training.jsonl"
    if esc_training.exists():
        with open(esc_training) as f:
            esc_count = sum(1 for _ in f)
        sources.append(("Escalations", esc_count, "∞"))

    return sources

def main():
    print("\n" + "═" * 60)
    print("  SAM PROGRESS DASHBOARD")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("═" * 60)

    # Escalation Learning
    print("\n📊 ESCALATION LEARNING")
    print("-" * 40)
    esc_data, err = get_escalation_trend()
    if err:
        print(f"  {err}")
    else:
        print(f"  Current local handling: {esc_data['current_local_rate']*100:.1f}%")
        print(f"  Previous period: {esc_data['previous_local_rate']*100:.1f}%")
        print(f"  Change: {esc_data['improvement']*100:+.1f}%")
        print(f"  Status: {esc_data['trending']}")

    # Perpetual Daemon
    print("\n🔄 PERPETUAL IMPROVEMENT")
    print("-" * 40)
    daemon_data, err = get_perpetual_daemon_status()
    if err:
        print(f"  {err}")
    else:
        print(f"  Total tasks: {daemon_data['total_tasks']}")
        print(f"  Success rate: {daemon_data['success_rate']*100:.1f}%")
        if daemon_data['top_projects']:
            print("  Evolution levels:")
            for proj, level in daemon_data['top_projects']:
                print(f"    {proj}: Level {level}")

    # Training Data
    print("\n📚 TRAINING DATA")
    print("-" * 40)
    sources = get_training_data_status()
    for name, downloaded, total in sources:
        if isinstance(total, int):
            pct = downloaded / total * 100 if total > 0 else 0
            print(f"  {name}: {downloaded:,} / {total:,} ({pct:.1f}%)")
        else:
            print(f"  {name}: {downloaded:,} examples")

    # Overall Assessment
    print("\n" + "═" * 60)
    print("  OVERALL: ", end="")
    if esc_data and esc_data.get('improvement', 0) > 0:
        print("✅ SAM is learning! Keep it running.")
    elif esc_data:
        print("⏳ Collecting data. Need more time.")
    else:
        print("🚀 Just started. Check back in a few days.")
    print("═" * 60 + "\n")

if __name__ == "__main__":
    main()
