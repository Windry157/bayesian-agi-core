#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反馈收集器模块
收集用户反馈以改进置信度评分模型
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FeedbackCollector:
    """反馈收集器
    
    收集用户对系统响应的反馈，用于改进置信度评分模型
    支持反馈类型：正确、不正确、不确定、需要改进
    """
    
    def __init__(self, storage_dir: str = "memory/feedback"):
        """初始化反馈收集器
        
        Args:
            storage_dir: 反馈存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.feedback_history = []
        self.load_feedback_history()
        
        logger.info(f"反馈收集器初始化完成，存储目录: {storage_dir}")
    
    async def submit_feedback(
        self,
        session_id: str,
        input_text: str,
        system_response: Dict[str, Any],
        feedback_type: str,
        feedback_details: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        user_correction: Optional[str] = None
    ) -> Dict[str, Any]:
        """提交反馈
        
        Args:
            session_id: 会话ID
            input_text: 原始输入文本
            system_response: 系统原始响应
            feedback_type: 反馈类型 (correct/incorrect/uncertain/needs_improvement)
            feedback_details: 反馈详情
            confidence_score: 系统置信度分数
            user_correction: 用户修正（如果反馈类型为incorrect）
            
        Returns:
            反馈提交结果
        """
        try:
            # 验证反馈类型
            valid_feedback_types = ["correct", "incorrect", "uncertain", "needs_improvement"]
            if feedback_type not in valid_feedback_types:
                raise ValueError(f"无效的反馈类型，必须是: {valid_feedback_types}")
            
            # 提取置信度分数（如果未提供）
            if confidence_score is None:
                confidence_score = system_response.get("confidence", 0.5)
            
            # 创建反馈记录
            feedback_record = {
                "feedback_id": f"feedback_{int(datetime.now().timestamp())}_{len(self.feedback_history)}",
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "input_text": input_text,
                "system_response": system_response,
                "feedback_type": feedback_type,
                "feedback_details": feedback_details or {},
                "confidence_score": confidence_score,
                "user_correction": user_correction,
                "metadata": {
                    "response_has_confidence": "confidence" in system_response,
                    "response_has_answer": "answer" in system_response,
                    "response_type": type(system_response).__name__
                }
            }
            
            # 保存反馈记录
            await self._save_feedback_record(feedback_record)
            
            # 更新反馈历史
            self.feedback_history.append(feedback_record)
            
            # 分析反馈以改进置信度模型
            await self._analyze_feedback_for_improvement(feedback_record)
            
            logger.info(f"反馈提交成功: {feedback_type}, ID: {feedback_record['feedback_id']}")
            
            return {
                "success": True,
                "feedback_id": feedback_record["feedback_id"],
                "message": "反馈已成功提交，将用于改进系统",
                "timestamp": feedback_record["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"反馈提交失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """获取反馈统计信息
        
        Returns:
            反馈统计信息
        """
        if not self.feedback_history:
            return {"total": 0, "by_type": {}, "avg_confidence": 0}
        
        # 按类型统计
        by_type = {}
        for feedback in self.feedback_history:
            ftype = feedback["feedback_type"]
            by_type[ftype] = by_type.get(ftype, 0) + 1
        
        # 计算平均置信度
        confidence_scores = [f.get("confidence_score", 0.5) for f in self.feedback_history]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # 计算准确性（基于正确/不正确反馈）
        correct_count = by_type.get("correct", 0)
        incorrect_count = by_type.get("incorrect", 0)
        total_rated = correct_count + incorrect_count
        
        accuracy = correct_count / total_rated if total_rated > 0 else 0
        
        return {
            "total": len(self.feedback_history),
            "by_type": by_type,
            "avg_confidence": avg_confidence,
            "accuracy": accuracy,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "uncertain_count": by_type.get("uncertain", 0),
            "needs_improvement_count": by_type.get("needs_improvement", 0),
            "first_feedback": self.feedback_history[0]["timestamp"] if self.feedback_history else None,
            "last_feedback": self.feedback_history[-1]["timestamp"] if self.feedback_history else None
        }
    
    async def get_feedback_for_confidence_calibration(self) -> List[Dict[str, Any]]:
        """获取用于置信度校准的反馈
        
        Returns:
            用于校准的反馈列表
        """
        # 筛选出可用于校准的反馈（正确/不正确）
        calibration_feedback = []
        
        for feedback in self.feedback_history:
            if feedback["feedback_type"] in ["correct", "incorrect"]:
                calibration_feedback.append({
                    "feedback_id": feedback["feedback_id"],
                    "input_text": feedback["input_text"],
                    "confidence_score": feedback["confidence_score"],
                    "was_correct": feedback["feedback_type"] == "correct",
                    "timestamp": feedback["timestamp"]
                })
        
        return calibration_feedback
    
    async def _save_feedback_record(self, feedback_record: Dict[str, Any]):
        """保存反馈记录到文件
        
        Args:
            feedback_record: 反馈记录
        """
        try:
            # 按日期组织文件
            date_str = datetime.now().strftime("%Y%m%d")
            date_dir = self.storage_dir / date_str
            date_dir.mkdir(exist_ok=True)
            
            # 保存为JSON文件
            filename = f"{feedback_record['feedback_id']}.json"
            filepath = date_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(feedback_record, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"反馈记录保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存反馈记录失败: {e}")
    
    async def _analyze_feedback_for_improvement(self, feedback_record: Dict[str, Any]):
        """分析反馈以改进置信度模型
        
        Args:
            feedback_record: 反馈记录
        """
        try:
            feedback_type = feedback_record["feedback_type"]
            confidence_score = feedback_record["confidence_score"]
            
            # 根据反馈类型分析置信度模型问题
            if feedback_type == "incorrect" and confidence_score > 0.7:
                # 高置信度但答案错误：模型过度自信
                logger.warning(f"检测到过度自信: 置信度={confidence_score:.3f} 但答案错误")
                
                # 记录过度自信案例
                overconfidence_record = {
                    "type": "overconfidence",
                    "original_feedback_id": feedback_record["feedback_id"],
                    "confidence_score": confidence_score,
                    "expected_confidence": 0.3,  # 应该更低的置信度
                    "discrepancy": confidence_score - 0.3,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self._save_analysis_record(overconfidence_record, "overconfidence")
                
            elif feedback_type == "correct" and confidence_score < 0.4:
                # 低置信度但答案正确：模型信心不足
                logger.warning(f"检测到信心不足: 置信度={confidence_score:.3f} 但答案正确")
                
                underconfidence_record = {
                    "type": "underconfidence",
                    "original_feedback_id": feedback_record["feedback_id"],
                    "confidence_score": confidence_score,
                    "expected_confidence": 0.7,  # 应该更高的置信度
                    "discrepancy": 0.7 - confidence_score,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self._save_analysis_record(underconfidence_record, "underconfidence")
                
            elif feedback_type == "uncertain":
                # 用户标记为不确定：需要改进不确定性表达
                logger.info(f"用户标记不确定: 系统置信度={confidence_score:.3f}")
                
                uncertainty_record = {
                    "type": "user_uncertainty",
                    "original_feedback_id": feedback_record["feedback_id"],
                    "system_confidence": confidence_score,
                    "user_perception": "uncertain",
                    "timestamp": datetime.now().isoformat()
                }
                
                await self._save_analysis_record(uncertainty_record, "uncertainty")
            
        except Exception as e:
            logger.error(f"反馈分析失败: {e}")
    
    async def _save_analysis_record(self, record: Dict[str, Any], category: str):
        """保存分析记录
        
        Args:
            record: 分析记录
            category: 记录类别
        """
        try:
            analysis_dir = self.storage_dir / "analysis" / category
            analysis_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{record['type']}_{int(datetime.now().timestamp())}.json"
            filepath = analysis_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存分析记录失败: {e}")
    
    def load_feedback_history(self):
        """加载反馈历史"""
        try:
            # 查找所有反馈JSON文件
            feedback_files = list(self.storage_dir.glob("**/*.json"))
            
            for filepath in feedback_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        feedback_record = json.load(f)
                    
                    self.feedback_history.append(feedback_record)
                    
                except Exception as e:
                    logger.warning(f"加载反馈文件失败 {filepath}: {e}")
            
            # 按时间戳排序
            self.feedback_history.sort(key=lambda x: x.get("timestamp", ""))
            
            logger.info(f"加载反馈历史: {len(self.feedback_history)} 条记录")
            
        except Exception as e:
            logger.error(f"加载反馈历史失败: {e}")
            self.feedback_history = []
    
    async def clear_feedback_history(self, confirm: bool = False) -> Dict[str, Any]:
        """清空反馈历史（谨慎使用）
        
        Args:
            confirm: 确认标志，必须为True才能执行
            
        Returns:
            操作结果
        """
        if not confirm:
            return {
                "success": False,
                "message": "请设置confirm=true以确认清空反馈历史"
            }
        
        try:
            # 备份当前历史
            backup_count = len(self.feedback_history)
            
            # 清空内存中的历史
            self.feedback_history = []
            
            # 删除存储文件（可选，谨慎操作）
            # 这里我们只清空内存，保留文件
            
            logger.warning(f"反馈历史已清空（内存中），备份记录数: {backup_count}")
            
            return {
                "success": True,
                "message": f"已清空内存中的反馈历史，备份记录数: {backup_count}",
                "backup_count": backup_count
            }
            
        except Exception as e:
            logger.error(f"清空反馈历史失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 全局反馈收集器实例
feedback_collector = FeedbackCollector()