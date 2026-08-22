#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音处理模块测试
测试 SpeechProcessor, AudioPreprocessor 和相关功能
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class TestSpeechProcessor:
    """SpeechProcessor 测试"""

    @pytest.fixture
    def processor(self):
        """创建 SpeechProcessor 实例"""
        if not WHISPER_AVAILABLE:
            pytest.skip("Whisper not available")

        from src.core.multimodal.speech_processor import SpeechProcessor
        return SpeechProcessor(model_size="tiny")

    def test_initialization(self, processor):
        """测试初始化"""
        assert processor.model_size == "tiny"
        assert processor.sample_rate == 16000
        assert processor.device in ["cuda", "cpu"]

    def test_get_model_info(self, processor):
        """测试获取模型信息"""
        info = processor.get_model_info()

        assert "model_size" in info
        assert "device" in info
        assert "sample_rate" in info
        assert "supported_languages" in info

    def test_get_supported_languages(self, processor):
        """测试获取支持的语言"""
        languages = processor.get_supported_languages()

        assert "zh" in languages
        assert "en" in languages
        assert languages["zh"] == "中文"

    def test_load_model(self, processor):
        """测试模型加载"""
        if not WHISPER_AVAILABLE:
            pytest.skip("Whisper not available")

        success = processor.load_model()
        assert success is True
        assert processor.model is not None

    def test_bytes_to_audio_conversion(self, processor):
        """测试字节到音频转换"""
        # 创建简单的音频数据（16位整数）
        sample_rate = 16000
        duration = 0.1  # 100ms
        samples = int(sample_rate * duration)

        # 生成正弦波
        frequency = 440  # A4
        t = np.linspace(0, duration, samples, dtype=np.float32)
        audio = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

        # 转换为字节
        audio_bytes = audio.tobytes()

        # 转换回音频
        audio_np = processor._bytes_to_audio(audio_bytes)

        assert isinstance(audio_np, np.ndarray)
        assert audio_np.dtype == np.float32
        assert len(audio_np) == samples

    def test_calculate_confidence(self, processor):
        """测试置信度计算"""
        # 模拟 Whisper 结果
        result = {
            "segments": [
                {"avg_logprob": -0.1, "text": "Hello"},
                {"avg_logprob": -0.2, "text": "World"}
            ]
        }

        confidence = processor._calculate_confidence(result)

        assert 0 <= confidence <= 1
        assert confidence > 0

    def test_calculate_confidence_empty_segments(self, processor):
        """测试空片段的置信度"""
        result = {"segments": []}

        confidence = processor._calculate_confidence(result)

        assert confidence == 0.0


class TestAudioPreprocessor:
    """AudioPreprocessor 测试"""

    @pytest.fixture
    def preprocessor(self):
        """创建 AudioPreprocessor 实例"""
        if not LIBROSA_AVAILABLE:
            pytest.skip("Librosa not available")

        from src.core.multimodal.audio_preprocessor import AudioPreprocessor
        return AudioPreprocessor(sample_rate=16000)

    def test_initialization(self, preprocessor):
        """测试初始化"""
        assert preprocessor.sample_rate == 16000
        assert preprocessor.mono is True
        assert preprocessor.normalize is True

    def test_normalize_audio(self, preprocessor):
        """测试音频归一化"""
        # 创建非归一化音频
        audio = np.array([0.5, 1.0, -0.5, -1.0, 0.0], dtype=np.float32)

        normalized = preprocessor.normalize_audio(audio)

        assert np.abs(normalized).max() <= 1.0
        assert np.abs(normalized).min() >= -1.0

    def test_denoise(self, preprocessor):
        """测试降噪"""
        # 创建带噪声的音频
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        audio[:1600] += 0.5  # 添加静音前的信号

        denoised = preprocessor.denoise(audio)

        assert denoised.shape == audio.shape
        assert denoised.dtype == np.float32

    def test_validate_audio(self, preprocessor):
        """测试音频验证"""
        # 有效音频
        audio = np.random.randn(16000).astype(np.float32) * 0.5
        valid, msg = preprocessor.validate_audio(audio, 16000)

        assert valid is True
        assert msg == ""

    def test_validate_audio_too_short(self, preprocessor):
        """测试过短音频验证"""
        audio = np.random.randn(100).astype(np.float32) * 0.5

        valid, msg = preprocessor.validate_audio(
            audio, 16000,
            min_duration=1.0
        )

        assert valid is False
        assert "short" in msg.lower()

    def test_validate_audio_empty(self, preprocessor):
        """测试空音频验证"""
        audio = np.array([], dtype=np.float32)

        valid, msg = preprocessor.validate_audio(audio, 16000)

        assert valid is False
        assert "empty" in msg.lower()

    def test_validate_audio_silent(self, preprocessor):
        """测试静音音频验证"""
        audio = np.zeros(16000, dtype=np.float32)

        valid, msg = preprocessor.validate_audio(audio, 16000)

        assert valid is False
        assert "silent" in msg.lower()

    def test_extract_features(self, preprocessor):
        """测试特征提取"""
        if not LIBROSA_AVAILABLE:
            pytest.skip("Librosa not available")

        # 创建测试音频
        audio = np.random.randn(16000).astype(np.float32) * 0.5

        features = preprocessor.extract_features(audio, 16000)

        assert "mfcc_mean" in features
        assert "mfcc_std" in features
        assert "chroma_mean" in features
        assert "zcr_mean" in features
        assert "rms_mean" in features


class TestCrossModalAttention:
    """跨模态注意力测试"""

    def test_multimodal_fusion_initialization(self):
        """测试多模态融合初始化"""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            pytest.skip("PyTorch/CUDA not available, skipping tests")

        from src.core.multimodal.crossmodal_attention import MultimodalFusion

        fusion = MultimodalFusion(
            vision_dim=768,
            text_dim=768,
            speech_dim=512,
            output_dim=512,
            fusion_type="concat"
        )

        assert fusion.vision_dim == 768
        assert fusion.output_dim == 512

    def test_multimodal_encoder_initialization(self):
        """测试多模态编码器初始化"""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            pytest.skip("PyTorch/CUDA not available, skipping tests")

        from src.core.multimodal.crossmodal_attention import MultimodalEncoder

        encoder = MultimodalEncoder(
            vision_dim=768,
            text_dim=768,
            speech_dim=512,
            hidden_dim=512
        )

        assert encoder is not None


class TestVoiceAPI:
    """语音API测试"""

    def test_voice_api_import(self):
        """测试语音API导入"""
        try:
            from src.api.voice_api import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import voice_api: {e}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
