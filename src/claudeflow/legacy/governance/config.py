"""熔断层配置

定义阈值参数：
- MAX_CALLS = 10（最大调用轮数）
- MAX_TOKENS = 50000（累计Token上限）
- MAX_SINGLE_TOKENS = 5000（单轮上限）
- SIMILARITY_THRESHOLD = 0.95（相似度阈值）
- WINDOW_SIZE = 3（滑动窗口大小）
"""

from dataclasses import dataclass


@dataclass
class GovernanceConfig:
    """熔断层配置"""

    max_calls: int = 10
    max_tokens: int = 50000
    max_single_tokens: int = 5000
    similarity_threshold: float = 0.95
    window_size: int = 3

    def __post_init__(self):
        """参数校验"""
        if self.max_calls < 1:
            raise ValueError("max_calls 必须 >= 1")
        if self.max_tokens < 1:
            raise ValueError("max_tokens 必须 >= 1")
        if self.max_single_tokens < 1:
            raise ValueError("max_single_tokens 必须 >= 1")
        if self.similarity_threshold <= 0 or self.similarity_threshold > 1:
            raise ValueError("similarity_threshold 必须在 (0, 1] 范围")
        if self.window_size < 2:
            raise ValueError("window_size 必须 >= 2（至少2轮才能对比）")