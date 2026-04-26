"""T004: GovernanceStateMachine — phase / gate 状态机骨架。

职责:
- 定义 phase 和 gate 状态枚举
- 定义合法流转
- 拒绝非法流转

Phase 流转链:
  drafting -> docs_confirm -> ready_for_dispatch -> in_execution
  in_execution -> implementation_review
  implementation_review -> quality_gate
  quality_gate -> accepted
  quality_gate -> reopened

Gate 状态:
  open / blocked / passed / failed / closed
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, List, Tuple


class GovernancePhase(str, Enum):
    """治理 Phase 状态枚举。"""

    DRAFTING = "drafting"
    DOCS_CONFIRM = "docs_confirm"
    READY_FOR_DISPATCH = "ready_for_dispatch"
    IN_EXECUTION = "in_execution"
    IMPLEMENTATION_REVIEW = "implementation_review"
    QUALITY_GATE = "quality_gate"
    ACCEPTED = "accepted"
    REOPENED = "reopened"


class GateStatus(str, Enum):
    """Gate 状态枚举。"""

    OPEN = "open"
    BLOCKED = "blocked"
    PASSED = "passed"
    FAILED = "failed"
    CLOSED = "closed"


# 合法的 Phase 流转表: (from, to)
VALID_PHASE_TRANSITIONS: Dict[GovernancePhase, FrozenSet[GovernancePhase]] = {
    GovernancePhase.DRAFTING: frozenset({GovernancePhase.DOCS_CONFIRM}),
    GovernancePhase.DOCS_CONFIRM: frozenset({GovernancePhase.READY_FOR_DISPATCH}),
    GovernancePhase.READY_FOR_DISPATCH: frozenset({GovernancePhase.IN_EXECUTION}),
    GovernancePhase.IN_EXECUTION: frozenset({GovernancePhase.IMPLEMENTATION_REVIEW}),
    GovernancePhase.IMPLEMENTATION_REVIEW: frozenset({GovernancePhase.QUALITY_GATE}),
    GovernancePhase.QUALITY_GATE: frozenset({
        GovernancePhase.ACCEPTED,
        GovernancePhase.REOPENED,
    }),
    GovernancePhase.ACCEPTED: frozenset(),
    GovernancePhase.REOPENED: frozenset({GovernancePhase.DRAFTING}),
}

# 合法的 Gate 流转表
VALID_GATE_TRANSITIONS: Dict[GateStatus, FrozenSet[GateStatus]] = {
    GateStatus.OPEN: frozenset({GateStatus.BLOCKED, GateStatus.PASSED}),
    GateStatus.BLOCKED: frozenset({GateStatus.OPEN, GateStatus.FAILED}),
    GateStatus.PASSED: frozenset({GateStatus.CLOSED}),
    GateStatus.FAILED: frozenset({GateStatus.OPEN}),
    GateStatus.CLOSED: frozenset(),
}


class IllegalTransitionError(Exception):
    """非法状态流转错误。"""

    def __init__(self, kind: str, from_state: str, to_state: str) -> None:
        self.kind = kind
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"非法 {kind} 流转: {from_state} -> {to_state}"
        )


class GovernanceStateMachine:
    """治理状态机 — 管理 phase 和 gate 的合法流转。"""

    def __init__(
        self,
        phase: GovernancePhase = GovernancePhase.DRAFTING,
        gate: GateStatus = GateStatus.OPEN,
    ) -> None:
        self.phase = phase
        self.gate = gate

    def advance_phase(self, target: GovernancePhase) -> GovernancePhase:
        """尝试推进 phase 到目标状态。

        Returns:
            新 phase 状态

        Raises:
            IllegalTransitionError: 流转不合法
        """
        allowed = VALID_PHASE_TRANSITIONS.get(self.phase, frozenset())
        if target not in allowed:
            raise IllegalTransitionError("phase", self.phase.value, target.value)
        self.phase = target
        return self.phase

    def transition_gate(self, target: GateStatus) -> GateStatus:
        """尝试转换 gate 状态。

        Returns:
            新 gate 状态

        Raises:
            IllegalTransitionError: 流转不合法
        """
        allowed = VALID_GATE_TRANSITIONS.get(self.gate, frozenset())
        if target not in allowed:
            raise IllegalTransitionError("gate", self.gate.value, target.value)
        self.gate = target
        return self.gate

    def can_advance_phase(self, target: GovernancePhase) -> bool:
        return target in VALID_PHASE_TRANSITIONS.get(self.phase, frozenset())

    def can_transition_gate(self, target: GateStatus) -> bool:
        return target in VALID_GATE_TRANSITIONS.get(self.gate, frozenset())

    def get_allowed_phase_transitions(self) -> List[GovernancePhase]:
        return sorted(VALID_PHASE_TRANSITIONS.get(self.phase, frozenset()),
                       key=lambda p: p.value)

    def get_allowed_gate_transitions(self) -> List[GateStatus]:
        return sorted(VALID_GATE_TRANSITIONS.get(self.gate, frozenset()),
                       key=lambda g: g.value)
