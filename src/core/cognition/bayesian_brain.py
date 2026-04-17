#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贝叶斯大脑模块
负责概率更新和决策逻辑
"""

import asyncio
import math
from typing import Dict, List, Optional, Tuple
from ..interfaces import IBayesianBrain
from .chain_of_thought import ChainOfThought


class BayesianBrain(IBayesianBrain):
    """贝叶斯大脑

    实现贝叶斯概率更新和主动推理
    """

    def __init__(self, cognition_coordinator=None):
        """初始化贝叶斯大脑

        Args:
            cognition_coordinator: 认知协调器实例
        """
        # 世界模型 - 存储状态概率
        self.world_model: Dict[str, float] = {}
        # 行动空间
        self.action_space: List[str] = []
        # 历史观测
        self.observations: List[Dict] = []
        # 历史行动
        self.actions: List[str] = []
        # 认知协调器
        self.cognition_coordinator = cognition_coordinator
        # 思维链
        self.chain_of_thought = ChainOfThought()

    def update_priors(self, new_evidence: Dict[str, float]):
        """更新先验概率

        Args:
            new_evidence: 新的证据，键为状态，值为概率
        """
        for state, probability in new_evidence.items():
            self.world_model[state] = probability

    def bayesian_update(self, observation: Dict) -> Dict[str, float]:
        """执行贝叶斯更新

        Args:
            observation: 当前观测

        Returns:
            更新后的后验概率
        """
        # 简化的贝叶斯更新实现
        # 实际应用中需要更复杂的似然计算
        posterior = {}
        total_prob = 0.0

        for state, prior in self.world_model.items():
            # 计算似然（简化版）
            likelihood = self._calculate_likelihood(state, observation)
            # 计算联合概率
            joint = prior * likelihood
            posterior[state] = joint
            total_prob += joint

        # 归一化
        if total_prob > 0:
            for state in posterior:
                posterior[state] /= total_prob

        # 更新世界模型
        self.world_model = posterior
        # 记录观测
        self.observations.append(observation)

        return posterior

    def _calculate_likelihood(self, state: str, observation: Dict) -> float:
        """计算似然概率

        Args:
            state: 当前状态
            observation: 观测数据

        Returns:
            似然概率
        """
        # 改进的似然计算
        likelihood = 0.5
        
        # 基于观测数据计算似然
        if 'evidence' in observation:
            evidence = observation['evidence']
            if isinstance(evidence, dict):
                # 检查证据中是否与状态相关
                for key, value in evidence.items():
                    if key in state.lower():
                        likelihood += 0.3
                    elif key in state.upper():
                        likelihood += 0.2
            elif isinstance(evidence, str):
                # 文本证据匹配
                if evidence.lower() in state.lower():
                    likelihood += 0.4
        
        # 确保似然值在合理范围内
        return min(0.99, max(0.01, likelihood))

    def active_inference(self, possible_actions: List[str]) -> str:
        """主动推理选择行动

        Args:
            possible_actions: 可能的行动列表

        Returns:
            选择的行动
        """
        if not possible_actions:
            return "no_action"
        
        # 计算每个行动的信息增益
        action_scores = {}
        for action in possible_actions:
            # 计算信息增益
            info_gain = self._calculate_information_gain(action)
            # 计算行动的预期价值
            expected_value = self._calculate_expected_value(action)
            # 综合评分
            action_scores[action] = info_gain * 0.6 + expected_value * 0.4
        
        # 选择评分最高的行动
        best_action = max(action_scores, key=action_scores.get)
        
        # 使用认知协调器做出最终决策
        situation = {
            "possible_actions": possible_actions,
            "action_scores": action_scores,
            "world_model": self.world_model,
            "observations": self.observations,
            "actions": self.actions,
        }

        # 生成思维链
        problem = f"从{possible_actions}中选择最佳行动，基于信息增益和预期价值"
        chain = self.chain_of_thought.generate_chain(problem, situation)

        # 使用认知协调器做出最终决策
        decision = self.cognition_coordinator.make_decision(situation)
        
        # 尊重认知协调器的决策（如果有）
        if "decision" in decision and decision["decision"] in possible_actions:
            best_action = decision["decision"]

        # 记录行动
        self.actions.append(best_action)

        return best_action
    
    def _calculate_expected_value(self, action: str) -> float:
        """计算行动的预期价值

        Args:
            action: 行动

        Returns:
            预期价值
        """
        # 简单的预期价值计算
        # 实际应用中需要更复杂的价值函数
        value = 0.0
        
        # 基于行动与当前状态的相关性
        for state, prob in self.world_model.items():
            if action in state.lower():
                value += prob * 1.5
            else:
                value += prob * 0.8
        
        return value

    def _calculate_information_gain(self, action: str) -> float:
        """计算行动的预期信息增益

        Args:
            action: 行动

        Returns:
            预期信息增益
        """
        # 改进的信息增益计算
        # 计算当前熵
        current_entropy = self._calculate_entropy(self.world_model)
        
        # 模拟行动后的状态分布
        predicted_states = self._predict_states_after_action(action)
        
        # 计算预期熵
        expected_entropy = 0.0
        for state, prob in predicted_states.items():
            expected_entropy -= prob * math.log2(prob) if prob > 0 else 0
        
        # 信息增益 = 当前熵 - 预期熵
        information_gain = current_entropy - expected_entropy
        
        return max(0.0, information_gain)
    
    def _calculate_entropy(self, distribution: Dict[str, float]) -> float:
        """计算概率分布的熵

        Args:
            distribution: 概率分布

        Returns:
            熵值
        """
        entropy = 0.0
        for prob in distribution.values():
            if prob > 0:
                entropy -= prob * math.log2(prob)
        return entropy
    
    def _predict_states_after_action(self, action: str) -> Dict[str, float]:
        """预测行动后的状态分布

        Args:
            action: 行动

        Returns:
            预测的状态分布
        """
        # 基于当前状态和行动预测新的状态分布
        predicted = {}
        
        for state, prob in self.world_model.items():
            # 简单的状态转移模型
            # 实际应用中需要更复杂的转移模型
            if action in state.lower():
                # 行动与状态相关，增加概率
                predicted[state] = prob * 1.2
            else:
                # 行动与状态无关，保持概率
                predicted[state] = prob * 0.9
        
        # 归一化
        total = sum(predicted.values())
        if total > 0:
            for state in predicted:
                predicted[state] /= total
        
        return predicted

    def get_beliefs(self) -> Dict[str, float]:
        """获取当前信念状态

        Returns:
            当前世界模型的概率分布
        """
        return self.world_model

    def reset(self):
        """重置贝叶斯大脑"""
        self.world_model = {}
        self.observations = []
        self.actions = []
