"""Governance治理层

熔断层：阈值拦截 + 相似度检测 + 熔断动作
快照层：baseline/incremental JSON模板 + 存储管理 + Git绑定
验收层：L1强制量化 + L2半量化 + L3人工入口
恢复层：熔断回滚 + 异常重试 + 增量快照生成
"""

from claudeflow.legacy.governance.config import GovernanceConfig
from claudeflow.legacy.governance.similarity import SimilarityCalculator
from claudeflow.legacy.governance.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerTrigger,
    CircuitBreakerResult,
)
from claudeflow.legacy.governance.snapshot import (
    SnapshotManager,
    BaselineSchema,
    IncrementalSchema,
    get_git_commit_hash,
    create_baseline_snapshot,
    create_incremental_snapshot,
)
from claudeflow.legacy.governance.acceptance import (
    parse_coverage_output,
    L1Validator,
    L2Validator,
    L3Validator,
    AcceptanceManager,
    AcceptanceResult,
    ViolationRecord,
    L3ReviewRequest,
    AcceptanceError,
)
from claudeflow.legacy.governance.recovery import (
    RecoveryManager,
    RecoveryResult,
    RecoveryError,
    ToolCallError,
    AcceptanceRetryError,
    rollback,
    retry_tool_call,
    handle_acceptance_failure,
)

__all__ = [
    # Config
    "GovernanceConfig",
    # Similarity
    "SimilarityCalculator",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerTrigger",
    "CircuitBreakerResult",
    # Snapshot
    "SnapshotManager",
    "BaselineSchema",
    "IncrementalSchema",
    "get_git_commit_hash",
    "create_baseline_snapshot",
    "create_incremental_snapshot",
    # Acceptance
    "parse_coverage_output",
    "L1Validator",
    "L2Validator",
    "L3Validator",
    "AcceptanceManager",
    "AcceptanceResult",
    "ViolationRecord",
    "L3ReviewRequest",
    "AcceptanceError",
    # Recovery
    "RecoveryManager",
    "RecoveryResult",
    "RecoveryError",
    "ToolCallError",
    "AcceptanceRetryError",
    "rollback",
    "retry_tool_call",
    "handle_acceptance_failure",
]