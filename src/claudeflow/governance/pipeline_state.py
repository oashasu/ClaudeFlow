"""T002: PipelineStateStore — pipeline-state.json 加载、校验、原子写回。

职责:
- 加载 pipeline-state.json
- 校验必填字段和枚举值
- 原子写回（先写临时文件再重命名）
- 提供结构化错误

约束:
- 非法输入不得污染旧状态
- 写回必须原子化
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = (
    "workflow_version",
    "current_phase",
    "current_stage",
    "current_gate",
    "gate_status",
    "governor",
    "advance_allowed",
    "reopen_required",
    "tasks",
    "timestamps",
)

VALID_PHASES = (
    "drafting",
    "docs_confirm",
    "ready_for_dispatch",
    "in_execution",
    "implementation_review",
    "quality_gate",
    "accepted",
    "reopened",
)

VALID_GATE_STATUSES = ("open", "blocked", "passed", "failed", "closed")


@dataclass
class PipelineStateError:
    """pipeline-state.json 校验错误。"""

    error_type: str
    file_path: str
    field_name: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "error_type": self.error_type,
            "file_path": self.file_path,
            "field_name": self.field_name,
            "reason": self.reason,
        }


@dataclass
class PipelineState:
    """内存中的 pipeline-state 对象。"""

    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_phase(self) -> str:
        return self.raw.get("current_phase", "")

    @current_phase.setter
    def current_phase(self, value: str) -> None:
        self.raw["current_phase"] = value

    @property
    def current_gate(self) -> str:
        return self.raw.get("current_gate", "")

    @current_gate.setter
    def current_gate(self, value: str) -> None:
        self.raw["current_gate"] = value

    @property
    def gate_status(self) -> str:
        return self.raw.get("gate_status", "")

    @gate_status.setter
    def gate_status(self, value: str) -> None:
        self.raw["gate_status"] = value

    @property
    def updated_at(self) -> str:
        return self.raw.get("timestamps", {}).get("updated_at", "")


class PipelineStateStore:
    """pipeline-state.json 的读写存储。"""

    def __init__(self, pipeline_state_path: str | Path) -> None:
        self.path = Path(pipeline_state_path)

    def load(self) -> tuple[PipelineState, List[PipelineStateError]]:
        """加载并校验 pipeline-state.json。

        返回 (state, errors)。errors 非空时表示校验失败，
        此时 state 为空对象，不包含任何非法内容。
        """
        errors: List[PipelineStateError] = []

        if not self.path.exists():
            errors.append(PipelineStateError(
                error_type="file_not_found",
                file_path=str(self.path),
                field_name="",
                reason="pipeline-state.json 不存在",
            ))
            return PipelineState(), errors

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(PipelineStateError(
                error_type="json_parse_error",
                file_path=str(self.path),
                field_name="",
                reason=str(exc),
            ))
            return PipelineState(), errors

        if not isinstance(raw, dict):
            errors.append(PipelineStateError(
                error_type="schema_error",
                file_path=str(self.path),
                field_name="",
                reason="顶层必须是 JSON 对象",
            ))
            return PipelineState(), errors

        errors.extend(self._validate(raw))
        if errors:
            return PipelineState(), errors

        return PipelineState(raw=raw), []

    def save(self, state: PipelineState) -> None:
        """原子写回 pipeline-state.json。

        先写入临时文件，再 os.replace 原子替换。
        """
        state.raw.setdefault("timestamps", {})["updated_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload_json = json.dumps(state.raw, ensure_ascii=False, indent=2)

        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".pipeline-state-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload_json)
            os.replace(tmp_path, str(self.path))
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def update_and_save(
        self,
        updates: Dict[str, Any],
    ) -> tuple[PipelineState, List[PipelineStateError]]:
        """加载、合并更新、校验、写回的原子操作。

        校验失败时不写回，保留旧文件。
        """
        state, errors = self.load()
        if errors:
            return state, errors

        merged = {**state.raw, **updates}
        merged.setdefault("timestamps", {})["updated_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

        merged_errors = self._validate(merged)
        if merged_errors:
            return PipelineState(), merged_errors

        new_state = PipelineState(raw=merged)
        self.save(new_state)
        return new_state, []

    def _validate(self, raw: Dict[str, Any]) -> List[PipelineStateError]:
        errors: List[PipelineStateError] = []

        for field_name in REQUIRED_FIELDS:
            if field_name not in raw:
                errors.append(PipelineStateError(
                    error_type="missing_field",
                    file_path=str(self.path),
                    field_name=field_name,
                    reason=f"必填字段缺失: {field_name}",
                ))

        phase = raw.get("current_phase")
        if phase is not None and phase not in VALID_PHASES:
            errors.append(PipelineStateError(
                error_type="enum_error",
                file_path=str(self.path),
                field_name="current_phase",
                reason=f"非法枚举值: {phase}，合法值: {VALID_PHASES}",
            ))

        gate = raw.get("gate_status")
        if gate is not None and gate not in VALID_GATE_STATUSES:
            errors.append(PipelineStateError(
                error_type="enum_error",
                file_path=str(self.path),
                field_name="gate_status",
                reason=f"非法枚举值: {gate}，合法值: {VALID_GATE_STATUSES}",
            ))

        governor = raw.get("governor")
        if governor is not None and not isinstance(governor, dict):
            errors.append(PipelineStateError(
                error_type="schema_error",
                file_path=str(self.path),
                field_name="governor",
                reason="governor 必须是对象",
            ))

        tasks = raw.get("tasks")
        if tasks is not None and not isinstance(tasks, list):
            errors.append(PipelineStateError(
                error_type="schema_error",
                file_path=str(self.path),
                field_name="tasks",
                reason="tasks 必须是数组",
            ))

        timestamps = raw.get("timestamps")
        if timestamps is not None and not isinstance(timestamps, dict):
            errors.append(PipelineStateError(
                error_type="schema_error",
                file_path=str(self.path),
                field_name="timestamps",
                reason="timestamps 必须是对象",
            ))

        return errors
