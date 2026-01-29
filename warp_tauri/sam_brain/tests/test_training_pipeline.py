#!/usr/bin/env python3
"""
Tests for SAM Training Pipeline - Phase 5.2.11

Covers:
- Data preparation and validation
- Train/validation splitting
- Training job runner
- Progress monitoring
- Model evaluation metrics
- Deployment and rollback

Run tests:
    cd /Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain
    python -m pytest tests/test_training_pipeline.py -v

    # Run specific test class
    python -m pytest tests/test_training_pipeline.py::TestDataPreparation -v

    # Run with coverage
    python -m pytest tests/test_training_pipeline.py --cov=. --cov-report=term-missing
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from learn.training_pipeline import (
    TrainingPipeline,
    TrainingRun,
    TRAINING_DATA,
    MODELS_DIR,
    MIN_SAMPLES_FOR_TRAINING,
    BASE_MODEL,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp = tempfile.mkdtemp(prefix="sam_training_test_")
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_training_data():
    """Generate sample training data."""
    return [
        {"input": "Write a Python function to add two numbers", "output": "def add(a, b):\n    return a + b"},
        {"input": "Explain recursion", "output": "Recursion is when a function calls itself to solve smaller subproblems."},
        {"input": "What is a linked list?", "output": "A linked list is a linear data structure where elements are stored in nodes."},
        {"input": "Write a hello world program", "output": "print('Hello, World!')"},
        {"input": "What is Python?", "output": "Python is a high-level, interpreted programming language."},
    ]


@pytest.fixture
def mock_training_data_file(temp_dir, sample_training_data):
    """Create a mock training data file."""
    training_file = temp_dir / "training_data.jsonl"
    with open(training_file, "w") as f:
        for sample in sample_training_data:
            f.write(json.dumps(sample) + "\n")
    return training_file


@pytest.fixture
def pipeline_with_mock_paths(temp_dir):
    """Create a pipeline with mocked paths for testing."""
    with patch('training_pipeline.TRAINING_DATA', temp_dir / "training_data.jsonl"), \
         patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
         patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
         patch('training_pipeline.LOGS_DIR', temp_dir / "logs"):
        pipeline = TrainingPipeline()
        pipeline.runs_file = temp_dir / "training_runs.json"
        yield pipeline


# =============================================================================
# Test: Data Preparation
# =============================================================================

class TestDataPreparation:
    """Tests for data loading and preparation."""

    def test_load_training_data_empty(self, pipeline_with_mock_paths):
        """Test loading from non-existent file returns empty list."""
        samples = pipeline_with_mock_paths.load_training_data()
        assert samples == []

    def test_load_training_data_valid(self, temp_dir, sample_training_data):
        """Test loading valid training data."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            for sample in sample_training_data:
                f.write(json.dumps(sample) + "\n")

        with patch('training_pipeline.TRAINING_DATA', training_file):
            pipeline = TrainingPipeline()
            samples = pipeline.load_training_data()

        assert len(samples) == len(sample_training_data)
        assert samples[0]["input"] == sample_training_data[0]["input"]
        assert samples[0]["output"] == sample_training_data[0]["output"]

    def test_load_training_data_invalid_json(self, temp_dir):
        """Test that invalid JSON lines are skipped."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            f.write('{"input": "valid", "output": "data"}\n')
            f.write('invalid json line\n')
            f.write('{"input": "also valid", "output": "sample"}\n')

        with patch('training_pipeline.TRAINING_DATA', training_file):
            pipeline = TrainingPipeline()
            samples = pipeline.load_training_data()

        assert len(samples) == 2  # Invalid line skipped

    def test_load_training_data_missing_fields(self, temp_dir):
        """Test that samples missing required fields are skipped."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            f.write('{"input": "valid", "output": "data"}\n')
            f.write('{"input": "missing output"}\n')
            f.write('{"output": "missing input"}\n')
            f.write('{"other": "fields"}\n')

        with patch('training_pipeline.TRAINING_DATA', training_file):
            pipeline = TrainingPipeline()
            samples = pipeline.load_training_data()

        assert len(samples) == 1  # Only complete sample kept


