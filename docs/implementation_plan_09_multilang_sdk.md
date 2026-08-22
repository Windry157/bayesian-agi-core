# 方案九：多语言客户端SDK

## 📋 任务概述

- **任务名称**: 多语言客户端 SDK 开发
- **优先级**: 🟢 低
- **难度**: ⭐⭐⭐
- **预计工时**: 60h
- **当前状态**: ⚠️ Python SDK 存在

---

## 🎯 目标

1. TypeScript/JavaScript SDK
2. Go SDK
3. Java SDK
4. REST API 文档完善
5. SDK 版本管理

---

## 🏗️ 实施方案

### 1. TypeScript SDK

```typescript
// sdk/typescript/src/index.ts

export class BayesianAGIClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl;
    this.apiKey = config.apiKey;
  }

  async chat(message: string): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({ message })
    });

    return response.json();
  }

  async evaluateConfidence(code: string, language: string): Promise<ConfidenceResult> {
    const response = await fetch(`${this.baseUrl}/mcp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        method: 'tools/call',
        params: {
          name: 'evaluate_code_confidence',
          arguments: { code, language }
        }
      })
    });

    return response.json();
  }
}
```

### 2. Go SDK

```go
// sdk/go/bayesian_agi.go

package bayesianagi

type Client struct {
    BaseURL string
    APIKey  string
}

func NewClient(baseURL, apiKey string) *Client {
    return &Client{
        BaseURL: baseURL,
        APIKey:  apiKey,
    }
}

func (c *Client) Chat(message string) (*ChatResponse, error) {
    reqBody := map[string]string{"message": message}
    body, err := json.Marshal(reqBody)
    if err != nil {
        return nil, err
    }

    req, _ := http.NewRequest("POST", c.BaseURL+"/api/chat", bytes.NewBuffer(body))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+c.APIKey)

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var chatResp ChatResponse
    json.NewDecoder(resp.Body).Decode(&chatResp)
    return &chatResp, nil
}
```

### 3. Java SDK

```java
// sdk/java/src/main/java/com/bayesian/BayesianAGIClient.java

package com.bayesian;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public class BayesianAGIClient {
    private final String baseUrl;
    private final String apiKey;
    private final HttpClient httpClient;

    public BayesianAGIClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.httpClient = HttpClient.newHttpClient();
    }

    public ChatResponse chat(String message) throws Exception {
        String json = String.format("{\"message\":\"%s\"}", message);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/chat"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer " + apiKey)
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();

        HttpResponse<String> response = httpClient.send(request,
            HttpResponse.BodyHandlers.ofString());

        return new ObjectMapper().readValue(response.body(), ChatResponse.class);
    }
}
```

### 4. API文档（OpenAPI）

```yaml
# docs/openapi.yaml

openapi: 3.0.0
info:
  title: Bayesian-AGI-Core API
  version: 2.0.0
  description: |
    Bayesian-AGI-Core REST API 文档
    支持多语言SDK调用

servers:
  - url: http://localhost:8090
    description: 本地开发服务器
  - url: https://api.example.com
    description: 生产服务器

paths:
  /api/chat:
    post:
      summary: 聊天接口
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  description: 用户消息
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatResponse'

  /mcp:
    post:
      summary: MCP协议端点
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MCPRequest'

components:
  schemas:
    ChatResponse:
      type: object
      properties:
        response:
          type: string
        confidence:
          type: number

    MCPRequest:
      type: object
      properties:
        method:
          type: string
        params:
          type: object
```

---

## ✅ 验收标准

1. ✅ TypeScript SDK可正常使用
2. ✅ Go SDK可正常使用
3. ✅ Java SDK可正常使用
4. ✅ OpenAPI文档完整

---

## 📦 发布管理

```bash
# TypeScript
npm publish @bayesian-agi/sdk

# Go
go publish github.com/bayesian-agi/sdk

# Java
mvn publish
```

---

## 🎯 下一步行动

1. 创建SDK目录结构
2. 实现TypeScript SDK
3. 实现Go SDK
4. 实现Java SDK
5. 编写API文档
6. 发布到各语言包管理器

是否继续？
