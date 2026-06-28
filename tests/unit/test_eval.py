from __future__ import annotations

import pytest

from inference_engine.benchmarking.eval import EvalType, evaluate_text, parse_eval_spec


def test_parse_eval_spec_for_json_keys() -> None:
    spec = parse_eval_spec({"type": "json_keys", "required": ["status", "reason"]})

    assert spec is not None
    assert spec.eval_type == EvalType.JSON_KEYS
    assert spec.required == ["status", "reason"]


def test_json_keys_eval_passes_valid_object() -> None:
    spec = parse_eval_spec({"type": "json_keys", "required": ["status", "reason"]})

    result = evaluate_text('{"status":"ok","reason":"valid"}', spec)

    assert result is not None
    assert result.passed is True
    assert result.score == 1.0


def test_json_keys_eval_fails_invalid_json() -> None:
    spec = parse_eval_spec({"type": "json_keys", "required": ["status"]})

    result = evaluate_text("status: ok", spec)

    assert result is not None
    assert result.passed is False
    assert "invalid JSON" in result.reason


def test_contains_all_eval_scores_partial_match() -> None:
    spec = parse_eval_spec({"type": "contains_all", "required": ["cost", "quality"]})

    result = evaluate_text("Cost-aware routing matters.", spec)

    assert result is not None
    assert result.passed is False
    assert result.score == 0.5


def test_exact_match_eval_ignores_case_by_default() -> None:
    spec = parse_eval_spec({"type": "exact_match", "expected": "positive"})

    result = evaluate_text("Positive", spec)

    assert result is not None
    assert result.passed is True


def test_parse_eval_spec_rejects_invalid_required() -> None:
    with pytest.raises(ValueError, match="eval.required"):
        parse_eval_spec({"type": "contains_all", "required": "cost"})
