"""Test that the evaluation harness runs correctly in mock mode.

This ensures the eval framework itself doesn't regress, even when the
full retrieval stack isn't available — it validates the metric computation
logic and golden dataset format.
"""
import subprocess
import sys
from pathlib import Path


def test_eval_harness_mock_mode_passes():
    """The eval script in mock mode should exit 0 with all metrics at 100%
    (since mock mode simulates perfect retrieval using the golden dataset's
    own expected content)."""
    eval_script = Path(__file__).parent.parent.parent / "eval" / "run_eval.py"
    assert eval_script.exists(), f"Eval script not found at {eval_script}"

    result = subprocess.run(
        [sys.executable, str(eval_script), "--mode", "mock"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Eval harness failed:\n{result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout
    assert "Answer Grounding Rate:  100.0%" in result.stdout
    assert "Source Recall@K:        100.0%" in result.stdout
    assert "Citation Coverage:      100.0%" in result.stdout


def test_eval_harness_detects_failure_below_threshold():
    """The eval script should exit 1 when thresholds are set impossibly
    high, verifying the CI gate logic actually blocks on regression."""
    eval_script = Path(__file__).parent.parent.parent / "eval" / "run_eval.py"

    result = subprocess.run(
        [sys.executable, str(eval_script), "--mode", "mock", "--min-grounding", "1.01"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # 1.01 is impossible to meet (max is 1.0), so the gate should fail
    assert result.returncode == 1, f"Expected failure but got exit 0:\n{result.stdout}"
    assert "FAIL" in result.stdout
