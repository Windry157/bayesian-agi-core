#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协作编排器
实现任务分解与并行化的核心引擎
支持 LLM 驱动的通用智能体 + 专用领域智能体

核心特性:
- DAG 任务编排（依赖管理）
- 并行执行（asyncio.gather）
- LLM 驱动的通用 Agent
- 带重试、超时的容错执行
- 效率指标计算
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEPENDENCY_WAIT = "dependency_wait"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class Task:
    """任务数据结构"""
    id: str
    name: str
    description: str
    agent_type: str
    input_data: Dict[str, Any] = None
    output_data: Dict[str, Any] = None
    dependencies: List[str] = None
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 120.0  # 秒

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.input_data is None:
            self.input_data = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "error": self.error,
            "retry_count": self.retry_count,
            "dependencies": self.dependencies,
        }


class BaseAgent(ABC):
    """智能体基类"""

    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.error_rate = 0.05

    @abstractmethod
    async def execute(self, task: Task) -> Task:
        """执行任务"""
        pass

    def get_agent_type(self) -> str:
        return self.__class__.__name__


# ================================================================
# LLM 驱动的通用智能体（新增）
# ================================================================


class LLMGeneralAgent(BaseAgent):
    """通用 LLM 智能体

    使用 LLM 执行任意类型的任务。
    不需要预定义领域知识，动态推理完成任务。
    """

    def __init__(self, llm: Any = None, agent_id: str = "llm_agent", name: str = "通用 LLM 智能体"):
        super().__init__(agent_id, name)
        self.llm = llm
        self.error_rate = 0.08

    async def execute(self, task: Task) -> Task:
        logger.info(f"[{self.name}] 开始执行: {task.name}")

        start_time = time.time()
        try:
            # 构建提示词
            prompt = self._build_prompt(task)

            # 调用 LLM
            if self.llm:
                result = await self._call_llm(prompt)
            else:
                # 无 LLM 时回退到模拟
                result = self._simulate_result(task)

            task.output_data = {
                "result": result,
                "agent_id": self.agent_id,
                "agent_name": self.name,
            }
            task.status = TaskStatus.COMPLETED
            task.execution_time = time.time() - start_time

            logger.info(f"[{self.name}] 完成: {task.name} ({task.execution_time:.2f}s)")
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.retry_count += 1
            task.execution_time = time.time() - start_time
            logger.error(f"[{self.name}] 失败: {task.name} - {e}")

        return task

    def _build_prompt(self, task: Task) -> str:
        """构建 LLM 提示词"""
        prompt_parts = [
            f"任务: {task.name}",
            f"描述: {task.description}",
        ]

        if task.input_data:
            prompt_parts.append("\n输入数据:")
            for key, value in task.input_data.items():
                if isinstance(value, str) and len(value) > 500:
                    value = value[:500] + "..."
                prompt_parts.append(f"  {key}: {value}")

        prompt_parts.append("\n请根据以上信息完成此任务，给出详细结果。")
        return "\n".join(prompt_parts)

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        if hasattr(self.llm, 'generate'):
            resp = self.llm.generate(prompt, temperature=0.7)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp.content if hasattr(resp, 'content') else str(resp)
        elif hasattr(self.llm, 'chat'):
            from ..llm.base_llm import Message
            messages = [Message(role="user", content=prompt)]
            resp = self.llm.chat(messages, temperature=0.7)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp.content if hasattr(resp, 'content') else str(resp)
        elif callable(self.llm):
            result = self.llm(prompt)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        else:
            return f"[{self.name}] 模拟结果: {prompt[:100]}..."

    def _simulate_result(self, task: Task) -> str:
        """无 LLM 时的模拟结果"""
        return (
            f"任务 '{task.name}' 已处理。\n"
            f"描述: {task.description}\n"
            f"输入数据: {list(task.input_data.keys()) if task.input_data else '无'}\n"
            f"状态: 模拟完成（无 LLM，请配置 LLM 实例获得真实输出）"
        )


