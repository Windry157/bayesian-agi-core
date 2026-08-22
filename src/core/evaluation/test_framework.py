#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试框架 - RAG系统的自动化评估
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from .quality_evaluator import QualityEvaluator, QualityScore


@dataclass
class TestCase:
    """测试用例"""
    question: str
    context: str
    reference_answer: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """测试结果"""
    test_case: TestCase
    generated_answer: str
    quality_score: QualityScore
    timestamp: str
    success: bool = False
    score: float = 0.0


@dataclass
class TestReport:
    """测试报告"""
    test_cases_run: int
    successful_tests: int
    failed_tests: int
    average_score: float
    min_score: float
    max_score: float
    timestamp: str
    results: List[TestResult] = field(default_factory=list)


class RAGTestFramework:
    """RAG系统测试框架"""

    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
        self.quality_evaluator = QualityEvaluator(ollama_url)
        self.test_cases: List[TestCase] = []
        self.results: List[TestResult] = []

    def add_test_case(
        self,
        question: str,
        context: str,
        reference_answer: Optional[str] = None,
        tags: List[str] = None
    ) -> None:
        """添加测试用例"""
        test_case = TestCase(
            question=question,
            context=context,
            reference_answer=reference_answer,
            tags=tags or []
        )
        self.test_cases.append(test_case)

    def add_sample_test_cases(self) -> None:
        """添加示例测试用例"""
        # 简单问题测试
        self.add_test_case(
            question="什么是Python?",
            context="Python是一种高级编程语言，由Guido van Rossum在1991年创建。它支持多种编程范式，包括面向对象、函数式和过程式编程。",
            reference_answer="Python是一种高级编程语言，由Guido van Rossum在1991年创建。",
            tags=["simple", "knowledge"]
        )

        # 复杂问题测试
        self.add_test_case(
            question="Python和Java有什么区别?",
            context="Python是一种解释型语言，而Java是编译型语言。Python使用动态类型系统，Java使用静态类型。Python语法更简洁，Java更严谨。",
            reference_answer="Python是解释型、动态类型，Java是编译型、静态类型。",
            tags=["complex", "comparison"]
        )

        # 边缘情况测试
        self.add_test_case(
            question="",
            context="测试空问题的处理。",
            tags=["edge", "empty"]
        )

    async def generate_answer(self, question: str, context: str) -> str:
        """生成回答"""
        try:
            import httpx

            prompt = f"""基于以下上下文回答问题。

上下文：
{context}

问题：
{question}

请给出简洁的回答。
"""

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            return f"生成回答时出错: {str(e)}"

    async def run_test_case(self, test_case: TestCase) -> TestResult:
        """运行单个测试用例"""
        # 生成回答
        generated_answer = await self.generate_answer(
            test_case.question,
            test_case.context
        )

        # 评估质量
        quality_score = await self.quality_evaluator.evaluate(
            test_case.question,
            test_case.context,
            generated_answer
        )

        # 确定是否成功（阈值0.6）
        success = quality_score.overall_score >= 0.6

        result = TestResult(
            test_case=test_case,
            generated_answer=generated_answer,
            quality_score=quality_score,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            success=success,
            score=quality_score.overall_score
        )

        self.results.append(result)
        return result

    async def run_all_tests(self) -> TestReport:
        """运行所有测试用例"""
        if not self.test_cases:
            self.add_sample_test_cases()

        print(f"开始运行 {len(self.test_cases)} 个测试用例...")

        tasks = [self.run_test_case(tc) for tc in self.test_cases]
        await asyncio.gather(*tasks)

        # 生成报告
        return self.generate_report()

    def generate_report(self) -> TestReport:
        """生成测试报告"""
        if not self.results:
            return TestReport(
                test_cases_run=0,
                successful_tests=0,
                failed_tests=0,
                average_score=0.0,
                min_score=0.0,
                max_score=0.0,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        scores = [r.score for r in self.results]
        successful = sum(1 for r in self.results if r.success)

        return TestReport(
            test_cases_run=len(self.results),
            successful_tests=successful,
            failed_tests=len(self.results) - successful,
            average_score=sum(scores) / len(scores),
            min_score=min(scores),
            max_score=max(scores),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results=self.results
        )

    def save_report(self, report: TestReport, filepath: str) -> None:
        """保存报告到文件"""
        report_dict = {
            "test_cases_run": report.test_cases_run,
            "successful_tests": report.successful_tests,
            "failed_tests": report.failed_tests,
            "average_score": report.average_score,
            "min_score": report.min_score,
            "max_score": report.max_score,
            "timestamp": report.timestamp,
            "results": [
                {
                    "question": r.test_case.question,
                    "generated_answer": r.generated_answer,
                    "score": r.score,
                    "success": r.success,
                    "timestamp": r.timestamp,
                    "quality": {
                        "overall_score": r.quality_score.overall_score,
                        "faithfulness": r.quality_score.faithfulness.overall_score,
                        "relevance": r.quality_score.relevance.overall_relevance_score,
                        "clarity": r.quality_score.clarity_score,
                        "completeness": r.quality_score.completeness_score,
                        "coherence": r.quality_score.coherence_score,
                        "explanation": r.quality_score.explanation
                    }
                }
                for r in report.results
            ]
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

    def print_summary(self, report: TestReport) -> None:
        """打印测试摘要"""
        print("\n" + "="*60)
        print("RAG系统测试报告".center(60))
        print("="*60)
        print(f"运行时间: {report.timestamp}")
        print(f"测试用例总数: {report.test_cases_run}")
        print(f"成功: {report.successful_tests}")
        print(f"失败: {report.failed_tests}")
        print("-"*60)
        print(f"平均得分: {report.average_score:.4f}")
        print(f"最低得分: {report.min_score:.4f}")
        print(f"最高得分: {report.max_score:.4f}")
        print("="*60)

    def clear_results(self) -> None:
        """清除结果"""
        self.results.clear()


async def main():
    """主函数 - 示例运行"""
    framework = RAGTestFramework()
    framework.add_sample_test_cases()

    report = await framework.run_all_tests()
    framework.print_summary(report)
    framework.save_report(report, "memory/evaluation/test_report.json")


if __name__ == "__main__":
    import sys
    asyncio.run(main())
