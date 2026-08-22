import math
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_INPUT_TOKENS = 8192


class ErrorCode(Enum):
    MEMORY_LAYER_NOT_FOUND = "MEMORY_LAYER_NOT_FOUND"
    INFERENCE_TIMEOUT = "INFERENCE_TIMEOUT"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INVALID_CHAIN = "INVALID_CHAIN"
    FREE_ENERGY_CRITICAL = "FREE_ENERGY_CRITICAL"
    CONTEXT_OVERFLOW = "CONTEXT_OVERFLOW"


def validate_input_text(text: str, field_name: str = "input", max_tokens: int = MAX_INPUT_TOKENS) -> Optional[str]:
    if not text:
        return None
    if len(text) > max_tokens * 4:
        return f"{field_name} exceeds maximum length ({len(text)} > {max_tokens * 4} chars). Please provide shorter input."
    return None


def tokenize(text: str, ngram_range: Tuple[int, int] = (2, 4)) -> List[str]:
    text = text.lower()
    tokens = re.findall(r'\w+', text)
    ngrams = []
    for token in tokens:
        for n in range(ngram_range[0], min(ngram_range[1], len(token)) + 1):
            for i in range(len(token) - n + 1):
                ngrams.append(token[i:i+n])
    return tokens + ngrams


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v*v for v in a.values()))
    norm_b = math.sqrt(sum(v*v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def beta_posterior(alpha: float, beta: float, successes: int, failures: int) -> Tuple[float, float]:
    return alpha + successes, beta + failures


def beta_mean(alpha: float, beta: float) -> float:
    if alpha + beta == 0:
        return 0.5
    return alpha / (alpha + beta)