# ================================================================
# 示例：领域专用智能体（保持向后兼容）
# ================================================================


class MarketResearchAgent(BaseAgent):
    """市场研究智能体（示例/演示用途）"""

    def __init__(self):
        super().__init__("market_agent", "市场研究专家")
        self.error_rate = 0.03

    async def execute(self, task: Task) -> Task:
        logger.info(f"[{self.name}] 开始执行: {task.name}")
        await asyncio.sleep(1)

        task.output_data = {
            "market_size": "500亿人民币",
            "target_users": "25-45岁城市白领",
            "competitors": ["竞品A", "竞品B", "竞品C"],
            "growth_rate": "15%/年",
            "trend_analysis": "AI+垂直领域是未来趋势",
        }
        task.status = TaskStatus.COMPLETED
        task.execution_time = 1.0

        logger.info(f"[{self.name}] 完成: {task.name}")
        return task


class FinancialForecastAgent(BaseAgent):
    """财务预测智能体（示例/演示用途）"""

    def __init__(self):
        super().__init__("finance_agent", "财务预测专家")
        self.error_rate = 0.04

    async def execute(self, task: Task) -> Task:
        logger.info(f"[{self.name}] 开始执行: {task.name}")
        await asyncio.sleep(1.5)

        market_data = task.input_data.get("market_data", {})
        task.output_data = {
            "initial_investment": "500万人民币",
            "break_even_period": "18个月",
            "roi_3year": "230%",
            "cash_flow_projection": [120, 280, 450, 680, 950],
            "risk_assessment": "中等风险",
            "market_basis": market_data.get("market_size", "未知"),
        }
        task.status = TaskStatus.COMPLETED
        task.execution_time = 1.5

        logger.info(f"[{self.name}] 完成: {task.name}")
        return task


class MarketingStrategyAgent(BaseAgent):
    """营销策略智能体（示例/演示用途）"""

    def __init__(self):
        super().__init__("marketing_agent", "营销策略专家")
        self.error_rate = 0.05

    async def execute(self, task: Task) -> Task:
        logger.info(f"[{self.name}] 开始执行: {task.name}")
        await asyncio.sleep(1.2)

        market_data = task.input_data.get("market_data", {})
        finance_data = task.input_data.get("finance_data", {})

        task.output_data = {
            "target_channels": ["社交媒体", "KOL合作", "内容营销", "线下活动"],
            "brand_positioning": "高端智能解决方案提供商",
            "pricing_strategy": "订阅制+增值服务",
            "customer_acquisition_cost": "200-300元/用户",
            "conversion_goal": "8%转化率",
            "budget_allocation": {"digital": 40, "content": 30, "events": 20, "other": 10},
        }
        task.status = TaskStatus.COMPLETED
        task.execution_time = 1.2

        logger.info(f"[{self.name}] 完成: {task.name}")
        return task


class ReportIntegrationAgent(BaseAgent):
    """报告整合智能体（示例/演示用途）"""

    def __init__(self):
        super().__init__("integration_agent", "报告整合专家")
        self.error_rate = 0.02

    async def execute(self, task: Task) -> Task:
        logger.info(f"[{self.name}] 开始执行: {task.name}")
        await asyncio.sleep(0.8)

        market_data = task.input_data.get("market_data", {})
        finance_data = task.input_data.get("finance_data", {})
        marketing_data = task.input_data.get("marketing_data", {})

        task.output_data = {
            "title": "商业计划书",
            "executive_summary": f"基于市场分析（规模{market_data.get('market_size')}），建议初始投资{finance_data.get('initial_investment')}",
            "market_section": market_data,
            "financial_section": finance_data,
            "marketing_section": marketing_data,
            "appendix": "详细数据见附录",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_analysis_steps": 4,
            "confidence_score": 0.95,
        }
        task.status = TaskStatus.COMPLETED
        task.execution_time = 0.8

        logger.info(f"[{self.name}] 完成: {task.name}")
        return task


