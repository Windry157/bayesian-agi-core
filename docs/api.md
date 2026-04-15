# Bayesian-AGI-Core API 文档

## 概述

Bayesian-AGI-Core 提供了一组RESTful API，用于与系统进行交互。所有API都通过API Gateway暴露，基础URL默认为 `http://localhost:8000`。

## 健康检查

### GET /health

**描述**：检查系统是否正常运行

**响应**：

```json
{
  "status": "ok",
  "message": "Bayesian-AGI-Core is running"
}
```

## 模型管理

### GET /api/models

**描述**：获取可用的模型列表

**响应**：

```json
{
  "models": [
    {
      "name": "deepseek-r1:7b",
      "provider": "ollama",
      "type": "local",
      "size": 4000000000
    }
  ]
}
```

## 记忆管理

### POST /api/memory

**描述**：添加新的记忆

**请求体**：

```json
{
  "content": "记忆内容",
  "metadata": {
    "source": "user",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

**响应**：

```json
{
  "id": "memory-123",
  "message": "Memory added successfully"
}
```

### GET /api/memory/search

**描述**：检索与查询相关的记忆

**查询参数**：
- `query`：查询内容
- `top_k`：返回的记忆数量，默认为5

**响应**：

```json
{
  "memories": [
    {
      "id": "memory-123",
      "content": "记忆内容",
      "metadata": {
        "source": "user",
        "timestamp": "2024-01-01T00:00:00Z"
      },
      "similarity": 0.95
    }
  ]
}
```

## 决策系统

### POST /api/decision

**描述**：基于可能的行动做出决策

**请求体**：

```json
{
  "possible_actions": ["行动1", "行动2", "行动3"]
}
```

**响应**：

```json
{
  "decision": "行动1"
}
```

## 视觉服务

### POST /api/vision/classify

**描述**：对图像进行分类

**请求体**：
- `file`：图像文件（multipart/form-data）

**响应**：

```json
{
  "classification": "cat",
  "confidence": 0.95
}
```

### POST /api/vision/detect

**描述**：检测图像中的目标

**请求体**：
- `file`：图像文件（multipart/form-data）

**响应**：

```json
{
  "objects": [
    {
      "class": "person",
      "confidence": 0.98,
      "bbox": [100, 100, 200, 300]
    },
    {
      "class": "car",
      "confidence": 0.92,
      "bbox": [300, 200, 500, 350]
    }
  ]
}
```

### POST /api/vision/describe

**描述**：生成图像的文字描述

**请求体**：
- `file`：图像文件（multipart/form-data）

**响应**：

```json
{
  "description": "A cat sitting on a couch"
}
```

## 监控

### GET /health/metrics

**描述**：获取系统的监控指标

**响应**：

```
# HELP http_requests_total Total HTTP Requests
# TYPE http_requests_total counter
http_requests_total 100

# HELP http_request_duration_seconds HTTP Request Duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 50
http_request_duration_seconds_bucket{le="0.5"} 80
http_request_duration_seconds_bucket{le="1.0"} 90
http_request_duration_seconds_bucket{le="5.0"} 95
http_request_duration_seconds_bucket{le="+Inf"} 100
http_request_duration_seconds_sum 50.0
http_request_duration_seconds_count 100
```

## Python SDK

Bayesian-AGI-Core 提供了Python SDK，方便开发者在Python中使用系统的API。

### 安装

```bash
pip install bayesian-agi-core
```

### 使用示例

```python
import asyncio
from bayesian_agi_core import BayesianAGICoreClient

async def main():
    # 初始化客户端
    async with BayesianAGICoreClient() as client:
        # 健康检查
        health = await client.health_check()
        print("健康检查:", health)
        
        # 获取模型列表
        models = await client.get_models()
        print("模型列表:", models)
        
        # 添加记忆
        memory_id = await client.add_memory("这是一个测试记忆", {"source": "test"})
        print("添加记忆:", memory_id)
        
        # 检索记忆
        memories = await client.search_memory("测试")
        print("检索记忆:", memories)
        
        # 做出决策
        decision = await client.make_decision(["行动1", "行动2", "行动3"])
        print("决策结果:", decision)
        
        # 图像分类
        # classification = await client.classify_image("path/to/image.jpg")
        # print("图像分类:", classification)

if __name__ == "__main__":
    asyncio.run(main())
```
