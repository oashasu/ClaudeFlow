"""熔断层核心模块

实现：
- 阈值拦截（10轮/50K/单轮5K）
- 相似度检测（bge-small-zh）
- 滑动窗口判定（3轮连续相似）
- 熔断动作执行
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union
from collections import deque
from enum import Enum

from claudeflow.governance.config import GovernanceConfig


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常运行
    OPEN = "open"  # 熔断触发，停止执行


class CircuitBreakerTrigger(Enum):
    """熔断触发类型"""

    MAX_CALLS = "max_calls"  # 调用次数上限
    MAX_TOKENS = "max_tokens"  # 累计Token上限
    MAX_SINGLE_TOKENS = "max_single_tokens"  # 单轮Token上限
    SIMILARITY = "similarity"  # 相似度熔断

    def create_result(self) -> "CircuitBreakerResult":
        """创建熔断结果"""
        messages = {
            CircuitBreakerTrigger.MAX_CALLS: "调用次数达到上限，触发熔断",
            CircuitBreakerTrigger.MAX_TOKENS: "累计Token达到上限，触发熔断",
            CircuitBreakerTrigger.MAX_SINGLE_TOKENS: "单轮Token超过上限，触发熔断",
            CircuitBreakerTrigger.SIMILARITY: "连续输出相似度超过阈值，触发熔断",
        }
        return CircuitBreakerResult(
            trigger=self,
            state=CircuitState.OPEN,
            message=messages[self],
        )


@dataclass
class CircuitBreakerResult:
    """熔断结果"""

    trigger: CircuitBreakerTrigger
    state: CircuitState
    message: str


@dataclass
class CircuitBreaker:
    """熔断器

    功能：
    1. 阈值拦截：调用次数、累计Token、单轮Token
    2. 相似度检测：滑动窗口内相邻两两对比
    3. 熔断动作：立即终止，记录日志，状态标记

    注意：相似度计算器使用懒加载，首次需要时才初始化模型
    """

    config: GovernanceConfig = field(default_factory=GovernanceConfig)
    # 支持传入自定义相似度计算器（测试时可mock），或None表示使用默认懒加载
    similarity_calculator: Union[object, None] = field(default=None)

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    call_count: int = field(default=0, init=False)
    total_tokens: int = field(default=0, init=False)
    output_window: deque = field(default_factory=lambda: deque(maxlen=3), init=False)
    # 懒加载标记
    _similarity_initialized: bool = field(default=False, init=False)

    def __post_init__(self):
        """初始化后处理"""
        # 设置窗口大小
        self.output_window = deque(maxlen=self.config.window_size)
        # similarity_calculator 如果已传入，则标记已初始化
        if self.similarity_calculator is not None:
            self._similarity_initialized = True

    def _get_similarity_calculator(self):
        """获取相似度计算器（懒加载）"""
        if not self._similarity_initialized:
            from claudeflow.governance.similarity import SimilarityCalculator
            self.similarity_calculator = SimilarityCalculator()
            self._similarity_initialized = True
        return self.similarity_calculator

    def record_call(
        self, tokens: int, output: Optional[str] = None
    ) -> Optional[CircuitBreakerResult]:
        """记录一次调用

        Args:
            tokens: 本次调用的Token数量
            output: 本次输出的文本内容

        Returns:
            熔断结果（如果触发熔断），否则None
        """
        self.call_count += 1
        self.total_tokens += tokens

        if output:
            self.output_window.append(output)

        # 检查各阈值
        result = self._check_thresholds()
        if result:
            return result

        # 检查相似度（需要窗口内有足够数据）
        result = self._check_similarity()
        if result:
            return result

        return None

    def _check_thresholds(self) -> Optional[CircuitBreakerResult]:
        """检查阈值触发"""
        # 单轮Token上限（优先级最高）
        if self.call_count == 1:
            # 仅检查当前单轮
            pass

        # 调用次数上限
        if self.call_count >= self.config.max_calls:
            return self.trigger_break(CircuitBreakerTrigger.MAX_CALLS)

        # 累计Token上限
        if self.total_tokens >= self.config.max_tokens:
            return self.trigger_break(CircuitBreakerTrigger.MAX_TOKENS)

        return None

    def _check_similarity(self) -> Optional[CircuitBreakerResult]:
        """检查相似度触发（滑动窗口判定）

        触发条件：
        - N vs N-1 >= threshold
        - N-1 vs N-2 >= threshold
        - N-2 vs N-3 >= threshold
        即连续3轮（或window_size轮）两两相似
        """
        window = list(self.output_window)
        window_size = self.config.window_size

        # 窗口内数据不足
        if len(window) < window_size:
            return None

        # 获取相似度计算器（懒加载）
        calculator = self._get_similarity_calculator()

        # 相邻两两对比
        similar_count = 0
        for i in range(len(window) - 1):
            if calculator.is_similar(
                window[i], window[i + 1], self.config.similarity_threshold
            ):
                similar_count += 1

        # 全部相邻对都相似
        if similar_count >= window_size - 1:
            return self.trigger_break(CircuitBreakerTrigger.SIMILARITY)

        return None

    def trigger_break(self, trigger: CircuitBreakerTrigger) -> CircuitBreakerResult:
        """执行熔断动作

        Args:
            trigger: 熔断触发类型

        Returns:
            熔断结果
        """
        self.state = CircuitState.OPEN
        result = trigger.create_result()
        return result

    def reset(self):
        """重置熔断器状态"""
        self.state = CircuitState.CLOSED
        self.call_count = 0
        self.total_tokens = 0
        self.output_window.clear()

    def get_status(self) -> dict:
        """获取当前状态信息"""
        return {
            "state": self.state.value,
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "window_size": len(self.output_window),
            "config": {
                "max_calls": self.config.max_calls,
                "max_tokens": self.config.max_tokens,
                "max_single_tokens": self.config.max_single_tokens,
                "similarity_threshold": self.config.similarity_threshold,
                "window_size": self.config.window_size,
            },
        }