# ================================================================
# 编排器核心
# ================================================================


class MultiAgentOrchestrator:
    """多智能体协作编排器

    支持 DAG 任务编排、并行执行、LLM 通用 Agent、容错重试。
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.agent_registry: Dict[str, type] = {
            "MarketResearchAgent": MarketResearchAgent,
            "FinancialForecastAgent": FinancialForecastAgent,
            "MarketingStrategyAgent": MarketingStrategyAgent,
            "ReportIntegrationAgent": ReportIntegrationAgent,
            "LLMGeneralAgent": LLMGeneralAgent,
        }

    def register_agent(self, agent: BaseAgent):
        """注册智能体"""
        self.agents[agent.agent_id] = agent
        logger.info(f"已注册智能体: {agent.name} ({agent.agent_id})")

    def register_agent_by_type(self, agent_type: str, **kwargs) -> BaseAgent:
        """按类型注册智能体

        Args:
            agent_type: 智能体类型名
            **kwargs: 传递给构造器的参数（如 llm=...）

        Returns:
            创建的智能体实例

        Raises:
            ValueError: 未知的智能体类型
        """
        if agent_type not in self.agent_registry:
            raise ValueError(f"未知的智能体类型: {agent_type}")

        agent_cls = self.agent_registry[agent_type]
        agent = agent_cls(**kwargs) if kwargs else agent_cls()
        self.register_agent(agent)
        return agent

    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.id] = task
        logger.info(f"已添加任务: {task.name} (依赖: {task.dependencies})")

    def add_tasks(self, tasks: List[Task]):
        """批量添加任务"""
        for task in tasks:
            self.add_task(task)

    def get_ready_tasks(self) -> List[str]:
        """获取可以执行的任务（依赖已完成且状态为 PENDING）"""
        ready = []
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue

            dependencies_ready = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if dep_task is None or dep_task.status not in (
                    TaskStatus.COMPLETED, TaskStatus.SKIPPED
                ):
                    dependencies_ready = False
                    break

            if dependencies_ready:
                ready.append(task_id)

        return ready

    async def execute_task(self, task_id: str, remaining_deadline: Optional[float] = None) -> Task:
        """执行单个任务（带重试和超时，deadline-aware）

        Args:
            task_id: 任务 ID
            remaining_deadline: 工作流剩余 deadline（秒），
                                当提供时 effective_timeout = min(task.timeout, remaining_deadline)
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        # deadline 传播：如果剩余时间为 0 或负，立即超时
        if remaining_deadline is not None and remaining_deadline <= 0:
            task.status = TaskStatus.FAILED
            task.error = "工作流 deadline 已耗尽"
            logger.warning(f"任务跳过（deadline 耗尽）: {task.name}")
            return task

        # 获取对应的智能体
        agent = self.agents.get(task.agent_type)
        if not agent:
            try:
                agent = self.register_agent_by_type(task.agent_type)
            except ValueError:
                task.status = TaskStatus.FAILED
                task.error = f"找不到智能体: {task.agent_type}"
                return task

        # 检查任何依赖是否失败（上游失败 = 本任务 BLOCKED）
        blocked = False
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.status == TaskStatus.FAILED:
                task.status = TaskStatus.BLOCKED
                task.error = f"上游任务 {dep_id} 失败"
                blocked = True
        if blocked:
            return task

        # 收集依赖输入
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.output_data:
                dep_key = dep_task.name.lower().replace(" ", "_")
                task.input_data[f"{dep_key}_data"] = dep_task.output_data

        # 带重试的执行（deadline-aware timeout）
        task.status = TaskStatus.RUNNING
        last_error = None

        for attempt in range(task.max_retries + 1):
            # 每次重试前重新计算有效超时
            effective_timeout = task.timeout
            if remaining_deadline is not None:
                effective_timeout = min(task.timeout, remaining_deadline)
                if effective_timeout <= 0:
                    last_error = "工作流 deadline 已耗尽"
                    logger.warning(f"任务超时（deadline 耗尽）: {task.name}")
                    break

            try:
                task = await asyncio.wait_for(
                    agent.execute(task),
                    timeout=effective_timeout,
                )
                if task.status == TaskStatus.COMPLETED:
                    return task

                last_error = task.error

            except asyncio.TimeoutError:
                last_error = f"超时 ({effective_timeout:.1f}s)"
                logger.warning(f"任务超时: {task.name}, 重试 {attempt + 1}/{task.max_retries}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"任务异常: {task.name}, 重试 {attempt + 1}/{task.max_retries}: {e}")

            task.retry_count += 1

            if attempt < task.max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # 递增延迟

        task.status = TaskStatus.FAILED
        task.error = last_error
        return task

    async def run_workflow(self, deadline: float = 300.0) -> Dict[str, Task]:
        """运行整个工作流（DAG 调度 — 完整终态机）

        工作流 deadline 会传播到 execute_task()，
        每个任务的 effective_timeout = min(task.timeout, 剩余 deadline)。

        Args:
            deadline: 工作流总超时（秒），默认 300

        Returns:
            所有任务（含状态）的字典
        """
        logger.info("========== 开始执行多智能体工作流 ==========")
        workflow_start = time.time()
        _deadline_at = time.monotonic() + deadline

        total_tasks = len(self.tasks)
        terminal_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.SKIPPED}

        def _remaining():
            return max(0.0, _deadline_at - time.monotonic())

        while True:
            # 1. 超时检查
            remaining = _remaining()
            if remaining <= 0:
                logger.error(f"工作流超时 ({deadline}s)，取消所有运行中任务")
                for task in self.tasks.values():
                    if task.status not in terminal_states:
                        task.status = TaskStatus.FAILED
                        task.error = "TIMED_OUT"
                break

            # 2. 计算当前状态分布
            status_counts = {}
            for t in self.tasks.values():
                status_counts[t.status] = status_counts.get(t.status, 0) + 1

            completed = status_counts.get(TaskStatus.COMPLETED, 0)
            failed = status_counts.get(TaskStatus.FAILED, 0)
            blocked = status_counts.get(TaskStatus.BLOCKED, 0)
            terminal = completed + failed + blocked + status_counts.get(TaskStatus.SKIPPED, 0)

            # 3. 全部进入终态 → 退出
            if terminal >= total_tasks:
                break

            # 4. 获取就绪任务
            ready_tasks = self.get_ready_tasks()

            # 5. 无可推进任务
            if not ready_tasks:
                pending = [t.id for t in self.tasks.values()
                          if t.status == TaskStatus.PENDING]
                running = [t.id for t in self.tasks.values()
                          if t.status == TaskStatus.RUNNING]
                if not pending and not running:
                    break  # 全部已进入终态或没有存活任务
                if pending:
                    logger.warning(f"DAG 无法推进 — 等待中的任务可能有环或依赖缺失: {pending}")
                    # 将所有 PENDING 且所有上游已失败的标记为 BLOCKED
                    for tid in pending:
                        task = self.tasks[tid]
                        if task.status != TaskStatus.PENDING:
                            continue
                        all_deps_terminal = all(
                            self.tasks.get(d) and self.tasks[d].status in terminal_states
                            for d in task.dependencies
                        )
                        if all_deps_terminal:
                            task.status = TaskStatus.BLOCKED
                            task.error = "所有上游已完成但任务未调度（缺失 Agent 或条件不满足）"
                    continue  # 下一轮重新评估

            # 6. 并行执行就绪任务（带 deadline 传播）
            tasks_to_execute = [
                self.execute_task(tid, remaining_deadline=_remaining())
                for tid in ready_tasks
            ]
            results = await asyncio.gather(*tasks_to_execute, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"任务执行异常: {result}")
                    continue
                if result.status == TaskStatus.COMPLETED:
                    logger.info(
                        f"任务完成: {result.name} "
                        f"(耗时: {result.execution_time:.2f}s, "
                        f"重试: {result.retry_count})"
                    )
                    # 检查是否新产生了任何 BLOCKED 下游
                    for t in self.tasks.values():
                        if t.status == TaskStatus.PENDING and result.id in t.dependencies:
                            # 将在下一轮 get_ready_tasks 中被评估
                            pass
                elif result.status == TaskStatus.FAILED:
                    logger.error(f"任务失败: {result.name} - {result.error}")
                    # 标记依赖此任务的下游为 BLOCKED
                    self._mark_downstream_blocked(result.id)
                    # 清除已失败任务的输出数据，防止下游错误使用
                    result.output_data = None

        # 收尾统计
        final_statuses = {}
        for t in self.tasks.values():
            final_statuses[t.status] = final_statuses.get(t.status, 0) + 1

        logger.info(f"========== 工作流执行完成 ==========")
        logger.info(f"终态分布: {dict(final_statuses)}")
        return self.tasks

    def _mark_downstream_blocked(self, failed_task_id: str):
        """递归标记所有下游为 BLOCKED"""
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING and failed_task_id in task.dependencies:
                task.status = TaskStatus.BLOCKED
                task.error = f"上游任务 {failed_task_id} 失败"
                self._mark_downstream_blocked(task.id)

    def validate_dag(self) -> List[str]:
        """验证 DAG：检查环和缺失依赖

        Returns:
            错误消息列表，空列表表示 DAG 有效
        """
        errors = []

        # 1. 检查所有依赖存在
        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    errors.append(f"任务 {task_id} 依赖不存在: {dep_id}")

        if errors:
            return errors

        # 2. 环检测（DFS）
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self.tasks}

        def dfs(tid):
            color[tid] = GRAY
            for dep_id in self.tasks[tid].dependencies:
                if color[dep_id] == GRAY:
                    return [dep_id, tid]  # 环
                if color[dep_id] == WHITE:
                    result = dfs(dep_id)
                    if result:
                        return result
            color[tid] = BLACK
            return None

        for tid in self.tasks:
            if color[tid] == WHITE:
                cycle = dfs(tid)
                if cycle:
                    errors.append(f"DAG 存在环: {' -> '.join(cycle)}")

        return errors

    # ================================================================
    # 指标与统计
    # ================================================================

    def calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """计算效率指标"""
        completed = [t for t in self.tasks.values()
                    if t.status == TaskStatus.COMPLETED]
        failed = [t for t in self.tasks.values()
                 if t.status == TaskStatus.FAILED]
        skipped = [t for t in self.tasks.values()
                  if t.status == TaskStatus.SKIPPED]

        total_time = sum(t.execution_time for t in completed)
        avg_time = total_time / len(completed) if completed else 0
        error_rate = len(failed) / len(self.tasks) if self.tasks else 0

        return {
            "total_tasks": len(self.tasks),
            "completed_tasks": len(completed),
            "failed_tasks": len(failed),
            "skipped_tasks": len(skipped),
            "total_execution_time": round(total_time, 2),
            "average_task_time": round(avg_time, 2),
            "error_rate": round(error_rate * 100, 2),
            "success_rate": round((1 - error_rate) * 100, 2),
        }

    def get_workflow_graph(self) -> Dict[str, Any]:
        """获取工作流 DAG 图"""
        nodes = []
        edges = []

        for task_id, task in self.tasks.items():
            nodes.append({
                "id": task_id,
                "label": task.name,
                "status": task.status.value,
            })
            for dep_id in task.dependencies:
                edges.append({"from": dep_id, "to": task_id})

        return {"nodes": nodes, "edges": edges}


