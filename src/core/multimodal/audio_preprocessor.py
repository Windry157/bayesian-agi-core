#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频预处理器
负责音频数据的加载、转换、增强和标准化

功能特性：
- 多格式音频加载（MP3, WAV, FLAC, OGG等）
- 重采样和声道转换
- 音频归一化
- 降噪处理
- 音频增强
- 特征提取
"""

import io
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path
import logging

import numpy as np

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """音频预处理器

    负责音频数据的加载、转换和预处理。

    Attributes:
        sample_rate: 目标采样率
        mono: 是否转换为单声道
        normalize: 是否归一化音频
        noise_reduction: 是否进行降噪
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        mono: bool = True,
        normalize: bool = True,
        noise_reduction: bool = False
    ):
        """初始化音频预处理器

        Args:
            sample_rate: 目标采样率，默认为16000Hz
            mono: 是否转换为单声道
            normalize: 是否对音频进行归一化
            noise_reduction: 是否进行降噪处理
        """
        self.sample_rate = sample_rate
        self.mono = mono
        self.normalize = normalize
        self.noise_reduction = noise_reduction

        # 支持的音频格式
        self.supported_formats = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma"]

        logger.info(
            f"AudioPreprocessor initialized: sample_rate={sample_rate}, "
            f"mono={mono}, normalize={normalize}, noise_reduction={noise_reduction}"
        )

    def load_audio(
        self,
        audio_path: Optional[str] = None,
        audio_bytes: Optional[bytes] = None
    ) -> Tuple[np.ndarray, int]:
        """加载音频文件或数据

        Args:
            audio_path: 音频文件路径
            audio_bytes: 音频字节数据

        Returns:
            (音频数组, 采样率) 元组

        Raises:
            ValueError: 当无法加载音频时抛出
        """
        if audio_path:
            return self._load_from_file(audio_path)
        elif audio_bytes:
            return self._load_from_bytes(audio_bytes)
        else:
            raise ValueError("必须提供audio_path或audio_bytes参数")

    def _load_from_file(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """从文件加载音频

        Args:
            audio_path: 音频文件路径

        Returns:
            (音频数组, 采样率) 元组
        """
        try:
            import librosa

            # 使用librosa加载
            audio, sr = librosa.load(
                audio_path,
                sr=self.sample_rate,
                mono=self.mono
            )

            logger.info(f"Loaded audio from {audio_path}: {len(audio)} samples, {sr}Hz")

            return audio, sr

        except ImportError:
            logger.warning("librosa not available, using scipy")
            return self._load_with_scipy(audio_path)

        except Exception as e:
            logger.error(f"Failed to load audio from {audio_path}: {e}")
            raise ValueError(f"Cannot load audio file: {e}")

    def _load_from_bytes(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """从字节数据加载音频

        Args:
            audio_bytes: 音频字节数据

        Returns:
            (音频数组, 采样率) 元组
        """
        try:
            import librosa

            # 从字节加载
            audio, sr = librosa.load(
                io.BytesIO(audio_bytes),
                sr=self.sample_rate,
                mono=self.mono
            )

            logger.info(f"Loaded audio from bytes: {len(audio)} samples, {sr}Hz")

            return audio, sr

        except ImportError:
            logger.warning("librosa not available")
            raise ValueError("librosa required for loading audio from bytes")

        except Exception as e:
            logger.error(f"Failed to load audio from bytes: {e}")
            raise ValueError(f"Cannot parse audio data: {e}")

    def _load_with_scipy(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """使用scipy加载音频（备用方法）

        Args:
            audio_path: 音频文件路径

        Returns:
            (音频数组, 采样率) 元组
        """
        from scipy.io import wavfile
        from scipy import signal

        try:
            # 读取WAV文件
            sr, audio = wavfile.read(audio_path)

            # 转换为float32
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0

            # 重采样
            if sr != self.sample_rate:
                num_samples = int(len(audio) * self.sample_rate / sr)
                audio = signal.resample(audio, num_samples)
                sr = self.sample_rate

            # 转换为单声道
            if len(audio.shape) > 1 and audio.shape[1] > 1:
                audio = np.mean(audio, axis=1)

            return audio, sr

        except Exception as e:
            logger.error(f"Failed to load with scipy: {e}")
            raise ValueError(f"Cannot load audio file: {e}")

    def preprocess(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """预处理音频

        Args:
            audio: 音频数组
            sr: 采样率

        Returns:
            处理后的音频数组
        """
        # 降噪
        if self.noise_reduction:
            audio = self.denoise(audio)

        # 归一化
        if self.normalize:
            audio = self.normalize_audio(audio)

        # 确保是float32
        audio = audio.astype(np.float32)

        return audio

    def denoise(self, audio: np.ndarray) -> np.ndarray:
        """简单降噪处理

        使用谱减法的简化版本。

        Args:
            audio: 音频数组

        Returns:
            降噪后的音频数组
        """
        try:
            # 使用简单的移动平均进行降噪
            window_size = 5
            kernel = np.ones(window_size) / window_size

            # 计算噪声估计（取前100ms作为噪声参考）
            noise_samples = int(0.1 * self.sample_rate)
            noise_profile = np.mean(audio[:noise_samples])

            # 减去噪声估计
            audio = audio - noise_profile * 0.3

            # 软阈值去噪
            threshold = 0.02
            audio = np.sign(audio) * np.maximum(np.abs(audio) - threshold, 0)

            return audio

        except Exception as e:
            logger.warning(f"Denoising failed: {e}, returning original audio")
            return audio

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """音频归一化

        将音频归一化到[-1, 1]范围。

        Args:
            audio: 音频数组

        Returns:
            归一化后的音频数组
        """
        max_val = np.abs(audio).max()

        if max_val > 0:
            audio = audio / max_val

        return audio

    def remove_silence(
        self,
        audio: np.ndarray,
        threshold: float = 0.01,
        frame_length: int = 2048,
        hop_length: int = 512
    ) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
        """移除静音部分

        Args:
            audio: 音频数组
            threshold: 能量阈值
            frame_length: 帧长度
            hop_length: 跳跃长度

        Returns:
            (处理后的音频, 保留的片段列表) 元组
        """
        try:
            import librosa

            # 计算RMS能量
            rms = librosa.feature.rms(
                y=audio,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]

            # 找到非静音的片段
            mask = rms > threshold

            # 找到连续的True片段
            片段列表 = []
            start = None

            for i, is_speech in enumerate(mask):
                if is_speech and start is None:
                    start = i * hop_length
                elif not is_speech and start is not None:
                    end = i * hop_length
                    片段列表.append((start, end))
                    start = None

            if start is not None:
                片段列表.append((start, len(audio)))

            # 合并相邻片段
            if 片段列表:
                audio = np.concatenate([
                    audio[start:end] for start, end in 片段列表
                ])

            return audio, 片段列表

        except Exception as e:
            logger.warning(f"Silence removal failed: {e}")
            return audio, [(0, len(audio))]

    def extract_features(
        self,
        audio: np.ndarray,
        sr: int
    ) -> Dict[str, Any]:
        """提取音频特征

        Args:
            audio: 音频数组
            sr: 采样率

        Returns:
            特征字典
        """
        try:
            import librosa

            features = {}

            # MFCC特征
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            features["mfcc_mean"] = np.mean(mfcc, axis=1).tolist()
            features["mfcc_std"] = np.std(mfcc, axis=1).tolist()

            # 色度特征
            chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
            features["chroma_mean"] = np.mean(chroma, axis=1).tolist()

            # 梅尔频谱
            mel_spec = librosa.feature.melspectrogram(y=audio, sr=sr)
            features["mel_mean"] = np.mean(mel_spec, axis=1).tolist()

            # 过零率
            zcr = librosa.feature.zero_crossing_rate(audio)
            features["zcr_mean"] = float(np.mean(zcr))

            # RMS能量
            rms = librosa.feature.rms(y=audio)
            features["rms_mean"] = float(np.mean(rms))

            # 语速估计
            onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
            tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            features["tempo"] = float(tempo)

            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {"error": str(e)}

    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """获取音频文件信息

        Args:
            audio_path: 音频文件路径

        Returns:
            音频信息字典
        """
        try:
            import librosa
            import soundfile as sf

            # 获取基本信息
            info = sf.info(audio_path)

            # 加载音频获取时长
            duration = librosa.get_duration(path=audio_path)

            return {
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "duration": duration,
                "format": info.format,
                "subtype": info.subtype,
                "sections": info.sections if hasattr(info, 'sections') else 0
            }

        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {"error": str(e)}

    def convert_format(
        self,
        input_path: str,
        output_path: str,
        output_format: str = "wav"
    ) -> bool:
        """转换音频格式

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            output_format: 输出格式（wav, mp3, flac等）

        Returns:
            是否转换成功
        """
        try:
            import soundfile as sf

            # 加载音频
            audio, sr = self.load_audio(input_path)

            # 预处理
            audio = self.preprocess(audio, sr)

            # 保存
            sf.write(output_path, audio, sr, format=output_format.upper())

            logger.info(f"Converted {input_path} to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            return False

    def split_into_chunks(
        self,
        audio: np.ndarray,
        chunk_duration: float = 30.0,
        overlap: float = 0.0
    ) -> List[np.ndarray]:
        """将音频分割成块

        Args:
            audio: 音频数组
            chunk_duration: 每块的时长（秒）
            overlap: 块之间的重叠（秒）

        Returns:
            音频块列表
        """
        chunk_samples = int(chunk_duration * self.sample_rate)
        overlap_samples = int(overlap * self.sample_rate)
        step = chunk_samples - overlap_samples

        chunks = []

        for start in range(0, len(audio), step):
            end = start + chunk_samples

            if end > len(audio):
                # 最后一块如果太短就合并到上一块
                if chunks and (len(audio) - start) < chunk_samples * 0.5:
                    chunks[-1] = np.concatenate([chunks[-1], audio[start:]])
                else:
                    chunks.append(audio[start:])
            else:
                chunks.append(audio[start:end])

        logger.info(f"Split audio into {len(chunks)} chunks")
        return chunks

    def validate_audio(
        self,
        audio: np.ndarray,
        sr: int,
        min_duration: float = 0.1,
        max_duration: float = 3600.0
    ) -> Tuple[bool, str]:
        """验证音频是否有效

        Args:
            audio: 音频数组
            sr: 采样率
            min_duration: 最小时长（秒）
            max_duration: 最大时长（秒）

        Returns:
            (是否有效, 错误消息) 元组
        """
        # 检查是否为空
        if len(audio) == 0:
            return False, "Audio is empty"

        # 检查时长
        duration = len(audio) / sr

        if duration < min_duration:
            return False, f"Audio too short: {duration:.2f}s < {min_duration}s"

        if duration > max_duration:
            return False, f"Audio too long: {duration:.2f}s > {max_duration}s"

        # 检查是否有足够的非静音
        if np.abs(audio).max() < 0.001:
            return False, "Audio is silent or nearly silent"

        # 检查是否全为NaN或Inf
        if np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
            return False, "Audio contains NaN or Inf values"

        return True, ""

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"AudioPreprocessor("
            f"sample_rate={self.sample_rate}, "
            f"mono={self.mono}, "
            f"normalize={self.normalize}, "
            f"noise_reduction={self.noise_reduction})"
        )
