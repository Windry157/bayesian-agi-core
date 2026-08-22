# 方案二：多模态输入增强（语音识别与处理）

## 📋 任务概述

- **任务名称**: 实现多模态输入（图像、语音）
- **优先级**: 🔴 高
- **难度**: ⭐⭐⭐
- **预计工时**: 40h
- **当前状态**: ⚠️ 基础架构已存在（文本、图像），语音未实现

---

## 🎯 目标

1. 实现语音识别（ASR）功能
2. 集成 Whisper 模型进行语音转文本
3. 添加语音命令识别
4. 实现语音与文本的融合处理
5. 优化多模态融合性能

---

## 📊 现有配置分析

### ✅ 已实现

```python
现有功能:
  - BasicMultimodalProcessor
  - /api/multimodal/text 端点
  - /api/multimodal/image 端点
  - /api/multimodal/audio 端点（框架）
  - supported_input_types = ["text", "image", "audio"]
```

### ❌ 缺失功能

```python
缺失功能:
  - Whisper模型集成
  - 语音预处理
  - 语音命令识别
  - 实时语音流处理
  - 多模态注意力融合
```

---

## 🏗️ 实施方案

### 阶段 1：语音识别基础（15h）

#### 1.1 添加语音处理依赖

更新：`requirements.txt`

```txt
# 语音处理
openai-whisper>=20231117
torchaudio>=2.0.0
librosa>=0.10.0

# 实时处理
websockets>=11.0.0
```

#### 1.2 创建语音服务模块

新建：`src/core/multimodal/speech_processor.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音处理模块
集成Whisper模型进行语音识别
"""

import io
import asyncio
from typing import Optional, Dict, Any
import numpy as np
import whisper
import torch

class SpeechProcessor:
    """语音处理器"""

    def __init__(self, model_size: str = "base"):
        """初始化语音处理器

        Args:
            model_size: Whisper模型大小 ("tiny", "base", "small", "medium", "large")
        """
        self.model_size = model_size
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_model(self):
        """加载Whisper模型"""
        if self.model is None:
            self.model = whisper.load_model(self.model_size, device=self.device)
            print(f"Whisper model '{self.model_size}' loaded on {self.device}")

    def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = "zh",
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """将语音转录为文本

        Args:
            audio_data: 音频数据（bytes）
            language: 语言代码
            task: 任务类型 ("transcribe" 或 "translate")

        Returns:
            转录结果
        """
        self.load_model()

        # 将bytes转换为numpy数组
        audio_np = self._bytes_to_audio(audio_data)

        # 执行转录
        result = self.model.transcribe(
            audio_np,
            language=language,
            task=task
        )

        return {
            "text": result["text"],
            "language": result.get("language", language),
            "segments": result.get("segments", []),
            "duration": result.get("duration", 0),
            "confidence": self._calculate_confidence(result)
        }

    def transcribe_streaming(self, audio_stream, language: Optional[str] = "zh"):
        """流式转录

        Args:
            audio_stream: 音频流
            language: 语言代码

        Yields:
            转录片段
        """
        self.load_model()

        # 处理流式音频
        buffer = []
        for chunk in audio_stream:
            buffer.append(chunk)

            # 每积累一定数据处理一次
            if len(buffer) >= 16000 * 5:  # 5秒音频
                audio_np = np.concatenate(buffer)
                result = self.model.transcribe(audio_np, language=language)
                yield result["text"]
                buffer = []

    def _bytes_to_audio(self, audio_bytes: bytes) -> np.ndarray:
        """将字节数据转换为音频数组"""
        # 使用numpy处理
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        return audio_float32

    def _calculate_confidence(self, result: Dict) -> float:
        """计算转录置信度"""
        if not result.get("segments"):
            return 0.0

        total_prob = 0.0
        count = 0
        for segment in result["segments"]:
            if "avg_logprob" in segment:
                # Whisper的log概率转换为置信度
                prob = np.exp(segment["avg_logprob"])
                total_prob += prob
                count += 1

        return total_prob / count if count > 0 else 0.0
```

#### 1.3 更新多模态处理器

修改：`src/core/multimodal/multimodal_processor.py`

