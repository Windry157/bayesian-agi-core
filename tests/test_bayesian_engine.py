import pytest
from src.mcp.bayesian import BayesianEngine, ActiveInferenceEngine


class TestBayesianEngine:
    def test_evaluate_confidence_all_success(self):
        result = BayesianEngine.evaluate_confidence([True, True, True])
        assert result["mean"] > 0.5
        assert result["confidence"] > 0

    def test_evaluate_confidence_all_failure(self):
        result = BayesianEngine.evaluate_confidence([False, False, False])
        assert result["mean"] < 0.5

    def test_evaluate_confidence_mixed(self):
        result = BayesianEngine.evaluate_confidence([True, False, True, False])
        assert 0 < result["mean"] < 1

    def test_evaluate_confidence_empty(self):
        result = BayesianEngine.evaluate_confidence([])
        assert result["mean"] == 0.5

    def test_propagate_confidence_empty(self):
        assert BayesianEngine.propagate_confidence([]) == 0.0

    def test_propagate_confidence_single(self):
        result = BayesianEngine.propagate_confidence([0.8])
        assert result == 0.8

    def test_propagate_confidence_multiple(self):
        result = BayesianEngine.propagate_confidence([0.8, 0.9, 0.7])
        assert 0 < result < 1

    def test_propagate_confidence_inconsistent(self):
        result = BayesianEngine.propagate_confidence([0.9, 0.1])
        assert result < 0.5


class TestActiveInferenceEngine:
    def test_expected_free_energy(self):
        result = ActiveInferenceEngine.expected_free_energy("state", "goal", "action")
        assert "expected_free_energy" in result
        assert "epistemic_value" in result
        assert "pragmatic_value" in result
        assert "complexity_cost" in result

    def test_select_action_basic(self):
        result = ActiveInferenceEngine.select_action("start", "end", ["a1", "a2"])
        assert "recommended_action" in result
        assert result["recommended_action"] is not None
        assert len(result["action_probabilities"]) == 2
        assert len(result["reasoning_chain"]) > 0

    def test_select_action_with_constraints(self):
        result = ActiveInferenceEngine.select_action("start", "end", ["a1"], ["must"])
        assert result["recommended_action"] == "a1"

    def test_select_action_single(self):
        result = ActiveInferenceEngine.select_action("s", "g", ["only_action"])
        assert result["recommended_action"] == "only_action"

    def test_action_probabilities_sum(self):
        result = ActiveInferenceEngine.select_action("s", "g", ["a", "b", "c"])
        total = sum(p["probability"] for p in result["action_probabilities"])
        assert total == pytest.approx(1.0, abs=0.01)

    def test_confidence_present(self):
        result = ActiveInferenceEngine.select_action("s", "g", ["a"])
        assert "confidence" in result