# ================================================================
# 示例：运行工作流对比（保持向后兼容）
# ================================================================


async def run_monolithic_approach() -> Dict[str, Any]:
    """模拟单一模型方法（对比基准）"""
    logger.info("===== 单一模型方法 =====")
    await asyncio.sleep(5)

    return {
        "method": "单模型",
        "steps": 5,
        "execution_time": 5.0,
        "error_rate": 25.0,
        "success_rate": 75.0,
        "explainability": "差",
        "robustness": "低",
    }


async def run_agentic_workflow() -> Tuple[Dict[str, Any], Dict[str, Task]]:
    """运行智能体工作流（示例）"""
    logger.info("===== 智能体协作方法 =====")

    orchestrator = MultiAgentOrchestrator()

    # 注册示例智能体
    orchestrator.register_agent_by_type("MarketResearchAgent")
    orchestrator.register_agent_by_type("FinancialForecastAgent")
    orchestrator.register_agent_by_type("MarketingStrategyAgent")
    orchestrator.register_agent_by_type("ReportIntegrationAgent")

    # 定义任务流程（DAG）
    tasks = [
        Task(id="task_market", name="市场调研分析",
             description="分析目标市场规模、用户群体和竞争格局",
             agent_type="MarketResearchAgent"),
        Task(id="task_finance", name="财务预测分析",
             description="基于市场数据进行财务预测",
             agent_type="FinancialForecastAgent",
             dependencies=["task_market"]),
        Task(id="task_marketing", name="营销策略制定",
             description="基于市场和财务数据制定营销策略",
             agent_type="MarketingStrategyAgent",
             dependencies=["task_market", "task_finance"]),
        Task(id="task_integration", name="商业计划书整合",
             description="整合所有分析结果生成完整报告",
             agent_type="ReportIntegrationAgent",
             dependencies=["task_market", "task_finance", "task_marketing"]),
    ]

    orchestrator.add_tasks(tasks)
    await orchestrator.run_workflow()

    metrics = orchestrator.calculate_efficiency_metrics()
    metrics.update({
        "method": "智能体协作",
        "steps": 4,
        "explainability": "极强",
        "robustness": "高",
    })

    return metrics, orchestrator.tasks


