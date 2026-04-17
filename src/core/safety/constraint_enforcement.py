#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
约束执行模块
负责对输出进行严格的非协商性检查
"""

import re
import logging
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConstraintEnforcementModule:
    """约束执行模块
    
    对系统输出进行严格的非协商性检查
    """
    
    def __init__(self):
        """初始化约束执行模块"""
        # 敏感主题列表
        self.sensitive_topics = {
            "medical": {
                "patterns": [
                    r"医疗", r"医生", r"药物", r"治疗", r"疾病", r"健康",
                    r"medical", r"doctor", r"medicine", r"treatment", r"disease", r"health"
                ],
                "response": "我无法提供医疗建议。请咨询专业医疗人员获取准确的医疗信息。"
            },
            "legal": {
                "patterns": [
                    r"法律", r"律师", r"诉讼", r"合同", r"权利", r"义务",
                    r"legal", r"lawyer", r"lawsuit", r"contract", r"rights", r"obligations"
                ],
                "response": "我无法提供法律建议。请咨询专业法律人士获取准确的法律信息。"
            },
            "financial": {
                "patterns": [
                    r"投资", r"股票", r"基金", r"理财", r"保险", r"税务",
                    r"invest", r"stock", r"fund", r"finance", r"insurance", r"tax"
                ],
                "response": "我无法提供财务建议。请咨询专业财务顾问获取准确的财务信息。"
            },
            "hacking": {
                "patterns": [
                    r"黑客", r"入侵", r"破解", r"密码", r"攻击", r"漏洞",
                    r"hack", r"crack", r"password", r"attack", r"vulnerability"
                ],
                "response": "我无法提供与黑客相关的信息。这种行为可能违法且不道德。"
            },
            "violence": {
                "patterns": [
                    r"暴力", r"伤害", r"武器", r"攻击", r"打架", r"杀人",
                    r"violence", r"harm", r"weapon", r"attack", r"fight", r"kill"
                ],
                "response": "我无法提供与暴力相关的信息。暴力行为是不道德且违法的。"
            },
            "self_harm": {
                "patterns": [
                    r"自杀", r"自残", r"伤害自己", r"结束生命",
                    r"suicide", r"self-harm", r"hurt yourself", r"end life"
                ],
                "response": "如果你正在考虑伤害自己，请立即联系专业心理健康机构或拨打紧急求助电话。"
            },
            "illegal": {
                "patterns": [
                    r"违法", r"犯罪", r"毒品", r"走私", r"盗窃", r"诈骗",
                    r"illegal", r"crime", r"drugs", r"smuggle", r"steal", r"fraud"
                ],
                "response": "我无法提供与违法行为相关的信息。请遵守法律法规。"
            }
        }
        
        # 偏见检测模式
        self.bias_patterns = [
            r"(男|女)性(不|不适合|不如|更适合)",
            r"(种族|民族|肤色)天生",
            r"(老年人|年轻人)无法",
            r"(宗教|信仰)是(暴力|邪恶|错误)",
            r"(国家|地区)的人都",
            r"(性别|性取向)不正常"
        ]
        
        # 隐私保护模式
        self.privacy_patterns = [
            r"个人信息", r"隐私", r"身份证", r"银行卡", r"密码",
            r"personal information", r"privacy", r"ID card", r"bank card", r"password"
        ]
        
        logger.info("约束执行模块初始化完成")
    
    def check_constraints(self, input_text: str, output_text: str) -> Dict[str, Any]:
        """检查约束
        
        Args:
            input_text: 输入文本
            output_text: 输出文本
            
        Returns:
            检查结果，包含是否通过和替代响应
        """
        # 检查敏感主题
        for topic, config in self.sensitive_topics.items():
            if self._contains_patterns(input_text, config["patterns"]) or \
               self._contains_patterns(output_text, config["patterns"]):
                logger.warning(f"检测到敏感主题: {topic}")
                return {
                    "passed": False,
                    "reason": f"敏感主题: {topic}",
                    "alternative_response": config["response"]
                }
        
        # 检查偏见
        if self._contains_patterns(output_text, self.bias_patterns):
            logger.warning("检测到偏见内容")
            return {
                "passed": False,
                "reason": "偏见内容",
                "alternative_response": "我致力于提供公平、无偏见的信息。每个人都应该受到尊重和平等对待。"
            }
        
        # 检查隐私泄露
        if self._contains_patterns(output_text, self.privacy_patterns):
            logger.warning("检测到隐私相关内容")
            return {
                "passed": False,
                "reason": "隐私内容",
                "alternative_response": "我重视您的隐私。请不要在对话中分享敏感个人信息。"
            }
        
        # 检查有害内容
        if self._contains_harmful_content(output_text):
            logger.warning("检测到有害内容")
            return {
                "passed": False,
                "reason": "有害内容",
                "alternative_response": "我无法提供可能有害或不适当的内容。"
            }
        
        # 检查法律合规性
        if self._contains_illegal_content(output_text):
            logger.warning("检测到违法内容")
            return {
                "passed": False,
                "reason": "违法内容",
                "alternative_response": "我无法提供与违法行为相关的信息。请遵守法律法规。"
            }
        
        # 所有检查通过
        return {
            "passed": True,
            "reason": "无问题",
            "alternative_response": None
        }
    
    def _contains_patterns(self, text: str, patterns: List[str]) -> bool:
        """检查文本是否包含指定模式
        
        Args:
            text: 文本
            patterns: 模式列表
            
        Returns:
            是否包含模式
        """
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _contains_harmful_content(self, text: str) -> bool:
        """检查是否包含有害内容
        
        Args:
            text: 文本
            
        Returns:
            是否包含有害内容
        """
        harmful_patterns = [
            r"如何自杀", r"如何自残", r"如何伤害他人",
            r"how to commit suicide", r"how to hurt yourself", r"how to harm others"
        ]
        return self._contains_patterns(text, harmful_patterns)
    
    def _contains_illegal_content(self, text: str) -> bool:
        """检查是否包含违法内容
        
        Args:
            text: 文本
            
        Returns:
            是否包含违法内容
        """
        illegal_patterns = [
            r"如何制作毒品", r"如何走私", r"如何盗窃",
            r"how to make drugs", r"how to smuggle", r"how to steal"
        ]
        return self._contains_patterns(text, illegal_patterns)
    
    def add_sensitive_topic(self, topic: str, patterns: List[str], response: str):
        """添加敏感主题
        
        Args:
            topic: 主题名称
            patterns: 模式列表
            response: 响应文本
        """
        self.sensitive_topics[topic] = {
            "patterns": patterns,
            "response": response
        }
        logger.info(f"添加敏感主题: {topic}")
    
    def remove_sensitive_topic(self, topic: str):
        """移除敏感主题
        
        Args:
            topic: 主题名称
        """
        if topic in self.sensitive_topics:
            del self.sensitive_topics[topic]
            logger.info(f"移除敏感主题: {topic}")
    
    def get_sensitive_topics(self) -> Dict[str, Dict[str, Any]]:
        """获取敏感主题列表
        
        Returns:
            敏感主题字典
        """
        return self.sensitive_topics


# 全局约束执行模块实例
constraint_enforcement = ConstraintEnforcementModule()