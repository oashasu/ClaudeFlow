"""Thinking过滤器 -过滤thinking + 死循环检测

V2新增模块：
- 过滤thinking内容（去除重复）
- 死循环检测（连续相同thinking触发告警）
"""

from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class ThinkingFilterConfig:
    """Thinking过滤器配置"""

    duplicate_threshold: int = 5  # 重复阈值
    max_thinking_length: int = 500  # 单条最大长度


@dataclass
class DeadLoopAlert:
    """死循环告警数据结构"""

    type: str
    alert_level: str
    task_id: str
    message: str
    duplicate_content: str
    duplicate_count: int
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return asdict(self)


class ThinkingFilter:
    """Thinking内容过滤器"""

    def __init__(self, config: Optional[ThinkingFilterConfig] = None):
        """
        初始化过滤器

        Args:
            config: 配置对象
        """
        self.config = config or ThinkingFilterConfig()

    def filter_thinking(self, thinking_list: List[str]) -> List[str]:
        """
        过滤thinking列表，去除死循环内容

        Args:
            thinking_list: thinking内容列表

        Returns:
            List[str]: 过滤后的列表
        """
        filtered = []
        duplicate_count: Dict[str, int] = {}

        for thinking in thinking_list:
            # 截断过长内容
            content = thinking[:self.config.max_thinking_length]

            # 统计重复次数
            if content not in duplicate_count:
                duplicate_count[content] = 0
            duplicate_count[content] += 1

            # 超过阈值的不保留
            if duplicate_count[content] <= self.config.duplicate_threshold:
                filtered.append(content)

        return filtered

    def detect_dead_loop(self, thinking_list: List[str]) -> Tuple[bool, Optional[str]]:
        """
        检测是否存在死循环

        Args:
            thinking_list: thinking内容列表

        Returns:
            Tuple[bool, Optional[str]]:
                - 是否检测到死循环
                - 死循环内容（如果检测到）
        """
        duplicate_count: Dict[str, int] = {}

        for thinking in thinking_list:
            # 截断后统计
            content = thinking[:self.config.max_thinking_length]
            duplicate_count[content] = duplicate_count.get(content, 0) + 1

            # 超过阈值视为死循环
            if duplicate_count[content] > self.config.duplicate_threshold:
                return True, content

        return False, None

    def generate_dead_loop_alert(
        self,
        task_id: str,
        content: str,
        count: int
    ) -> DeadLoopAlert:
        """
        生成死循环告警

        Args:
            task_id: 任务ID
            content: 重复内容
            count: 重复次数

        Returns:
            DeadLoopAlert: 告警对象
        """
        return DeadLoopAlert(
            type="log_alert",
            alert_level="WARNING",
            task_id=task_id,
            message="检测到thinking死循环",
            duplicate_content=content[:self.config.max_thinking_length],
            duplicate_count=count
        )