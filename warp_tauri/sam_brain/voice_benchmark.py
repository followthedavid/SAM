#!/usr/bin/env python3
"""
SAM Voice Benchmark - Measure TTS and voice pipeline performance.

Task 6.2.1: Benchmark TTS latency and generate performance reports.

Benchmarks:
1. TTS latency for each engine (macOS, Coqui, edge-tts)
2. RVC voice conversion time
3. Full pipeline end-to-end timing

Results are saved to docs/VOICE_BENCHMARK.md

Usage:
    python voice_benchmark.py run           # Run all benchmarks
    python voice_benchmark.py tts           # Benchmark TTS only
    python voice_benchmark.py rvc           # Benchmark RVC only
    python voice_benchmark.py pipeline      # Benchmark full pipeline
    python voice_benchmark.py report        # Generate report from last results
"""

import os
import sys
import time
import json
import statistics
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
import numpy as np

SCRIPT_DIR = Path(__file__).parent
BENCHMARK_RESULTS_FILE = SCRIPT_DIR / ".voice_benchmark_results.json"
DOCS_DIR = SCRIPT_DIR / "docs"
BENCHMARK_REPORT_FILE = DOCS_DIR / "VOICE_BENCHMARK.md"


@dataclass
class BenchmarkResult:
    """Single benchmark measurement result."""
    name: str
    engine: str
    duration_ms: float
    text_length: int
    audio_duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "engine": self.engine,
            "duration_ms": round(self.duration_ms, 2),
            "text_length": self.text_length,
            "audio_duration_ms": round(self.audio_duration_ms, 2),
            "realtime_factor": round(self.audio_duration_ms / self.duration_ms, 2) if self.duration_ms > 0 else 0,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class BenchmarkSummary:
    """Summary statistics for a benchmark category."""
    name: str
    engine: str
    count: int
    mean_ms: float
    median_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "engine": self.engine,
            "count": self.count,
            "mean_ms": round(self.mean_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "std_ms": round(self.std_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "success_rate": round(self.success_rate * 100, 1)
        }


class VoiceBenchmark:
    """
    Benchmark voice pipeline performance.

    Measures latency for:
    - TTS engines (macOS say, Coqui, edge-tts)
    - RVC voice conversion
    - Full end-to-end pipeline
    """

    # Test phrases of varying length
    TEST_PHRASES = [
        "Hello.",                                                           # 6 chars
        "I am SAM.",                                                        # 10 chars
        "The build completed successfully.",                                # 33 chars
        "I found three potential issues in your code that need attention.", # 64 chars
        "Based on my analysis of 3,241 projects across 7 drives, I can provide comprehensive insights into your development patterns and suggest optimizations.", # 151 chars
    ]

    # SAM's common phrases for precomputation testing
    SAM_COMMON_PHRASES = [
        "Sure thing!",
        "On it.",
        "Done.",
        "Got it.",
        "Let me check.",
        "Working on it.",
        "Here's what I found.",
        "I'm analyzing that now.",
        "Interesting. Let me dig deeper.",
        "That looks good to me.",
        "I see a few issues here.",
        "The build was successful.",
        "Tests are passing.",
        "Ready when you are.",
        "Need more context on that.",
    ]

    def __init__(self, iterations: int = 5, warmup: int = 1):
        """
        Initialize benchmark.

        Args:
            iterations: Number of iterations per test
            warmup: Number of warmup runs (not counted)
        """
        self.iterations = iterations
        self.warmup = warmup
        self.results: List[BenchmarkResult] = []
        self.summaries: Dict[str, BenchmarkSummary] = {}
        self._temp_dir = tempfile.mkdtemp(prefix="sam_voice_bench_")

    def _time_function(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[float, Any, Optional[str]]:
        """
        Time a function call.

        Returns:
            (duration_ms, result, error_str)
        """
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            return duration, result, None
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return duration, None, str(e)

    def _get_audio_duration_ms(self, audio_path: Path) -> float:
        """Get duration of audio file in milliseconds."""
        if not audio_path or not audio_path.exists():
            return 0.0
        try:
            # Use afinfo on macOS
            result = subprocess.run(
                ["afinfo", str(audio_path)],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split("\n"):
                if "estimated duration:" in line.lower():
                    # Parse "estimated duration: 1.234567 sec"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        duration_str = parts[1].strip().split()[0]
                        return float(duration_str) * 1000
        except:
            pass
        return 0.0

    # =========================================================================
    # TTS BENCHMARKS
    # =========================================================================

    def benchmark_tts(self) -> Dict[str, BenchmarkSummary]:
        """
        Benchmark TTS latency for each available engine.

        Tests:
        - macOS say command
        - Coqui TTS (if installed)
        - edge-tts (if installed)

        Returns:
            Dict of engine name -> BenchmarkSummary
        """
        print("\n" + "=" * 60)
        print("TTS Benchmark")
        print("=" * 60)

        engines = self._detect_tts_engines()
        summaries = {}

        for engine_name, engine_func in engines.items():
            print(f"\nBenchmarking {engine_name}...")
            engine_results = []

            for phrase in self.TEST_PHRASES:
                # Warmup
                for _ in range(self.warmup):
                    engine_func(phrase, self._temp_dir)

                # Timed runs
                for i in range(self.iterations):
                    output_path = Path(self._temp_dir) / f"{engine_name}_{hash(phrase)}_{i}.wav"

                    duration_ms, audio_path, error = self._time_function(
                        engine_func, phrase, str(output_path)
                    )

                    audio_duration = self._get_audio_duration_ms(audio_path) if audio_path else 0.0

                    result = BenchmarkResult(
                        name="tts",
                        engine=engine_name,
                        duration_ms=duration_ms,
                        text_length=len(phrase),
                        audio_duration_ms=audio_duration,
                        success=error is None,
                        error=error,
                        metadata={"phrase": phrase[:30] + "..." if len(phrase) > 30 else phrase}
                    )
                    engine_results.append(result)
                    self.results.append(result)

            # Calculate summary
            successful = [r for r in engine_results if r.success]
            if successful:
                durations = [r.duration_ms for r in successful]
                summaries[engine_name] = BenchmarkSummary(
                    name="tts",
                    engine=engine_name,
                    count=len(successful),
                    mean_ms=statistics.mean(durations),
                    median_ms=statistics.median(durations),
                    std_ms=statistics.stdev(durations) if len(durations) > 1 else 0,
                    min_ms=min(durations),
                    max_ms=max(durations),
                    p95_ms=np.percentile(durations, 95),
                    success_rate=len(successful) / len(engine_results)
                )
                self._print_summary(summaries[engine_name])

        self.summaries.update({f"tts_{k}": v for k, v in summaries.items()})
        return summaries

    def _detect_tts_engines(self) -> Dict[str, Callable]:
        """Detect available TTS engines."""
        engines = {}

        # macOS say (always available)
        engines["macos_say"] = self._benchmark_macos_say

        # Coqui TTS
        try:
            from TTS.api import TTS
            engines["coqui"] = self._benchmark_coqui
        except ImportError:
            print("  Coqui TTS not available")

        # edge-tts
        try:
            import edge_tts
            engines["edge_tts"] = self._benchmark_edge_tts
        except ImportError:
            print("  edge-tts not available")

        return engines

    def _benchmark_macos_say(self, text: str, output_path: str) -> Optional[Path]:
        """Benchmark macOS say command."""
        output = Path(output_path)
        if not output.suffix:
            output = output.with_suffix(".aiff")

        result = subprocess.run(
            ["say", "-o", str(output), text],
            capture_output=True
        )
        return output if result.returncode == 0 else None

    def _benchmark_coqui(self, text: str, output_path: str) -> Optional[Path]:
        """Benchmark Coqui TTS."""
        try:
            from TTS.api import TTS
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            output = Path(output_path).with_suffix(".wav")
            tts.tts_to_file(text=text, file_path=str(output))
            return output if output.exists() else None
        except Exception as e:
            raise RuntimeError(f"Coqui TTS failed: {e}")

    def _benchmark_edge_tts(self, text: str, output_path: str) -> Optional[Path]:
        """Benchmark edge-tts."""
        import asyncio
        import edge_tts

        async def generate():
            output = Path(output_path).with_suffix(".mp3")
            communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
            await communicate.save(str(output))
            return output

        return asyncio.run(generate())

    # =========================================================================
    # RVC BENCHMARKS
    # =========================================================================

    def benchmark_rvc(self) -> Optional[BenchmarkSummary]:
        """
        Benchmark RVC voice conversion time.

        Tests conversion of pre-generated audio files.

        Returns:
            BenchmarkSummary or None if RVC not available
        """
        print("\n" + "=" * 60)
        print("RVC Benchmark")
        print("=" * 60)

        # Check if RVC is available
        rvc_project = Path.home() / "Projects" / "RVC" / "rvc-webui"
        rvc_weights = rvc_project / "weights"

        if not rvc_weights.exists():
            print("  RVC not available - skipping")
            return None

        # Find available models
        models = list(rvc_weights.glob("*.pth"))
        if not models:
            print("  No RVC models found - skipping")
            return None

        model = models[0]
        print(f"  Using model: {model.stem}")

        # Generate test audio first
        test_audios = []
        for phrase in self.TEST_PHRASES[:3]:  # Use fewer for RVC (it's slow)
            output = Path(self._temp_dir) / f"rvc_input_{hash(phrase)}.aiff"
            subprocess.run(["say", "-o", str(output), phrase], capture_output=True)
            test_audios.append((phrase, output))

        rvc_results = []
        for phrase, input_audio in test_audios:
            # Warmup
            for _ in range(self.warmup):
                self._run_rvc(input_audio, model, Path(self._temp_dir) / "warmup.wav")

            # Timed runs
            for i in range(self.iterations):
                output_path = Path(self._temp_dir) / f"rvc_output_{hash(phrase)}_{i}.wav"

                duration_ms, result, error = self._time_function(
                    self._run_rvc, input_audio, model, output_path
                )

                audio_duration = self._get_audio_duration_ms(input_audio)

                bench_result = BenchmarkResult(
                    name="rvc",
                    engine="rvc",
                    duration_ms=duration_ms,
                    text_length=len(phrase),
                    audio_duration_ms=audio_duration,
                    success=error is None,
                    error=error,
                    metadata={"model": model.stem}
                )
                rvc_results.append(bench_result)
                self.results.append(bench_result)

        # Calculate summary
        successful = [r for r in rvc_results if r.success]
        if successful:
            durations = [r.duration_ms for r in successful]
            summary = BenchmarkSummary(
                name="rvc",
                engine="rvc",
                count=len(successful),
                mean_ms=statistics.mean(durations),
                median_ms=statistics.median(durations),
                std_ms=statistics.stdev(durations) if len(durations) > 1 else 0,
                min_ms=min(durations),
                max_ms=max(durations),
                p95_ms=np.percentile(durations, 95),
                success_rate=len(successful) / len(rvc_results)
            )
            self.summaries["rvc"] = summary
            self._print_summary(summary)
            return summary

        return None

    def _run_rvc(self, input_path: Path, model_path: Path, output_path: Path) -> Optional[Path]:
        """Run RVC voice conversion."""
        rvc_project = Path.home() / "Projects" / "RVC" / "rvc-webui"

        cmd = [
            "python3", str(rvc_project / "infer_cli.py"),
            "--model", str(model_path),
            "--input", str(input_path),
            "--output", str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return output_path if result.returncode == 0 and output_path.exists() else None

    # =========================================================================
    # FULL PIPELINE BENCHMARKS
    # =========================================================================

    def benchmark_full_pipeline(self) -> Dict[str, BenchmarkSummary]:
        """
        Benchmark complete end-to-end voice pipeline.

        Measures: TTS -> RVC (optional) -> playback ready

        Returns:
            Dict of pipeline name -> BenchmarkSummary
        """
        print("\n" + "=" * 60)
        print("Full Pipeline Benchmark")
        print("=" * 60)

        summaries = {}

        # Pipeline 1: TTS only (macOS)
        print("\nPipeline: macOS TTS only")
        tts_results = self._benchmark_pipeline(
            name="pipeline_tts_only",
            tts_func=self._benchmark_macos_say,
            rvc_enabled=False
        )
        if tts_results:
            summaries["tts_only"] = tts_results
            self._print_summary(tts_results)

        # Pipeline 2: TTS + RVC (if available)
        rvc_weights = Path.home() / "Projects" / "RVC" / "rvc-webui" / "weights"
        if rvc_weights.exists() and list(rvc_weights.glob("*.pth")):
            print("\nPipeline: macOS TTS + RVC")
            full_results = self._benchmark_pipeline(
                name="pipeline_full",
                tts_func=self._benchmark_macos_say,
                rvc_enabled=True
            )
            if full_results:
                summaries["tts_plus_rvc"] = full_results
                self._print_summary(full_results)

        self.summaries.update({f"pipeline_{k}": v for k, v in summaries.items()})
        return summaries

    def _benchmark_pipeline(
        self,
        name: str,
        tts_func: Callable,
        rvc_enabled: bool
    ) -> Optional[BenchmarkSummary]:
        """Benchmark a specific pipeline configuration."""
        pipeline_results = []

        # Get RVC model if needed
        rvc_model = None
        if rvc_enabled:
            rvc_weights = Path.home() / "Projects" / "RVC" / "rvc-webui" / "weights"
            models = list(rvc_weights.glob("*.pth"))
            if models:
                rvc_model = models[0]

        for phrase in self.TEST_PHRASES[:3]:  # Fewer for full pipeline
            for i in range(self.iterations):
                start = time.perf_counter()

                try:
                    # Step 1: TTS
                    tts_output = Path(self._temp_dir) / f"{name}_tts_{hash(phrase)}_{i}.aiff"
                    tts_func(phrase, str(tts_output))

                    final_output = tts_output

                    # Step 2: RVC (optional)
                    if rvc_enabled and rvc_model:
                        rvc_output = Path(self._temp_dir) / f"{name}_rvc_{hash(phrase)}_{i}.wav"
                        self._run_rvc(tts_output, rvc_model, rvc_output)
                        if rvc_output.exists():
                            final_output = rvc_output

                    duration_ms = (time.perf_counter() - start) * 1000
                    audio_duration = self._get_audio_duration_ms(final_output)

                    result = BenchmarkResult(
                        name=name,
                        engine="full_pipeline",
                        duration_ms=duration_ms,
                        text_length=len(phrase),
                        audio_duration_ms=audio_duration,
                        success=True,
                        metadata={"rvc_enabled": rvc_enabled}
                    )
                except Exception as e:
                    duration_ms = (time.perf_counter() - start) * 1000
                    result = BenchmarkResult(
                        name=name,
                        engine="full_pipeline",
                        duration_ms=duration_ms,
                        text_length=len(phrase),
                        success=False,
                        error=str(e)
                    )

                pipeline_results.append(result)
                self.results.append(result)

        # Calculate summary
        successful = [r for r in pipeline_results if r.success]
        if successful:
            durations = [r.duration_ms for r in successful]
            return BenchmarkSummary(
                name=name,
                engine="full_pipeline",
                count=len(successful),
                mean_ms=statistics.mean(durations),
                median_ms=statistics.median(durations),
                std_ms=statistics.stdev(durations) if len(durations) > 1 else 0,
                min_ms=min(durations),
                max_ms=max(durations),
                p95_ms=np.percentile(durations, 95),
                success_rate=len(successful) / len(pipeline_results)
            )
        return None

    # =========================================================================
    # REPORTING
    # =========================================================================

    def _print_summary(self, summary: BenchmarkSummary):
        """Print a benchmark summary."""
        print(f"  Mean: {summary.mean_ms:.1f}ms | Median: {summary.median_ms:.1f}ms | "
              f"P95: {summary.p95_ms:.1f}ms | Success: {summary.success_rate*100:.0f}%")

    def save_results(self):
        """Save benchmark results to JSON file."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "iterations": self.iterations,
            "warmup": self.warmup,
            "results": [r.to_dict() for r in self.results],
            "summaries": {k: v.to_dict() for k, v in self.summaries.items()}
        }

        with open(BENCHMARK_RESULTS_FILE, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nResults saved to: {BENCHMARK_RESULTS_FILE}")

    def generate_report(self) -> str:
        """
        Generate markdown benchmark report.

        Saves to docs/VOICE_BENCHMARK.md

        Returns:
            Path to report file
        """
        DOCS_DIR.mkdir(exist_ok=True)

        lines = [
            "# SAM Voice Performance Benchmark",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Executive Summary",
            "",
            f"- **Iterations per test**: {self.iterations}",
            f"- **Warmup runs**: {self.warmup}",
            f"- **Total measurements**: {len(self.results)}",
            "",
        ]

        # TTS Summary
        tts_summaries = {k: v for k, v in self.summaries.items() if k.startswith("tts_")}
        if tts_summaries:
            lines.extend([
                "## TTS Engine Performance",
                "",
                "| Engine | Mean (ms) | Median (ms) | P95 (ms) | Min (ms) | Max (ms) | Success Rate |",
                "|--------|-----------|-------------|----------|----------|----------|--------------|",
            ])
            for name, summary in sorted(tts_summaries.items()):
                lines.append(
                    f"| {summary.engine} | {summary.mean_ms:.1f} | {summary.median_ms:.1f} | "
                    f"{summary.p95_ms:.1f} | {summary.min_ms:.1f} | {summary.max_ms:.1f} | "
                    f"{summary.success_rate*100:.0f}% |"
                )
            lines.append("")

        # RVC Summary
        if "rvc" in self.summaries:
            summary = self.summaries["rvc"]
            lines.extend([
                "## RVC Voice Conversion Performance",
                "",
                f"- **Mean conversion time**: {summary.mean_ms:.1f}ms",
                f"- **Median conversion time**: {summary.median_ms:.1f}ms",
                f"- **P95 conversion time**: {summary.p95_ms:.1f}ms",
                f"- **Success rate**: {summary.success_rate*100:.0f}%",
                "",
            ])

        # Pipeline Summary
        pipeline_summaries = {k: v for k, v in self.summaries.items() if k.startswith("pipeline_")}
        if pipeline_summaries:
            lines.extend([
                "## Full Pipeline Performance",
                "",
                "| Pipeline | Mean (ms) | Median (ms) | P95 (ms) | Realtime Factor |",
                "|----------|-----------|-------------|----------|-----------------|",
            ])
            for name, summary in sorted(pipeline_summaries.items()):
                # Calculate realtime factor from results
                pipeline_results = [r for r in self.results if r.name == summary.name and r.success]
                if pipeline_results:
                    avg_audio = statistics.mean([r.audio_duration_ms for r in pipeline_results if r.audio_duration_ms > 0])
                    rtf = avg_audio / summary.mean_ms if summary.mean_ms > 0 else 0
                else:
                    rtf = 0
                lines.append(
                    f"| {name.replace('pipeline_', '')} | {summary.mean_ms:.1f} | {summary.median_ms:.1f} | "
                    f"{summary.p95_ms:.1f} | {rtf:.2f}x |"
                )
            lines.append("")

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
        ])

        # Find fastest TTS
        if tts_summaries:
            fastest_tts = min(tts_summaries.values(), key=lambda s: s.median_ms)
            lines.append(f"- **Fastest TTS**: {fastest_tts.engine} ({fastest_tts.median_ms:.1f}ms median)")

        # RVC overhead
        if "rvc" in self.summaries:
            rvc_overhead = self.summaries["rvc"].median_ms
            lines.append(f"- **RVC overhead**: +{rvc_overhead:.0f}ms per utterance")

        # Cache recommendation
        lines.extend([
            "",
            "### Caching Strategy",
            "",
            "Based on benchmark results, recommended caching approach:",
            "",
            "1. **Pre-compute SAM's common phrases** (greetings, confirmations)",
            "2. **Cache all TTS output** with hash(text + voice + settings) as key",
            "3. **LRU eviction** with max cache size of ~500MB",
            "",
        ])

        # Hardware info
        lines.extend([
            "## Test Environment",
            "",
            f"- **Platform**: macOS (M2 Mac Mini, 8GB RAM)",
            f"- **Date**: {datetime.now().strftime('%Y-%m-%d')}",
            "",
        ])

        report_content = "\n".join(lines)

        with open(BENCHMARK_REPORT_FILE, "w") as f:
            f.write(report_content)

        print(f"\nReport saved to: {BENCHMARK_REPORT_FILE}")
        return str(BENCHMARK_REPORT_FILE)

    def run_all(self):
        """Run all benchmarks and generate report."""
        self.benchmark_tts()
        self.benchmark_rvc()
        self.benchmark_full_pipeline()
        self.save_results()
        self.generate_report()

    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        if self._temp_dir and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir)


# CLI
def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Voice Benchmark")
    parser.add_argument("command", nargs="?", default="run",
                       choices=["run", "tts", "rvc", "pipeline", "report"],
                       help="Benchmark command")
    parser.add_argument("--iterations", "-n", type=int, default=5,
                       help="Number of iterations per test")
    parser.add_argument("--warmup", "-w", type=int, default=1,
                       help="Number of warmup runs")

    args = parser.parse_args()

    benchmark = VoiceBenchmark(iterations=args.iterations, warmup=args.warmup)

    try:
        if args.command == "run":
            benchmark.run_all()
        elif args.command == "tts":
            benchmark.benchmark_tts()
            benchmark.save_results()
        elif args.command == "rvc":
            benchmark.benchmark_rvc()
            benchmark.save_results()
        elif args.command == "pipeline":
            benchmark.benchmark_full_pipeline()
            benchmark.save_results()
        elif args.command == "report":
            # Load existing results if available
            if BENCHMARK_RESULTS_FILE.exists():
                with open(BENCHMARK_RESULTS_FILE) as f:
                    data = json.load(f)
                    benchmark.summaries = {
                        k: BenchmarkSummary(**v) for k, v in data.get("summaries", {}).items()
                    }
                    benchmark.results = [
                        BenchmarkResult(**r) for r in data.get("results", [])
                    ]
            benchmark.generate_report()
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()
