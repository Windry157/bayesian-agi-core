import math
import hashlib
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from src.mcp.common import sigmoid, beta_posterior, beta_mean


class BayesianEngine:
    @staticmethod
    def evaluate_confidence(observations: List[bool], prior_alpha: float = 1, prior_beta: float = 1) -> Dict[str, Any]:
        successes = sum(1 for o in observations if o)
        failures = len(observations) - successes
        alpha_post, beta_post = beta_posterior(prior_alpha, prior_beta, successes, failures)
        mean = beta_mean(alpha_post, beta_post)
        precision = alpha_post + beta_post
        confidence = 1.0 - (1.0 / math.sqrt(precision + 1))
        std = math.sqrt((alpha_post * beta_post) / ((alpha_post + beta_post) ** 2 * (alpha_post + beta_post + 1)))
        ci_lower = max(0.0, mean - 1.96 * std)
        ci_upper = min(1.0, mean + 1.96 * std)
        return {
            "posterior_alpha": alpha_post,
            "posterior_beta": beta_post,
            "mean": round(mean, 4),
            "confidence": round(max(0, confidence), 4),
            "credible_interval": [round(ci_lower, 4), round(ci_upper, 4)],
            "sample_size": len(observations)
        }

    @staticmethod
    def propagate_confidence(step_confidences: List[float]) -> float:
        if not step_confidences:
            return 0.0
        product = 1.0
        for c in step_confidences:
            product *= max(c, 0.01)
        n = len(step_confidences)
        geometric_mean = product ** (1.0 / n)
        if n > 1:
            variance = statistics.variance(step_confidences) if len(set(step_confidences)) > 1 else 0
            consistency = 1.0 - min(variance * 2, 0.5)
        else:
            consistency = 1.0
        return round(geometric_mean * consistency, 4)


class ActiveInferenceEngine:
    @staticmethod
    def expected_free_energy(state: str, goal: str, action: str) -> Dict[str, float]:
        h = int(hashlib.md5(f"{state}:{action}".encode()).hexdigest()[:8], 16)
        gh = int(hashlib.md5(goal.encode()).hexdigest()[:8], 16)
        epistemic_value = sigmoid((h % 1000) / 1000)
        pragmatic_value = sigmoid((gh % 1000) / 1000)
        complexity_cost = len(action) / 100
        G = -(epistemic_value * 0.4 + pragmatic_value * 0.6) + complexity_cost
        return {
            "expected_free_energy": round(G, 4),
            "epistemic_value": round(epistemic_value, 4),
            "pragmatic_value": round(pragmatic_value, 4),
            "complexity_cost": round(complexity_cost, 4)
        }

    @staticmethod
    def select_action(state: str, goal: str, actions: List[str], constraints: Optional[List[str]] = None) -> Dict[str, Any]:
        constraints = constraints or []
        action_evals = []
        for action in actions:
            fe = ActiveInferenceEngine.expected_free_energy(state, goal, action)
            action_evals.append({"action": action, **fe})
        action_evals.sort(key=lambda x: x["expected_free_energy"])
        feasible = action_evals[:]
        recommended = feasible[0] if feasible else None
        if feasible:
            energies = [a["expected_free_energy"] for a in feasible]
            min_energy = min(energies)
            probs = []
            for e in energies:
                p = math.exp(-(e - min_energy))
                probs.append(p)
            prob_sum = sum(probs)
            for i, ae in enumerate(feasible):
                ae["probability"] = round(probs[i] / prob_sum, 4) if prob_sum > 0 else 0
        reasoning = [
            f"当前状态: {state}",
            f"目标状态: {goal}",
            f"备选动作: {', '.join(actions)}",
            f"约束条件: {', '.join(constraints) if constraints else '无'}",
            f"选择原则: 最小化预期自由能",
            f"推荐动作: {recommended['action'] if recommended else '无可行动作'}"
        ]
        return {
            "recommended_action": recommended["action"] if recommended else None,
            "expected_free_energy": recommended["expected_free_energy"] if recommended else None,
            "action_probabilities": action_evals,
            "reasoning_chain": reasoning,
            "confidence": round(1.0 - (recommended["expected_free_energy"] if recommended else 0.5), 4),
            "timestamp": datetime.now().isoformat()
        }
