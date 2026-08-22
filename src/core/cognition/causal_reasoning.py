#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因果推理引擎
基于贝叶斯网络和因果图模型的因果推理系统
"""
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import math
from collections import defaultdict

logger = logging.getLogger(__name__)


class CausalStrength(Enum):
    """因果强度"""
    STRONG = 0.8
    MODERATE = 0.5
    WEAK = 0.2
    NONE = 0.0


@dataclass
class CausalVariable:
    """因果变量"""
    id: str
    name: str
    current_value: Any = None
    possible_values: List[Any] = field(default_factory=list)
    probability_dist: Dict[Any, float] = field(default_factory=dict)
    is_observed: bool = False


@dataclass
class CausalRelation:
    """因果关系"""
    cause_id: str
    effect_id: str
    strength: CausalStrength
    conditional_probabilities: Dict[Tuple[Any, Any], float] = field(default_factory=dict)
    confidence: float = 0.5


@dataclass
class Intervention:
    """干预"""
    variable_id: str
    value: Any
    is_intervened: bool = True


class CausalGraph:
    """因果图"""

    def __init__(self):
        self.variables: Dict[str, CausalVariable] = {}
        self.relations: List[CausalRelation] = []
        self.parents: Dict[str, List[str]] = defaultdict(list)
        self.children: Dict[str, List[str]] = defaultdict(list)

    def add_variable(self, variable: CausalVariable):
        """添加变量"""
        self.variables[variable.id] = variable
        logger.debug(f"Added variable: {variable.name}")

    def add_relation(self, cause_id: str, effect_id: str,
                   strength: CausalStrength,
                   cond_probs: Dict = None):
        """添加因果关系"""
        if cause_id not in self.variables or effect_id not in self.variables:
            raise ValueError("Variables not found")
        
        relation = CausalRelation(
            cause_id=cause_id,
            effect_id=effect_id,
            strength=strength,
            conditional_probabilities=cond_probs or {}
        )
        
        self.relations.append(relation)
        self.parents[effect_id].append(cause_id)
        self.children[cause_id].append(effect_id)
        logger.debug(f"Added causal relation: {cause_id} -> {effect_id}")

    def get_parents(self, variable_id: str) -> List[CausalVariable]:
        """获取父节点"""
        return [self.variables[pid] for pid in self.parents.get(variable_id, [])]

    def get_children(self, variable_id: str) -> List[CausalVariable]:
        """获取子节点"""
        return [self.variables[cid] for cid in self.children.get(variable_id, [])]


class CausalReasoningEngine:
    """因果推理引擎"""

    def __init__(self):
        self.graph = CausalGraph()
        self.observations: Dict[str, Any] = {}
        self.interventions: List[Intervention] = []

    def add_variable(self, var_id: str, name: str, 
                   possible_values: List[Any] = None):
        """添加变量"""
        var = CausalVariable(
            id=var_id,
            name=name,
            possible_values=possible_values or [True, False]
        )
        self.graph.add_variable(var)

    def add_causal_relation(self, cause_id: str, effect_id: str,
                          strength: float = 0.5,
                          cond_probs: Dict = None):
        """添加因果关系"""
        causal_strength = self._float_to_strength(strength)
        self.graph.add_relation(cause_id, effect_id, causal_strength, cond_probs)

    def _float_to_strength(self, value: float) -> CausalStrength:
        """转换为强度枚举"""
        if value >= 0.7:
            return CausalStrength.STRONG
        elif value >= 0.4:
            return CausalStrength.MODERATE
        elif value > 0:
            return CausalStrength.WEAK
        return CausalStrength.NONE

    def observe(self, variable_id: str, value: Any):
        """观察变量值"""
        if variable_id in self.graph.variables:
            var = self.graph.variables[variable_id]
            var.current_value = value
            var.is_observed = True
            self.observations[variable_id] = value
            logger.info(f"Observed {var.name} = {value}")

    def intervene(self, variable_id: str, value: Any):
        """干预变量"""
        intervention = Intervention(variable_id=variable_id, value=value)
        self.interventions.append(intervention)
        
        if variable_id in self.graph.variables:
            var = self.graph.variables[variable_id]
            var.current_value = value
            logger.info(f"Intervened {var.name} = {value}")

    def infer_probability(self, target_id: str, 
                       given: Dict[str, Any] = None) -> float:
        """推理目标变量的概率"""
        given = given or {}
        
        # 使用简单的贝叶斯推理
        target_var = self.graph.variables.get(target_id)
        if not target_var:
            raise ValueError(f"Variable {target_id} not found")
        
        # 获取父节点
        parents = self.graph.get_parents(target_id)
        
        if not parents:
            # 先验概率
            return target_var.probability_dist.get(True, 0.5)
        
        # 考虑父节点影响
        total_prob = 0.0
        
        for parent in parents:
            rel = self._find_relation(parent.id, target_id)
            if rel:
                parent_value = self.observations.get(parent.id, parent.current_value)
                
                if parent_value is not None:
                    strength = rel.strength.value
                    base_prob = target_var.probability_dist.get(True, 0.5)
                    
                    if parent_value:
                        total_prob += strength * base_prob + (1 - strength) * 0.5
                    else:
                        total_prob += (1 - strength) * base_prob + strength * 0.1
        
        return min(1.0, max(0.0, total_prob / max(1, len(parents))))

    def _find_relation(self, cause_id: str, effect_id: str) -> Optional[CausalRelation]:
        """查找因果关系"""
        for rel in self.graph.relations:
            if rel.cause_id == cause_id and rel.effect_id == effect_id:
                return rel
        return None

    def causal_effect(self, cause_id: str, effect_id: str) -> Dict[str, float]:
        """计算因果效应（ATE - Average Treatment Effect)"""
        # 计算干预前的基线概率
        baseline = self.infer_probability(effect_id)
        
        # 干预原因
        self.intervene(cause_id, True)
        prob_true = self.infer_probability(effect_id)
        
        self.intervene(cause_id, False)
        prob_false = self.infer_probability(effect_id)
        
        # ATE = P(Y|do(X=1)) - P(Y|do(X=0))
        ate = prob_true - prob_false
        
        return {
            'ate': ate,
            'prob_true': prob_true,
            'prob_false': prob_false,
            'baseline': baseline
        }

    def counterfactual_query(self, target_id: str, 
                            hypothetical: Dict[str, Any]) -> float:
        """反事实推理"""
        original_obs = dict(self.observations)
        
        # 施加反事实条件
        for var_id, value in hypothetical.items():
            self.observe(var_id, value)
        
        result = self.infer_probability(target_id)
        
        # 恢复原状
        for var_id, value in original_obs.items():
            self.observe(var_id, value)
        
        return result

    def backdoor_adjustment(self, treatment_id: str, outcome_id: str,
                         confounders: List[str]) -> float:
        """后门调整公式计算因果效应"""
        total_effect = 0.0
        
        # 简单实现
        effect = self.causal_effect(treatment_id, outcome_id)
        return effect['ate']

    def find_confounders(self, cause_id: str, effect_id: str) -> List[str]:
        """发现潜在的混淆变量"""
        confounders = []
        
        # 寻找共同父节点
        cause_parents = set(self.graph.parents.get(cause_id, []))
        effect_parents = set(self.graph.parents.get(effect_id, []))
        common_parents = cause_parents.intersection(effect_parents)
        confounders.extend(common_parents)
        
        return list(confounders)

    def explain_causation(self, effect_id: str) -> List[Dict[str, Any]]:
        """解释因果关系"""
        explanations = []
        
        parents = self.graph.get_parents(effect_id)
        
        for parent in parents:
            rel = self._find_relation(parent.id, effect_id)
            if rel:
                effect = self.causal_effect(parent.id, effect_id)
                explanations.append({
                    'cause': parent.name,
                    'effect': self.graph.variables[effect_id].name,
                    'strength': rel.strength.value,
                    'ate': effect['ate'],
                    'explanation': f"{parent.name} influences {self.graph.variables[effect_id].name}"
                })
        
        return sorted(explanations, key=lambda x: x['ate'], reverse=True)

    def reset(self):
        """重置观察和干预"""
        self.observations.clear()
        self.interventions.clear()
        
        for var in self.graph.variables.values():
            var.is_observed = False
            var.current_value = None
