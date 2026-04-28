"""相似度计算模块

使用 bge-small-zh-v1.5 模型计算文本语义相似度
余弦距离 >= 0.95 判定为高度重复

依赖：pip install sentence-transformers
"""

import numpy as np
from typing import Optional
from sentence_transformers import SentenceTransformer


class SimilarityCalculator:
    """文本语义相似度计算器"""

    _model: Optional[SentenceTransformer] = None
    _model_name: str = "BAAI/bge-small-zh-v1.5"

    def __init__(self, model_name: Optional[str] = None):
        """初始化模型（懒加载）"""
        if model_name:
            self._model_name = model_name
        self._model = SentenceTransformer(self._model_name)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            # 空向量返回1.0（两个空文本视为相同）
            return 1.0

        return dot_product / (norm1 * norm2)

    def calculate(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度

        Args:
            text1: 第一段文本
            text2: 第二段文本

        Returns:
            余弦相似度值 (0-1)
        """
        if not text1 and not text2:
            # 两个空文本视为完全相同
            return 1.0

        if not text1 or not text2:
            # 一个空一个非空视为不相似
            return 0.0

        embeddings = self._model.encode([text1, text2])
        vec1 = embeddings[0]
        vec2 = embeddings[1]

        return self._cosine_similarity(vec1, vec2)

    def is_similar(self, text1: str, text2: str, threshold: float = 0.95) -> bool:
        """判断两段文本是否相似

        Args:
            text1: 第一段文本
            text2: 第二段文本
            threshold: 相似度阈值，默认0.95

        Returns:
            True if 相似度 >= threshold
        """
        similarity = self.calculate(text1, text2)
        return bool(similarity >= threshold)