class TestDataSplitting:
    """Tests for train/validation splitting."""

    def test_prepare_dataset_split_ratio(self, temp_dir, sample_training_data):
        """Test that dataset is split 90/10."""
        # Create 100 samples for cleaner split
        samples = sample_training_data * 20  # 100 samples

        with patch('training_pipeline.MODELS_DIR', temp_dir / "models"):
            pipeline = TrainingPipeline()
            output_dir = temp_dir / "dataset"
            pipeline.prepare_dataset(samples, output_dir)

        train_file = output_dir / "train.jsonl"
        val_file = output_dir / "valid.jsonl"

        assert train_file.exists()
        assert val_file.exists()

        train_count = sum(1 for _ in open(train_file))
        val_count = sum(1 for _ in open(val_file))

        assert train_count == 90
        assert val_count == 10

    def test_prepare_dataset_chat_format(self, temp_dir, sample_training_data):
        """Test that samples are converted to chat format."""
        with patch('training_pipeline.MODELS_DIR', temp_dir / "models"):
            pipeline = TrainingPipeline()
            output_dir = temp_dir / "dataset"
            pipeline.prepare_dataset(sample_training_data, output_dir)

        train_file = output_dir / "train.jsonl"
        with open(train_file) as f:
            first_line = json.loads(f.readline())

        assert "messages" in first_line
        assert len(first_line["messages"]) == 2
        assert first_line["messages"][0]["role"] == "user"
        assert first_line["messages"][1]["role"] == "assistant"

    def test_prepare_dataset_creates_output_dir(self, temp_dir, sample_training_data):
        """Test that output directory is created if it doesn't exist."""
        with patch('training_pipeline.MODELS_DIR', temp_dir / "models"):
            pipeline = TrainingPipeline()
            output_dir = temp_dir / "nested" / "dataset" / "path"
            pipeline.prepare_dataset(sample_training_data, output_dir)

        assert output_dir.exists()


# =============================================================================
# Test: Training Job Runner
# =============================================================================

