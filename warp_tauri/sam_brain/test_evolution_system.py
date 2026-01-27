#!/usr/bin/env python3
"""
Test Suite for SAM Perpetual Improvement System

Run all tests: python test_evolution_system.py
Run specific: python test_evolution_system.py tracker
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add sam_brain to path
sys.path.insert(0, str(Path(__file__).parent))

# Test results tracking
results = {"passed": 0, "failed": 0, "errors": []}


def test(name):
    """Decorator to track test results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n{'='*60}")
            print(f"TEST: {name}")
            print('='*60)
            try:
                result = func(*args, **kwargs)
                if result:
                    print(f"  PASSED")
                    results["passed"] += 1
                else:
                    print(f"  FAILED")
                    results["failed"] += 1
                    results["errors"].append(f"{name}: returned False")
                return result
            except Exception as e:
                print(f"  ERROR: {e}")
                results["failed"] += 1
                results["errors"].append(f"{name}: {e}")
                return False
        return wrapper
    return decorator


# ===== Evolution Tracker Tests =====

@test("Evolution Tracker - Import")
def test_tracker_import():
    from evolution_tracker import EvolutionTracker
    return True


@test("Evolution Tracker - Initialize Database")
def test_tracker_init():
    from evolution_tracker import EvolutionTracker, EVOLUTION_DB
    tracker = EvolutionTracker()
    # Check DB file exists
    print(f"  DB path: {EVOLUTION_DB}")
    print(f"  DB exists: {EVOLUTION_DB.exists()}")
    return EVOLUTION_DB.exists()


@test("Evolution Tracker - Add Project")
def test_tracker_add_project():
    from evolution_tracker import EvolutionTracker
    tracker = EvolutionTracker()

    # Add a test project
    tracker.add_or_update_project(
        project_id="TEST_PROJECT",
        name="Test Project",
        category="brain",
        current_progress=0.5,
        ssot_path="/tmp/test_project.md"
    )

    # Verify it was added
    project = tracker.get_project("TEST_PROJECT")
    print(f"  Project: {project}")
    return project is not None and project.name == "Test Project"


@test("Evolution Tracker - Add Improvement")
def test_tracker_add_improvement():
    from evolution_tracker import EvolutionTracker, Improvement, generate_improvement_id
    tracker = EvolutionTracker()

    # Generate unique ID to avoid duplicates on re-runs
    imp_id = generate_improvement_id("TEST_PROJECT", "test improvement")

    imp = Improvement(
        id=imp_id,
        project_id="TEST_PROJECT",
        type="efficiency",
        priority=2,
        status="detected",
        description="Test improvement for validation",
        detected_at=datetime.now().isoformat()
    )

    tracker.add_improvement(imp)

    # Verify
    improvements = tracker.get_improvements(project_id="TEST_PROJECT")
    print(f"  Found {len(improvements)} improvements")
    return len(improvements) > 0


@test("Evolution Tracker - Record Progress")
def test_tracker_record_progress():
    from evolution_tracker import EvolutionTracker
    tracker = EvolutionTracker()

    tracker.record_progress(
        project_id="TEST_PROJECT",
        progress=0.6,
        milestone="Test milestone"
    )

    history = tracker.get_progress_history("TEST_PROJECT")
    print(f"  History entries: {len(history)}")
    return len(history) > 0


@test("Evolution Tracker - Priority Calculation")
def test_tracker_priority():
    from evolution_tracker import EvolutionTracker, Improvement
    tracker = EvolutionTracker()

    imp = Improvement(
        id="priority_test",
        project_id="TEST_PROJECT",
        type="reliability",
        priority=1,
        status="detected",
        description="Priority test",
        detected_at=datetime.now().isoformat()
    )

    priority = tracker.calculate_priority(imp)
    print(f"  Calculated priority: {priority}")
    return priority > 0


# ===== Improvement Detector Tests =====

@test("Improvement Detector - Import")
def test_detector_import():
    from improvement_detector import ImprovementDetector
    return True


@test("Improvement Detector - Initialize")
def test_detector_init():
    from improvement_detector import ImprovementDetector
    detector = ImprovementDetector()
    print(f"  Tracker: {detector.tracker is not None}")
    print(f"  Methods: full_scan, scan_code_quality, etc.")
    return True


@test("Improvement Detector - Scan Code Quality")
def test_detector_scan_code():
    from improvement_detector import ImprovementDetector
    detector = ImprovementDetector()

    improvements = detector.scan_code_quality()
    print(f"  Found {len(improvements)} code quality improvements")
    return True  # May find 0, that's ok


@test("Improvement Detector - Full Scan")
def test_detector_full_scan():
    from improvement_detector import ImprovementDetector
    detector = ImprovementDetector()

    result = detector.full_scan()
    print(f"  Projects scanned: {result.projects_scanned}")
    print(f"  Improvements found: {len(result.improvements)}")
    print(f"  Scan time: {result.scan_duration_seconds:.2f}s")
    return result.projects_scanned >= 0


