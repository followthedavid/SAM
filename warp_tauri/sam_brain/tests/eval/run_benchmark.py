#!/usr/bin/env python3
"""
SAM Benchmark Evaluation Runner

Sends curated prompts to the SAM API (localhost:8765) and scores responses
across 6 domains: coding, chat, roleplay, reasoning, macOS, reverse_engineering.

Scoring dimensions per response:
  - keyword_match:  % of expected_keywords found in response
  - length_score:   penalizes too-short or too-long responses
  - quality_score:  detects hedging, repetition, refusal, truncation
  - confidence:     from API response field if present
  - composite:      weighted combination of all scores

Usage:
    python3 run_benchmark.py                          # Run all prompts
    python3 run_benchmark.py --domain coding          # Run one domain
    python3 run_benchmark.py --domain coding --domain reasoning
    python3 run_benchmark.py --compare results/a.json results/b.json
    python3 run_benchmark.py --url http://host:port   # Custom API URL
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Quality patterns drawn from cognitive/quality_validator.py
# ---------------------------------------------------------------------------

HEDGING_PATTERNS = [
    r"i('m| am) not (sure|certain)",
    r"i (don't|do not) (really )?know",
    r"(maybe|perhaps|possibly) (you|we|i)",
    r"(could|might|may) be",
    r"i('m| am) (just|only) (a|an)",
]

REFUSAL_PATTERNS = [
    r"i (can't|cannot|won't|will not) (help|assist|do)",
    r"(inappropriate|unethical|harmful|dangerous)",
    r"beyond my (capabilities|ability|scope)",
    r"(against|violates) (my|the) (guidelines|policies)",
    r"i('m| am) not able to",
]

TRUNCATION_PATTERNS = [
    r"\.{3,}$",
    r"\u2026$",
    r"and then$",
    r"such as$",
]

REPETITION_PHRASE = r"(.{15,}?)\1{2,}"
REPETITION_WORD = r"\b(\w+)(?:\s+\1){4,}\b"

STOP_TOKENS = [
    "<|im_end|>",
    "<|end|>",
    "<|endoftext|>",
    "</s>",
    "<|assistant|>",
    "<|user|>",
    "[INST]",
    "[/INST]",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_DIR = Path(__file__).resolve().parent
PROMPTS_FILE = EVAL_DIR / "benchmark_prompts.json"
RESULTS_DIR = EVAL_DIR / "results"
DEFAULT_API_URL = "http://localhost:8765"
DEFAULT_ENDPOINT = "/api/query"
REQUEST_TIMEOUT = 60  # seconds per prompt


# ============================================================================
# Scoring functions
# ============================================================================


def score_keyword_match(response: str, expected_keywords: List[str]) -> float:
    """Return fraction of expected keywords found (case-insensitive)."""
    if not expected_keywords:
        return 1.0  # no expectations = full marks
    response_lower = response.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    return hits / len(expected_keywords)


def score_length(response: str, domain: str) -> float:
    """
    Score response length appropriateness.

    Short responses are penalised more for technical domains.
    Returns 0.0-1.0.
    """
    word_count = len(response.split())

    # Domain-specific ideal ranges
    ideal_ranges = {
        "coding": (30, 400),
        "chat": (10, 200),
        "roleplay": (15, 250),
        "reasoning": (25, 350),
        "macos": (20, 350),
        "reverse_engineering": (25, 400),
    }
    lo, hi = ideal_ranges.get(domain, (20, 300))

    if word_count < 3:
        return 0.0
    if lo <= word_count <= hi:
        return 1.0
    if word_count < lo:
        return max(0.0, word_count / lo)
    # over hi
    return max(0.3, 1.0 - (word_count - hi) / (hi * 2))


def score_quality(response: str) -> Tuple[float, List[str]]:
    """
    Detect quality issues. Returns (score, list_of_issues).

    Score starts at 1.0 and is reduced by detected problems.
    """
    score = 1.0
    issues: List[str] = []
    resp_lower = response.lower()

    # Hedging
    for pat in HEDGING_PATTERNS:
        if re.search(pat, resp_lower):
            score -= 0.10
            issues.append("hedging")
            break

    # Refusal
    for pat in REFUSAL_PATTERNS:
        if re.search(pat, resp_lower):
            score -= 0.20
            issues.append("refusal")
            break

    # Truncation
    for pat in TRUNCATION_PATTERNS:
        if re.search(pat, response.strip()):
            score -= 0.10
            issues.append("truncated")
            break

    # Repetition (phrase)
    if re.search(REPETITION_PHRASE, response):
        score -= 0.30
        issues.append("repetition_phrase")

    # Repetition (word)
    if re.search(REPETITION_WORD, response, re.IGNORECASE):
        score -= 0.20
        issues.append("repetition_word")

    # Stop tokens leaked
    for tok in STOP_TOKENS:
        if tok in response:
            score -= 0.10
            issues.append("stop_token_leak")
            break

    # Code block balance for coding prompts
    open_blocks = response.count("```")
    if open_blocks % 2 != 0:
        score -= 0.10
        issues.append("unclosed_code_block")

    return max(0.0, score), issues


def composite_score(
    keyword: float, length: float, quality: float, confidence: float
) -> float:
    """Weighted composite of all score dimensions."""
    return (
        keyword * 0.35
        + length * 0.15
        + quality * 0.30
        + confidence * 0.20
    )


# ============================================================================
# API interaction
# ============================================================================


def query_sam(
    prompt: str, api_url: str, endpoint: str, timeout: int = REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """
    Send a prompt to the SAM API.

    Returns dict with keys: response, confidence, response_time_ms, error.
    """
    import requests  # deferred so --compare mode works without requests

    url = api_url.rstrip("/") + endpoint
    payload = {"query": prompt}

    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        elapsed_ms = int((time.time() - start) * 1000)
        resp.raise_for_status()
        data = resp.json()
        return {
            "response": data.get("response", ""),
            "confidence": float(data.get("confidence", 0.5)),
            "response_time_ms": elapsed_ms,
            "error": None,
        }
    except requests.ConnectionError:
        return {
            "response": "",
            "confidence": 0.0,
            "response_time_ms": int((time.time() - start) * 1000),
            "error": "connection_refused",
        }
    except requests.Timeout:
        return {
            "response": "",
            "confidence": 0.0,
            "response_time_ms": int((time.time() - start) * 1000),
            "error": "timeout",
        }
    except Exception as exc:
        return {
            "response": "",
            "confidence": 0.0,
            "response_time_ms": int((time.time() - start) * 1000),
            "error": str(exc),
        }


# ============================================================================
# Benchmark runner
# ============================================================================


def load_prompts(path: Path, domains: Optional[List[str]] = None) -> List[Dict]:
    """Load prompts from JSON, optionally filtering by domain."""
    with open(path) as f:
        data = json.load(f)
    prompts = data.get("prompts", [])
    if domains:
        prompts = [p for p in prompts if p["domain"] in domains]
    return prompts


def run_benchmark(
    prompts: List[Dict],
    api_url: str = DEFAULT_API_URL,
    endpoint: str = DEFAULT_ENDPOINT,
) -> Dict[str, Any]:
    """
    Execute benchmark against the SAM API.

    Returns a full results dict ready to be serialised.
    """
    results: List[Dict[str, Any]] = []
    domain_scores: Dict[str, List[float]] = {}
    total_time_ms = 0
    errors = 0

    print(f"\nRunning benchmark: {len(prompts)} prompts")
    print(f"API: {api_url}{endpoint}")
    print("-" * 60)

    for i, prompt_data in enumerate(prompts, 1):
        pid = prompt_data["id"]
        domain = prompt_data["domain"]
        prompt_text = prompt_data["prompt"]
        expected_kw = prompt_data.get("expected_keywords", [])
        min_conf = prompt_data.get("min_confidence", 0.5)
        difficulty = prompt_data.get("difficulty", "medium")

        sys.stdout.write(f"  [{i:3d}/{len(prompts)}] {pid:<12s} ... ")
        sys.stdout.flush()

        api_result = query_sam(prompt_text, api_url, endpoint)

        if api_result["error"]:
            print(f"ERROR: {api_result['error']}")
            errors += 1
            results.append({
                "id": pid,
                "domain": domain,
                "difficulty": difficulty,
                "prompt": prompt_text,
                "response": "",
                "error": api_result["error"],
                "scores": {
                    "keyword_match": 0.0,
                    "length_score": 0.0,
                    "quality_score": 0.0,
                    "confidence": 0.0,
                    "composite": 0.0,
                },
                "quality_issues": [],
                "passed": False,
                "response_time_ms": api_result["response_time_ms"],
            })
            continue

        resp_text = api_result["response"]
        total_time_ms += api_result["response_time_ms"]

        # --- Score ---
        kw_score = score_keyword_match(resp_text, expected_kw)
        len_score = score_length(resp_text, domain)
        qual_score, qual_issues = score_quality(resp_text)
        conf_score = api_result["confidence"]
        comp = composite_score(kw_score, len_score, qual_score, conf_score)

        passed = comp >= min_conf

        # Track domain scores
        domain_scores.setdefault(domain, []).append(comp)

        status = "PASS" if passed else "FAIL"
        print(f"{status}  composite={comp:.2f}  kw={kw_score:.2f}  qual={qual_score:.2f}  {api_result['response_time_ms']}ms")

        results.append({
            "id": pid,
            "domain": domain,
            "difficulty": difficulty,
            "prompt": prompt_text,
            "response": resp_text[:2000],  # cap stored response
            "error": None,
            "scores": {
                "keyword_match": round(kw_score, 4),
                "length_score": round(len_score, 4),
                "quality_score": round(qual_score, 4),
                "confidence": round(conf_score, 4),
                "composite": round(comp, 4),
            },
            "quality_issues": qual_issues,
            "passed": passed,
            "response_time_ms": api_result["response_time_ms"],
        })

    # --- Aggregate ---
    scored = [r for r in results if r["error"] is None]
    overall_composite = (
        sum(r["scores"]["composite"] for r in scored) / len(scored) if scored else 0.0
    )
    pass_count = sum(1 for r in results if r["passed"])

    domain_summary = {}
    for dom, scores in domain_scores.items():
        domain_summary[dom] = {
            "count": len(scores),
            "mean": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "min": round(min(scores), 4) if scores else 0.0,
            "max": round(max(scores), 4) if scores else 0.0,
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "benchmark_version": "1.0.0",
        "timestamp": timestamp,
        "api_url": api_url,
        "total_prompts": len(prompts),
        "total_scored": len(scored),
        "total_errors": errors,
        "pass_count": pass_count,
        "fail_count": len(prompts) - pass_count,
        "pass_rate": round(pass_count / len(prompts), 4) if prompts else 0.0,
        "overall_composite": round(overall_composite, 4),
        "total_time_ms": total_time_ms,
        "avg_time_ms": round(total_time_ms / len(scored), 1) if scored else 0.0,
        "domain_summary": domain_summary,
        "results": results,
    }

    return output


# ============================================================================
# Summary printing
# ============================================================================


def print_summary(data: Dict[str, Any]) -> None:
    """Print a human-readable summary."""
    print("\n" + "=" * 60)
    print("  SAM BENCHMARK RESULTS")
    print("=" * 60)
    print(f"  Timestamp:        {data['timestamp']}")
    print(f"  API:              {data['api_url']}")
    print(f"  Prompts:          {data['total_prompts']}")
    print(f"  Errors:           {data['total_errors']}")
    print(f"  Pass / Fail:      {data['pass_count']} / {data['fail_count']}")
    print(f"  Pass Rate:        {data['pass_rate']:.1%}")
    print(f"  Overall Score:    {data['overall_composite']:.3f}")
    print(f"  Avg Response:     {data['avg_time_ms']:.0f} ms")
    print(f"  Total Time:       {data['total_time_ms']} ms")
    print()
    print("  Domain Breakdown:")
    print("  " + "-" * 50)
    for dom, info in sorted(data["domain_summary"].items()):
        bar_len = int(info["mean"] * 30)
        bar = "#" * bar_len + "." * (30 - bar_len)
        print(f"  {dom:<22s} {info['mean']:.3f}  [{bar}]  n={info['count']}")
    print()

    # Failures detail
    failures = [r for r in data["results"] if not r["passed"]]
    if failures:
        print("  Failed Prompts:")
        print("  " + "-" * 50)
        for r in failures:
            reason = r["error"] or ", ".join(r["quality_issues"]) or "low score"
            print(f"  {r['id']:<14s}  {r['scores']['composite']:.2f}  ({reason})")
        print()

    print("=" * 60)


# ============================================================================
# Compare mode
# ============================================================================


def compare_results(path_a: str, path_b: str) -> None:
    """Compare two benchmark result files and print a regression report."""
    with open(path_a) as f:
        a = json.load(f)
    with open(path_b) as f:
        b = json.load(f)

    print("\n" + "=" * 70)
    print("  SAM BENCHMARK COMPARISON")
    print("=" * 70)
    print(f"  Run A: {a['timestamp']}  (overall {a['overall_composite']:.3f})")
    print(f"  Run B: {b['timestamp']}  (overall {b['overall_composite']:.3f})")
    diff = b["overall_composite"] - a["overall_composite"]
    direction = "IMPROVED" if diff > 0 else "REGRESSED" if diff < 0 else "UNCHANGED"
    print(f"  Delta: {diff:+.4f}  ({direction})")
    print()

    # Domain comparison
    all_domains = sorted(set(list(a.get("domain_summary", {}).keys()) + list(b.get("domain_summary", {}).keys())))
    print("  Domain Comparison:")
    print("  " + "-" * 60)
    print(f"  {'Domain':<22s} {'Run A':>8s} {'Run B':>8s} {'Delta':>8s}  Status")
    print("  " + "-" * 60)
    for dom in all_domains:
        sa = a.get("domain_summary", {}).get(dom, {}).get("mean", 0.0)
        sb = b.get("domain_summary", {}).get(dom, {}).get("mean", 0.0)
        d = sb - sa
        st = "+" if d > 0.01 else "-" if d < -0.01 else "="
        print(f"  {dom:<22s} {sa:>8.3f} {sb:>8.3f} {d:>+8.4f}  {st}")
    print()

    # Per-prompt regressions
    a_by_id = {r["id"]: r for r in a.get("results", [])}
    b_by_id = {r["id"]: r for r in b.get("results", [])}

    regressions = []
    improvements = []
    for pid in sorted(set(list(a_by_id.keys()) + list(b_by_id.keys()))):
        ra = a_by_id.get(pid, {}).get("scores", {}).get("composite", 0.0)
        rb = b_by_id.get(pid, {}).get("scores", {}).get("composite", 0.0)
        d = rb - ra
        if d < -0.05:
            regressions.append((pid, ra, rb, d))
        elif d > 0.05:
            improvements.append((pid, ra, rb, d))

    if regressions:
        print(f"  REGRESSIONS ({len(regressions)}):")
        for pid, ra, rb, d in sorted(regressions, key=lambda x: x[3]):
            print(f"    {pid:<14s}  {ra:.3f} -> {rb:.3f}  ({d:+.3f})")
        print()

    if improvements:
        print(f"  IMPROVEMENTS ({len(improvements)}):")
        for pid, ra, rb, d in sorted(improvements, key=lambda x: -x[3]):
            print(f"    {pid:<14s}  {ra:.3f} -> {rb:.3f}  ({d:+.3f})")
        print()

    # Pass rate comparison
    pa = a.get("pass_rate", 0)
    pb = b.get("pass_rate", 0)
    print(f"  Pass Rate: {pa:.1%} -> {pb:.1%}  ({pb - pa:+.1%})")

    # Response time comparison
    ta = a.get("avg_time_ms", 0)
    tb = b.get("avg_time_ms", 0)
    print(f"  Avg Time:  {ta:.0f}ms -> {tb:.0f}ms  ({tb - ta:+.0f}ms)")

    print("=" * 70)


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAM Benchmark Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_benchmark.py                            # Full run
  python3 run_benchmark.py --domain coding            # One domain
  python3 run_benchmark.py --domain coding --domain reasoning
  python3 run_benchmark.py --compare results/a.json results/b.json
  python3 run_benchmark.py --url http://localhost:9000 --endpoint /v1/chat
""",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("RUN_A", "RUN_B"),
        help="Compare two result files instead of running a benchmark.",
    )
    parser.add_argument(
        "--domain",
        action="append",
        choices=["coding", "chat", "roleplay", "reasoning", "macos", "reverse_engineering"],
        help="Limit to specific domain(s). Can be repeated.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_API_URL,
        help=f"SAM API base URL (default: {DEFAULT_API_URL}).",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"API endpoint path (default: {DEFAULT_ENDPOINT}).",
    )
    parser.add_argument(
        "--prompts",
        default=str(PROMPTS_FILE),
        help="Path to benchmark_prompts.json.",
    )
    parser.add_argument(
        "--out",
        help="Custom output path for results JSON. Default: results/<timestamp>.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List prompts that would be run without calling the API.",
    )

    args = parser.parse_args()

    # --- Compare mode ---
    if args.compare:
        compare_results(args.compare[0], args.compare[1])
        return

    # --- Load prompts ---
    prompts_path = Path(args.prompts)
    if not prompts_path.exists():
        print(f"ERROR: Prompts file not found: {prompts_path}")
        sys.exit(1)

    prompts = load_prompts(prompts_path, domains=args.domain)
    if not prompts:
        print("ERROR: No prompts matched the selected domain(s).")
        sys.exit(1)

    # --- Dry run ---
    if args.dry_run:
        print(f"Dry run: {len(prompts)} prompts loaded")
        for p in prompts:
            print(f"  {p['id']:<14s}  [{p['domain']:<20s}]  {p['difficulty']:<8s}  {p['prompt'][:60]}")
        return

    # --- Pre-flight check ---
    print("SAM Benchmark Evaluation Suite")
    print("=" * 60)
    print(f"Prompts file: {prompts_path}")
    print(f"Prompts:      {len(prompts)}")
    if args.domain:
        print(f"Domains:      {', '.join(args.domain)}")
    else:
        print("Domains:      all")

    # Quick connectivity check
    try:
        import requests
        r = requests.get(args.url.rstrip("/") + "/api/health", timeout=5)
        print(f"API health:   OK ({r.status_code})")
    except Exception:
        print("API health:   UNREACHABLE")
        print()
        print("WARNING: SAM API is not responding at " + args.url)
        print("Make sure `python3 sam_api.py server 8765` is running.")
        print()
        answer = input("Continue anyway? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    # --- Run benchmark ---
    output = run_benchmark(prompts, api_url=args.url, endpoint=args.endpoint)

    # --- Save results ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = RESULTS_DIR / f"{output['timestamp']}.json"

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved: {out_path}")

    # --- Print summary ---
    print_summary(output)


if __name__ == "__main__":
    main()