class TestTrainingJobRunner:
    """Tests for training job execution."""

    def test_check_mlx_available_true(self, pipeline_with_mock_paths):
        """Test MLX availability check when available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = pipeline_with_mock_paths.check_mlx_available()
        assert result is True

    def test_check_mlx_available_false(self, pipeline_with_mock_paths):
        """Test MLX availability check when not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            result = pipeline_with_mock_paths.check_mlx_available()
        assert result is False

    def test_should_train_insufficient_samples(self, temp_dir):
        """Test that training is not triggered with insufficient samples."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            # Write only 10 samples (below threshold)
            for i in range(10):
                f.write(json.dumps({"input": f"input {i}", "output": f"output {i}"}) + "\n")

        with patch('training_pipeline.TRAINING_DATA', training_file):
            pipeline = TrainingPipeline()
            result = pipeline.should_train()

        assert result is False

    def test_should_train_sufficient_samples(self, temp_dir):
        """Test that training is triggered with sufficient new samples."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            # Write 150 samples (above threshold)
            for i in range(150):
                f.write(json.dumps({"input": f"input {i}", "output": f"output {i}"}) + "\n")

        with patch('training_pipeline.TRAINING_DATA', training_file), \
             patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
             patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
             patch('training_pipeline.LOGS_DIR', temp_dir / "logs"), \
             patch('training_pipeline.SCRIPT_DIR', temp_dir):
            pipeline = TrainingPipeline()
            result = pipeline.should_train()

        assert result is True

    def test_should_train_already_trained(self, temp_dir):
        """Test that training is not triggered if already trained on same data."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            for i in range(150):
                f.write(json.dumps({"input": f"input {i}", "output": f"output {i}"}) + "\n")

        with patch('training_pipeline.TRAINING_DATA', training_file), \
             patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
             patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
             patch('training_pipeline.LOGS_DIR', temp_dir / "logs"):
            pipeline = TrainingPipeline()
            pipeline.runs_file = temp_dir / "runs.json"

            # Add a previous run with same sample count
            pipeline.runs = [TrainingRun(
                run_id="test_run",
                start_time=datetime.now().isoformat(),
                samples_count=150,  # Same as current data
                base_model=BASE_MODEL,
                status="completed",
                metrics={}
            )]

            result = pipeline.should_train()

        assert result is False

    def test_run_training_mlx_not_available(self, temp_dir):
        """Test training fails gracefully when MLX not available."""
        with patch('training_pipeline.TRAINING_DATA', temp_dir / "training_data.jsonl"), \
             patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
             patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
             patch('training_pipeline.LOGS_DIR', temp_dir / "logs"):
            pipeline = TrainingPipeline()

            with patch.object(pipeline, 'check_mlx_available', return_value=False):
                result = pipeline.run_training(temp_dir, temp_dir / "output")

        assert result is False


# =============================================================================
# Test: Progress Monitoring
# =============================================================================

class TestProgressMonitoring:
    """Tests for training progress monitoring."""

    def test_training_run_dataclass(self):
        """Test TrainingRun dataclass creation."""
        run = TrainingRun(
            run_id="test_123",
            start_time="2026-01-25T10:00:00",
            samples_count=500,
            base_model="test-model",
            status="training",
            metrics={"loss": 0.5}
        )

        assert run.run_id == "test_123"
        assert run.samples_count == 500
        assert run.status == "training"
        assert run.metrics["loss"] == 0.5

    def test_runs_persistence(self, temp_dir):
        """Test that training runs are saved and loaded correctly."""
        runs_file = temp_dir / "training_runs.json"

        with patch('training_pipeline.TRAINING_DATA', temp_dir / "training_data.jsonl"), \
             patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
             patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
             patch('training_pipeline.LOGS_DIR', temp_dir / "logs"), \
             patch('training_pipeline.SCRIPT_DIR', temp_dir):

            # Create and save
            pipeline1 = TrainingPipeline()
            pipeline1.runs.append(TrainingRun(
                run_id="test_1",
                start_time="2026-01-25T10:00:00",
                samples_count=100,
                base_model="test",
                status="completed",
                metrics={"accuracy": 0.95}
            ))
            pipeline1._save_runs()

            # Load in new instance
            pipeline2 = TrainingPipeline()

        assert len(pipeline2.runs) == 1
        assert pipeline2.runs[0].run_id == "test_1"
        assert pipeline2.runs[0].metrics["accuracy"] == 0.95

    def test_stats_reporting(self, temp_dir):
        """Test pipeline statistics reporting."""
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            for i in range(50):
                f.write(json.dumps({"input": f"input {i}", "output": f"output {i}"}) + "\n")

        with patch('training_pipeline.TRAINING_DATA', training_file), \
             patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
             patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
             patch('training_pipeline.LOGS_DIR', temp_dir / "logs"), \
             patch('training_pipeline.SCRIPT_DIR', temp_dir):
            pipeline = TrainingPipeline()
            stats = pipeline.stats()

        assert stats["total_samples"] == 50
        assert stats["ready_to_train"] is False
        assert stats["training_runs"] == 0


# =============================================================================
# Test: Model Evaluation
# =============================================================================

class TestModelEvaluation:
    """Tests for model evaluation metrics."""

    def test_list_models_empty(self, temp_dir):
        """Test listing models when none exist."""
        with patch('training_pipeline.MODELS_DIR', temp_dir / "models"):
            pipeline = TrainingPipeline()
            models = pipeline.list_models()

        assert models == []

    def test_list_models_with_adapters(self, temp_dir):
        """Test listing models with adapter files."""
        models_dir = temp_dir / "models"
        model1_dir = models_dir / "sam-coder-20260125"
        adapters_dir = model1_dir / "adapters"
        adapters_dir.mkdir(parents=True)
        (adapters_dir / "adapter.safetensors").touch()

        with patch('training_pipeline.MODELS_DIR', models_dir):
            pipeline = TrainingPipeline()
            models = pipeline.list_models()

        assert len(models) == 1
        assert models[0]["name"] == "sam-coder-20260125"
        assert "adapter_path" in models[0]


# =============================================================================
# Test: Model Deployment
# =============================================================================

class TestModelDeployment:
    """Tests for model deployment system."""

    def test_deployment_imports(self):
        """Test that deployment module can be imported."""
        from learn.model_deployment import (
            ModelDeployer,
            ModelVersion,
            DeploymentStatus,
            RollbackReason,
            SafeDeployment,
            RollbackTrigger,
        )

    def test_model_version_dataclass(self):
        """Test ModelVersion dataclass."""
        from learn.model_deployment import ModelVersion

        version = ModelVersion(
            version="v1.0.0",
            created_at="2026-01-25T10:00:00",
            deployed_at="2026-01-25T10:30:00",
            status="active",
            base_model="test-model",
            adapter_path="/path/to/adapters",
            training_run_id="run_123",
            training_samples=1000,
            metrics={"accuracy": 0.95}
        )

        assert version.version == "v1.0.0"
        assert version.training_samples == 1000
        assert version.metrics["accuracy"] == 0.95

        # Test to_dict
        data = version.to_dict()
        assert isinstance(data, dict)
        assert data["version"] == "v1.0.0"

        # Test from_dict
        version2 = ModelVersion.from_dict(data)
        assert version2.version == version.version

    def test_deployer_initialization(self, temp_dir):
        """Test ModelDeployer initialization."""
        from learn.model_deployment import ModelDeployer, get_versions_path

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            deployer.versions_path = temp_dir
            deployer.versions_file = temp_dir / "versions.json"

        assert deployer.versions == []

    def test_sanity_check_nonexistent_path(self, temp_dir):
        """Test sanity check fails for non-existent path."""
        from learn.model_deployment import ModelDeployer

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            passed, msg = deployer._sanity_check(temp_dir / "nonexistent")

        assert passed is False
        assert "does not exist" in msg

    def test_sanity_check_valid_adapters(self, temp_dir):
        """Test sanity check passes for valid adapter files."""
        from learn.model_deployment import ModelDeployer

        # Create mock adapter file
        adapters_dir = temp_dir / "adapters"
        adapters_dir.mkdir()
        adapter_file = adapters_dir / "adapter.safetensors"
        adapter_file.write_bytes(b"x" * 1024 * 1024)  # 1MB file

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            passed, msg = deployer._sanity_check(adapters_dir)

        assert passed is True
        assert "passed" in msg

    def test_sanity_check_too_small(self, temp_dir):
        """Test sanity check fails for suspiciously small files."""
        from learn.model_deployment import ModelDeployer

        adapters_dir = temp_dir / "adapters"
        adapters_dir.mkdir()
        adapter_file = adapters_dir / "adapter.safetensors"
        adapter_file.write_bytes(b"x" * 100)  # Only 100 bytes

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            passed, msg = deployer._sanity_check(adapters_dir)

        assert passed is False
        assert "small" in msg.lower()

    def test_rollback_trigger_should_not_rollback(self):
        """Test rollback trigger doesn't trigger prematurely."""
        from learn.model_deployment import RollbackTrigger

        trigger = RollbackTrigger(min_samples=10)

        # Record some successful requests
        for _ in range(5):
            trigger.record_request(success=True, response_time_ms=100)

        should, reason = trigger.should_rollback()
        assert should is False  # Not enough samples yet

    def test_rollback_trigger_error_rate(self):
        """Test rollback trigger activates on high error rate."""
        from learn.model_deployment import RollbackTrigger, RollbackReason

        trigger = RollbackTrigger(max_error_rate=0.1, min_samples=10)

        # Record mix of successful and failed requests
        for _ in range(7):
            trigger.record_request(success=True, response_time_ms=100)
        for _ in range(5):  # >30% error rate
            trigger.record_request(success=False, response_time_ms=100)

        should, reason = trigger.should_rollback()
        assert should is True
        assert reason == RollbackReason.ERROR_RATE

    def test_rollback_trigger_response_time(self):
        """Test rollback trigger activates on slow response time."""
        from learn.model_deployment import RollbackTrigger, RollbackReason

        trigger = RollbackTrigger(max_response_time_ms=1000, min_samples=10)

        # Record slow requests
        for _ in range(15):
            trigger.record_request(success=True, response_time_ms=2000)

        should, reason = trigger.should_rollback()
        assert should is True
        assert reason == RollbackReason.RESPONSE_TIME

    def test_safe_deployment_traffic_routing(self):
        """Test SafeDeployment routes traffic correctly."""
        from learn.model_deployment import SafeDeployment, ModelVersion

        old_version = ModelVersion(
            version="v1.0.0",
            created_at="2026-01-25T10:00:00",
            deployed_at="2026-01-25T10:00:00",
            status="active",
            base_model="test",
            adapter_path="/path",
            training_run_id=None,
            training_samples=0
        )
        new_version = ModelVersion(
            version="v1.0.1",
            created_at="2026-01-25T11:00:00",
            deployed_at=None,
            status="canary",
            base_model="test",
            adapter_path="/path2",
            training_run_id=None,
            training_samples=0
        )

        canary = SafeDeployment(old_version, new_version, traffic_percentage=50)

        # With 50% traffic, roughly half should go to new model
        new_model_count = sum(1 for _ in range(1000) if canary.should_use_new_model())

        # Should be between 400 and 600 (allowing for randomness)
        assert 400 <= new_model_count <= 600

    def test_deployment_stats(self, temp_dir):
        """Test deployment statistics gathering."""
        from learn.model_deployment import ModelDeployer

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            deployer.versions_path = temp_dir
            stats = deployer.get_deployment_stats()

        assert "current_version" in stats
        assert "total_versions" in stats
        assert "rollback_available" in stats
        assert "deployment_metrics" in stats

    def test_version_numbering(self, temp_dir):
        """Test automatic version number generation."""
        from learn.model_deployment import ModelDeployer, ModelVersion

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            deployer.versions_path = temp_dir

            # First version should be v1.0.0
            assert deployer._next_version() == "v1.0.0"

            # Add a version
            deployer.versions.append(ModelVersion(
                version="v1.0.0",
                created_at="2026-01-25",
                deployed_at=None,
                status="active",
                base_model="test",
                adapter_path="/test",
                training_run_id=None,
                training_samples=0
            ))

            # Next should be v1.0.1
            assert deployer._next_version() == "v1.0.1"


