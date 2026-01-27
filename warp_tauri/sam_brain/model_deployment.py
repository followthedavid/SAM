#!/usr/bin/env python3
"""
SAM Model Deployment System - Phase 5.2

Handles safe deployment and rollback of fine-tuned models with:
- Version tracking and metadata
- Sanity checks before deployment
- Safe model swapping with minimal downtime
- Automatic rollback on degradation
- Canary releases for gradual rollout

Storage: /Volumes/David External/SAM_models/versions/

Usage:
    # Deploy a new model
    python model_deployment.py deploy /path/to/new/adapters --dry-run
    python model_deployment.py deploy /path/to/new/adapters

    # List versions
    python model_deployment.py list

    # Rollback to previous version
    python model_deployment.py rollback

    # Rollback to specific version
    python model_deployment.py rollback v1.0.0

    # Get current version
    python model_deployment.py current

    # Start canary deployment
    python model_deployment.py canary /path/to/adapters --traffic 10
"""

import os
import sys
import json
import shutil
import time
import psutil
import hashlib
import threading
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

# Version storage - external drive is primary
EXTERNAL_VERSIONS_PATH = Path("/Volumes/David External/SAM_models/versions")
LOCAL_VERSIONS_PATH = Path.home() / ".sam" / "models" / "versions"

# Active model symlink location
ACTIVE_MODEL_PATH = Path.home() / ".sam" / "models" / "sam-brain-active"
ACTIVE_ADAPTERS_PATH = Path.home() / ".sam" / "models" / "sam-brain-lora" / "adapters"

# Base model reference
BASE_MODEL = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"


def get_versions_path() -> Path:
    """Get the appropriate versions path, preferring external drive."""
    if EXTERNAL_VERSIONS_PATH.parent.exists():
        EXTERNAL_VERSIONS_PATH.mkdir(parents=True, exist_ok=True)
        return EXTERNAL_VERSIONS_PATH
    else:
        LOCAL_VERSIONS_PATH.mkdir(parents=True, exist_ok=True)
        return LOCAL_VERSIONS_PATH


class DeploymentStatus(Enum):
    """Status of a deployment operation."""
    PENDING = "pending"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    CANARY = "canary"  # Partial rollout


class RollbackReason(Enum):
    """Reasons for automatic rollback."""
    MANUAL = "manual"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    MEMORY_EXCEEDED = "memory_exceeded"
    VALIDATION_FAILED = "validation_failed"
    SANITY_CHECK_FAILED = "sanity_check_failed"


@dataclass
class ModelVersion:
    """Metadata for a deployed model version."""
    version: str
    created_at: str
    deployed_at: Optional[str]
    status: str
    base_model: str
    adapter_path: str
    training_run_id: Optional[str]
    training_samples: int
    metrics: Dict[str, float] = field(default_factory=dict)
    checksum: Optional[str] = None
    description: str = ""
    deployed_by: str = "automated"
    rollback_reason: Optional[str] = None
    canary_percentage: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelVersion':
        return cls(**data)


@dataclass
class DeploymentMetrics:
    """Metrics tracked during deployment for rollback decisions."""
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    requests_processed: int = 0
    errors_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


