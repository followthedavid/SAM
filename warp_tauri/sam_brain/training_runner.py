#!/usr/bin/env python3
"""
SAM Training Job Runner

Phase 5.2.4 & 5.2.5: Training job orchestration and monitoring

Features:
- TrainingConfig dataclass with all hyperparameters
- Training job lifecycle management (start, stop, pause, resume)
- 8GB optimizations: gradient checkpointing, small batch + accumulation
- Memory monitoring with auto-pause
- Training metrics tracking and loss curve visualization

Optimized for 8GB M2 Mac Mini.
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("training_runner")


class TrainingStatus(Enum):
    """Training job status."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    TRAINING = "training"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TrainingConfig:
    """
    Configuration for MLX LoRA fine-tuning.

    Optimized defaults for 8GB M2 Mac Mini.
    """
    # Model
    model_name: str = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    adapter_path: Optional[str] = None  # Path to existing adapters to resume

    # LoRA configuration (memory-efficient)
    lora_layers: int = 8        # Number of layers to adapt
    lora_rank: int = 4          # Low rank for 8GB (4-8 recommended)
    lora_alpha: int = 8         # Alpha = 2 * rank typically
    lora_dropout: float = 0.05

    # Training hyperparameters (8GB optimized)
    batch_size: int = 1         # Must be 1 for 8GB
    grad_accumulation_steps: int = 4   # Effective batch = 4
    learning_rate: float = 1e-4
    num_epochs: int = 1
    max_seq_length: int = 512   # Shorter for memory
    warmup_steps: int = 10

    # Memory optimizations
    gradient_checkpointing: bool = True  # Trade compute for memory
    use_8bit_optimizer: bool = False     # Not supported in MLX yet
    max_memory_gb: float = 6.0           # Target memory usage

    # Checkpointing
    save_every_steps: int = 100
    eval_every_steps: int = 50
    log_every_steps: int = 10
    val_batches: int = 10

    # Paths
    data_dir: Optional[str] = None
    output_dir: Optional[str] = None
    log_file: Optional[str] = None

    # Auto-pause thresholds
    memory_pause_threshold_gb: float = 0.3   # Pause if free memory drops below this
    memory_resume_threshold_gb: float = 0.5  # Resume when memory is above this

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors."""
        errors = []

        if self.batch_size < 1:
            errors.append("batch_size must be >= 1")

        if self.lora_rank < 1 or self.lora_rank > 64:
            errors.append("lora_rank should be between 1 and 64")

        if self.learning_rate <= 0:
            errors.append("learning_rate must be positive")

        if self.max_seq_length < 64:
            errors.append("max_seq_length should be at least 64")

        if self.data_dir and not Path(self.data_dir).exists():
            errors.append(f"data_dir does not exist: {self.data_dir}")

        return errors


@dataclass
class TrainingMetrics:
    """Training metrics at a point in time."""
    step: int = 0
    epoch: int = 0
    train_loss: float = 0.0
    val_loss: Optional[float] = None
    learning_rate: float = 0.0
    tokens_per_second: float = 0.0
    memory_used_gb: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingJob:
    """A training job instance."""
    job_id: str
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    current_step: int = 0
    total_steps: int = 0
    current_epoch: int = 0
    best_val_loss: Optional[float] = None
    metrics_history: List[TrainingMetrics] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_epoch": self.current_epoch,
            "best_val_loss": self.best_val_loss,
            "metrics_history": [m.to_dict() for m in self.metrics_history],
            "error_message": self.error_message,
        }


class TrainingMonitor:
    """
    Monitors training progress and system resources.

    Provides:
    - Real-time metrics tracking
    - Memory usage monitoring
    - Loss curve visualization
    - ETA estimation
    """

    def __init__(self, job: TrainingJob):
        self.job = job
        self._start_time: Optional[datetime] = None
        self._step_times: List[float] = []
        self._max_history = 1000  # Keep last 1000 metrics

    def update_metrics(self, metrics: TrainingMetrics):
        """Record new metrics."""
        metrics.timestamp = datetime.now().isoformat()
        self.job.metrics_history.append(metrics)

        # Trim history if too long
        if len(self.job.metrics_history) > self._max_history:
            self.job.metrics_history = self.job.metrics_history[-self._max_history:]

        # Track best val loss
        if metrics.val_loss is not None:
            if self.job.best_val_loss is None or metrics.val_loss < self.job.best_val_loss:
                self.job.best_val_loss = metrics.val_loss

    def get_metrics(self) -> Dict[str, Any]:
        """Get current training metrics summary."""
        if not self.job.metrics_history:
            return {"status": "no_metrics"}

        latest = self.job.metrics_history[-1]

        # Calculate averages
        recent = self.job.metrics_history[-10:]
        avg_loss = sum(m.train_loss for m in recent) / len(recent)
        avg_tokens = sum(m.tokens_per_second for m in recent) / len(recent)

        return {
            "current_step": self.job.current_step,
            "total_steps": self.job.total_steps,
            "current_epoch": self.job.current_epoch,
            "train_loss": latest.train_loss,
            "val_loss": latest.val_loss,
            "best_val_loss": self.job.best_val_loss,
            "learning_rate": latest.learning_rate,
            "avg_loss_recent": avg_loss,
            "tokens_per_second": avg_tokens,
            "memory_used_gb": latest.memory_used_gb,
            "progress_percent": (self.job.current_step / self.job.total_steps * 100
                                if self.job.total_steps > 0 else 0),
        }

    def estimate_completion(self) -> Optional[Dict[str, Any]]:
        """Estimate time to completion."""
        if not self.job.metrics_history or self.job.total_steps == 0:
            return None

        if len(self.job.metrics_history) < 5:
            return {"status": "insufficient_data"}

        # Calculate average time per step from recent history
        recent = self.job.metrics_history[-50:]
        if len(recent) < 2:
            return {"status": "insufficient_data"}

        # Parse timestamps
        try:
            first_time = datetime.fromisoformat(recent[0].timestamp)
            last_time = datetime.fromisoformat(recent[-1].timestamp)
            elapsed = (last_time - first_time).total_seconds()
            steps_done = recent[-1].step - recent[0].step

            if steps_done <= 0:
                return {"status": "no_progress"}

            seconds_per_step = elapsed / steps_done
            remaining_steps = self.job.total_steps - self.job.current_step
            eta_seconds = remaining_steps * seconds_per_step

            eta_time = datetime.now() + timedelta(seconds=eta_seconds)

            return {
                "remaining_steps": remaining_steps,
                "seconds_per_step": round(seconds_per_step, 2),
                "eta_seconds": int(eta_seconds),
                "eta_formatted": str(timedelta(seconds=int(eta_seconds))),
                "eta_timestamp": eta_time.isoformat(),
            }
        except Exception as e:
            return {"status": f"error: {e}"}

    def get_loss_data(self) -> Dict[str, List[float]]:
        """Get loss data for plotting."""
        steps = []
        train_losses = []
        val_losses = []

        for m in self.job.metrics_history:
            steps.append(m.step)
            train_losses.append(m.train_loss)
            if m.val_loss is not None:
                val_losses.append(m.val_loss)
            else:
                val_losses.append(None)

        return {
            "steps": steps,
            "train_loss": train_losses,
            "val_loss": val_losses,
        }

    def plot_loss_curve(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate and save loss curve visualization.

        Returns path to saved image or None if plotting failed.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt

            data = self.get_loss_data()
            if not data["steps"]:
                return None

            fig, ax = plt.subplots(figsize=(10, 6))

            # Plot train loss
            ax.plot(data["steps"], data["train_loss"],
                   label="Train Loss", color="blue", alpha=0.7)

            # Plot val loss (filter out None values)
            val_steps = [s for s, v in zip(data["steps"], data["val_loss"]) if v is not None]
            val_losses = [v for v in data["val_loss"] if v is not None]
            if val_losses:
                ax.plot(val_steps, val_losses,
                       label="Val Loss", color="orange", alpha=0.7)

            ax.set_xlabel("Step")
            ax.set_ylabel("Loss")
            ax.set_title(f"Training Loss - {self.job.job_id}")
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Save
            if output_path is None:
                output_path = f"/tmp/training_loss_{self.job.job_id}.png"

            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

            return output_path

        except ImportError:
            logger.warning("matplotlib not available for loss plotting")
            return None
        except Exception as e:
            logger.error(f"Failed to plot loss curve: {e}")
            return None


class TrainingJobRunner:
    """
    Manages MLX LoRA fine-tuning jobs.

    Provides:
    - Job lifecycle management (start, stop, pause, resume)
    - Memory-aware training with auto-pause
    - Progress tracking and logging
    - Checkpoint management

    Usage:
        runner = TrainingJobRunner()
        config = TrainingConfig(data_dir="/path/to/data")
        job = runner.start_training(config)

        # Monitor progress
        status = runner.get_status(job.job_id)
        metrics = runner.get_metrics(job.job_id)

        # Stop if needed
        runner.stop_training(job.job_id)
    """

    def __init__(self, jobs_dir: Optional[str] = None):
        """
        Initialize the training job runner.

        Args:
            jobs_dir: Directory to store job state (defaults to external storage)
        """
        self.jobs_dir = Path(jobs_dir) if jobs_dir else Path("/Volumes/David External/sam_training/jobs")
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

        self._active_jobs: Dict[str, TrainingJob] = {}
        self._monitors: Dict[str, TrainingMonitor] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._pause_events: Dict[str, threading.Event] = {}

        # Memory monitoring
        self._memory_check_interval = 5.0  # seconds
        self._memory_monitor_thread: Optional[threading.Thread] = None
        self._running = False

        # Load any persisted jobs
        self._load_jobs()

    def _load_jobs(self):
        """Load persisted job state."""
        for job_file in self.jobs_dir.glob("job_*.json"):
            try:
                with open(job_file) as f:
                    data = json.load(f)
                config = TrainingConfig.from_dict(data.get("config", {}))
                job = TrainingJob(
                    job_id=data["job_id"],
                    config=config,
                    status=TrainingStatus(data.get("status", "pending")),
                    start_time=data.get("start_time"),
                    end_time=data.get("end_time"),
                    current_step=data.get("current_step", 0),
                    total_steps=data.get("total_steps", 0),
                    current_epoch=data.get("current_epoch", 0),
                    best_val_loss=data.get("best_val_loss"),
                    error_message=data.get("error_message"),
                )
                self._active_jobs[job.job_id] = job
            except Exception as e:
                logger.warning(f"Failed to load job from {job_file}: {e}")

    def _save_job(self, job: TrainingJob):
        """Persist job state."""
        job_file = self.jobs_dir / f"job_{job.job_id}.json"
        with open(job_file, "w") as f:
            json.dump(job.to_dict(), f, indent=2)

    def _get_memory_info(self) -> tuple[float, float]:
        """Get available and total memory in GB."""
        try:
            import subprocess

            # Get page size
            pagesize = int(subprocess.check_output(['pagesize']).decode().strip())

            # Get vm_stat output
            vm_stat = subprocess.check_output(['vm_stat']).decode()

            # Parse stats
            stats = {}
            for line in vm_stat.split('\n'):
                if ':' in line:
                    key, value = line.split(':')
                    value = value.strip().rstrip('.')
                    try:
                        stats[key.strip()] = int(value)
                    except ValueError:
                        pass

            # Calculate available memory
            free_pages = stats.get('Pages free', 0)
            inactive_pages = stats.get('Pages inactive', 0)
            speculative_pages = stats.get('Pages speculative', 0)

            available_bytes = (free_pages + inactive_pages + speculative_pages) * pagesize
            available_gb = available_bytes / (1024 ** 3)

            # Total memory
            total_bytes = int(subprocess.check_output(
                ['sysctl', '-n', 'hw.memsize']
            ).decode().strip())
            total_gb = total_bytes / (1024 ** 3)

            return available_gb, total_gb

        except Exception:
            return 2.0, 8.0  # Fallback

    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def start_training(
        self,
        config: TrainingConfig,
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> TrainingJob:
        """
        Start a new training job.

        Args:
            config: Training configuration
            callbacks: Optional callbacks for events (on_step, on_eval, on_complete)

        Returns:
            TrainingJob instance
        """
        # Validate config
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid config: {errors}")

        # Create job
        job_id = self._generate_job_id()
        job = TrainingJob(
            job_id=job_id,
            config=config,
            status=TrainingStatus.INITIALIZING,
            start_time=datetime.now().isoformat(),
        )

        # Set up output directory
        if not config.output_dir:
            config.output_dir = str(self.jobs_dir / job_id / "output")
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        # Set up logging
        if not config.log_file:
            config.log_file = str(Path(config.output_dir) / "training.log")

        self._active_jobs[job_id] = job
        self._monitors[job_id] = TrainingMonitor(job)
        self._stop_events[job_id] = threading.Event()
        self._pause_events[job_id] = threading.Event()

        # Save initial state
        self._save_job(job)

        # Start training in background thread
        train_thread = threading.Thread(
            target=self._run_training,
            args=(job, callbacks),
            daemon=True,
        )
        train_thread.start()

        # Start memory monitor if not running
        if not self._running:
            self._start_memory_monitor()

        return job

    def _run_training(
        self,
        job: TrainingJob,
        callbacks: Optional[Dict[str, Callable]] = None,
    ):
        """Run training in background thread."""
        config = job.config

        try:
            job.status = TrainingStatus.TRAINING
            self._save_job(job)

            # Build MLX training command
            cmd = [
                sys.executable, "-m", "mlx_lm.lora",
                "--model", config.model_name,
                "--data", config.data_dir,
                "--train",
                "--batch-size", str(config.batch_size),
                "--lora-layers", str(config.lora_layers),
                "--lora-rank", str(config.lora_rank),
                "--learning-rate", str(config.learning_rate),
                "--iters", str(self._calculate_total_steps(config)),
                "--steps-per-report", str(config.log_every_steps),
                "--steps-per-eval", str(config.eval_every_steps),
                "--val-batches", str(config.val_batches),
                "--save-every", str(config.save_every_steps),
                "--adapter-path", str(Path(config.output_dir) / "adapters"),
                "--max-seq-length", str(config.max_seq_length),
            ]

            # Add gradient checkpointing
            if config.gradient_checkpointing:
                cmd.extend(["--grad-checkpoint"])

            # Add gradient accumulation
            if config.grad_accumulation_steps > 1:
                cmd.extend(["--grad-accumulation-steps", str(config.grad_accumulation_steps)])

            # Resume from existing adapters
            if config.adapter_path and Path(config.adapter_path).exists():
                cmd.extend(["--resume-adapter-file", config.adapter_path])

            logger.info(f"Starting training: {' '.join(cmd)}")

            # Open log file
            log_file = open(config.log_file, "w")

            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._processes[job.job_id] = process

            # Parse output and track progress
            job.total_steps = self._calculate_total_steps(config)

            for line in process.stdout:
                # Write to log
                log_file.write(line)
                log_file.flush()

                # Check for stop/pause signals
                if self._stop_events[job.job_id].is_set():
                    process.terminate()
                    job.status = TrainingStatus.STOPPED
                    break

                while self._pause_events[job.job_id].is_set():
                    time.sleep(1.0)
                    if self._stop_events[job.job_id].is_set():
                        break

                # Parse training output
                metrics = self._parse_training_output(line)
                if metrics:
                    job.current_step = metrics.step
                    job.current_epoch = metrics.epoch
                    self._monitors[job.job_id].update_metrics(metrics)

                    if callbacks and "on_step" in callbacks:
                        callbacks["on_step"](job, metrics)

            # Wait for process to complete
            return_code = process.wait()
            log_file.close()

            if job.status == TrainingStatus.STOPPED:
                pass  # Already set
            elif return_code == 0:
                job.status = TrainingStatus.COMPLETED
            else:
                job.status = TrainingStatus.FAILED
                job.error_message = f"Training process exited with code {return_code}"

        except Exception as e:
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            logger.error(f"Training failed: {e}")

        finally:
            job.end_time = datetime.now().isoformat()
            self._save_job(job)

            # Clean up
            if job.job_id in self._processes:
                del self._processes[job.job_id]

            if callbacks and "on_complete" in callbacks:
                callbacks["on_complete"](job)

    def _calculate_total_steps(self, config: TrainingConfig) -> int:
        """Calculate total training steps."""
        if not config.data_dir:
            return 1000  # Default

        # Try to count examples
        train_file = Path(config.data_dir) / "train.jsonl"
        if train_file.exists():
            with open(train_file) as f:
                num_examples = sum(1 for _ in f)

            effective_batch = config.batch_size * config.grad_accumulation_steps
            steps_per_epoch = max(1, num_examples // effective_batch)
            return steps_per_epoch * config.num_epochs

        return 1000  # Default fallback

    def _parse_training_output(self, line: str) -> Optional[TrainingMetrics]:
        """Parse training progress from MLX output."""
        try:
            # MLX training output format:
            # "Iter X: train loss Y.YYYY, val loss Z.ZZZZ, it/s A.AA"
            if "Iter" not in line:
                return None

            metrics = TrainingMetrics()

            # Parse step
            import re

            iter_match = re.search(r'Iter\s+(\d+)', line)
            if iter_match:
                metrics.step = int(iter_match.group(1))

            # Parse train loss
            train_match = re.search(r'train loss\s+([\d.]+)', line)
            if train_match:
                metrics.train_loss = float(train_match.group(1))

            # Parse val loss
            val_match = re.search(r'val loss\s+([\d.]+)', line)
            if val_match:
                metrics.val_loss = float(val_match.group(1))

            # Parse throughput
            speed_match = re.search(r'it/s\s+([\d.]+)', line)
            if speed_match:
                metrics.tokens_per_second = float(speed_match.group(1))

            # Get current memory
            available, _ = self._get_memory_info()
            metrics.memory_used_gb = 8.0 - available  # Approximate

            return metrics

        except Exception:
            return None

    def _start_memory_monitor(self):
        """Start background memory monitoring."""
        self._running = True

        def monitor_loop():
            while self._running:
                available, _ = self._get_memory_info()

                # Check all active training jobs
                for job_id, job in self._active_jobs.items():
                    if job.status != TrainingStatus.TRAINING:
                        continue

                    config = job.config

                    # Auto-pause if memory is critically low
                    if available < config.memory_pause_threshold_gb:
                        if not self._pause_events.get(job_id, threading.Event()).is_set():
                            logger.warning(
                                f"Low memory ({available:.2f}GB), pausing job {job_id}"
                            )
                            self.pause_training(job_id)
                            job.status = TrainingStatus.PAUSED

                    # Auto-resume if memory recovered
                    elif available > config.memory_resume_threshold_gb:
                        if self._pause_events.get(job_id, threading.Event()).is_set():
                            logger.info(
                                f"Memory recovered ({available:.2f}GB), resuming job {job_id}"
                            )
                            self.resume_training(job_id)
                            job.status = TrainingStatus.TRAINING

                time.sleep(self._memory_check_interval)

        self._memory_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._memory_monitor_thread.start()

    def stop_training(self, job_id: str) -> bool:
        """
        Stop a training job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was stopped
        """
        if job_id not in self._active_jobs:
            return False

        self._stop_events[job_id].set()

        # Terminate process if running
        if job_id in self._processes:
            try:
                self._processes[job_id].terminate()
            except Exception:
                pass

        job = self._active_jobs[job_id]
        job.status = TrainingStatus.STOPPED
        job.end_time = datetime.now().isoformat()
        self._save_job(job)

        return True

    def pause_training(self, job_id: str) -> bool:
        """Pause a training job."""
        if job_id not in self._active_jobs:
            return False

        self._pause_events[job_id].set()
        self._active_jobs[job_id].status = TrainingStatus.PAUSED
        self._save_job(self._active_jobs[job_id])
        return True

    def resume_training(self, job_id: str) -> bool:
        """Resume a paused training job."""
        if job_id not in self._active_jobs:
            return False

        self._pause_events[job_id].clear()
        self._active_jobs[job_id].status = TrainingStatus.TRAINING
        self._save_job(self._active_jobs[job_id])
        return True

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a training job."""
        if job_id not in self._active_jobs:
            return None

        job = self._active_jobs[job_id]
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "start_time": job.start_time,
            "end_time": job.end_time,
            "current_step": job.current_step,
            "total_steps": job.total_steps,
            "progress_percent": (job.current_step / job.total_steps * 100
                                if job.total_steps > 0 else 0),
            "error_message": job.error_message,
        }

    def get_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get training metrics for a job."""
        if job_id not in self._monitors:
            return None
        return self._monitors[job_id].get_metrics()

    def get_logs(
        self,
        job_id: str,
        tail_lines: int = 100,
    ) -> Optional[List[str]]:
        """Get recent log lines for a job."""
        if job_id not in self._active_jobs:
            return None

        log_file = self._active_jobs[job_id].config.log_file
        if not log_file or not Path(log_file).exists():
            return []

        try:
            with open(log_file) as f:
                lines = f.readlines()
            return lines[-tail_lines:]
        except Exception:
            return []

    def estimate_completion(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Estimate time to completion for a job."""
        if job_id not in self._monitors:
            return None
        return self._monitors[job_id].estimate_completion()

    def plot_loss_curve(
        self,
        job_id: str,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Generate and save loss curve for a job."""
        if job_id not in self._monitors:
            return None
        return self._monitors[job_id].plot_loss_curve(output_path)

    def list_jobs(
        self,
        status_filter: Optional[TrainingStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List all jobs, optionally filtered by status."""
        jobs = []
        for job in self._active_jobs.values():
            if status_filter is None or job.status == status_filter:
                jobs.append(self.get_status(job.job_id))
        return jobs

    def cleanup_completed_jobs(self, older_than_days: int = 7) -> int:
        """Remove completed/failed jobs older than specified days."""
        cutoff = datetime.now() - timedelta(days=older_than_days)
        removed = 0

        for job_id in list(self._active_jobs.keys()):
            job = self._active_jobs[job_id]

            if job.status not in (TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.STOPPED):
                continue

            if job.end_time:
                end_time = datetime.fromisoformat(job.end_time)
                if end_time < cutoff:
                    # Remove job file
                    job_file = self.jobs_dir / f"job_{job_id}.json"
                    if job_file.exists():
                        job_file.unlink()

                    del self._active_jobs[job_id]
                    if job_id in self._monitors:
                        del self._monitors[job_id]

                    removed += 1

        return removed

    def shutdown(self):
        """Clean shutdown of all training jobs."""
        self._running = False

        # Stop all active training
        for job_id in list(self._active_jobs.keys()):
            if self._active_jobs[job_id].status == TrainingStatus.TRAINING:
                self.stop_training(job_id)


def main():
    """CLI interface for training job runner."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Training Job Runner")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a training job")
    start_parser.add_argument("data_dir", help="Path to prepared training data")
    start_parser.add_argument("--model", default="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit")
    start_parser.add_argument("--epochs", type=int, default=1)
    start_parser.add_argument("--lora-rank", type=int, default=4)
    start_parser.add_argument("--learning-rate", type=float, default=1e-4)
    start_parser.add_argument("--max-seq-length", type=int, default=512)

    # Status command
    status_parser = subparsers.add_parser("status", help="Get job status")
    status_parser.add_argument("job_id", help="Job ID")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a training job")
    stop_parser.add_argument("job_id", help="Job ID")

    # List command
    subparsers.add_parser("list", help="List all jobs")

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Get training metrics")
    metrics_parser.add_argument("job_id", help="Job ID")

    # Plot command
    plot_parser = subparsers.add_parser("plot", help="Plot loss curve")
    plot_parser.add_argument("job_id", help="Job ID")
    plot_parser.add_argument("--output", "-o", help="Output path for plot")

    args = parser.parse_args()

    runner = TrainingJobRunner()

    if args.command == "start":
        config = TrainingConfig(
            model_name=args.model,
            data_dir=args.data_dir,
            num_epochs=args.epochs,
            lora_rank=args.lora_rank,
            learning_rate=args.learning_rate,
            max_seq_length=args.max_seq_length,
        )

        job = runner.start_training(config)
        print(f"Started training job: {job.job_id}")
        print(f"Output directory: {job.config.output_dir}")
        print(f"Log file: {job.config.log_file}")

    elif args.command == "status":
        status = runner.get_status(args.job_id)
        if status:
            print(json.dumps(status, indent=2))
        else:
            print(f"Job not found: {args.job_id}")

    elif args.command == "stop":
        if runner.stop_training(args.job_id):
            print(f"Stopped job: {args.job_id}")
        else:
            print(f"Failed to stop job: {args.job_id}")

    elif args.command == "list":
        jobs = runner.list_jobs()
        if jobs:
            for job in jobs:
                print(f"{job['job_id']}: {job['status']} ({job['progress_percent']:.1f}%)")
        else:
            print("No jobs found")

    elif args.command == "metrics":
        metrics = runner.get_metrics(args.job_id)
        if metrics:
            print(json.dumps(metrics, indent=2))
        else:
            print(f"No metrics for job: {args.job_id}")

    elif args.command == "plot":
        path = runner.plot_loss_curve(args.job_id, args.output)
        if path:
            print(f"Loss curve saved to: {path}")
        else:
            print(f"Failed to plot loss curve for job: {args.job_id}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