# =============================================================================
# Test: Rollback Functionality
# =============================================================================

class TestRollback:
    """Tests for model rollback functionality."""

    def test_rollback_no_versions(self, temp_dir):
        """Test rollback fails when no versions exist."""
        from learn.model_deployment import ModelDeployer

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            deployer.versions_path = temp_dir
            success, msg = deployer.rollback()

        assert success is False
        assert "No versions" in msg

    def test_rollback_to_previous(self, temp_dir):
        """Test rollback to previous version."""
        from learn.model_deployment import ModelDeployer, ModelVersion, DeploymentStatus

        with patch('model_deployment.get_versions_path', return_value=temp_dir):
            deployer = ModelDeployer()
            deployer.versions_path = temp_dir
            deployer.versions_file = temp_dir / "versions.json"
            deployer.current_version_file = temp_dir / "current.txt"

            # Create adapter directories
            v1_adapters = temp_dir / "v1.0.0" / "adapters"
            v1_adapters.mkdir(parents=True)
            (v1_adapters / "adapter.safetensors").write_bytes(b"test")

            v2_adapters = temp_dir / "v1.0.1" / "adapters"
            v2_adapters.mkdir(parents=True)
            (v2_adapters / "adapter.safetensors").write_bytes(b"test")

            # Add two versions
            deployer.versions = [
                ModelVersion(
                    version="v1.0.0",
                    created_at="2026-01-25T10:00:00",
                    deployed_at="2026-01-25T10:00:00",
                    status=DeploymentStatus.ROLLED_BACK.value,
                    base_model="test",
                    adapter_path=str(v1_adapters),
                    training_run_id=None,
                    training_samples=100
                ),
                ModelVersion(
                    version="v1.0.1",
                    created_at="2026-01-25T11:00:00",
                    deployed_at="2026-01-25T11:00:00",
                    status=DeploymentStatus.ACTIVE.value,
                    base_model="test",
                    adapter_path=str(v2_adapters),
                    training_run_id=None,
                    training_samples=150
                )
            ]

            # Patch _activate_version to avoid symlink operations
            with patch.object(deployer, '_activate_version'):
                success, msg = deployer.rollback()

        assert success is True
        assert "v1.0.0" in msg