class RollbackTrigger:
    """Monitors metrics and triggers automatic rollback if thresholds exceeded."""

    def __init__(
        self,
        max_error_rate: float = 0.15,  # 15% error rate triggers rollback
        max_response_time_ms: float = 5000.0,  # 5 second response time
        max_memory_mb: float = 6000.0,  # 6GB memory (for 8GB system)
        min_samples: int = 10  # Minimum requests before checking
    ):
        self.max_error_rate = max_error_rate
        self.max_response_time_ms = max_response_time_ms
        self.max_memory_mb = max_memory_mb
        self.min_samples = min_samples

        # Tracking
        self.errors = 0
        self.successes = 0
        self.response_times: List[float] = []
        self.memory_samples: List[float] = []
        self._lock = threading.Lock()

    def record_request(self, success: bool, response_time_ms: float):
        """Record a request outcome."""
        with self._lock:
            if success:
                self.successes += 1
            else:
                self.errors += 1
            self.response_times.append(response_time_ms)

            # Keep only last 100 samples
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]

    def record_memory(self, memory_mb: float):
        """Record memory usage sample."""
        with self._lock:
            self.memory_samples.append(memory_mb)
            if len(self.memory_samples) > 20:
                self.memory_samples = self.memory_samples[-20:]

    def get_metrics(self) -> DeploymentMetrics:
        """Get current metrics."""
        with self._lock:
            total = self.errors + self.successes
            error_rate = self.errors / total if total > 0 else 0.0
            avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
            avg_memory = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0.0

            return DeploymentMetrics(
                error_rate=error_rate,
                avg_response_time_ms=avg_time,
                memory_usage_mb=avg_memory,
                requests_processed=total,
                errors_count=self.errors
            )

    def should_rollback(self) -> Tuple[bool, Optional[RollbackReason]]:
        """Check if rollback should be triggered."""
        with self._lock:
            total = self.errors + self.successes

            # Not enough samples yet
            if total < self.min_samples:
                return False, None

            # Check error rate
            error_rate = self.errors / total
            if error_rate > self.max_error_rate:
                return True, RollbackReason.ERROR_RATE

            # Check response time
            if self.response_times:
                avg_time = sum(self.response_times) / len(self.response_times)
                if avg_time > self.max_response_time_ms:
                    return True, RollbackReason.RESPONSE_TIME

            # Check memory
            if self.memory_samples:
                avg_memory = sum(self.memory_samples) / len(self.memory_samples)
                if avg_memory > self.max_memory_mb:
                    return True, RollbackReason.MEMORY_EXCEEDED

            return False, None

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.errors = 0
            self.successes = 0
            self.response_times = []
            self.memory_samples = []


class SafeDeployment:
    """
    Canary deployment handler for gradual rollout.
    Routes a percentage of traffic to the new model.
    """

    def __init__(
        self,
        old_version: ModelVersion,
        new_version: ModelVersion,
        traffic_percentage: int = 10
    ):
        self.old_version = old_version
        self.new_version = new_version
        self.traffic_percentage = traffic_percentage
        self.trigger = RollbackTrigger()
        self.active = True
        self._lock = threading.Lock()

    def should_use_new_model(self) -> bool:
        """Determine if this request should use the new model."""
        if not self.active:
            return False
        return random.randint(1, 100) <= self.traffic_percentage

    def increase_traffic(self, increment: int = 10):
        """Increase canary traffic percentage."""
        with self._lock:
            self.traffic_percentage = min(100, self.traffic_percentage + increment)

    def promote_to_full(self):
        """Promote canary to full deployment (100% traffic)."""
        with self._lock:
            self.traffic_percentage = 100
            self.active = False  # No longer canary, fully deployed

    def stop(self):
        """Stop canary deployment."""
        self.active = False


