#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询重写器 - 将模糊查询优化为更精确的检索查询
"""

import httpx
import re
from typing import List, Dict, Any, Optional

class QueryRewriter:
    """查询重写器 - 使用 LLM 优化查询"""
    
    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
    
    async def rewrite_query(self, query: str, context: Optional[str] = None) -> str:
        """重写查询为更适合检索的形式"""
        rewrite_prompt = f"""
你是一个专业的查询优化专家。请将用户的问题重写为更适合在知识库中检索的形式。

要求：
1. 将模糊的问题具体化
2. 提取关键实体和术语
3. 补充必要的上下文
4. 保持原意，去除冗余
5. 使用简洁的问句形式

示例：
- 输入："那个政策怎么样？" 
  输出："请提供关于[产品X] 2024年新政策的详细信息和影响"

- 输入："不太明白" 
  输出："[具体术语或概念]的定义和解释"

用户原始问题：
{query}
"""
        
        if context:
            rewrite_prompt += f"\n\n当前对话上下文：\n{context[-500:]}"
        
        messages = [
            {"role": "system", "content": "你是一个专业的查询优化专家。"},
            {"role": "user", "content": rewrite_prompt}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                rewritten = data.get("message", {}).get("content", "").strip()
                return rewritten if rewritten else query
        except Exception as e:
            print(f"查询重写失败: {e}")
            return query
    
    async def expand_query(self, query: str) -> List[str]:
        """扩展查询，生成多个检索词"""
        expand_prompt = f"""
请根据用户的问题，生成3-5个相关的检索词/短语，用于在知识库中进行多角度检索。

要求：
1. 每个检索词应该从不同角度切入
2. 包含同义词和相关概念
3. 使用名词短语或问句形式

用户问题：{query}

请以列表形式输出每个检索词，每行一个。
"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的查询优化专家。"},
            {"role": "user", "content": expand_prompt}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                result = data.get("message", {}).get("content", "")
                
                lines = result.split('\n')
                queries = []
                for line in lines:
                    cleaned = re.sub(r'^[\-\*\d\s\.、]+', '', line.strip())
                    if cleaned and len(cleaned) > 2:
                        queries.append(cleaned)
                
                return queries if queries else [query]
        except Exception as e:
            print(f"查询扩展失败: {e}")
            return [query]


class StructuredOutputFormatter:
    """结构化输出格式化器"""
    
    @staticmethod
    def format_as_json(schema: Dict[str, Any]) -> str:
        """生成 JSON 输出的 Prompt"""
        schema_lines = ["请严格按照以下 JSON Schema 输出：", "", "```json"]
        
        for key, value in schema.items():
            if isinstance(value, dict):
                schema_lines.append(f'  "{key}": {{')
                for sub_key, sub_value in value.items():
                    schema_lines.append(f'    "{sub_key}": "{sub_value}",')
                schema_lines.append('  },')
            else:
                schema_lines.append(f'  "{key}": "{value}",')
        
        schema_lines.append("```")
        
        return '\n'.join(schema_lines)
    
    @staticmethod
    def generate_extraction_prompt(
        task: str,
        context: str,
        schema: Dict[str, Any]
    ) -> str:
        """生成信息提取的 Prompt"""
        prompt = f"""
任务：{task}

参考内容：
{context}

{StructuredOutputFormatter.format_as_json(schema)}

请基于参考内容，按照上述 Schema 提取信息，并以 JSON 格式输出。
如果某个字段在参考内容中没有找到，请使用 null。
"""
        return prompt
    
    @staticmethod
    def generate_summary_prompt(context: str, format: str = "bullet") -> str:
        """生成摘要 Prompt"""
        if format == "bullet":
            return f"""
请总结以下内容的要点：

{context}

请用项目符号列表的形式输出，每个要点简洁明了。
"""
        elif format == "paragraph":
            return f"""
请总结以下内容：

{context}

请用简洁的段落形式输出。
"""
        elif format == "table":
            return f"""
请以表格形式总结以下内容的关键信息：

{context}

请用 Markdown 表格格式输出。
"""
        else:
            return f"""
请总结以下内容：

{context}
"""


class SelfReflectionChecker:
    """自我反思检查器 - 评估答案质量"""
    
    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
    
    async def check_answer(
        self,
        question: str,
        context: str,
        answer: str
    ) -> Dict[str, Any]:
        """检查答案质量"""
        check_prompt = f"""
请评估以下问答的质量：

问题：{question}

参考内容：
{context}

生成的答案：
{answer}

请从以下几个维度评估：

1. 准确性：答案是否准确反映了参考内容？
2. 完整性：答案是否涵盖了参考内容中的重要信息？
3. 相关性：答案是否直接回答了用户的问题？
4. 可读性：答案是否清晰易懂？

如果发现任何问题，请指出并给出改进建议。

请以 JSON 格式输出：
```json
{{
  "quality_score": 0-10,
  "issues": ["问题1", "问题2"],
  "improvements": ["改进建议1", "改进建议2"],
  "needs_revision": true/false
}}
```
"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的答案评估专家。"},
            {"role": "user", "content": check_prompt}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                result = data.get("message", {}).get("content", "")
                
                return self._parse_check_result(result)
        except Exception as e:
            print(f"答案检查失败: {e}")
            return {
                "quality_score": 5,
                "issues": [],
                "improvements": [],
                "needs_revision": False
            }
    
    def _parse_check_result(self, result: str) -> Dict[str, Any]:
        """解析检查结果"""
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "quality_score": 5,
            "issues": ["无法解析评估结果"],
            "improvements": [],
            "needs_revision": False
        }