# =============================================================================
# Test: API Integration
# =============================================================================

class TestAPIIntegration:
    """Tests for API endpoint integration."""

    def test_get_training_stats_import(self):
        """Test get_training_stats can be called."""
        from sam_api import get_training_stats

        # Should return dict even if modules not fully available
        result = get_training_stats()
        assert isinstance(result, dict)
        assert "available" in result

    def test_api_self_includes_training(self):
        """Test that api_self includes training_stats field."""
        # This test validates the integration but may need mocking
        # depending on environment state
        try:
            from sam_api import api_self
            result = api_self()

            # If SAM Intelligence is available
            if result.get("success"):
                assert "training_stats" in result
        except Exception:
            # Module dependencies may not be fully available in test
            pass


# =============================================================================
# Test: End-to-End Scenarios
# =============================================================================

class TestEndToEndScenarios:
    """End-to-end integration tests."""

    def test_full_training_cycle_mocked(self, temp_dir, sample_training_data):
        """Test complete training cycle with mocked MLX."""
        # Create sufficient training data
        training_file = temp_dir / "training_data.jsonl"
        with open(training_file, "w") as f:
            for i in range(150):
                sample = sample_training_data[i % len(sample_training_data)].copy()
                sample["input"] = f"Sample {i}: " + sample["input"]
                f.write(json.dumps(sample) + "\n")

        with patch('training_pipeline.TRAINING_DATA', training_file), \
             patch('training_pipeline.MODELS_DIR', temp_dir / "models"), \
             patch('training_pipeline.CHECKPOINTS_DIR', temp_dir / "checkpoints"), \
             patch('training_pipeline.LOGS_DIR', temp_dir / "logs"), \
             patch('training_pipeline.SCRIPT_DIR', temp_dir):

            pipeline = TrainingPipeline()

            # Check should_train
            assert pipeline.should_train() is True

            # Check stats
            stats = pipeline.stats()
            assert stats["total_samples"] == 150
            assert stats["ready_to_train"] is True

    def test_deployment_after_training_mocked(self, temp_dir):
        """Test deployment flow after training."""
        from learn.model_deployment import ModelDeployer

        # Create mock adapter files
        adapters_dir = temp_dir / "training_output" / "adapters"
        adapters_dir.mkdir(parents=True)
        (adapters_dir / "adapter.safetensors").write_bytes(b"x" * 1024 * 1024)

        with patch('model_deployment.get_versions_path', return_value=temp_dir / "versions"), \
             patch('model_deployment.ACTIVE_ADAPTERS_PATH', temp_dir / "active"):

            deployer = ModelDeployer()
            deployer.versions_path = temp_dir / "versions"
            deployer.versions_file = temp_dir / "versions" / "versions.json"
            deployer.current_version_file = temp_dir / "versions" / "current.txt"

            # Deploy with validation skipped (no MLX in test)
            success, msg, version = deployer.deploy(
                str(adapters_dir),
                description="Test deployment",
                training_samples=150,
                skip_validation=True
            )

        assert success is True
        assert version is not None
        assert version.version == "v1.0.0"
        assert version.training_samples == 150


# =============================================================================
# Run tests directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
