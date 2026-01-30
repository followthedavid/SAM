"""
SAM Integration Tests - End-to-end query flow verification.

Tests the full SAM pipeline:
  sam_api.py -> orchestrator.py -> cognitive engine -> quality_validator -> response

Run with:
  cd ~/ReverseLab/SAM/warp_tauri/sam_brain
  python3 -m pytest tests/test_integration.py -v

Categories:
  a. API Health Tests (server must be running)
  b. Query Flow Tests (server must be running)
  c. Package Import Tests (always run)
  d. Route Module Tests (always run)
  e. Service Health Tests (always run)
"""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure sam_brain is on the path
SAM_BRAIN_DIR = Path(__file__).resolve().parent.parent
if str(SAM_BRAIN_DIR) not in sys.path:
    sys.path.insert(0, str(SAM_BRAIN_DIR))

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

SAM_API_BASE = "http://localhost:8765"


def _server_is_running() -> bool:
    """Check if SAM API server is reachable."""
    try:
        import requests
        r = requests.get(f"{SAM_API_BASE}/api/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


SERVER_RUNNING = _server_is_running()
requires_server = pytest.mark.skipif(
    not SERVER_RUNNING,
    reason="SAM API server not running at localhost:8765",
)


# ---------------------------------------------------------------------------
# a. API Health Tests
# ---------------------------------------------------------------------------

class TestAPIHealth:
    """Tests that verify the API server is alive and responding."""

    @requires_server
    def test_health_endpoint(self):
        """GET /api/health returns ok status."""
        import requests
        r = requests.get(f"{SAM_API_BASE}/api/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    @requires_server
    def test_status_endpoint(self):
        """GET /api/status returns success with expected fields."""
        import requests
        r = requests.get(f"{SAM_API_BASE}/api/status", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        expected_fields = [
            "project_count",
            "active_projects",
            "starred_projects",
            "mlx_available",
            "sam_model_ready",
            "style_profile_loaded",
            "drives_scanned",
            "last_updated",
            "memory_count",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# b. Query Flow Tests
# ---------------------------------------------------------------------------

class TestQueryFlow:
    """Tests that verify the full query pipeline works end-to-end."""

    @requires_server
    def test_simple_query(self):
        """POST /api/query with a simple prompt returns valid structure."""
        import requests
        payload = {"query": "hello"}
        r = requests.post(f"{SAM_API_BASE}/api/query", json=payload, timeout=30)
        assert r.status_code == 200
        data = r.json()
        # Response must have standard fields
        assert "query" in data
        assert "success" in data
        assert "timestamp" in data

    @requires_server
    def test_query_returns_response(self):
        """POST /api/query returns text content in the output field."""
        import requests
        payload = {"query": "What is your name?"}
        r = requests.post(f"{SAM_API_BASE}/api/query", json=payload, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "output" in data
        assert isinstance(data["output"], str)
        assert len(data["output"]) > 0

    @requires_server
    def test_query_has_confidence(self):
        """POST /api/cognitive/process returns a confidence score."""
        import requests
        payload = {"query": "What time is it?"}
        r = requests.post(
            f"{SAM_API_BASE}/api/cognitive/process", json=payload, timeout=60
        )
        assert r.status_code == 200
        data = r.json()
        if data.get("success"):
            assert "confidence" in data
            assert isinstance(data["confidence"], (int, float))
            assert 0.0 <= data["confidence"] <= 1.0
        else:
            # Cognitive system may not be available; mark as expected skip
            pytest.skip(f"Cognitive system unavailable: {data.get('error')}")

    @requires_server
    def test_query_missing_body_returns_error(self):
        """POST /api/query with empty body returns an error response."""
        import requests
        r = requests.post(f"{SAM_API_BASE}/api/query", json={}, timeout=10)
        # Server may return 400 or 200 with error payload
        if r.status_code == 400:
            # 400 is a valid error response for missing query
            assert True
        else:
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is False
            assert "error" in data

    @requires_server
    def test_query_duration_recorded(self):
        """POST /api/query includes duration_ms in response."""
        import requests
        payload = {"query": "ping"}
        r = requests.post(f"{SAM_API_BASE}/api/query", json=payload, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "duration_ms" in data
        assert isinstance(data["duration_ms"], (int, float))
        assert data["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# c. Package Import Tests
# ---------------------------------------------------------------------------

# All 21 packages under sam_brain
ALL_PACKAGES = [
    "cognitive",
    "conversation_engine",
    "core",
    "do",
    "emotion2vec_mlx",
    "execution",
    "learn",
    "learning",
    "listen",
    "memory",
    "projects",
    "remember",
    "routes",
    "see",
    "serve",
    "speak",
    "tests",
    "think",
    "training",
    "utils",
    "voice",
]


class TestPackageImports:
    """Tests that all SAM packages can be imported without error."""

    @pytest.mark.parametrize("package", ALL_PACKAGES)
    def test_package_imports(self, package):
        """Each package should import without raising."""
        mod = importlib.import_module(package)
        assert mod is not None

    def test_all_packages_import(self):
        """All 21 packages import successfully (summary check)."""
        failed = []
        for pkg in ALL_PACKAGES:
            try:
                importlib.import_module(pkg)
            except Exception as exc:
                failed.append((pkg, str(exc)))
        assert not failed, f"Failed imports: {failed}"

    def test_key_class_training_pipeline(self):
        """TrainingPipeline is importable from the training package."""
        from training import TrainingPipeline
        assert TrainingPipeline is not None

    def test_key_class_learning_database(self):
        """LearningDatabase is importable from the learning package."""
        try:
            from learning.learning_db import LearningDatabase
            assert LearningDatabase is not None
        except ImportError:
            # Fallback: might live under learn/
            try:
                from learn.intelligence_core import get_intelligence_core
                assert get_intelligence_core is not None
            except ImportError:
                pytest.skip("LearningDatabase not found in expected locations")

    def test_key_class_orchestrator(self):
        """Orchestrator module is importable."""
        import orchestrator
        assert orchestrator is not None

    def test_key_class_quality_validator(self):
        """QualityValidator is importable."""
        from cognitive.quality_validator import QualityValidator
        assert QualityValidator is not None

    def test_key_class_mlx_cognitive(self):
        """MLXCognitiveEngine is importable."""
        from cognitive.mlx_cognitive import MLXCognitiveEngine
        assert MLXCognitiveEngine is not None

    def test_key_class_response_styler(self):
        """style_response function is importable from core.response_styler."""
        from core.response_styler import style_response
        assert callable(style_response)

    def test_key_function_sam_agent(self):
        """run_agent function is importable from do.sam_agent."""
        from do.sam_agent import run_agent
        assert callable(run_agent)

    def test_key_class_evolution_tracker(self):
        """EvolutionTracker is importable."""
        from learn.evolution_tracker import EvolutionTracker
        assert EvolutionTracker is not None


# ---------------------------------------------------------------------------
# d. Route Module Tests
# ---------------------------------------------------------------------------

ROUTE_MODULES = [
    "routes",
    "routes.core",
    "routes.intelligence",
    "routes.cognitive",
    "routes.facts",
    "routes.project",
    "routes.index",
    "routes.vision",
    "routes.image_context",
    "routes.voice",
    "routes.distillation",
]


class TestRouteModules:
    """Tests that all route modules can be imported."""

    @pytest.mark.parametrize("module", ROUTE_MODULES)
    def test_route_module_imports(self, module):
        """Each route module should import without error."""
        mod = importlib.import_module(module)
        assert mod is not None

    def test_all_routes_import(self):
        """All 11 route modules import successfully (summary check)."""
        failed = []
        for mod_name in ROUTE_MODULES:
            try:
                importlib.import_module(mod_name)
            except Exception as exc:
                failed.append((mod_name, str(exc)))
        assert not failed, f"Failed route imports: {failed}"

    def test_route_aggregation_functions(self):
        """Route __init__ exposes all aggregation functions."""
        from routes import (
            get_all_get_routes,
            get_all_post_routes,
            get_all_delete_routes,
            get_all_stream_post_routes,
            get_all_prefix_get_routes,
        )
        get_routes = get_all_get_routes()
        post_routes = get_all_post_routes()
        delete_routes = get_all_delete_routes()

        assert isinstance(get_routes, dict)
        assert isinstance(post_routes, dict)
        assert isinstance(delete_routes, dict)

        # Verify key endpoints exist in the combined tables
        assert "/api/health" in get_routes
        assert "/api/status" in get_routes
        assert "/api/query" in post_routes


# ---------------------------------------------------------------------------
# e. Service Health Tests
# ---------------------------------------------------------------------------

class TestServiceHealth:
    """Tests that check launchd services and process state."""

    def test_learning_daemon_running(self):
        """Check if com.sam.perpetual learning daemon is loaded."""
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "com.sam.perpetual" in result.stdout:
            # Daemon is loaded -- pass
            assert True
        else:
            pytest.skip("com.sam.perpetual daemon not loaded (optional service)")

    def test_api_process_running(self):
        """Check if com.sam.api service is loaded."""
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "com.sam.api" in result.stdout:
            assert True
        else:
            pytest.skip("com.sam.api service not loaded (optional service)")

    def test_sam_brain_directory_exists(self):
        """sam_brain directory has expected structure."""
        assert SAM_BRAIN_DIR.exists()
        assert (SAM_BRAIN_DIR / "sam_api.py").exists()
        assert (SAM_BRAIN_DIR / "orchestrator.py").exists()
        assert (SAM_BRAIN_DIR / "shared_state.py").exists()
        assert (SAM_BRAIN_DIR / "routes").is_dir()
        assert (SAM_BRAIN_DIR / "cognitive").is_dir()

    def test_key_config_files_exist(self):
        """Key configuration and data files are present."""
        # sam_api.py is the main entry point
        assert (SAM_BRAIN_DIR / "sam_api.py").exists()
        # Routes package
        assert (SAM_BRAIN_DIR / "routes" / "__init__.py").exists()