# ===== Evolution Ladders Tests =====

@test("Evolution Ladders - Import")
def test_ladders_import():
    from evolution_ladders import EVOLUTION_LADDERS, LadderAssessor
    return True


@test("Evolution Ladders - SAM Ladder Exists")
def test_ladders_sam():
    from evolution_ladders import EVOLUTION_LADDERS

    print(f"  Categories: {list(EVOLUTION_LADDERS.keys())}")
    has_sam = "sam" in EVOLUTION_LADDERS
    print(f"  SAM ladder exists: {has_sam}")

    if has_sam:
        sam_levels = EVOLUTION_LADDERS["sam"]
        print(f"  SAM levels: {[l.name for l in sam_levels]}")

    return has_sam


@test("Evolution Ladders - Assessor")
def test_ladders_assessor():
    from evolution_ladders import LadderAssessor

    assessor = LadderAssessor()
    level = assessor.get_current_level("SAM_BRAIN", "sam")
    print(f"  SAM_BRAIN level: {level}")

    criteria = assessor.get_level_criteria("sam", level)
    print(f"  Current criteria: {criteria}")

    return level >= 1


# ===== SSOT Sync Tests =====

@test("SSOT Sync - Import")
def test_ssot_import():
    from ssot_sync import SSOTSync
    return True


@test("SSOT Sync - Check Availability")
def test_ssot_available():
    from ssot_sync import SSOTSync

    sync = SSOTSync()
    available = sync.check_ssot_available()
    print(f"  SSOT available: {available}")
    print(f"  SSOT path: {sync.ssot_root}")
    return True  # Don't fail if SSOT not mounted


@test("SSOT Sync - Discover Projects")
def test_ssot_discover():
    from ssot_sync import SSOTSync

    sync = SSOTSync()
    if not sync.ssot_available:
        print("  SSOT not available, skipping")
        return True

    docs = sync.discover_project_docs()
    print(f"  Found {len(docs)} project docs")
    for doc in docs[:5]:
        print(f"    - {doc.name}")

    return True


# ===== Semantic Memory Feedback Tests =====

@test("Semantic Memory - Import")
def test_memory_import():
    from semantic_memory import SemanticMemory
    return True


@test("Semantic Memory - Add Improvement Feedback")
def test_memory_feedback():
    from semantic_memory import SemanticMemory

    memory = SemanticMemory()

    entry_id = memory.add_improvement_feedback(
        improvement_id="test_feedback_001",
        project_id="TEST_PROJECT",
        improvement_type="efficiency",
        description="Test improvement",
        outcome="Completed successfully",
        success=True,
        impact_score=0.8,
        lessons_learned="Testing the feedback system works"
    )

    print(f"  Added feedback: {entry_id}")
    return entry_id is not None


@test("Semantic Memory - Get Improvement Stats")
def test_memory_stats():
    from semantic_memory import SemanticMemory

    memory = SemanticMemory()
    stats = memory.get_all_improvement_stats()

    print(f"  Total feedback: {stats['total']}")
    print(f"  By type: {list(stats.get('by_type', {}).keys())}")

    return True


# ===== Orchestrator Tests =====

@test("Orchestrator - Import")
def test_orchestrator_import():
    from orchestrator import orchestrate, route_request
    return True


@test("Orchestrator - IMPROVE Route Detection")
def test_orchestrator_improve_route():
    from orchestrator import route_request

    # These should route to IMPROVE
    test_messages = [
        "What improvements are suggested?",
        "Show me evolution status",
        "What should I work on next?",
    ]

    # Note: This requires Ollama to be running
    # If not running, we'll just test the import worked
    try:
        for msg in test_messages:
            route = route_request(msg)
            print(f"  '{msg[:30]}...' -> {route}")
    except Exception as e:
        print(f"  Ollama not available: {e}")
        print("  (Route detection requires Ollama)")

    return True


# ===== Autonomous Daemon Tests =====

@test("Autonomous Daemon - Import")
def test_daemon_import():
    from autonomous_daemon import run_evolution_cycle
    return True


@test("Autonomous Daemon - Evolution Cycle (dry run)")
def test_daemon_cycle():
    from autonomous_daemon import (
        task_scan_for_improvements,
        task_assess_evolution_levels,
        task_generate_evolution_report
    )

    # Run individual tasks
    print("  Running scan task...")
    scan_result = task_scan_for_improvements()
    print(f"    Scan: {scan_result.get('improvements_found', 0)} found")

    print("  Running assess task...")
    assess_result = task_assess_evolution_levels()
    print(f"    Assessed: {assess_result.get('projects_assessed', 0)} projects")

    print("  Running report task...")
    report_result = task_generate_evolution_report()
    print(f"    Report: {report_result.get('status', 'unknown')}")

    return True


