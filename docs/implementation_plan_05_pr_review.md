# 方案五：GitHub Pull Request自动审查

## 📋 任务概述

- **任务名称**: 支持 GitHub Pull Request 自动审查
- **优先级**: 🟡 中
- **难度**: ⭐⭐⭐
- **预计工时**: 40h
- **当前状态**: ❌ 未实现

---

## 🎯 目标

1. GitHub API集成
2. PR自动拉取和分析
3. 代码审查报告生成
4. 审查意见格式化输出

---

## 🏗️ 实施方案

### 1. GitHub API集成

```python
# src/services/github_service.py

import github
from typing import List, Dict

class GitHubService:
    """GitHub服务"""

    def __init__(self, token: str):
        self.github = github.Github(token)

    def get_pull_request(self, owner: str, repo: str, pr_number: int):
        """获取PR信息"""
        repo = self.github.get_repo(f"{owner}/{repo}")
        return repo.get_pull(pr_number)

    def get_changed_files(self, pr) -> List[Dict]:
        """获取变更文件"""
        files = pr.get_files()
        return [
            {
                "filename": f.filename,
                "status": f.status,
                "patch": f.patch,
                "additions": f.additions,
                "deletions": f.deletions
            }
            for f in files
        ]

    def add_review_comment(self, pr, body: str, commit: str, path: str, line: int):
        """添加审查评论"""
        pr.create_review_comment(
            body=body,
            commit=commit,
            path=path,
            line=line
        )
```

### 2. 代码审查分析

```python
# src/services/code_reviewer.py

class CodeReviewer:
    """代码审查器"""

    def __init__(self, llm_service):
        self.llm = llm_service

    def review_changes(self, changed_files: List[Dict]) -> List[Dict]:
        """审查变更"""
        reviews = []

        for file in changed_files:
            analysis = self._analyze_file(file)

            if analysis["issues"]:
                reviews.append({
                    "file": file["filename"],
                    "issues": analysis["issues"],
                    "suggestions": analysis["suggestions"],
                    "score": analysis["score"]
                })

        return reviews

    def _analyze_file(self, file: Dict) -> Dict:
        """分析单个文件"""
        prompt = f"""
        请审查以下代码变更:

        文件: {file['filename']}
        状态: {file['status']}

        变更内容:
        {file['patch']}

        请检查:
        1. 代码质量
        2. 潜在bug
        3. 安全问题
        4. 性能问题
        """

        response = self.llm.generate(prompt)

        return {
            "issues": self._extract_issues(response),
            "suggestions": self._extract_suggestions(response),
            "score": self._calculate_score(response)
        }
```

### 3. MCP Server集成

```python
# src/mcp_server.py - 添加PR审查工具

"review_pull_request": ToolDefinition(
    name="review_pull_request",
    description="自动审查GitHub Pull Request",
    input_schema={
        "type": "object",
        "properties": {
            "owner": {"type": "string"},
            "repo": {"type": "string"},
            "pr_number": {"type": "integer"},
            "github_token": {"type": "string"}
        },
        "required": ["owner", "repo", "pr_number", "github_token"]
    }
)
```

---

## ✅ 验收标准

1. ✅ GitHub API集成完成
2. ✅ PR自动拉取和分析
3. ✅ 审查报告生成
4. ✅ 评论自动提交

是否继续？