class ModelDeployer:
    """
    Model deployment manager with version control and safe rollback.

    Features:
    - Version tracking with metadata
    - Sanity checks before deployment
    - Automatic rollback on degradation
    - Canary releases for gradual rollout
    - Checksum validation
    """

    def __init__(self):
        self.versions_path = get_versions_path()
        self.versions_file = self.versions_path / "versions.json"
        self.current_version_file = self.versions_path / "current.txt"
        self.versions: List[ModelVersion] = self._load_versions()
        self.canary: Optional[SafeDeployment] = None
        self.rollback_trigger = RollbackTrigger()

    def _load_versions(self) -> List[ModelVersion]:
        """Load version history from disk."""
        if self.versions_file.exists():
            try:
                data = json.loads(self.versions_file.read_text())
                return [ModelVersion.from_dict(v) for v in data]
            except Exception as e:
                print(f"Warning: Could not load versions: {e}")
        return []

    def _save_versions(self):
        """Save version history to disk."""
        self.versions_path.mkdir(parents=True, exist_ok=True)
        data = [v.to_dict() for v in self.versions]
        self.versions_file.write_text(json.dumps(data, indent=2))

    def _compute_checksum(self, path: Path) -> str:
        """Compute SHA256 checksum of adapter files."""
        hasher = hashlib.sha256()

        if path.is_file():
            hasher.update(path.read_bytes())
        elif path.is_dir():
            for file in sorted(path.rglob("*")):
                if file.is_file():
                    hasher.update(file.read_bytes())

        return hasher.hexdigest()[:16]

    def _next_version(self) -> str:
        """Generate next version number."""
        if not self.versions:
            return "v1.0.0"

        latest = self.versions[-1].version
        parts = latest.lstrip('v').split('.')
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            return f"v{major}.{minor}.{patch + 1}"
        except (IndexError, ValueError):
            # Fallback to timestamp-based version
            return f"v{datetime.now().strftime('%Y%m%d.%H%M%S')}"

    def _sanity_check(self, adapter_path: Path) -> Tuple[bool, str]:
        """
        Perform sanity checks on adapter files before deployment.

        Returns:
            Tuple of (passed: bool, message: str)
        """
        # Check path exists
        if not adapter_path.exists():
            return False, f"Adapter path does not exist: {adapter_path}"

        # Check for required files
        if adapter_path.is_dir():
            # Look for safetensors or npz files
            adapter_files = list(adapter_path.glob("*.safetensors")) + list(adapter_path.glob("*.npz"))
            if not adapter_files:
                return False, "No adapter files (*.safetensors, *.npz) found"
        elif not adapter_path.suffix in ['.safetensors', '.npz']:
            return False, f"Unexpected adapter file format: {adapter_path.suffix}"

        # Check file size (adapters should be 1MB - 1GB typically)
        total_size = 0
        if adapter_path.is_dir():
            for f in adapter_path.rglob("*"):
                if f.is_file():
                    total_size += f.stat().st_size
        else:
            total_size = adapter_path.stat().st_size

        size_mb = total_size / (1024 * 1024)
        if size_mb < 0.1:
            return False, f"Adapter files suspiciously small: {size_mb:.2f}MB"
        if size_mb > 2000:
            return False, f"Adapter files suspiciously large: {size_mb:.2f}MB"

        return True, f"Sanity check passed. Adapter size: {size_mb:.2f}MB"

    def _validate_model(self, adapter_path: Path) -> Tuple[bool, str]:
        """
        Validate that the model can be loaded and generates coherent output.

        Returns:
            Tuple of (valid: bool, message: str)
        """
        try:
            # Try to import MLX and load
            from mlx_lm import load, generate

            # Load with adapters
            model, tokenizer = load(BASE_MODEL, adapter_path=str(adapter_path))

            # Test generation with a simple prompt
            test_prompt = "What is 2 + 2?"
            messages = [{"role": "user", "content": test_prompt}]
            formatted = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False
            )

            # Generate short response
            response = generate(
                model, tokenizer,
                prompt=formatted,
                max_tokens=50,
                verbose=False
            )

            # Basic validation - response should contain something meaningful
            if not response or len(response.strip()) < 5:
                return False, "Model generated empty or very short response"

            # Check for obvious garbage
            if response.count(response[0]) > len(response) * 0.9:
                return False, "Model generated repetitive garbage"

            return True, f"Validation passed. Sample response: {response[:100]}..."

        except ImportError:
            return False, "MLX not available for validation"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    def deploy(
        self,
        adapter_path: str,
        description: str = "",
        training_run_id: Optional[str] = None,
        training_samples: int = 0,
        metrics: Optional[Dict[str, float]] = None,
        dry_run: bool = False,
        skip_validation: bool = False
    ) -> Tuple[bool, str, Optional[ModelVersion]]:
        """
        Deploy a new model version.

        Args:
            adapter_path: Path to adapter files
            description: Human-readable description
            training_run_id: ID of the training run that produced this model
            training_samples: Number of training samples used
            metrics: Evaluation metrics from training
            dry_run: If True, validate but don't actually deploy
            skip_validation: If True, skip model loading validation

        Returns:
            Tuple of (success: bool, message: str, version: ModelVersion or None)
        """
        adapter_path = Path(adapter_path)

        # Sanity checks
        passed, message = self._sanity_check(adapter_path)
        if not passed:
            return False, f"Sanity check failed: {message}", None

        print(f"Sanity check: {message}")

        # Validation (load model and test)
        if not skip_validation:
            print("Validating model...")
            valid, message = self._validate_model(adapter_path)
            if not valid:
                return False, f"Validation failed: {message}", None
            print(f"Validation: {message}")

        if dry_run:
            return True, "Dry run passed all checks", None

        # Create version
        version_str = self._next_version()
        checksum = self._compute_checksum(adapter_path)

        # Copy adapters to versioned storage
        version_dir = self.versions_path / version_str
        version_dir.mkdir(parents=True, exist_ok=True)

        target_adapter_dir = version_dir / "adapters"
        if adapter_path.is_dir():
            shutil.copytree(adapter_path, target_adapter_dir, dirs_exist_ok=True)
        else:
            target_adapter_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(adapter_path, target_adapter_dir / adapter_path.name)

        # Create version record
        version = ModelVersion(
            version=version_str,
            created_at=datetime.now().isoformat(),
            deployed_at=datetime.now().isoformat(),
            status=DeploymentStatus.ACTIVE.value,
            base_model=BASE_MODEL,
            adapter_path=str(target_adapter_dir),
            training_run_id=training_run_id,
            training_samples=training_samples,
            metrics=metrics or {},
            checksum=checksum,
            description=description
        )

        # Update active model symlink/copy
        self._activate_version(version)

        # Mark previous version as rolled back
        for v in self.versions:
            if v.status == DeploymentStatus.ACTIVE.value:
                v.status = DeploymentStatus.ROLLED_BACK.value

        self.versions.append(version)
        self._save_versions()

        # Save current version pointer
        self.current_version_file.write_text(version_str)

        # Reset rollback trigger for new deployment
        self.rollback_trigger.reset()

        return True, f"Successfully deployed {version_str}", version

    def _activate_version(self, version: ModelVersion):
        """Activate a version by updating the active adapters."""
        source_path = Path(version.adapter_path)

        # Remove existing active adapters
        if ACTIVE_ADAPTERS_PATH.exists():
            if ACTIVE_ADAPTERS_PATH.is_symlink():
                ACTIVE_ADAPTERS_PATH.unlink()
            else:
                shutil.rmtree(ACTIVE_ADAPTERS_PATH, ignore_errors=True)

        # Create parent directory if needed
        ACTIVE_ADAPTERS_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Create symlink or copy
        try:
            ACTIVE_ADAPTERS_PATH.symlink_to(source_path)
        except OSError:
            # Symlink failed (maybe cross-filesystem), copy instead
            shutil.copytree(source_path, ACTIVE_ADAPTERS_PATH)

    def rollback(self, target_version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Rollback to a previous version.

        Args:
            target_version: Specific version to rollback to, or None for previous

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.versions:
            return False, "No versions available for rollback"

        # Find target version
        if target_version:
            target = None
            for v in self.versions:
                if v.version == target_version:
                    target = v
                    break
            if not target:
                return False, f"Version {target_version} not found"
        else:
            # Find the most recent non-active version
            active_versions = [v for v in self.versions if v.status == DeploymentStatus.ACTIVE.value]
            if not active_versions:
                return False, "No active version to rollback from"

            current = active_versions[-1]
            previous_versions = [v for v in self.versions if v.version != current.version]
            if not previous_versions:
                return False, "No previous version to rollback to"

            target = previous_versions[-1]

        # Validate target adapter path exists
        if not Path(target.adapter_path).exists():
            return False, f"Adapter files missing for {target.version}"

        # Mark current as rolled back
        for v in self.versions:
            if v.status == DeploymentStatus.ACTIVE.value:
                v.status = DeploymentStatus.ROLLED_BACK.value
                v.rollback_reason = RollbackReason.MANUAL.value

        # Activate target
        target.status = DeploymentStatus.ACTIVE.value
        target.deployed_at = datetime.now().isoformat()
        self._activate_version(target)

        self._save_versions()
        self.current_version_file.write_text(target.version)

        # Reset rollback trigger
        self.rollback_trigger.reset()

        return True, f"Rolled back to {target.version}"

    def auto_rollback_if_needed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if automatic rollback should be triggered and perform it.

        Returns:
            Tuple of (rollback_performed: bool, reason: str or None)
        """
        should_rollback, reason = self.rollback_trigger.should_rollback()

        if not should_rollback:
            return False, None

        # Find previous version
        active_versions = [v for v in self.versions if v.status == DeploymentStatus.ACTIVE.value]
        if not active_versions:
            return False, None

        current = active_versions[-1]
        previous_versions = [v for v in self.versions if v.version != current.version]
        if not previous_versions:
            return False, None

        # Mark current with rollback reason
        current.status = DeploymentStatus.ROLLED_BACK.value
        current.rollback_reason = reason.value if reason else RollbackReason.MANUAL.value

        # Activate previous
        target = previous_versions[-1]
        target.status = DeploymentStatus.ACTIVE.value
        target.deployed_at = datetime.now().isoformat()
        self._activate_version(target)

        self._save_versions()
        self.current_version_file.write_text(target.version)

        # Reset trigger
        self.rollback_trigger.reset()

        return True, reason.value if reason else "manual"

    def start_canary(
        self,
        adapter_path: str,
        traffic_percentage: int = 10,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Start a canary deployment.

        Args:
            adapter_path: Path to new adapter files
            traffic_percentage: Initial percentage of traffic (1-100)
            **kwargs: Additional args passed to deploy()

        Returns:
            Tuple of (success: bool, message: str)
        """
        if self.canary and self.canary.active:
            return False, "Canary deployment already in progress"

        # Deploy as canary
        success, msg, version = self.deploy(
            adapter_path,
            dry_run=False,
            **kwargs
        )

        if not success or not version:
            return False, msg

        # Mark as canary
        version.status = DeploymentStatus.CANARY.value
        version.canary_percentage = traffic_percentage
        self._save_versions()

        # Get current active version
        current_versions = [v for v in self.versions
                           if v.status == DeploymentStatus.ACTIVE.value
                           and v.version != version.version]
        old_version = current_versions[-1] if current_versions else version

        # Start canary handler
        self.canary = SafeDeployment(old_version, version, traffic_percentage)

        return True, f"Started canary deployment at {traffic_percentage}% traffic"

    def promote_canary(self) -> Tuple[bool, str]:
        """Promote canary to full deployment."""
        if not self.canary or not self.canary.active:
            return False, "No active canary deployment"

        # Update version status
        for v in self.versions:
            if v.version == self.canary.new_version.version:
                v.status = DeploymentStatus.ACTIVE.value
                v.canary_percentage = 100
                v.deployed_at = datetime.now().isoformat()

        self.canary.promote_to_full()
        self._save_versions()

        return True, f"Promoted {self.canary.new_version.version} to full deployment"

    def list_versions(self) -> List[ModelVersion]:
        """Get all versions."""
        return self.versions

    def get_current_version(self) -> Optional[ModelVersion]:
        """Get the currently active version."""
        for v in reversed(self.versions):
            if v.status == DeploymentStatus.ACTIVE.value:
                return v
        return None

    def get_version(self, version_str: str) -> Optional[ModelVersion]:
        """Get a specific version by version string."""
        for v in self.versions:
            if v.version == version_str:
                return v
        return None

    def get_deployment_stats(self) -> Dict[str, Any]:
        """Get deployment statistics for /api/self endpoint."""
        current = self.get_current_version()
        metrics = self.rollback_trigger.get_metrics()

        return {
            "current_version": current.version if current else None,
            "current_deployed_at": current.deployed_at if current else None,
            "total_versions": len(self.versions),
            "active_versions": len([v for v in self.versions if v.status == DeploymentStatus.ACTIVE.value]),
            "rollback_available": len(self.versions) > 1,
            "canary_active": self.canary.active if self.canary else False,
            "canary_traffic_pct": self.canary.traffic_percentage if self.canary else 0,
            "deployment_metrics": metrics.to_dict(),
            "base_model": BASE_MODEL,
            "storage_path": str(self.versions_path),
            "using_external_storage": str(self.versions_path).startswith("/Volumes/David External"),
        }

    def record_request(self, success: bool, response_time_ms: float):
        """Record a request for rollback monitoring."""
        self.rollback_trigger.record_request(success, response_time_ms)

        # Check for canary metrics too
        if self.canary and self.canary.active:
            self.canary.trigger.record_request(success, response_time_ms)

    def record_memory(self, memory_mb: float):
        """Record memory usage for rollback monitoring."""
        self.rollback_trigger.record_memory(memory_mb)


# Singleton instance
_deployer: Optional[ModelDeployer] = None

def get_deployer() -> ModelDeployer:
    """Get the singleton ModelDeployer instance."""
    global _deployer
    if _deployer is None:
        _deployer = ModelDeployer()
    return _deployer


def main():
    """CLI interface for model deployment."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Model Deployment System")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a new model version")
    deploy_parser.add_argument("adapter_path", help="Path to adapter files")
    deploy_parser.add_argument("--description", "-d", default="", help="Description")
    deploy_parser.add_argument("--training-run", help="Training run ID")
    deploy_parser.add_argument("--samples", type=int, default=0, help="Training samples")
    deploy_parser.add_argument("--dry-run", action="store_true", help="Validate only")
    deploy_parser.add_argument("--skip-validation", action="store_true", help="Skip model validation")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to previous version")
    rollback_parser.add_argument("version", nargs="?", help="Target version (default: previous)")

    # List command
    subparsers.add_parser("list", help="List all versions")

    # Current command
    subparsers.add_parser("current", help="Show current version")

    # Stats command
    subparsers.add_parser("stats", help="Show deployment statistics")

    # Canary command
    canary_parser = subparsers.add_parser("canary", help="Start canary deployment")
    canary_parser.add_argument("adapter_path", help="Path to adapter files")
    canary_parser.add_argument("--traffic", type=int, default=10, help="Traffic percentage (1-100)")
    canary_parser.add_argument("--description", "-d", default="", help="Description")

    # Promote command
    subparsers.add_parser("promote", help="Promote canary to full deployment")

    args = parser.parse_args()
    deployer = get_deployer()

    if args.command == "deploy":
        success, msg, version = deployer.deploy(
            args.adapter_path,
            description=args.description,
            training_run_id=args.training_run,
            training_samples=args.samples,
            dry_run=args.dry_run,
            skip_validation=args.skip_validation
        )
        print(msg)
        if version:
            print(json.dumps(version.to_dict(), indent=2))
        sys.exit(0 if success else 1)

    elif args.command == "rollback":
        success, msg = deployer.rollback(args.version)
        print(msg)
        sys.exit(0 if success else 1)

    elif args.command == "list":
        versions = deployer.list_versions()
        if not versions:
            print("No versions found")
        else:
            print(f"{'Version':<12} {'Status':<12} {'Deployed':<20} {'Samples':<8} Description")
            print("-" * 80)
            for v in versions:
                deployed = v.deployed_at[:16] if v.deployed_at else "N/A"
                print(f"{v.version:<12} {v.status:<12} {deployed:<20} {v.training_samples:<8} {v.description[:30]}")

    elif args.command == "current":
        current = deployer.get_current_version()
        if current:
            print(json.dumps(current.to_dict(), indent=2))
        else:
            print("No active version")

    elif args.command == "stats":
        stats = deployer.get_deployment_stats()
        print(json.dumps(stats, indent=2))

    elif args.command == "canary":
        success, msg = deployer.start_canary(
            args.adapter_path,
            traffic_percentage=args.traffic,
            description=args.description
        )
        print(msg)
        sys.exit(0 if success else 1)

    elif args.command == "promote":
        success, msg = deployer.promote_canary()
        print(msg)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
