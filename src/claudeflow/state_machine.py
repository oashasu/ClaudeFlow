"""状态机模块 - 七状态模型

V1核心功能：任务状态流转、重试策略、阶段节点管理
"""

from enum import Enum
from typing import Dict, Optional


class TaskStatus(Enum):
    """任务状态枚举 - 七状态模型"""
    PENDING = "pending"          # 待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 已失败
    RETRYING = "retrying"        # 重试中
    HUMAN_INTERVENTION = "human_intervention"  # 人工介入点
    ARCHIVED = "archived"        # 已归档


class Phase(Enum):
    """工作流阶段枚举 - 八阶段"""
    REQUIREMENTS = 1     # 需求收集
    BRAINSTORM = 2       # 头脑风暴
    ARCHITECTURE = 3     # 概要设计
    DESIGN = 4           # 详细设计
    DEVELOPMENT = 5      # 开发实现
    TESTING = 6          # 测试验证
    REVIEW = 7           # 代码审查
    ACCEPTANCE = 8       # 验收报告

    @property
    def checkpoint_file(self) -> str:
        """阶段checkpoint文件名"""
        names = {
            Phase.REQUIREMENTS: "v1_init.json",
            Phase.BRAINSTORM: "v2_brainstorm.json",
            Phase.ARCHITECTURE: "v3_architecture.json",
            Phase.DESIGN: "v4_design.json",
            Phase.DEVELOPMENT: "v5_dev.json",
            Phase.TESTING: "v6_test.json",
            Phase.REVIEW: "v7_review.json",
            Phase.ACCEPTANCE: "v8_acceptance.json",
        }
        return names[self]


class InvalidTransitionError(Exception):
    """非法状态流转错误"""
    pass


# 状态流转规则表
TRANSITION_RULES: Dict[TaskStatus, Dict[str, TaskStatus]] = {
    TaskStatus.PENDING: {
        "assign_employee": TaskStatus.RUNNING,
        "cancel": TaskStatus.ARCHIVED,
    },
    TaskStatus.RUNNING: {
        "success": TaskStatus.COMPLETED,
        "fail": TaskStatus.FAILED,
        "pause": TaskStatus.PENDING,
    },
    TaskStatus.FAILED: {
        "retry": TaskStatus.RETRYING,
        "archive": TaskStatus.ARCHIVED,
    },
    TaskStatus.RETRYING: {
        "retry_success": TaskStatus.RUNNING,
        "retry_fail": TaskStatus.RETRYING,  # 继续重试或进入人工介入
    },
    TaskStatus.COMPLETED: {
        "archive": TaskStatus.ARCHIVED,
    },
    TaskStatus.HUMAN_INTERVENTION: {
        "resolve": TaskStatus.COMPLETED,
        "archive": TaskStatus.ARCHIVED,
    },
}

# 可重试错误类型
RETRIABLE_ERRORS = {
    "network_timeout",
    "api_rate_limit",
    "process_crash",
    "knowledge_retrieval_failed",
}

# 不可重试错误类型
NON_RETRIABLE_ERRORS = {
    "permission_denied",
    "logic_error",
    "invalid_params",
}


class StateMachine:
    """状态机 - 管理任务状态流转"""

    def __init__(self):
        self.current_status: TaskStatus = TaskStatus.PENDING
        self.context: Dict = {"retry_count": 0}

    def transition(self, from_status: TaskStatus, action: str) -> TaskStatus:
        """
        执行状态流转

        Args:
            from_status: 当前状态
            action: 触发动作

        Returns:
            新状态

        Raises:
            InvalidTransitionError: 非法流转
        """
        rules = TRANSITION_RULES.get(from_status, {})

        if action not in rules:
            raise InvalidTransitionError(
                f"非法状态流转: {from_status.value} -> action={action}"
            )

        new_status = rules[action]

        # 重试逻辑特殊处理
        if from_status == TaskStatus.RETRYING and action == "retry_fail":
            retry_count = self.context.get("retry_count", 0)
            if retry_count >= 3:
                new_status = TaskStatus.HUMAN_INTERVENTION

        # 重试次数递增
        if from_status == TaskStatus.FAILED and action == "retry":
            self.context["retry_count"] = self.context.get("retry_count", 0) + 1

        self.current_status = new_status
        return new_status


def get_retry_interval(retry_count: int) -> int:
    """
    获取重试间隔时间（秒）

    Args:
        retry_count: 重试次数

    Returns:
        间隔秒数: 10s → 60s → 300s
    """
    intervals = {1: 10, 2: 60, 3: 300}
    return intervals.get(retry_count, 300)


def is_retriable(error_type: str) -> bool:
    """
    判断错误是否可重试

    Args:
        error_type: 错误类型

    Returns:
        True表示可重试
    """
    return error_type in RETRIABLE_ERRORS