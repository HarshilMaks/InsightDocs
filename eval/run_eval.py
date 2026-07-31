"""InsightDocs Evaluation Harness

Measures retrieval and answer quality against a golden dataset of
questions with known-correct answers and expected source citations.

Usage:
    # Against a real running backend (requires API at localhost:8000):
    python eval/run_eval.py --mode live --token <jwt_token>

    # Against mocked retrieval results (for CI, no services needed):
    python eval/run_eval.py --mode mock

Metrics produced:
    - Answer Grounding Rate: % of answers containing expected keywords
    - Source Recall@K: % of expected source content found in retrieved chunks
    - Citation Coverage: % of eval cases where at least one source matched

Exit code:
    0 if all metrics meet minimum thresholds (configurable via CLI args)
    1 if any metric is below threshold (acts as a CI gate)
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_grounding_rate(results: list[dict]) -> float:
    """Fraction of eval cases where the answer contains all expected keywords."""
    if not results:
        return 0.0
    grounded = sum(1 for r in results if r["answer_grounded"])
    return grounded / len(results)


def compute_source_recall(results: list[dict]) -> float:
    """Average fraction of expected source substrings found in retrieved chunks."""
    if not results:
        return 0.0
    recalls = [r["source_recall"] for r in results]
    return sum(recalls) / len(recalls)


def compute_citation_coverage(results: list[dict]) -> float:
    """Fraction of eval cases where at least one expected source was retrieved."""
    if not results:
        return 0.0
    covered = sum(1 for r in results if r["source_recall"] > 0)
    return covered / len(results)


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def evaluate_case(case: dict, answer: str, sources: list[dict]) -> dict:
    """Evaluate a single case against the model's response."""
    expected_keywords = case.get("expected_answer_contains", [])
    answer_lower = answer.lower()
    answer_grounded = all(kw.lower() in answer_lower for kw in expected_keywords)

    expected_sources = case.get("expected_sources", [])
    matched_sources = 0
    for expected in expected_sources:
        substring = expected.get("content_substring", "").lower()
        if not substring:
            continue
        for source in sources:
            content = (source.get("content") or source.get("content_preview") or "").lower()
            if substring in content:
                matched_sources += 1
                break

    source_recall = matched_sources / len(expected_sources) if expected_sources else 1.0

    return {
        "id": case["id"],
        "query": case["query"],
        "answer_grounded": answer_grounded,
        "source_recall": source_recall,
    }


# ---------------------------------------------------------------------------
# Mock mode: simulates retrieval using the golden dataset's own expected
# content as if the system returned it. This validates the eval framework
# itself and serves as a CI baseline even without running services.
# ---------------------------------------------------------------------------


def run_mock_eval(dataset: list[dict]) -> list[dict]:
    """Run evaluation in mock mode (no backend required)."""
    results = []
    for case in dataset:
        # Simulate a "perfect" retrieval: the answer contains the expected
        # keywords and the sources contain the expected substrings.
        mock_answer = " ".join(case.get("expected_answer_contains", []))
        mock_sources = [
            {"content": s.get("content_substring", "")}
            for s in case.get("expected_sources", [])
        ]
        results.append(evaluate_case(case, mock_answer, mock_sources))
    return results


# ---------------------------------------------------------------------------
# Live mode: queries the real backend API
# ---------------------------------------------------------------------------


def run_live_eval(dataset: list[dict], base_url: str, token: str) -> list[dict]:
    """Run evaluation against a live backend."""
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' package required for live mode. Install with: pip install requests")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    results = []

    for case in dataset:
        try:
            resp = requests.post(
                f"{base_url}/api/v1/query/",
                headers=headers,
                json={"query": case["query"], "top_k": 5},
                timeout=60,
            )
            if resp.status_code != 200:
                print(f"  WARN: {case['id']} returned {resp.status_code}: {resp.text[:100]}")
                results.append(evaluate_case(case, "", []))
                continue

            data = resp.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            results.append(evaluate_case(case, answer, sources))
        except Exception as e:
            print(f"  ERROR: {case['id']} failed: {e}")
            results.append(evaluate_case(case, "", []))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="InsightDocs Evaluation Harness")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--token", default=None, help="JWT token for live mode")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--min-grounding", type=float, default=0.8, help="Minimum grounding rate (0-1)")
    parser.add_argument("--min-recall", type=float, default=0.6, help="Minimum source recall (0-1)")
    parser.add_argument("--min-coverage", type=float, default=0.6, help="Minimum citation coverage (0-1)")
    args = parser.parse_args()

    dataset_path = Path(__file__).parent / "golden_dataset.json"
    if not dataset_path.exists():
        print(f"ERROR: Golden dataset not found at {dataset_path}")
        sys.exit(1)

    dataset = json.loads(dataset_path.read_text())
    print(f"Loaded {len(dataset)} evaluation cases from {dataset_path.name}")
    print(f"Mode: {args.mode}")
    print()

    if args.mode == "mock":
        results = run_mock_eval(dataset)
    else:
        if not args.token:
            print("ERROR: --token required for live mode")
            sys.exit(1)
        results = run_live_eval(dataset, args.base_url, args.token)

    grounding = compute_grounding_rate(results)
    recall = compute_source_recall(results)
    coverage = compute_citation_coverage(results)

    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Answer Grounding Rate:  {grounding:.1%}  (threshold: {args.min_grounding:.1%})")
    print(f"  Source Recall@K:        {recall:.1%}  (threshold: {args.min_recall:.1%})")
    print(f"  Citation Coverage:      {coverage:.1%}  (threshold: {args.min_coverage:.1%})")
    print("=" * 60)

    # Per-case details
    print("\nPer-case breakdown:")
    for r in results:
        status = "✓" if r["answer_grounded"] and r["source_recall"] > 0 else "✗"
        print(f"  {status} {r['id']}: grounded={r['answer_grounded']}, recall={r['source_recall']:.0%}")

    # CI gate
    passed = True
    if grounding < args.min_grounding:
        print(f"\nFAIL: Grounding rate {grounding:.1%} < {args.min_grounding:.1%}")
        passed = False
    if recall < args.min_recall:
        print(f"\nFAIL: Source recall {recall:.1%} < {args.min_recall:.1%}")
        passed = False
    if coverage < args.min_coverage:
        print(f"\nFAIL: Citation coverage {coverage:.1%} < {args.min_coverage:.1%}")
        passed = False

    if passed:
        print("\nPASS: All metrics meet minimum thresholds.")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
