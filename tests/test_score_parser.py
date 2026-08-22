import pytest
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.core.cognition.score_parser import (
    parse_evaluation_score,
    ScoreParseError,
)


class TestScoreParser:
    """评分解析器 — 参数化全覆盖"""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ('{"score": 0.82, "reason": "good"}', 0.82),
            ('{"score": 0.0}', 0.0),
            ('{"score": 1.0}', 1.0),
            ('{"score": 0.5}', 0.5),
            # Markdown 代码块
            ('```json\n{"score": 0.82}\n```', 0.82),
            ('```\n{"score": 0.75}\n```', 0.75),
            # 带语义锚点的自然语言
            ("评分：0.82", 0.82),
            ("score=0.82", 0.82),
            ("分数: 0.82", 0.82),
            # 百分比
            ("score=82%", 0.82),
            ("评分：82%", 0.82),
            # 行尾纯小数
            ("这个思路很好。\n0.85", 0.85),
            # 多数字干扰，末尾有效评分
            ("有 3 个方案，评分 0.82", 0.82),
        ],
    )
    def test_valid_scores(self, text, expected):
        result = parse_evaluation_score(text)
        assert result == pytest.approx(expected, abs=1e-9)

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "没有给出评分",
            "我觉得这个想法不错",  # 无数字
            # 非法 JSON 结构
            '{"reason": "missing score"}',
            "[]",  # JSON 数组
            # 非法类型
            '{"score": "abc"}',
            '{"score": null}',
            '{"score": true}',
            '{"score": false}',
            # 越界
            '{"score": 1.5}',
            '{"score": -0.2}',
            '82',  # 裸数字被认为是 Python literal 但不是 JSON
            "评分：82",  # 无百分号锚点，数值>1.0
        ],
    )
    def test_invalid_scores(self, text):
        with pytest.raises(ScoreParseError):
            parse_evaluation_score(text)

    def test_nan_score_json(self):
        """NaN 必须被拒绝"""
        with pytest.raises(ScoreParseError):
            parse_evaluation_score('{"score": NaN}')

    def test_infinity_score_json(self):
        with pytest.raises(ScoreParseError):
            parse_evaluation_score('{"score": Infinity}')

    def test_invalid_percent_above_100(self):
        """100% 以上应拒绝"""
        with pytest.raises(ScoreParseError):
            parse_evaluation_score("评分：150%")

    def test_zero_is_valid(self):
        assert parse_evaluation_score('{"score": 0.0}') == 0.0

    def test_one_is_valid(self):
        assert parse_evaluation_score('{"score": 1.0}') == 1.0