```python
from .speech_processor import SpeechProcessor

class EnhancedMultimodalProcessor(MultimodalProcessor):
    """增强版多模态处理器"""

    def __init__(self):
        super().__init__()
        self.speech_processor = SpeechProcessor(model_size="base")
        self.supported_input_types = ["text", "image", "audio", "video"]
        self.supported_tasks = [
            "transcription",      # 新增
            "translation",        # 新增
            "command_recognition", # 新增
            "sentiment_analysis", # 新增
        ]

    def process_audio(self, audio_data: bytes, task: str) -> Dict[str, Any]:
        """处理音频输入"""
        if task == "transcription":
            return self.speech_processor.transcribe(audio_data, language="zh")
        elif task == "translation":
            return self.speech_processor.transcribe(audio_data, task="translate")
        elif task == "command_recognition":
            return self._recognize_commands(audio_data)
        else:
            raise ValueError(f"Unsupported audio task: {task}")

    def _recognize_commands(self, audio_data: bytes) -> Dict[str, Any]:
        """识别语音命令"""
        # 简单的命令识别逻辑
        transcription = self.speech_processor.transcribe(audio_data)

        commands = {
            "启动": "start",
            "停止": "stop",
            "搜索": "search",
            "分析": "analyze"
        }

        for keyword, command in commands.items():
            if keyword in transcription["text"]:
                return {
                    "command": command,
                    "confidence": transcription["confidence"],
                    "transcription": transcription["text"]
                }

        return {
            "command": "unknown",
            "confidence": 0.0,
            "transcription": transcription["text"]
        }
```

---

### 阶段 2：实时语音处理（15h）

#### 2.1 创建WebSocket语音端点

新建：`src/api/voice_api.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import APIRouter
import asyncio
import json

router = APIRouter()

class VoiceConnectionManager:
    """语音连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.speech_processor = SpeechProcessor()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def stream_transcribe(self, websocket: WebSocket):
        """流式转录处理"""
        try:
            while True:
                # 接收音频数据
                data = await websocket.receive_bytes()

                # 转录
                result = self.speech_processor.transcribe(data)

                # 发送结果
                await websocket.send_json({
                    "type": "transcription",
                    "data": result
                })

        except WebSocketDisconnect:
            self.disconnect(websocket)

voice_manager = VoiceConnectionManager()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket语音端点"""
    await voice_manager.connect(websocket)
    await voice_manager.stream_transcribe(websocket)
```

#### 2.2 添加音频预处理

新建：`src/core/multimodal/audio_preprocessor.py`

```python
import librosa
import numpy as np
from typing import Tuple

class AudioPreprocessor:
    """音频预处理器"""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def load_and_preprocess(
        self,
        audio_path: str = None,
        audio_bytes: bytes = None
    ) -> Tuple[np.ndarray, int]:
        """加载并预处理音频

        Args:
            audio_path: 音频文件路径
            audio_bytes: 音频字节数据

        Returns:
            (音频数组, 采样率)
        """
        if audio_path:
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
        else:
            audio, sr = librosa.load(
                io.BytesIO(audio_bytes),
                sr=self.sample_rate
            )

        # 降噪
        audio = self.denoise(audio)

        # 归一化
        audio = self.normalize(audio)

        return audio, sr

    def denoise(self, audio: np.ndarray) -> np.ndarray:
        """简单的降噪处理"""
        # 使用谱减法降噪
        # 简化版本
        return audio

    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """音频归一化"""
        max_val = np.abs(audio).max()
        if max_val > 0:
            audio = audio / max_val
        return audio
```

---

### 阶段 3：多模态融合（10h）

#### 3.1 实现跨模态注意力

新建：`src/core/multimodal/crossmodal_attention.py`

```python
import torch
import torch.nn as nn
from typing import Dict, List

class CrossModalAttention(nn.Module):
    """跨模态注意力机制"""

    def __init__(self, hidden_dim: int = 512):
        super().__init__()
        self.hidden_dim = hidden_dim

        # 视觉-文本注意力
        self.vision_text_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=8,
            dropout=0.1
        )

        # 语音-文本注意力
        self.speech_text_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=8,
            dropout=0.1
        )

        # 融合层
        self.fusion_layer = nn.Linear(hidden_dim * 3, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(
        self,
        vision_features: torch.Tensor,
        text_features: torch.Tensor,
        speech_features: torch.Tensor
    ) -> torch.Tensor:
        """跨模态特征融合

        Args:
            vision_features: 视觉特征 [seq_len, batch, hidden]
            text_features: 文本特征 [seq_len, batch, hidden]
            speech_features: 语音特征 [seq_len, batch, hidden]

        Returns:
            融合后的特征
        """
        # 视觉-文本注意力
        vision_text_out, _ = self.vision_text_attention(
            vision_features,
            text_features,
            text_features
        )

        # 语音-文本注意力
        speech_text_out, _ = self.speech_text_attention(
            speech_features,
            text_features,
            text_features
        )

        # 拼接所有模态
        combined = torch.cat([
            vision_text_out,
            speech_text_out,
            text_features
        ], dim=-1)

        # 融合
        fused = self.fusion_layer(combined)
        fused = self.norm(fused)

        return fused
```

