#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码生成器模块 - OpenCode核心能力
"""

import httpx
import json
from typing import List, Dict, Any, Optional

class CodeGenerator:
    """代码生成器"""
    
    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
    
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        system_prompt = f"""
你是一个专业的{language}程序员，精通代码编写。请根据用户需求生成高质量、可运行的{language}代码。

要求：
1. 代码必须正确、可运行
2. 添加必要的注释
3. 遵循最佳实践
4. 处理边界情况
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
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
                return data.get("message", {}).get("content", "")
        except Exception as e:
            return f"代码生成失败: {str(e)}"
    
    async def optimize_code(self, code: str) -> str:
        prompt = f"""
请优化以下代码，使其更高效、更可读：

```python
{code}
```

优化方向：
1. 性能优化
2. 代码可读性
3. 错误处理
4. 代码风格
"""
        
        return await self.generate_code(prompt)
    
    async def debug_code(self, code: str, error: str = "") -> str:
        prompt = f"""
请帮助调试以下代码：

```python
{code}
```

错误信息（如果有）：
{error}

请找出问题并提供修复后的代码。
"""
        
        return await self.generate_code(prompt)
    
    async def explain_code(self, code: str) -> str:
        prompt = f"""
请详细解释以下代码的功能和实现原理：

```python
{code}
```

包括：
1. 代码的整体功能
2. 关键逻辑的解释
3. 使用的算法或设计模式
"""
        
        return await self.generate_code(prompt)
    
    async def generate_test(self, code: str) -> str:
        prompt = f"""
请为以下代码生成单元测试（使用 pytest）：

```python
{code}
```

测试要求：
1. 覆盖主要功能
2. 包含边界情况测试
3. 使用 pytest 框架
"""
        
        return await self.generate_code(prompt)
    
    async def generate_documentation(self, code: str) -> str:
        prompt = f"""
请为以下代码生成详细的文档：

```python
{code}
```

文档要求：
1. 函数/类的功能说明
2. 参数说明
3. 返回值说明
4. 使用示例
"""
        
        return await self.generate_code(prompt)