async def compare_approaches():
    """对比两种方法（演示）"""
    mono_result = await run_monolithic_approach()
    agent_result, tasks = await run_agentic_workflow()

    print("\n" + "=" * 60)
    print("                    方法对比报告")
    print("=" * 60)
    print(f"{'指标':<20} {'单模型方法':<15} {'智能体协作':<15} {'效率提升':<10}")
    print("-" * 60)
    print(f"{'步骤数':<20} {mono_result['steps']:<15} {agent_result['steps']:<15} {'-20%':<10}")
    time_saving = round((1 - agent_result['total_execution_time'] / mono_result['execution_time']) * 100)
    print(f"{'执行时间(s)':<20} {mono_result['execution_time']:<15} {agent_result['total_execution_time']:<15} {'-{}%'.format(time_saving):<10}")
    print(f"{'错误率':<20} {str(mono_result['error_rate'])+'%':<15} {str(agent_result['error_rate'])+'%':<15} {'-80%':<10}")
    print(f"{'成功率':<20} {str(mono_result['success_rate'])+'%':<15} {str(agent_result['success_rate'])+'%':<15} {'+27%':<10}")
    print(f"{'可解释性':<20} {mono_result['explainability']:<15} {agent_result['explainability']:<15} {'显著提升':<10}")
    print(f"{'鲁棒性':<20} {mono_result['robustness']:<15} {agent_result['robustness']:<15} {'显著提升':<10}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("                    智能体任务执行详情")
    print("=" * 60)
    print(f"{'任务名称':<20} {'智能体':<15} {'状态':<10} {'耗时(s)':<10}")
    print("-" * 60)
    for task_id, task in tasks.items():
        print(f"{task.name:<20} {task.agent_type:<15} {task.status.value:<10} {task.execution_time:<10}")
    print("=" * 60)

    return {"monolithic": mono_result, "agentic": agent_result}


if __name__ == "__main__":
    asyncio.run(compare_approaches())
