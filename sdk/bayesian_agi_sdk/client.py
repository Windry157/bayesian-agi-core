#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core Python SDK
为 HengshuAgent 提供标准化的 API 客户端
"""

import requests
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime


class BayesianAGIClient:
    """
    Bayesian-AGI-Core API 客户端
    为 HengshuAgent 提供安全、可观测性和自愈服务的访问接口
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        初始化客户端
        
        :param base_url: Bayesian-AGI-Core 服务地址
        :param timeout: 请求超时时间(秒)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        内部请求方法
        
        :param method: HTTP方法
        :param endpoint: API端点
        :param kwargs: 请求参数
        :return: 响应数据
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise BayesianAGIError(f"请求失败: {e}") from e

    # ==================== 安全服务 ====================

    def validate_input(self, input_data: str, validation_type: str = "full") -> Dict[str, Any]:
        """
        验证输入安全性
        
        :param input_data: 待验证的输入数据
        :param validation_type: 验证类型: full/syntax/semantic
        :return: 验证结果
        """
        data = {
            "input_data": input_data,
            "validation_type": validation_type
        }
        return self._request("POST", "/api/v1/security/validate", json=data)

    def execute_in_sandbox(self, code: str, timeout: int = 30, max_memory_mb: int = 512) -> Dict[str, Any]:
        """
        在沙箱中执行代码
        
        :param code: 待执行的代码
        :param timeout: 超时时间(秒)
        :param max_memory_mb: 最大内存(MB)
        :return: 执行结果
        """
        data = {
            "code": code,
            "timeout": timeout,
            "max_memory_mb": max_memory_mb
        }
        return self._request("POST", "/api/v1/security/execute", json=data)

    def validate_sql(self, query: str, allowed_tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        验证SQL查询安全性
        
        :param query: 待验证的SQL查询
        :param allowed_tables: 允许访问的表名列表
        :return: 验证结果
        """
        data = {
            "query": query,
            "allowed_tables": allowed_tables or []
        }
        return self._request("POST", "/api/v1/security/validate/sql", json=data)

    def validate_shell(self, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        验证Shell命令安全性
        
        :param command: 命令
        :param args: 参数列表
        :return: 验证结果
        """
        data = {
            "command": command,
            "args": args or []
        }
        return self._request("POST", "/api/v1/security/validate/shell", json=data)

    def get_security_status(self) -> Dict[str, Any]:
        """获取安全服务状态"""
        return self._request("GET", "/api/v1/security/status")

    # ==================== 可观测性服务 ====================

    def record_cost(self, input_tokens: int = 0, output_tokens: int = 0, 
                    duration_ms: int = 0, model_name: str = "unknown") -> Dict[str, Any]:
        """
        记录成本消耗
        
        :param input_tokens: 输入Token数
        :param output_tokens: 输出Token数
        :param duration_ms: 计算时长(毫秒)
        :param model_name: 模型名称
        :return: 记录结果
        """
        data = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "model_name": model_name
        }
        return self._request("POST", "/api/v1/observability/cost/record", json=data)

    def get_cost_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取成本摘要
        
        :param hours: 统计周期(小时)
        :return: 成本摘要
        """
        return self._request("GET", f"/api/v1/observability/cost/summary?hours={hours}")

    def trigger_alert(self, alert_id: str, message: str, 
                      level: str = "WARNING", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        触发告警
        
        :param alert_id: 告警ID
        :param message: 告警消息
        :param level: 告警级别: INFO/WARNING/CRITICAL
        :param metadata: 附加元数据
        :return: 触发结果
        """
        data = {
            "alert_id": alert_id,
            "message": message,
            "level": level,
            "metadata": metadata or {}
        }
        return self._request("POST", "/api/v1/observability/alerts/trigger", json=data)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活动告警列表"""
        return self._request("GET", "/api/v1/observability/alerts")

    def resolve_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        解决告警
        
        :param alert_id: 告警ID
        :return: 解决结果
        """
        return self._request("POST", f"/api/v1/observability/alerts/{alert_id}/resolve")

    def get_metrics(self) -> List[Dict[str, Any]]:
        """获取指标数据"""
        return self._request("GET", "/api/v1/observability/metrics")

    def get_dashboard(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        return self._request("GET", "/api/v1/observability/dashboard")

    def get_observability_status(self) -> Dict[str, Any]:
        """获取可观测性服务状态"""
        return self._request("GET", "/api/v1/observability/status")

    # ==================== 自愈服务 ====================

    def list_actions(self) -> List[Dict[str, Any]]:
        """获取所有可用的修复动作"""
        return self._request("GET", "/api/v1/self-healing/actions")

    def get_action(self, action_id: str) -> Dict[str, Any]:
        """
        获取单个动作详情
        
        :param action_id: 动作ID
        :return: 动作信息
        """
        return self._request("GET", f"/api/v1/self-healing/actions/{action_id}")

    def execute_action(self, action_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行单个修复动作
        
        :param action_id: 动作ID
        :param parameters: 动作参数
        :return: 执行结果
        """
        data = {
            "action_id": action_id,
            "parameters": parameters or {}
        }
        return self._request("POST", f"/api/v1/self-healing/actions/{action_id}/execute", json=data)

    def list_playbooks(self) -> List[Dict[str, Any]]:
        """获取所有可用的修复剧本"""
        return self._request("GET", "/api/v1/self-healing/playbooks")

    def get_playbook(self, playbook_name: str) -> Dict[str, Any]:
        """
        获取单个剧本详情
        
        :param playbook_name: 剧本名称
        :return: 剧本信息
        """
        return self._request("GET", f"/api/v1/self-healing/playbooks/{playbook_name}")

    def execute_playbook(self, playbook_name: str) -> Dict[str, Any]:
        """
        执行修复剧本
        
        :param playbook_name: 剧本名称
        :return: 执行结果
        """
        return self._request("POST", f"/api/v1/self-healing/playbooks/{playbook_name}/execute")

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        :param limit: 返回条数限制
        :return: 执行历史列表
        """
        return self._request("GET", f"/api/v1/self-healing/execution-history?limit={limit}")

    def get_running_actions(self) -> Dict[str, Any]:
        """获取正在执行的动作"""
        return self._request("GET", "/api/v1/self-healing/running-actions")

    def get_self_healing_status(self) -> Dict[str, Any]:
        """获取自愈服务状态"""
        return self._request("GET", "/api/v1/self-healing/status")

    # ==================== 通用 ====================

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._request("GET", "/health")

    def get_version(self) -> Dict[str, Any]:
        """获取版本信息"""
        return self._request("GET", "/")

    def close(self):
        """关闭会话"""
        self.session.close()


class BayesianAGIError(Exception):
    """Bayesian-AGI-Core SDK 异常"""
    pass


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建客户端
    client = BayesianAGIClient(base_url="http://localhost:8000")
    
    try:
        # 健康检查
        print("=== 健康检查 ===")
        result = client.health_check()
        print(f"状态: {result}")
        
        # 安全验证
        print("\n=== 安全验证 ===")
        result = client.validate_input("print('hello')")
        print(f"验证结果: {result}")
        
        # 获取成本摘要
        print("\n=== 成本摘要 ===")
        result = client.get_cost_summary(hours=24)
        print(f"成本: {result}")
        
        # 获取告警
        print("\n=== 活动告警 ===")
        result = client.get_active_alerts()
        print(f"告警数量: {len(result)}")
        
        # 获取修复动作
        print("\n=== 修复动作 ===")
        result = client.list_actions()
        print(f"动作数量: {len(result)}")
        
    except BayesianAGIError as e:
        print(f"错误: {e}")
    finally:
        client.close()