#### 3.2 更新MCP Server添加多模态工具

修改：`src/mcp_server.py`

```python
# 添加新的MCP工具
def _register_tools(self):
    # ... 现有工具 ...

    # 新增多模态工具
    self.tools["transcribe_audio"] = ToolDefinition(
        name="transcribe_audio",
        description="使用Whisper模型将音频转录为文本",
        input_schema={
            "type": "object",
            "properties": {
                "audio_data": {"type": "string"},  # Base64编码
                "language": {"type": "string", "default": "zh"},
                "task": {"type": "string", "enum": ["transcribe", "translate"]}
            },
            "required": ["audio_data"]
        }
    )

    self.tools["analyze_multimodal"] = ToolDefinition(
        name="analyze_multimodal",
        description="多模态内容分析（图像+文本+语音）",
        input_schema={
            "type": "object",
            "properties": {
                "image_data": {"type": "string"},
                "text": {"type": "string"},
                "audio_data": {"type": "string"},
                "task": {"type": "string"}
            }
        }
    )
```

---

## 📁 文件清单

### 需要创建的文件

| 文件路径 | 说明 | 优先级 |
|---------|------|--------|
| `src/core/multimodal/speech_processor.py` | Whisper语音处理器 | P0 |
| `src/core/multimodal/audio_preprocessor.py` | 音频预处理器 | P1 |
| `src/core/multimodal/crossmodal_attention.py` | 跨模态注意力 | P1 |
| `src/api/voice_api.py` | WebSocket语音API | P0 |
| `tests/test_speech_processor.py` | 语音处理测试 | P1 |

### 需要修改的文件

| 文件路径 | 修改内容 | 优先级 |
|---------|---------|--------|
| `requirements.txt` | 添加语音依赖 | P0 |
| `src/core/multimodal/multimodal_processor.py` | 集成语音处理 | P0 |
| `src/mcp_server.py` | 添加多模态工具 | P0 |

---

## 🔧 依赖项

```txt
# 核心依赖
openai-whisper>=20231117
torchaudio>=2.0.0
librosa>=0.10.0
soundfile>=0.12.0

# 模型优化
torch>=2.0.0
torchvision>=0.15.0

# 实时处理
websockets>=11.0.0
numpy>=1.24.0
scipy>=1.10.0
```

---

## ✅ 验收标准

1. ✅ Whisper模型成功加载并转录音频
2. ✅ 转录准确率 > 85%（中文普通话）
3. ✅ 实时语音流处理延迟 < 500ms
4. ✅ 语音命令识别准确率 > 90%
5. ✅ 多模态融合正常工作
6. ✅ WebSocket端点可正常连接

---

## 📈 性能指标

- 语音识别延迟（Whisper base）：< 2秒
- 实时流处理延迟：< 500ms
- 内存占用：< 2GB（Whisper base）
- GPU占用：< 4GB（Whisper base）
- 准确率（中文）：> 85%

---

## ⚠️ 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 模型加载慢 | 中 | 异步预加载到内存 |
| GPU内存不足 | 高 | 使用量化模型 |
| 识别准确率低 | 中 | 使用large模型 |
| 音频格式不支持 | 低 | 添加格式转换 |

---

## 🎯 下一步行动

1. ✅ 添加语音处理依赖到requirements.txt
2. ✅ 创建SpeechProcessor类
3. ✅ 实现AudioPreprocessor
4. ✅ 添加WebSocket语音端点
5. ✅ 实现跨模态注意力
6. ✅ 集成到MCP Server
7. ✅ 添加测试
8. ✅ 性能优化

是否开始执行？
