#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话历史管理器 - 支持多轮对话和上下文管理
"""

from typing import List, Dict, Any, Optional
from collections import deque
import json
import os

class ConversationManager:
    """对话管理器"""
    
    def __init__(
        self,
        max_history: int = 20,
        max_tokens: int = 4000,
        summarize_threshold: int = 15
    ):
        self.max_history = max_history
        self.max_tokens = max_tokens
        self.summarize_threshold = summarize_threshold
        self.conversations = {}
    
    def create_conversation(self, session_id: str) -> str:
        """创建新对话"""
        self.conversations[session_id] = {
            'history': deque(maxlen=self.max_history),
            'summary': '',
            'message_count': 0,
            'created_at': self._get_timestamp()
        }
        return session_id
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """添加消息到对话历史"""
        if session_id not in self.conversations:
            self.create_conversation(session_id)
        
        conv = self.conversations[session_id]
        
        message = {
            'role': role,
            'content': content,
            'timestamp': self._get_timestamp()
        }
        
        if metadata:
            message['metadata'] = metadata
        
        conv['history'].append(message)
        conv['message_count'] += 1
        
        if conv['message_count'] >= self.summarize_threshold:
            self._auto_summarize(session_id)
    
    def get_context(
        self,
        session_id: str,
        include_summary: bool = True,
        max_turns: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """获取对话上下文"""
        if session_id not in self.conversations:
            return []
        
        conv = self.conversations[session_id]
        messages = []
        
        if include_summary and conv['summary']:
            messages.append({
                'role': 'system',
                'content': f"【对话摘要】{conv['summary']}"
            })
        
        history_list = list(conv['history'])
        
        if max_turns:
            history_list = history_list[-max_turns:]
        
        for msg in history_list:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        return self._trim_by_tokens(messages)
    
    def _trim_by_tokens(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """按 token 数量裁剪消息"""
        total_chars = sum(len(m['content']) for m in messages)
        max_chars = self.max_tokens * 4
        
        if total_chars <= max_chars:
            return messages
        
        trimmed = []
        current_chars = 0
        
        for msg in reversed(messages):
            msg_chars = len(msg['content'])
            if current_chars + msg_chars <= max_chars:
                trimmed.insert(0, msg)
                current_chars += msg_chars
            else:
                break
        
        return trimmed
    
    def _auto_summarize(self, session_id: str):
        """自动生成摘要"""
        if session_id not in self.conversations:
            return
        
        conv = self.conversations[session_id]
        
        if conv['summary']:
            summary_prompt = f"""
当前对话摘要：
{conv['summary']}

请根据以下新消息，更新这个摘要：

{self._format_history(conv['history'][-self.summarize_threshold:])}

请用简洁的语言总结对话的主要内容和关键点。
"""
        else:
            summary_prompt = f"""
请总结以下对话的主要内容和关键点：

{self._format_history(conv['history'])}

请用简洁的语言总结。
"""
        
        conv['summary'] = summary_prompt
    
    def _format_history(self, history: deque) -> str:
        """格式化对话历史"""
        return "\n".join([
            f"{msg['role']}: {msg['content'][:200]}"
            for msg in history
        ])
    
    def set_summary(self, session_id: str, summary: str):
        """手动设置摘要"""
        if session_id not in self.conversations:
            self.create_conversation(session_id)
        self.conversations[session_id]['summary'] = summary
    
    def clear_conversation(self, session_id: str):
        """清空对话"""
        if session_id in self.conversations:
            del self.conversations[session_id]
    
    def get_conversation_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取对话信息"""
        if session_id not in self.conversations:
            return None
        
        conv = self.conversations[session_id]
        return {
            'message_count': conv['message_count'],
            'has_summary': bool(conv['summary']),
            'summary_preview': conv['summary'][:100] if conv['summary'] else '',
            'created_at': conv['created_at']
        }
    
    def save_to_file(self, filepath: str):
        """保存对话到文件"""
        data = {
            session_id: {
                'history': list(conv['history']),
                'summary': conv['summary'],
                'message_count': conv['message_count'],
                'created_at': conv['created_at']
            }
            for session_id, conv in self.conversations.items()
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str):
        """从文件加载对话"""
        if not os.path.exists(filepath):
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for session_id, conv_data in data.items():
            self.conversations[session_id] = {
                'history': deque(conv_data['history'], maxlen=self.max_history),
                'summary': conv_data.get('summary', ''),
                'message_count': conv_data.get('message_count', 0),
                'created_at': conv_data.get('created_at', '')
            }
    
    @staticmethod
    def _get_timestamp() -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
