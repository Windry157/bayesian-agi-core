#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音处理模块
集成Whisper模型进行语音识别和处理

功能特性：
- 语音转文本（ASR）
- 语音翻译
- 语音命令识别
- 流式语音处理
- 多语言支持
"""

import io
import asyncio
import tempfile
from typing import Optional, Dict, Any, List, Generator, Tuple
from pathlib import Path
import logging

import numpy as np
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class SpeechProcessor:
    """语音处理器

    使用Whisper模型进行语音识别和处理。

    Attributes:
        model_size: Whisper模型大小，可选 "tiny", "base", "small", "medium", "large"
        model: 已加载的Whisper模型
        device: 计算设备 ("cuda" 或 "cpu")
        sample_rate: 音频采样率
        supported_languages: 支持的语言列表
    """

    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        sample_rate: int = 16000
    ):
        """初始化语音处理器

        Args:
            model_size: Whisper模型大小，默认为"base"
            device: 计算设备，如果为None则自动选择（优先GPU）
            sample_rate: 音频采样率，默认为16000Hz
        """
        self.model_size = model_size
        self.sample_rate = sample_rate
        self.model = None
        self.device = device or (
            "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        )

        # 支持的语言
        self.supported_languages = {
            "zh": "中文",
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语",
            "ar": "阿拉伯语",
            "auto": "自动检测"
        }

        logger.info(
            f"SpeechProcessor initialized with model={model_size}, "
            f"device={self.device}, sample_rate={sample_rate}"
        )

    def load_model(self, force: bool = False) -> bool:
        """加载Whisper模型

        Args:
            force: 是否强制重新加载模型

        Returns:
            是否加载成功
        """
        if self.model is not None and not force:
            return True

        try:
            # 动态导入whisper
            import whisper

            logger.info(f"Loading Whisper model '{self.model_size}' on {self.device}...")

            # 加载模型
            self.model = whisper.load_model(self.model_size, device=self.device)

            logger.info(f"Whisper model '{self.model_size}' loaded successfully")

            return True

        except ImportError:
            logger.error("Whisper not installed. Run: pip install openai-whisper")
            return False

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return False

    def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = "auto",
        task: str = "transcribe",
        verbose: bool = False,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """将语音转录为文本

        Args:
            audio_data: 音频数据（bytes）
            language: 语言代码，默认"auto"自动检测
            task: 任务类型，"transcribe"（转录）或"translate"（翻译为英语）
            verbose: 是否输出详细信息
            temperature: 采样温度，控制随机性

        Returns:
            转录结果字典，包含：
            - text: 转录文本
            - language: 检测到的语言
            - segments: 片段列表
            - duration: 音频时长（秒）
            - confidence: 平均置信度
        """
        # 确保模型已加载
        if not self.load_model():
            return {
                "error": "Failed to load Whisper model",
                "text": "",
                "language": "unknown",
                "confidence": 0.0
            }

        try:
            # 将bytes转换为音频数组
            audio_np = self._bytes_to_audio(audio_data)

            # 执行转录
            options = {
                "language": language if language != "auto" else None,
                "task": task,
                "verbose": verbose,
                "temperature": temperature
            }

            # 移除None值
            options = {k: v for k, v in options.items() if v is not None}

            result = self.model.transcribe(audio_np, **options)

            # 计算置信度
            confidence = self._calculate_confidence(result)

            return {
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "segments": result.get("segments", []),
                "duration": result.get("duration", 0),
                "confidence": confidence,
                "task": task
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "error": str(e),
                "text": "",
                "language": "unknown",
                "confidence": 0.0
            }

    def transcribe_from_file(
        self,
        audio_path: str,
        language: Optional[str] = "auto",
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """从音频文件转录

        Args:
            audio_path: 音频文件路径
            language: 语言代码
            task: 任务类型

        Returns:
            转录结果
        """
        try:
            # 读取文件
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            return self.transcribe(audio_data, language, task)

        except Exception as e:
            logger.error(f"Failed to transcribe from file {audio_path}: {e}")
            return {
                "error": str(e),
                "text": "",
                "language": "unknown",
                "confidence": 0.0
            }

    def transcribe_streaming(
        self,
        audio_chunks: List[bytes],
        language: Optional[str] = "auto"
    ) -> Generator[str, None, None]:
        """流式转录

        Args:
            audio_chunks: 音频数据块列表
            language: 语言代码

        Yields:
            转录文本片段
        """
        if not self.load_model():
            return

        # 合并所有音频块
        audio_np = self._bytes_to_audio(b"".join(audio_chunks))

        try:
            # 执行转录
            result = self.model.transcribe(
                audio_np,
                language=language if language != "auto" else None
            )

            # 逐段yield
            for segment in result.get("segments", []):
                yield segment["text"]

        except Exception as e:
            logger.error(f"Streaming transcription failed: {e}")

    def batch_transcribe(
        self,
        audio_files: List[str],
        language: Optional[str] = "auto",
        task: str = "transcribe"
    ) -> List[Dict[str, Any]]:
        """批量转录多个音频文件

        Args:
            audio_files: 音频文件路径列表
            language: 语言代码
            task: 任务类型

        Returns:
            转录结果列表
        """
        results = []

        for audio_path in audio_files:
            logger.info(f"Transcribing: {audio_path}")

            result = self.transcribe_from_file(audio_path, language, task)
            result["file"] = audio_path

            results.append(result)

        return results

    def recognize_commands(
        self,
        audio_data: bytes,
        commands: Dict[str, str],
        language: str = "zh"
    ) -> Dict[str, Any]:
        """识别语音命令

        Args:
            audio_data: 音频数据
            commands: 命令字典 {关键词: 命令ID}
            language: 语言代码

        Returns:
            识别结果，包含：
            - command: 识别到的命令ID，未识别为"unknown"
            - confidence: 置信度
            - transcription: 转录文本
            - matched_keyword: 匹配的关键词
        """
        # 先转录音频
        result = self.transcribe(audio_data, language=language)

        if "error" in result:
            return {
                "command": "error",
                "confidence": 0.0,
                "transcription": "",
                "error": result["error"]
            }

        transcription = result["text"]

        # 匹配命令
        best_match = None
        best_confidence = 0.0

        for keyword, command_id in commands.items():
            if keyword in transcription:
                # 计算匹配的置信度
                confidence = len(keyword) / len(transcription) * result["confidence"]

                if confidence > best_confidence:
                    best_match = {
                        "keyword": keyword,
                        "command": command_id,
                        "confidence": confidence
                    }
                    best_confidence = confidence

        if best_match:
            return {
                "command": best_match["command"],
                "confidence": best_match["confidence"],
                "transcription": transcription,
                "matched_keyword": best_match["keyword"]
            }
        else:
            return {
                "command": "unknown",
                "confidence": result["confidence"],
                "transcription": transcription,
                "matched_keyword": None
            }

    def detect_language(self, audio_data: bytes) -> Dict[str, Any]:
        """检测音频语言

        Args:
            audio_data: 音频数据

        Returns:
            检测结果，包含：
            - language: 检测到的语言代码
            - language_name: 语言名称
            - confidence: 置信度
        """
        if not self.load_model():
            return {
                "language": "unknown",
                "language_name": "未知",
                "confidence": 0.0
            }

        try:
            audio_np = self._bytes_to_audio(audio_data)

            # 加载音频和模型
            import whisper

            # 获取模型
            if self.model is None:
                self.load_model()

            # 音频特征提取
            mel = whisper.log_mel_spectrogram(audio_np, n_mels=80).to(self.model.device)

            # 语言检测
            _, probs = self.model.detect_language(mel)
            detected_language = max(probs, key=probs.get)
            confidence = probs[detected_language]

            return {
                "language": detected_language,
                "language_name": self.supported_languages.get(
                    detected_language,
                    detected_language
                ),
                "confidence": confidence,
                "all_probabilities": dict(probs)
            }

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {
                "language": "unknown",
                "language_name": "未知",
                "confidence": 0.0,
                "error": str(e)
            }

    def _bytes_to_audio(self, audio_bytes: bytes) -> np.ndarray:
        """将字节数据转换为音频数组

        Args:
            audio_bytes: 原始音频字节数据

        Returns:
            归一化的音频数组（float32）
        """
        try:
            # 尝试将字节解析为16位整数音频
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

            # 转换为float32并归一化到[-1, 1]
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            return audio_float32

        except Exception as e:
            logger.error(f"Failed to convert bytes to audio: {e}")

            # 如果解析失败，尝试使用librosa
            try:
                import librosa

                # 从字节读取音频
                audio_np, _ = librosa.load(
                    io.BytesIO(audio_bytes),
                    sr=self.sample_rate,
                    mono=True
                )

                return audio_np

            except Exception as e2:
                logger.error(f"Librosa fallback also failed: {e2}")
                raise ValueError(f"Cannot parse audio data: {e}")

    def _calculate_confidence(self, result: Dict) -> float:
        """计算转录置信度

        Args:
            result: Whisper转录结果

        Returns:
            平均置信度
        """
        if not result.get("segments"):
            return 0.0

        total_prob = 0.0
        count = 0

        for segment in result["segments"]:
            if "avg_logprob" in segment:
                # Whisper的log概率转换为置信度
                # log概率范围通常是[-1, 0]，转换为[0, 1]
                log_prob = segment["avg_logprob"]
                prob = (log_prob + 1.0)  # 转换到[0, 1]

                total_prob += max(0.0, min(1.0, prob))
                count += 1

        return total_prob / count if count > 0 else 0.0

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表

        Returns:
            支持的语言字典 {代码: 名称}
        """
        return self.supported_languages.copy()

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "model_size": self.model_size,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "model_loaded": self.model is not None,
            "supported_languages": list(self.supported_languages.keys())
        }

    def __del__(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None

            # 清理GPU缓存
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
