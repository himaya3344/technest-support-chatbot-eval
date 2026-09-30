"""Tests for metric calculations."""

import pandas as pd

from src.metrics import compute_metrics


def test_metrics_compute_known_accuracy_and_action_scores() -> None:
	data = pd.DataFrame(
		[
			{"case_id": "a", "category": "standard_faq", "expected_action": "answer", "action": "answer", "action_correct": True, "must_include_passed": True, "must_not_include_violation": False, "json_valid": True, "hallucination": False, "judge_score": 5, "injection_success": False, "run_index": 0, "latency_s": 1.0, "input_tokens": 10, "output_tokens": 5},
			{"case_id": "b", "category": "escalation", "expected_action": "escalate", "action": "refuse", "action_correct": False, "must_include_passed": False, "must_not_include_violation": True, "json_valid": False, "hallucination": True, "judge_score": 2, "injection_success": False, "run_index": 0, "latency_s": 3.0, "input_tokens": 20, "output_tokens": 7},
		]
	)

	metrics, tables = compute_metrics(data, seed=7,)

	assert metrics["overall_action_accuracy"] == 0.5
	assert metrics["json_compliance_rate"] == 0.5
	assert metrics["action_metrics"]["escalate"]["recall"] == 0.0
	assert metrics["total_input_tokens"] == 30
	assert set(tables) == {"by_category", "by_action", "judge_by_category", "run_consistency"}