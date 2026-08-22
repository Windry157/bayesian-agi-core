# 方案一：CI/CD流水线增强与生产部署

## 📋 任务概述

- **任务名称**: 集成到 CI/CD 流水线
- **优先级**: 🔴 高
- **难度**: ⭐⭐
- **预计工时**: 15h
- **当前状态**: ⚠️ 基础CI配置存在，需完善

---

## 🎯 目标

1. 完善现有CI/CD工作流
2. 添加MCP Server自动化测试
3. 配置生产环境自动部署
4. 添加监控和告警集成
5. 实现回滚机制

---

## 📊 现有配置分析

### ✅ 已实现

```yaml
现有CI功能:
  - 代码检出 (actions/checkout)
  - Python环境设置
  - 依赖缓存
  - 单元测试
  - 代码质量检查 (flake8, black, isort)
  - 代码覆盖率报告
  - Docker镜像构建
```

### ❌ 缺失功能

```yaml
缺失功能:
  - MCP Server集成测试
  - 生产环境部署
  - 监控集成
  - 告警配置
  - 回滚机制
```

---

## 🏗️ 实施方案

### 阶段 1：完善CI测试覆盖（5h）

#### 1.1 添加MCP Server测试

创建新文件：`tests/test_mcp_server.py`

```python
import pytest
from src.mcp_server import BayesianMCPServer

@pytest.fixture
def mcp_server():
    return BayesianMCPServer()

def test_health_endpoint(mcp_server):
    # 测试健康检查端点

def test_tools_list(mcp_server):
    # 测试工具列表

def test_tools_call(mcp_server):
    # 测试工具调用

def test_resources_list(mcp_server):
    # 测试资源列表

def test_bayesian_reasoning(mcp_server):
    # 测试贝叶斯推理功能
```

#### 1.2 更新CI配置

修改：`.github/workflows/ci.yml`

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # ... 现有步骤 ...

      - name: Run MCP Server tests
        run: pytest tests/test_mcp_server.py -v

      - name: Run integration tests
        run: pytest tests/test_integration.py -v

      - name: Run E2E tests
        run: pytest tests/test_e2e.py -v
```

---

### 阶段 2：添加CD部署配置（5h）

#### 2.1 创建CD工作流

新建：`.github/workflows/cd.yml`

```yaml
name: CD Pipeline

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Staging
        run: |
          # SSH到staging服务器
          # 拉取最新代码
          # 重启服务
          echo "Deployed to staging"

      - name: Run smoke tests
        run: |
          # 健康检查
          curl -f https://staging.example.com/health
          # MCP Server测试
          curl -f https://staging.example.com:8090/health

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.event_name == 'push'
    environment:
      name: production
      url: https://production.example.com
    steps:
      - name: Deploy to Production
        run: |
          # 备份当前版本
          # 部署新版本
          # 健康检查
          echo "Deployed to production"

      - name: Notify on Slack
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: 'deployments'
          payload: |
            {
              "text": "Deployment successful: ${{ github.event.repository.name }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Deployment Successful* :white_check_mark:"
                  }
                }
              ]
            }
```

#### 2.2 添加回滚脚本

新建：`scripts/rollback.sh`

```bash
#!/bin/bash
# rollback.sh - 回滚到上一个稳定版本

BACKUP_DIR="/opt/bayesian-agi/backups"
CURRENT_VERSION=$(cat $BACKUP_DIR/current_version.txt)
PREVIOUS_VERSION=$(ls -t $BACKUP_DIR | head -2 | tail -1)

echo "Rolling back from $CURRENT_VERSION to $PREVIOUS_VERSION"

# 停止当前服务
sudo systemctl stop bayesian-agi

# 恢复配置
sudo cp $BACKUP_DIR/$PREVIOUS_VERSION/config.yaml /opt/bayesian-agi/config.yaml

# 启动服务
sudo systemctl start bayesian-agi

echo "Rollback complete"
```

---

### 阶段 3：监控与告警集成（5h）

#### 3.1 配置Prometheus告警规则

新建：`prometheus/alerts.yml`

```yaml
groups:
  - name: bayesian-agi-alerts
    rules:
      - alert: ServiceDown
        expr: up{job="bayesian-agi"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"

      - alert: MCPServerDown
        expr: up{job="mcp-server"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "MCP Server is not responding"
```

#### 3.2 添加健康检查端点

更新：`src/mcp_server.py`

```python
@app.get("/health/detailed")
async def detailed_health():
    """详细健康检查"""
    return {
        "status": "healthy",
        "server": "BayesianAGICore",
        "version": "2.0.0",
        "checks": {
            "ollama": check_ollama_connection(),
            "memory": check_memory_system(),
            "llm": check_llm_service()
        },
        "uptime": get_uptime(),
        "metrics": get_basic_metrics()
    }
```

---

## 📁 文件清单

### 需要创建的文件

| 文件路径 | 说明 | 优先级 |
|---------|------|--------|
| `tests/test_mcp_server.py` | MCP Server测试 | P0 |
| `.github/workflows/cd.yml` | CD部署工作流 | P0 |
| `scripts/rollback.sh` | 回滚脚本 | P1 |
| `scripts/deploy.sh` | 部署脚本 | P1 |
| `prometheus/alerts.yml` | 告警规则 | P2 |

### 需要修改的文件

| 文件路径 | 修改内容 | 优先级 |
|---------|---------|--------|
| `.github/workflows/ci.yml` | 添加MCP测试 | P0 |
| `src/mcp_server.py` | 详细健康检查 | P1 |
| `docker-compose.yml` | 添加监控服务 | P2 |

---

## 🔧 依赖项

```yaml
测试依赖:
  - pytest
  - pytest-asyncio
  - pytest-cov
  - httpx (用于HTTP测试)

监控依赖:
  - prometheus-client
  - aioprometheus
  - psutil

部署依赖:
  - ansible (可选)
  - docker
  - docker-compose
```

---

## ✅ 验收标准

1. ✅ 所有CI测试通过（单元测试、集成测试、E2E测试）
2. ✅ 代码覆盖率 > 80%
3. ✅ 自动化部署到staging成功
4. ✅ 部署后自动运行烟雾测试
5. ✅ Prometheus告警规则正确配置
6. ✅ 回滚脚本可正常使用
7. ✅ Slack/邮件告警正常工作

---

## 📈 成功指标

- CI pipeline执行时间 < 10分钟
- 测试覆盖率 > 80%
- 部署频率：每天最多5次
- 平均部署时间 < 5分钟
- 回滚时间 < 3分钟
- 告警响应时间 < 5分钟

---

## ⚠️ 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 部署失败 | 高 | 蓝绿部署，保持旧版本可用 |
| 数据库迁移失败 | 高 | 迁移前备份，失败即回滚 |
| 服务中断 | 中 | 健康检查 + 自动回滚 |
| 配置错误 | 中 | 配置验证 + 回滚机制 |

---

## 🎯 下一步行动

1. ✅ 创建 `tests/test_mcp_server.py`
2. ✅ 更新 `.github/workflows/ci.yml`
3. ✅ 创建 `.github/workflows/cd.yml`
4. ✅ 创建 `scripts/rollback.sh`
5. ✅ 创建 `scripts/deploy.sh`
6. ✅ 配置Prometheus告警
7. ✅ 测试完整CI/CD流程

是否开始执行？
