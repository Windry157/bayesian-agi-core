#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评分解析器 — 从 LLM 回复中提取数值评分（0-1）

支持 JSON 结构化输出、带语义锚点的正则、Markdown 代码块。
越界、NaN、类型错误均显式失败。
"""

import json
import math
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScoreParseError(ValueError):
    """评分解析失败"""
    pass


def _strip_markdown_fence(text: str) -> str:
    """去除 Markdown 代码块围栏"""
    text = text.strip()
    # ```json ... ```, ``` ... ```
    if text.startswith("```"):
        # 移除开头的 ``` 及可选的语言标识
        text = re.sub(r'^```\w*\n?', '', text)
        # 移除结尾的 ```
        text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def _parse_json_score(text: str) -> Optional[float]:
    """尝试从 JSON 对象中解析 score 字段"""
    if not (text.startswith("{") or text.startswith("```")):
        return None

    cleaned = _strip_markdown_fence(text)

    if not cleaned.startswith("{"):
        return None

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        raise ScoreParseError("评分必须是 JSON 对象")

    if "score" not in payload:
        raise ScoreParseError("缺少 score 字段")

    raw = payload["score"]

    # bool 是 int 的子类，需优先判断
    if isinstance(raw, bool):
        raise ScoreParseError(f"score 不能是布尔值: {raw}")

    if raw is None:
        raise ScoreParseError("score 为 null")

    try:
        score = float(raw)
    except (TypeError, ValueError) as e:
        raise ScoreParseError(f"score 无法转换为浮点数: {raw}") from e

    if not math.isfinite(score):
        raise ScoreParseError(f"score 必须是有限数: {score}")

    if not (0.0 <= score <= 1.0):
        raise ScoreParseError(f"score 必须在 [0, 1] 范围内: {score}")

    return score


def _parse_anchored_score(text: str) -> Optional[float]:
    """通过语义锚点正则提取评分"""
    patterns = [
        re.compile(r'(?i)(?:score|评分|分数)\s*[:：=]\s*(\d+(?:\.\d+)?)\s*(%)?'),
        re.compile(r'(?i)\b(\d+(?:\.\d+)?)\s*(%)\s*$'),
        re.compile(r'(?i)(\d+\.\d+)\s*$'),  # 行尾纯小数
    ]

    for pat in patterns:
        m = pat.search(text)
        if m:
            raw = m.group(1)
            is_pct = bool(m.group(2)) if m.lastindex and m.lastindex >= 2 else False
            val = float(raw)
            if is_pct:
                val /= 100.0
            if not (0.0 <= val <= 1.0):
                raise ScoreParseError(f"解析评分越界: {val} (原始: {raw})")
            if not math.isfinite(val):
                raise ScoreParseError(f"解析评分非有限数: {val}")
            return val

    return None


def parse_evaluation_score(text: str) -> float:
    """从 LLM 回复中解析评分（0-1）

    尝试顺序:
    1. JSON 结构化（含 Markdown 代码块）
    2. 带语义锚点的正则
    3. 全部失败 → ScoreParseError

    Args:
        text: LLM 回复文本

    Returns:
        0-1 之间的浮点数

    Raises:
        ScoreParseError: 无法解析或值非法
    """
    if not text or not text.strip():
        raise ScoreParseError("空响应")

    text = text.strip()

    # 方案 1: JSON
    score = _parse_json_score(text)
    if score is not None:
        return score

    # 方案 2: 正则
    score = _parse_anchored_score(text)
    if score is not None:
        return score

    raise ScoreParseError(f"无法从响应中解析评分: {text[:200]}")
