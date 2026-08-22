#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨模态注意力模块
实现不同模态（文本、图像、语音）之间的特征融合

功能特性：
- 多模态特征提取
- 跨模态注意力机制
- 特征对齐和融合
- 多模态推理
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CrossModalAttention(nn.Module):
    """跨模态注意力机制

    实现不同模态之间的注意力交互。

    Attributes:
        hidden_dim: 隐藏层维度
        num_heads: 注意力头数
        dropout: Dropout概率
    """

    def __init__(
        self,
        hidden_dim: int = 512,
        num_heads: int = 8,
        dropout: float = 0.1
    ):
        """初始化跨模态注意力

        Args:
            hidden_dim: 隐藏层维度
            num_heads: 注意力头数
            dropout: Dropout概率
        """
        super().__init__()

        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        assert hidden_dim % num_heads == 0, "hidden_dim必须能被num_heads整除"

        # 视觉-文本注意力
        self.vision_text_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )

        # 语音-文本注意力
        self.speech_text_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )

        # 视觉-语音注意力
        self.vision_speech_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )

        # 融合层
        self.fusion_layer = nn.Linear(hidden_dim * 3, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)

        self.dropout = nn.Dropout(dropout)

        logger.info(
            f"CrossModalAttention initialized: "
            f"hidden_dim={hidden_dim}, num_heads={num_heads}"
        )

    def forward(
        self,
        vision_features: torch.Tensor,
        text_features: torch.Tensor,
        speech_features: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """跨模态特征融合

        Args:
            vision_features: 视觉特征 [batch, seq_len, hidden]
            text_features: 文本特征 [batch, seq_len, hidden]
            speech_features: 语音特征 [batch, seq_len, hidden]（可选）

        Returns:
            融合后的特征 [batch, seq_len, hidden]
        """
        # 视觉-文本注意力
        vision_text_out, _ = self.vision_text_attention(
            vision_features,
            text_features,
            text_features
        )
        vision_text_out = self.dropout(vision_text_out)

        # 语音-文本注意力（如果有语音特征）
        if speech_features is not None:
            speech_text_out, _ = self.speech_text_attention(
                speech_features,
                text_features,
                text_features
            )
            speech_text_out = self.dropout(speech_text_out)

            # 视觉-语音注意力
            vision_speech_out, _ = self.vision_speech_attention(
                vision_features,
                speech_features,
                speech_features
            )
            vision_speech_out = self.dropout(vision_speech_out)

            # 拼接所有模态
            combined = torch.cat([
                vision_text_out,
                speech_text_out,
                vision_speech_out,
                text_features
            ], dim=-1)
        else:
            # 只拼接视觉和文本
            combined = torch.cat([
                vision_text_out,
                text_features
            ], dim=-1)

        # 融合
        fused = self.fusion_layer(combined)
        fused = self.norm(fused)

        return fused


class MultimodalFusion(nn.Module):
    """多模态融合器

    将多个模态的特征融合为一个统一的表示。
    """

    def __init__(
        self,
        vision_dim: int = 768,
        text_dim: int = 768,
        speech_dim: int = 512,
        output_dim: int = 512,
        fusion_type: str = "concat"
    ):
        """初始化多模态融合器

        Args:
            vision_dim: 视觉特征维度
            text_dim: 文本特征维度
            speech_dim: 语音特征维度
            output_dim: 输出特征维度
            fusion_type: 融合类型 ("concat", "add", "average")
        """
        super().__init__()

        self.vision_dim = vision_dim
        self.text_dim = text_dim
        self.speech_dim = speech_dim
        self.output_dim = output_dim
        self.fusion_type = fusion_type

        # 投影层
        self.vision_proj = nn.Linear(vision_dim, output_dim)
        self.text_proj = nn.Linear(text_dim, output_dim)
        self.speech_proj = nn.Linear(speech_dim, output_dim)

        # 融合策略
        if fusion_type == "concat":
            total_dim = vision_dim + text_dim + speech_dim
            self.fusion = nn.Sequential(
                nn.Linear(total_dim, output_dim * 2),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(output_dim * 2, output_dim)
            )
        elif fusion_type == "cross_attention":
            self.cross_attention = CrossModalAttention(
                hidden_dim=output_dim,
                num_heads=8
            )
            self.fusion = nn.Identity()
        else:
            self.fusion = nn.Identity()

        self.norm = nn.LayerNorm(output_dim)

        logger.info(
            f"MultimodalFusion initialized: fusion_type={fusion_type}"
        )

    def forward(
        self,
        vision_features: torch.Tensor,
        text_features: torch.Tensor,
        speech_features: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """多模态融合

        Args:
            vision_features: 视觉特征
            text_features: 文本特征
            speech_features: 语音特征（可选）

        Returns:
            融合后的特征
        """
        # 投影到统一维度
        vision_proj = self.vision_proj(vision_features)
        text_proj = self.text_proj(text_features)

        if speech_features is not None:
            speech_proj = self.speech_proj(speech_features)

        # 根据融合策略进行融合
        if self.fusion_type == "concat":
            if speech_features is not None:
                combined = torch.cat([vision_proj, text_proj, speech_proj], dim=-1)
            else:
                combined = torch.cat([vision_proj, text_proj], dim=-1)

            fused = self.fusion(combined)

        elif self.fusion_type == "add":
            fused = vision_proj + text_proj
            if speech_features is not None:
                fused = fused + speech_proj

        elif self.fusion_type == "average":
            fused = (vision_proj + text_proj) / 2
            if speech_features is not None:
                fused = (fused + speech_proj) / 2

        elif self.fusion_type == "cross_attention":
            if speech_features is not None:
                fused = self.cross_attention(vision_proj, text_proj, speech_proj)
            else:
                fused = self.cross_attention(vision_proj, text_proj, None)

        else:
            raise ValueError(f"Unknown fusion type: {self.fusion_type}")

        fused = self.norm(fused)

        return fused


class MultimodalEncoder(nn.Module):
    """多模态编码器

    编码多种模态的输入。
    """

    def __init__(
        self,
        vision_dim: int = 768,
        text_dim: int = 768,
        speech_dim: int = 512,
        hidden_dim: int = 512
    ):
        """初始化多模态编码器"""
        super().__init__()

        self.vision_encoder = nn.Sequential(
            nn.Linear(vision_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.text_encoder = nn.Sequential(
            nn.Linear(text_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.speech_encoder = nn.Sequential(
            nn.Linear(speech_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.norm = nn.LayerNorm(hidden_dim)

    def encode_vision(self, x: torch.Tensor) -> torch.Tensor:
        """编码视觉特征"""
        return self.norm(self.vision_encoder(x))

    def encode_text(self, x: torch.Tensor) -> torch.Tensor:
        """编码文本特征"""
        return self.norm(self.text_encoder(x))

    def encode_speech(self, x: torch.Tensor) -> torch.Tensor:
        """编码语音特征"""
        return self.norm(self.speech_encoder(x))

    def forward(
        self,
        vision: Optional[torch.Tensor] = None,
        text: Optional[torch.Tensor] = None,
        speech: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """编码所有模态"""
        outputs = {}

        if vision is not None:
            outputs["vision"] = self.encode_vision(vision)

        if text is not None:
            outputs["text"] = self.encode_text(text)

        if speech is not None:
            outputs["speech"] = self.encode_speech(speech)

        return outputs


class MultimodalReasoner(nn.Module):
    """多模态推理器

    基于多模态输入进行推理。
    """

    def __init__(self, hidden_dim: int = 512, num_layers: int = 3):
        """初始化多模态推理器"""
        super().__init__()

        self.encoder = MultimodalEncoder(
            vision_dim=768,
            text_dim=768,
            speech_dim=512,
            hidden_dim=hidden_dim
        )

        self.fusion = MultimodalFusion(
            vision_dim=768,
            text_dim=768,
            speech_dim=512,
            output_dim=hidden_dim,
            fusion_type="cross_attention"
        )

        # 推理层
        self.reasoning_layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=hidden_dim,
                nhead=8,
                dim_feedforward=hidden_dim * 4,
                dropout=0.1,
                batch_first=True
            )
            for _ in range(num_layers)
        ])

        # 输出层
        self.output_proj = nn.Linear(hidden_dim, hidden_dim)

    def forward(
        self,
        vision: Optional[torch.Tensor] = None,
        text: Optional[torch.Tensor] = None,
        speech: Optional[torch.Tensor] = None
    ) -> Dict[str, Any]:
        """多模态推理

        Args:
            vision: 视觉特征
            text: 文本特征
            speech: 语音特征

        Returns:
            推理结果
        """
        # 编码各模态
        encoded = self.encoder(vision, text, speech)

        # 获取各模态特征
        vision_feat = encoded.get("vision")
        text_feat = encoded.get("text")
        speech_feat = encoded.get("speech")

        # 融合
        if vision_feat is not None and text_feat is not None:
            fused = self.fusion(vision_feat, text_feat, speech_feat)
        elif text_feat is not None:
            fused = text_feat
        elif vision_feat is not None:
            fused = vision_feat
        elif speech_feat is not None:
            fused = speech_feat
        else:
            raise ValueError("At least one modality must be provided")

        # 推理
        for layer in self.reasoning_layers:
            fused = layer(fused)

        # 输出
        output = self.output_proj(fused)

        return {
            "output": output,
            "fused_features": fused,
            "encoded_features": encoded
        }


def create_multimodal_reasoner(
    vision_dim: int = 768,
    text_dim: int = 768,
    speech_dim: int = 512,
    hidden_dim: int = 512,
    num_layers: int = 3
) -> MultimodalReasoner:
    """创建多模态推理器

    Args:
        vision_dim: 视觉特征维度
        text_dim: 文本特征维度
        speech_dim: 语音特征维度
        hidden_dim: 隐藏层维度
        num_layers: 推理层数

    Returns:
        初始化好的多模态推理器
    """
    model = MultimodalReasoner(
        hidden_dim=hidden_dim,
        num_layers=num_layers
    )

    logger.info(f"Created MultimodalReasoner with {num_layers} layers")

    return model


class AttentionWeights:
    """注意力权重分析工具"""

    @staticmethod
    def compute_attention_importance(
        attention_weights: torch.Tensor
    ) -> torch.Tensor:
        """计算注意力重要性

        Args:
            attention_weights: 注意力权重

        Returns:
            重要性分数
        """
        # 平均池化
        importance = attention_weights.mean(dim=-1)

        # 归一化
        importance = F.softmax(importance, dim=-1)

        return importance

    @staticmethod
    def visualize_cross_modal_attention(
        vision_tokens: List[str],
        text_tokens: List[str],
        attention_weights: torch.Tensor
    ) -> Dict[str, Any]:
        """可视化跨模态注意力

        Args:
            vision_tokens: 视觉token列表
            text_tokens: 文本token列表
            attention_weights: 注意力权重

        Returns:
            可视化数据
        """
        import numpy as np

        # 转换为numpy
        weights = attention_weights.detach().cpu().numpy()

        # 只取前N个token
        n_vision = min(len(vision_tokens), weights.shape[0])
        n_text = min(len(text_tokens), weights.shape[1])

        attention_matrix = weights[:n_vision, :n_text]

        return {
            "matrix": attention_matrix.tolist(),
            "vision_tokens": vision_tokens[:n_vision],
            "text_tokens": text_tokens[:n_text],
            "max_attention": float(np.max(attention_matrix)),
            "mean_attention": float(np.mean(attention_matrix))
        }
