#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度可视化模块
提供用户友好的置信度展示和交互
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfidenceVisualizer:
    """置信度可视化器
    
    将置信度分数转换为用户友好的展示格式
    支持多种可视化级别和交互建议
    """

    CONFIDENCE_MESSAGES = {
        "high": {
            "emoji": "🟢",
            "title": "高置信度",
            "description": "我们有高度把握，这是基于综合判断的结果。",
            "user_guidance": "您可以放心使用此答案。"
        },
        "medium": {
            "emoji": "🟡",
            "title": "中等置信度",
            "description": "初步判断为某个结论，但建议您参考更多信息以获得更全面的了解。",
            "user_guidance": "建议结合其他来源交叉验证。"
        },
        "low": {
            "emoji": "🔴",
            "title": "低置信度",
            "description": "信息存在歧义，系统对答案的把握有限。",
            "user_guidance": "强烈建议您提供更多上下文或咨询专家。"
        },
        "very_low": {
            "emoji": "⚫",
            "title": "极低置信度",
            "description": "系统无法有效处理此问题，可能超出当前知识范围。",
            "user_guidance": "建议您换一个更具体的问题或提供更多背景信息。"
        },
        "unknown": {
            "emoji": "⚪",
            "title": "未知置信度",
            "description": "无法评估此响应的置信度。",
            "user_guidance": "请谨慎使用此答案。"
        },
        "error": {
            "emoji": "❌",
            "title": "错误",
            "description": "处理过程中出现错误。",
            "user_guidance": "请稍后重试或联系支持。"
        }
    }

    UNCERTAINTY_SOURCE_MESSAGES = {
        "memory_match": {
            "title": "记忆匹配不足",
            "recommendation": "需要更多相关领域的知识或示例"
        },
        "context_consistency": {
            "title": "上下文一致性低",
            "recommendation": "需要澄清问题背景或提供更多上下文"
        },
        "knowledge_coverage": {
            "title": "知识覆盖不足",
            "recommendation": "需要扩展相关知识库"
        },
        "historical_similarity": {
            "title": "缺乏类似历史案例",
            "recommendation": "需要更多类似问题的经验积累"
        }
    }

    def __init__(self):
        """初始化置信度可视化器"""
        self.display_settings = {
            "show_emoji": True,
            "show_percentage": True,
            "show_confidence_range": True,
            "show_user_guidance": True,
            "show_uncertainty_sources": True,
            "color_enabled": True
        }
        logger.info("置信度可视化器初始化完成")

    def visualize_confidence(
        self,
        confidence_score: float,
        confidence_level: str = None,
        confidence_details: Dict[str, Any] = None,
        input_text: str = None,
        response_text: str = None
    ) -> Dict[str, Any]:
        """生成置信度可视化数据
        
        Args:
            confidence_score: 置信度分数 (0-1)
            confidence_level: 置信度级别
            confidence_details: 置信度详情
            input_text: 输入文本
            response_text: 响应文本
            
        Returns:
            可视化数据
        """
        try:
            if confidence_level is None:
                confidence_level = self._classify_confidence(confidence_score)

            message_info = self.CONFIDENCE_MESSAGES.get(
                confidence_level,
                self.CONFIDENCE_MESSAGES["unknown"]
            )

            visualization = {
                "confidence_score": confidence_score,
                "confidence_percentage": round(confidence_score * 100, 1),
                "confidence_level": confidence_level,
                "display": {
                    "emoji": message_info["emoji"] if self.display_settings["show_emoji"] else "",
                    "title": message_info["title"],
                    "description": message_info["description"],
                    "user_guidance": message_info["user_guidance"] if self.display_settings["show_user_guidance"] else None,
                    "color": self._get_confidence_color(confidence_score)
                }
            }

            if self.display_settings["show_confidence_range"]:
                visualization["confidence_range"] = self._calculate_confidence_range(confidence_score)

            if self.display_settings["show_uncertainty_sources"] and confidence_details:
                visualization["uncertainty_sources"] = self._format_uncertainty_sources(confidence_details)

            if input_text:
                visualization["input_text"] = input_text[:100] + ("..." if len(input_text) > 100 else "")

            if response_text:
                visualization["response_preview"] = response_text[:200] + ("..." if len(response_text) > 200 else "")

            return visualization

        except Exception as e:
            logger.error(f"置信度可视化生成失败: {e}")
            return self._create_error_visualization()

    def _calculate_confidence_range(self, confidence_score: float) -> Dict[str, float]:
        """计算置信度区间
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            置信度区间
        """
        base_range = 0.1
        
        if confidence_score >= 0.8:
            range_width = 0.1
        elif confidence_score >= 0.6:
            range_width = 0.15
        elif confidence_score >= 0.4:
            range_width = 0.2
        else:
            range_width = 0.25
        
        lower = max(0.0, confidence_score - range_width)
        upper = min(1.0, confidence_score + range_width)
        
        return {
            "lower": round(lower * 100, 1),
            "upper": round(upper * 100, 1),
            "display": f"{round(lower * 100, 1)}% - {round(upper * 100, 1)}%"
        }

    def _format_uncertainty_sources(self, confidence_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """格式化不确定性来源
        
        Args:
            confidence_details: 置信度详情
            
        Returns:
            格式化的不确定性来源列表
        """
        formatted_sources = []
        
        uncertainty_analysis = confidence_details.get("uncertainty_analysis", {})
        sources = uncertainty_analysis.get("uncertainty_sources", [])
        
        for source in sources:
            source_type = source.get("source", "unknown")
            source_info = self.UNCERTAINTY_SOURCE_MESSAGES.get(source_type, {
                "title": source_type,
                "recommendation": source.get("description", "")
            })
            
            formatted_sources.append({
                "type": source_type,
                "title": source_info["title"],
                "score": source.get("score", 0),
                "recommendation": source_info["recommendation"],
                "description": source.get("description", "")
            })
        
        return formatted_sources

    def _get_confidence_color(self, confidence_score: float) -> str:
        """获取置信度对应的颜色
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            颜色代码
        """
        if confidence_score >= 0.8:
            return "#28a745"
        elif confidence_score >= 0.6:
            return "#ffc107"
        elif confidence_score >= 0.4:
            return "#fd7e14"
        else:
            return "#dc3545"

    def _classify_confidence(self, confidence_score: float) -> str:
        """分类置信度
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            置信度级别
        """
        if confidence_score >= 0.8:
            return "high"
        elif confidence_score >= 0.6:
            return "medium"
        elif confidence_score >= 0.4:
            return "low"
        elif confidence_score >= 0.2:
            return "very_low"
        else:
            return "unknown"

    def _create_error_visualization(self) -> Dict[str, Any]:
        """创建错误可视化
        
        Returns:
            错误可视化数据
        """
        return {
            "confidence_score": 0.0,
            "confidence_percentage": 0.0,
            "confidence_level": "error",
            "display": self.CONFIDENCE_MESSAGES["error"],
            "error": True
        }

    def generate_user_feedback_suggestions(
        self,
        confidence_level: str,
        uncertainty_sources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成用户反馈建议
        
        Args:
            confidence_level: 置信度级别
            uncertainty_sources: 不确定性来源列表
            
        Returns:
            反馈建议
        """
        suggestions = {
            "primary_action": None,
            "alternative_actions": [],
            "questions_to_ask": []
        }

        if confidence_level == "high":
            suggestions["primary_action"] = {
                "text": "接受答案",
                "type": "accept"
            }
            suggestions["alternative_actions"] = [
                {"text": "请求详细解释", "type": "explain"},
                {"text": "查看引用来源", "type": "cite"}
            ]

        elif confidence_level == "medium":
            suggestions["primary_action"] = {
                "text": "查看不确定性提示",
                "type": "review_uncertainty"
            }
            suggestions["alternative_actions"] = [
                {"text": "提供更多上下文", "type": "provide_context"},
                {"text": "请求其他信息来源", "type": "alternative_source"}
            ]
            suggestions["questions_to_ask"] = [
                "您能提供更多关于这个问题的背景信息吗？",
                "您想了解这个问题的哪个具体方面？"
            ]

        elif confidence_level == "low" or confidence_level == "very_low":
            suggestions["primary_action"] = {
                "text": "提供更多信息或澄清问题",
                "type": "request_clarification"
            }
            suggestions["alternative_actions"] = [
                {"text": "换一个更具体的问题", "type": "rephrase"},
                {"text": "切换到专家模式", "type": "expert_mode"},
                {"text": "联系人工客服", "type": "human_support"}
            ]
            suggestions["questions_to_ask"] = [
                "您能更具体地描述您的问题吗？",
                "这个问题的背景是什么？",
                "您期望得到什么样的答案？"
            ]

        if uncertainty_sources:
            for source in uncertainty_sources[:2]:
                suggestions["questions_to_ask"].append(
                    f"关于{source.get('title', '这个方面')}，您能提供更多具体信息吗？"
                )

        return suggestions

    def format_response_for_display(
        self,
        answer: str,
        confidence_score: float,
        confidence_level: str = None,
        confidence_details: Dict[str, Any] = None,
        include_guidance: bool = True
    ) -> str:
        """格式化用于显示的响应文本
        
        Args:
            answer: 答案文本
            confidence_score: 置信度分数
            confidence_level: 置信度级别
            confidence_details: 置信度详情
            include_guidance: 是否包含用户指导
            
        Returns:
            格式化的显示文本
        """
        if confidence_level is None:
            confidence_level = self._classify_confidence(confidence_score)

        message_info = self.CONFIDENCE_MESSAGES.get(
            confidence_level,
            self.CONFIDENCE_MESSAGES["unknown"]
        )

        lines = []

        lines.append(f"{message_info['emoji']} **{message_info['title']}**")
        lines.append(f"置信度: {round(confidence_score * 100, 1)}%")

        if self.display_settings["show_confidence_range"]:
            confidence_range = self._calculate_confidence_range(confidence_score)
            lines.append(f"置信区间: {confidence_range['display']}")

        lines.append("")
        lines.append(f"**答案:** {answer}")
        lines.append("")

        if include_guidance:
            lines.append(f"💡 {message_info['user_guidance']}")

        if confidence_details and confidence_level in ["low", "very_low", "medium"]:
            uncertainty_analysis = confidence_details.get("uncertainty_analysis", {})
            sources = uncertainty_analysis.get("uncertainty_sources", [])
            
            if sources:
                lines.append("")
                lines.append("**不确定性的可能来源:**")
                for source in sources[:2]:
                    source_type = source.get("source", "unknown")
                    source_info = self.UNCERTAINTY_SOURCE_MESSAGES.get(source_type, {})
                    lines.append(f"- {source_info.get('title', source_type)}")

        return "\n".join(lines)

    def set_display_settings(self, settings: Dict[str, bool]):
        """设置显示选项
        
        Args:
            settings: 显示设置
        """
        valid_settings = [
            "show_emoji",
            "show_percentage",
            "show_confidence_range",
            "show_user_guidance",
            "show_uncertainty_sources",
            "color_enabled"
        ]
        
        for key, value in settings.items():
            if key in valid_settings:
                self.display_settings[key] = value
                logger.info(f"设置显示选项: {key} = {value}")

    def get_display_settings(self) -> Dict[str, bool]:
        """获取显示选项
        
        Returns:
            显示设置
        """
        return self.display_settings.copy()


class ConfidenceFormatter:
    """置信度格式化器
    
    提供不同格式的置信度输出
    """

    @staticmethod
    def format_percentage(confidence_score: float, decimals: int = 1) -> str:
        """格式化为百分比
        
        Args:
            confidence_score: 置信度分数
            decimals: 小数位数
            
        Returns:
            百分比字符串
        """
        return f"{round(confidence_score * 100, decimals)}%"

    @staticmethod
    def format_fraction(confidence_score: float) -> str:
        """格式化为分数
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            分数字符串
        """
        return f"{confidence_score:.2f}"

    @staticmethod
    def format_bar(confidence_score: float, length: int = 10) -> str:
        """格式化为进度条
        
        Args:
            confidence_score: 置信度分数
            length: 进度条长度
            
        Returns:
            进度条字符串
        """
        filled = int(confidence_score * length)
        empty = length - filled
        return "[" + "=" * filled + " " * empty + "]"

    @staticmethod
    def format_badge(confidence_score: float) -> Dict[str, Any]:
        """格式化为徽章
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            徽章数据
        """
        if confidence_score >= 0.8:
            label = "高"
            color = "success"
        elif confidence_score >= 0.6:
            label = "中"
            color = "warning"
        elif confidence_score >= 0.4:
            label = "低"
            color = "danger"
        else:
            label = "极低"
            color = "dark"

        return {
            "label": label,
            "color": color,
            "score": confidence_score
        }


# 全局可视化器实例
confidence_visualizer = ConfidenceVisualizer()