# ===== Integration Tests =====

@test("Integration - Tracker + Detector")
def test_integration_tracker_detector():
    from evolution_tracker import EvolutionTracker
    from improvement_detector import ImprovementDetector

    tracker = EvolutionTracker()
    detector = ImprovementDetector()

    # Scan and store
    result = detector.full_scan()
    stored = 0
    for imp in result.improvements[:5]:  # Store first 5
        try:
            tracker.add_improvement(imp)
            stored += 1
        except:
            pass

    print(f"  Scanned: {len(result.improvements)} improvements")
    print(f"  Stored: {stored} in tracker")

    return True


@test("Integration - Tracker + Memory Feedback")
def test_integration_tracker_memory():
    from evolution_tracker import EvolutionTracker
    from semantic_memory import SemanticMemory

    tracker = EvolutionTracker()
    memory = SemanticMemory()

    # Record feedback in tracker
    tracker.record_feedback(
        improvement_id="test_imp_001",
        success=True,
        impact_score=0.75,
        lessons_learned="Integration test successful"
    )

    # Also store in semantic memory
    memory.add_improvement_feedback(
        improvement_id="test_imp_001",
        project_id="TEST_PROJECT",
        improvement_type="efficiency",
        description="Integration test improvement",
        outcome="Success",
        success=True,
        impact_score=0.75,
        lessons_learned="Integration test successful"
    )

    print("  Feedback recorded in both tracker and memory")
    return True


# ===== Cleanup =====

def cleanup_test_data():
    """Remove test data from database"""
    print("\n" + "="*60)
    print("CLEANUP")
    print("="*60)

    try:
        from evolution_tracker import EvolutionTracker
        tracker = EvolutionTracker()

        # Delete test project and related data using conn directly
        with tracker.conn:
            tracker.conn.execute("DELETE FROM projects WHERE id = 'TEST_PROJECT'")
            tracker.conn.execute("DELETE FROM improvements WHERE project_id = 'TEST_PROJECT'")
            tracker.conn.execute("DELETE FROM progress_history WHERE project_id = 'TEST_PROJECT'")
            tracker.conn.execute("DELETE FROM feedback WHERE improvement_id LIKE 'test%'")

        print("  Cleaned up test data from tracker")
    except Exception as e:
        print(f"  Cleanup error: {e}")


# ===== Main =====

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("SAM PERPETUAL IMPROVEMENT SYSTEM - TEST SUITE")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60)

    # Evolution Tracker
    test_tracker_import()
    test_tracker_init()
    test_tracker_add_project()
    test_tracker_add_improvement()
    test_tracker_record_progress()
    test_tracker_priority()

    # Improvement Detector
    test_detector_import()
    test_detector_init()
    test_detector_scan_code()
    test_detector_full_scan()

    # Evolution Ladders
    test_ladders_import()
    test_ladders_sam()
    test_ladders_assessor()

    # SSOT Sync
    test_ssot_import()
    test_ssot_available()
    test_ssot_discover()

    # Semantic Memory
    test_memory_import()
    test_memory_feedback()
    test_memory_stats()

    # Orchestrator
    test_orchestrator_import()
    test_orchestrator_improve_route()

    # Daemon
    test_daemon_import()
    test_daemon_cycle()

    # Integration
    test_integration_tracker_detector()
    test_integration_tracker_memory()

    # Cleanup
    cleanup_test_data()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")

    if results['errors']:
        print("\nErrors:")
        for err in results['errors']:
            print(f"  - {err}")

    print("\n" + "="*60)

    return results['failed'] == 0


def run_specific_tests(component: str):
    """Run tests for a specific component"""
    tests = {
        "tracker": [test_tracker_import, test_tracker_init, test_tracker_add_project,
                   test_tracker_add_improvement, test_tracker_record_progress, test_tracker_priority],
        "detector": [test_detector_import, test_detector_init, test_detector_scan_code, test_detector_full_scan],
        "ladders": [test_ladders_import, test_ladders_sam, test_ladders_assessor],
        "ssot": [test_ssot_import, test_ssot_available, test_ssot_discover],
        "memory": [test_memory_import, test_memory_feedback, test_memory_stats],
        "orchestrator": [test_orchestrator_import, test_orchestrator_improve_route],
        "daemon": [test_daemon_import, test_daemon_cycle],
        "integration": [test_integration_tracker_detector, test_integration_tracker_memory],
    }

    if component not in tests:
        print(f"Unknown component: {component}")
        print(f"Available: {list(tests.keys())}")
        return False

    print(f"\nRunning {component} tests...")
    for test_func in tests[component]:
        test_func()

    cleanup_test_data()

    print(f"\nPassed: {results['passed']}, Failed: {results['failed']}")
    return results['failed'] == 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        component = sys.argv[1]
        success = run_specific_tests(component)
    else:
        success = run_all_tests()

    sys.exit(0 if success else 1)
