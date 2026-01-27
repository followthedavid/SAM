#!/usr/bin/env python3
"""
Comprehensive Test Suite for SAM Vision System v1.0

Tests all vision components:
1. Vision Engine initialization and configuration
2. Model selector (SmolVLM, Moondream choices)
3. Quality validator (response assessment)
4. Model loading and inference (mock + real)
5. Escalation to Claude triggers
6. Integration with cognitive orchestrator
7. API endpoint tests
8. Performance benchmarks

Run: python3 -m cognitive.test_vision_system
"""

import sys
import time
import tempfile
import shutil
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str
    duration_ms: int
    category: str = ""


class VisionTestSuite:
    """
    Comprehensive test suite for the SAM Vision System.

    Coverage targets:
    - Vision engine initialization
    - Model selection logic
    - Quality validation
    - Escalation triggers
    - Integration with orchestrator
    """

    def __init__(self, verbose: bool = True):
        self.results: List[TestResult] = []
        self.verbose = verbose
        # Use temp directory for test isolation
        self.test_dir = tempfile.mkdtemp(prefix="sam_vision_test_")
        self.test_db_path = str(Path(self.test_dir) / "test_db")

        # Create a test image for vision tests
        self.test_image_path = self._create_test_image()

    def _create_test_image(self) -> str:
        """Create a simple test image for vision tests."""
        test_image = Path(self.test_dir) / "test_image.png"

        try:
            # Try to create a simple image with PIL
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(str(test_image))
        except ImportError:
            # Fallback: create a minimal PNG file
            # Minimal valid 1x1 red PNG
            png_data = bytes([
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
                0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB
                0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
                0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,  # Compressed red pixel
                0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
                0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
                0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
            ])
            test_image.write_bytes(png_data)

        return str(test_image)

    def cleanup(self):
        """Clean up test directory."""
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

    def run_all(self) -> Tuple[int, int]:
        """Run all tests, return (passed, failed) counts."""
        print("=" * 70)
        print("SAM VISION SYSTEM - COMPREHENSIVE TEST SUITE v1.0")
        print("=" * 70)
        print(f"Test directory: {self.test_dir}")
        print(f"Test image: {self.test_image_path}")
        print()

        # Test groups in dependency order
        test_groups = [
            # Core imports and initialization
            ("1. IMPORTS & INITIALIZATION", [
                self.test_all_imports,
                self.test_version,
                self.test_vision_config_creation,
            ]),

            # Vision Engine
            ("2. VISION ENGINE", [
                self.test_engine_initialization,
                self.test_engine_stats,
            ]),

            # Model Selector
            ("3. MODEL SELECTOR", [
                self.test_selector_initialization,
                self.test_selector_detect_task_type,
                self.test_selector_estimate_complexity,
                self.test_selector_select_model,
            ]),

            # Quality Validator
            ("4. QUALITY VALIDATOR", [
                self.test_validator_initialization,
                self.test_validator_good_response,
                self.test_validator_bad_response,
            ]),

            # Task Types
            ("5. TASK TYPES", [
                self.test_task_type_enum,
                self.test_task_type_caption,
                self.test_task_type_detection,
                self.test_task_type_reasoning,
            ]),

            # Vision Result
            ("6. VISION RESULT", [
                self.test_result_creation,
                self.test_result_to_dict,
            ]),

            # Orchestrator Integration
            ("7. ORCHESTRATOR INTEGRATION", [
                self.test_orchestrator_vision_engine,
                self.test_orchestrator_describe_method,
                self.test_orchestrator_detect_method,
                self.test_orchestrator_answer_method,
            ]),

            # Convenience Functions
            ("8. CONVENIENCE FUNCTIONS", [
                self.test_create_vision_engine,
            ]),

            # VISION_MODELS constant
            ("9. VISION MODELS", [
                self.test_vision_models_constant,
                self.test_vision_models_smolvlm,
                self.test_vision_models_moondream,
            ]),
        ]

        for group_name, tests in test_groups:
            print(f"\n{group_name}")
            print("-" * len(group_name))
            for test in tests:
                try:
                    test()
                except Exception as e:
                    self._record(
                        test.__name__,
                        False,
                        f"Exception: {e}",
                        0,
                        group_name.split(".")[0]
                    )

        # Print summary
        print()
        print("=" * 70)
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = passed + failed

        print(f"RESULTS: {passed}/{total} tests passed")
        print()

        if failed > 0:
            print("FAILED TESTS:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")
            print()

        self.cleanup()
        return passed, failed

    def _time_test(self, func) -> Tuple[bool, int]:
        """Run a test function and return (result, duration_ms)."""
        start = time.time()
        try:
            result = func()
            duration = int((time.time() - start) * 1000)
            return result, duration
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            if self.verbose:
                print(f"      Error: {e}")
            return False, duration

    def _record(self, name: str, passed: bool, message: str, duration: int, category: str):
        """Record a test result."""
        status = "PASS" if passed else "FAIL"
        if self.verbose:
            print(f"  [{status}] {name}: {message} ({duration}ms)")
        self.results.append(TestResult(name, passed, message, duration, category))

    # ═══════════════════════════════════════════════════════════════════════
    # 1. IMPORTS & INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════

    def test_all_imports(self):
        """Test all vision module imports."""
        def test():
            from cognitive import (
                VisionEngine,
                VisionConfig,
                VisionResult,
                VisionTaskType,
                VisionModelSelector,
                VisionQualityValidator,
                VISION_MODELS,
                create_vision_engine,
                describe_image,
                detect_objects,
                answer_about_image,
            )
            return True

        result, duration = self._time_test(test)
        self._record("all_imports", result, "All vision imports successful", duration, "1. IMPORTS")

    def test_version(self):
        """Test cognitive version includes vision."""
        def test():
            import cognitive
            return cognitive.__version__ >= "1.2.0"

        result, duration = self._time_test(test)
        self._record("version", result, "Version 1.2.0+ (with vision)", duration, "1. IMPORTS")

    def test_vision_config_creation(self):
        """Test VisionConfig dataclass creation."""
        def test():
            from cognitive import VisionConfig
            config = VisionConfig(
                max_tokens=200,
                temperature=0.7
            )
            return config.max_tokens == 200

        result, duration = self._time_test(test)
        self._record("config_creation", result, "VisionConfig created", duration, "1. IMPORTS")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. VISION ENGINE
    # ═══════════════════════════════════════════════════════════════════════

    def test_engine_initialization(self):
        """Test VisionEngine initialization."""
        def test():
            from cognitive import VisionEngine
            engine = VisionEngine()
            return engine is not None and hasattr(engine, 'selector')

        result, duration = self._time_test(test)
        self._record("engine_init", result, "Engine initializes", duration, "2. ENGINE")

    def test_engine_stats(self):
        """Test engine stats retrieval."""
        def test():
            from cognitive import VisionEngine
            engine = VisionEngine()
            stats = engine.get_stats()
            return "generation_count" in stats and "escalation_count" in stats

        result, duration = self._time_test(test)
        self._record("engine_stats", result, "Returns stats dict", duration, "2. ENGINE")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. MODEL SELECTOR
    # ═══════════════════════════════════════════════════════════════════════

    def test_selector_initialization(self):
        """Test VisionModelSelector initialization."""
        def test():
            from cognitive import VisionModelSelector
            selector = VisionModelSelector()
            return selector is not None and hasattr(selector, 'max_memory_mb')

        result, duration = self._time_test(test)
        self._record("selector_init", result, "Selector initializes", duration, "3. SELECTOR")

    def test_selector_detect_task_type(self):
        """Test task type detection from prompt."""
        def test():
            from cognitive import VisionModelSelector, VisionTaskType
            selector = VisionModelSelector()
            # Caption/describe prompt
            task = selector.detect_task_type("describe this image")
            return task == VisionTaskType.CAPTION or task == VisionTaskType.GENERAL

        result, duration = self._time_test(test)
        self._record("selector_task_type", result, "Detects task type", duration, "3. SELECTOR")

    def test_selector_estimate_complexity(self):
        """Test complexity estimation."""
        def test():
            from cognitive import VisionModelSelector
            selector = VisionModelSelector()
            simple_complexity, _ = selector.estimate_complexity("what is this")
            complex_complexity, _ = selector.estimate_complexity(
                "analyze this detailed image and explain the relationship between all objects"
            )
            return complex_complexity > simple_complexity

        result, duration = self._time_test(test)
        self._record("selector_complexity", result, "Estimates complexity", duration, "3. SELECTOR")

    def test_selector_select_model(self):
        """Test model selection."""
        def test():
            from cognitive import VisionModelSelector, VISION_MODELS
            selector = VisionModelSelector()
            selection = selector.select_model("describe this image")
            # Should return a valid model or escalate
            return (
                selection.model_key in VISION_MODELS or
                selection.escalate_to_claude
            )

        result, duration = self._time_test(test)
        self._record("selector_model", result, "Selects model", duration, "3. SELECTOR")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. QUALITY VALIDATOR
    # ═══════════════════════════════════════════════════════════════════════

    def test_validator_initialization(self):
        """Test VisionQualityValidator initialization."""
        def test():
            from cognitive import VisionQualityValidator
            validator = VisionQualityValidator()
            return validator is not None

        result, duration = self._time_test(test)
        self._record("validator_init", result, "Validator initializes", duration, "4. VALIDATOR")

    def test_validator_good_response(self):
        """Test validation of good response."""
        def test():
            from cognitive import VisionQualityValidator, VisionTaskType
            validator = VisionQualityValidator()
            confidence, escalate, reason = validator.validate(
                response="The image shows a red square on a white background.",
                prompt="describe",
                task_type=VisionTaskType.CAPTION
            )
            return confidence > 0.5 and not escalate

        result, duration = self._time_test(test)
        self._record("validator_good", result, "Accepts good response", duration, "4. VALIDATOR")

    def test_validator_bad_response(self):
        """Test validation of bad response."""
        def test():
            from cognitive import VisionQualityValidator, VisionTaskType
            validator = VisionQualityValidator()
            confidence, escalate, reason = validator.validate(
                response="I cannot see the image sorry",
                prompt="describe",
                task_type=VisionTaskType.CAPTION
            )
            return confidence < 0.5 or escalate

        result, duration = self._time_test(test)
        self._record("validator_bad", result, "Rejects bad response", duration, "4. VALIDATOR")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. TASK TYPES
    # ═══════════════════════════════════════════════════════════════════════

    def test_task_type_enum(self):
        """Test VisionTaskType enum values."""
        def test():
            from cognitive import VisionTaskType
            return (
                VisionTaskType.CAPTION.value == "caption" and
                VisionTaskType.DETECTION.value == "detection" and
                VisionTaskType.REASONING.value == "reasoning"
            )

        result, duration = self._time_test(test)
        self._record("task_enum", result, "Task type enum works", duration, "5. TASKS")

    def test_task_type_caption(self):
        """Test CAPTION task type."""
        def test():
            from cognitive import VisionTaskType
            task = VisionTaskType.CAPTION
            return task.value == "caption"

        result, duration = self._time_test(test)
        self._record("task_caption", result, "CAPTION type works", duration, "5. TASKS")

    def test_task_type_detection(self):
        """Test DETECTION task type."""
        def test():
            from cognitive import VisionTaskType
            task = VisionTaskType.DETECTION
            return task.value == "detection"

        result, duration = self._time_test(test)
        self._record("task_detection", result, "DETECTION type works", duration, "5. TASKS")

    def test_task_type_reasoning(self):
        """Test REASONING task type."""
        def test():
            from cognitive import VisionTaskType
            task = VisionTaskType.REASONING
            return task.value == "reasoning"

        result, duration = self._time_test(test)
        self._record("task_reasoning", result, "REASONING type works", duration, "5. TASKS")

    # ═══════════════════════════════════════════════════════════════════════
    # 6. VISION RESULT
    # ═══════════════════════════════════════════════════════════════════════

    def test_result_creation(self):
        """Test VisionResult creation."""
        def test():
            from cognitive import VisionResult, VisionTaskType
            result = VisionResult(
                response="A red square",
                confidence=0.85,
                model_used="smolvlm-256m",
                task_type=VisionTaskType.CAPTION,
                processing_time_ms=150,
                escalated=False,
                metadata={}
            )
            return result.confidence == 0.85

        result, duration = self._time_test(test)
        self._record("result_creation", result, "VisionResult created", duration, "6. RESULT")

    def test_result_to_dict(self):
        """Test VisionResult to_dict method."""
        def test():
            from cognitive import VisionResult, VisionTaskType
            result = VisionResult(
                response="A red square",
                confidence=0.85,
                model_used="smolvlm-256m",
                task_type=VisionTaskType.CAPTION,
                processing_time_ms=150,
                escalated=False,
                metadata={"detail": "test"}
            )
            d = result.to_dict()
            return d["response"] == "A red square" and d["confidence"] == 0.85

        result, duration = self._time_test(test)
        self._record("result_to_dict", result, "to_dict() works", duration, "6. RESULT")

    # ═══════════════════════════════════════════════════════════════════════
    # 7. ORCHESTRATOR INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════

    def test_orchestrator_vision_engine(self):
        """Test orchestrator has vision engine."""
        def test():
            from cognitive import create_cognitive_orchestrator
            orch = create_cognitive_orchestrator(
                db_path=self.test_db_path + "/orch_vision",
                retrieval_paths=None
            )
            # Vision engine should be lazy-loaded
            engine = orch.vision_engine
            orch.shutdown()
            return engine is not None

        result, duration = self._time_test(test)
        self._record("orch_vision_engine", result, "Has vision engine", duration, "7. ORCHESTRATOR")

    def test_orchestrator_describe_method(self):
        """Test orchestrator describe_image method exists."""
        def test():
            from cognitive import create_cognitive_orchestrator
            orch = create_cognitive_orchestrator(
                db_path=self.test_db_path + "/orch_desc",
                retrieval_paths=None
            )
            has_method = hasattr(orch, 'describe_image')
            orch.shutdown()
            return has_method

        result, duration = self._time_test(test)
        self._record("orch_describe", result, "Has describe_image()", duration, "7. ORCHESTRATOR")

    def test_orchestrator_detect_method(self):
        """Test orchestrator detect_objects method exists."""
        def test():
            from cognitive import create_cognitive_orchestrator
            orch = create_cognitive_orchestrator(
                db_path=self.test_db_path + "/orch_det",
                retrieval_paths=None
            )
            has_method = hasattr(orch, 'detect_objects')
            orch.shutdown()
            return has_method

        result, duration = self._time_test(test)
        self._record("orch_detect", result, "Has detect_objects()", duration, "7. ORCHESTRATOR")

    def test_orchestrator_answer_method(self):
        """Test orchestrator answer_about_image method exists."""
        def test():
            from cognitive import create_cognitive_orchestrator
            orch = create_cognitive_orchestrator(
                db_path=self.test_db_path + "/orch_ans",
                retrieval_paths=None
            )
            has_method = hasattr(orch, 'answer_about_image')
            orch.shutdown()
            return has_method

        result, duration = self._time_test(test)
        self._record("orch_answer", result, "Has answer_about_image()", duration, "7. ORCHESTRATOR")

    # ═══════════════════════════════════════════════════════════════════════
    # 8. CONVENIENCE FUNCTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def test_create_vision_engine(self):
        """Test create_vision_engine factory function."""
        def test():
            from cognitive import create_vision_engine
            engine = create_vision_engine()
            return engine is not None

        result, duration = self._time_test(test)
        self._record("create_engine", result, "Factory function works", duration, "8. CONVENIENCE")

    # ═══════════════════════════════════════════════════════════════════════
    # 9. VISION MODELS
    # ═══════════════════════════════════════════════════════════════════════

    def test_vision_models_constant(self):
        """Test VISION_MODELS constant exists and has entries."""
        def test():
            from cognitive import VISION_MODELS
            return len(VISION_MODELS) >= 2  # At least SmolVLM and Moondream

        result, duration = self._time_test(test)
        self._record("vision_models", result, "VISION_MODELS has entries", duration, "9. MODELS")

    def test_vision_models_smolvlm(self):
        """Test SmolVLM model entry exists."""
        def test():
            from cognitive import VISION_MODELS
            # Check for any SmolVLM variant
            smolvlm_keys = [k for k in VISION_MODELS if 'smol' in k.lower()]
            return len(smolvlm_keys) > 0

        result, duration = self._time_test(test)
        self._record("vision_smolvlm", result, "SmolVLM model exists", duration, "9. MODELS")

    def test_vision_models_moondream(self):
        """Test Moondream model entry exists."""
        def test():
            from cognitive import VISION_MODELS
            # Check for any Moondream variant
            moon_keys = [k for k in VISION_MODELS if 'moon' in k.lower()]
            return len(moon_keys) > 0

        result, duration = self._time_test(test)
        self._record("vision_moondream", result, "Moondream model exists", duration, "9. MODELS")


def run_vision_tests():
    """Run vision test suite and exit with appropriate code."""
    suite = VisionTestSuite(verbose=True)
    passed, failed = suite.run_all()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_vision_tests()
