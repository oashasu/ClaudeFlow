"""T003: TaskPackageLoader — 任务包 YAML 解析与校验。

职责:
- 装载 tasks/*.yaml
- 解析成结构化对象
- 严格校验必填字段和枚举值
- 输出校验错误

Schema 来源: 09_Governor编排对象Schema设计.md

约束:
- 严格字段校验，禁止宽松解析
- allowed_write_paths 不能为空
- acceptance_refs 至少一个
- done_definition 必须是数组
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

REQUIRED_TASK_FIELDS = (
    "id",
    "phase_id",
    "title",
    "executor_type",
    "reviewer_type",
    "inputs",
    "constraints",
    "allowed_write_paths",
    "acceptance_refs",
    "done_definition",
    "gate_on_complete",
)

VALID_EXECUTOR_TYPES = ("claude", "codex", "future")
VALID_REVIEWER_TYPES = ("governor", "external-reviewer")
VALID_PRIORITIES = ("critical", "high", "medium", "low")
VALID_GATE_ON_COMPLETE = ("review_required", "acceptance_required")


@dataclass
class TaskPackageError:
    """任务包校验错误。"""

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
class TaskPackage:
    """解析后的结构化任务包。"""

    id: str
    phase_id: str
    title: str
    executor_type: str
    reviewer_type: str
    inputs: List[str]
    constraints: List[str]
    allowed_write_paths: List[str]
    acceptance_refs: List[str]
    done_definition: List[str]
    gate_on_complete: str
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase_id": self.phase_id,
            "title": self.title,
            "executor_type": self.executor_type,
            "reviewer_type": self.reviewer_type,
            "inputs": list(self.inputs),
            "constraints": list(self.constraints),
            "allowed_write_paths": list(self.allowed_write_paths),
            "acceptance_refs": list(self.acceptance_refs),
            "done_definition": list(self.done_definition),
            "gate_on_complete": self.gate_on_complete,
        }


class TaskPackageLoader:
    """任务包 YAML 加载器。"""

    def load_file(self, path: str | Path) -> tuple[Optional[TaskPackage], List[TaskPackageError]]:
        """从单个 YAML 文件加载任务包。"""
        file_path = Path(path)
        if not file_path.exists():
            return None, [TaskPackageError(
                error_type="file_not_found",
                file_path=str(file_path),
                field_name="",
                reason="任务包文件不存在",
            )]

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            return None, [TaskPackageError(
                error_type="read_error",
                file_path=str(file_path),
                field_name="",
                reason=str(exc),
            )]

        try:
            raw = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            return None, [TaskPackageError(
                error_type="yaml_parse_error",
                file_path=str(file_path),
                field_name="",
                reason=str(exc),
            )]

        if not isinstance(raw, dict):
            return None, [TaskPackageError(
                error_type="schema_error",
                file_path=str(file_path),
                field_name="",
                reason="YAML 顶层必须是对象/映射",
            )]

        errors = self._validate(raw, str(file_path))
        if errors:
            return None, errors

        pkg = TaskPackage(
            id=raw["id"],
            phase_id=raw["phase_id"],
            title=raw["title"],
            executor_type=raw["executor_type"],
            reviewer_type=raw["reviewer_type"],
            inputs=list(raw["inputs"]),
            constraints=list(raw["constraints"]),
            allowed_write_paths=list(raw["allowed_write_paths"]),
            acceptance_refs=list(raw["acceptance_refs"]),
            done_definition=list(raw["done_definition"]),
            gate_on_complete=raw["gate_on_complete"],
            raw=raw,
        )
        return pkg, []

    def load_directory(self, dir_path: str | Path) -> tuple[List[TaskPackage], List[TaskPackageError]]:
        """从目录加载所有 *.yaml 任务包。"""
        directory = Path(dir_path)
        if not directory.is_dir():
            return [], [TaskPackageError(
                error_type="dir_not_found",
                file_path=str(directory),
                field_name="",
                reason="任务包目录不存在",
            )]

        packages: List[TaskPackage] = []
        errors: List[TaskPackageError] = []

        for yaml_file in sorted(directory.glob("*.yaml")):
            pkg, file_errors = self.load_file(yaml_file)
            if file_errors:
                errors.extend(file_errors)
            elif pkg:
                packages.append(pkg)

        return packages, errors

    def _validate(self, raw: Dict[str, Any], file_path: str) -> List[TaskPackageError]:
        errors: List[TaskPackageError] = []

        for field_name in REQUIRED_TASK_FIELDS:
            if field_name not in raw:
                errors.append(TaskPackageError(
                    error_type="missing_field",
                    file_path=file_path,
                    field_name=field_name,
                    reason=f"必填字段缺失: {field_name}",
                ))

        if errors:
            return errors

        executor = raw.get("executor_type")
        if executor and executor not in VALID_EXECUTOR_TYPES:
            errors.append(TaskPackageError(
                error_type="enum_error",
                file_path=file_path,
                field_name="executor_type",
                reason=f"非法枚举值: {executor}，合法值: {VALID_EXECUTOR_TYPES}",
            ))

        reviewer = raw.get("reviewer_type")
        if reviewer and reviewer not in VALID_REVIEWER_TYPES:
            errors.append(TaskPackageError(
                error_type="enum_error",
                file_path=file_path,
                field_name="reviewer_type",
                reason=f"非法枚举值: {reviewer}，合法值: {VALID_REVIEWER_TYPES}",
            ))

        gate = raw.get("gate_on_complete")
        if gate and gate not in VALID_GATE_ON_COMPLETE:
            errors.append(TaskPackageError(
                error_type="enum_error",
                file_path=file_path,
                field_name="gate_on_complete",
                reason=f"非法枚举值: {gate}，合法值: {VALID_GATE_ON_COMPLETE}",
            ))

        for list_field in ("inputs", "constraints", "allowed_write_paths", "acceptance_refs", "done_definition"):
            val = raw.get(list_field)
            if val is not None and not isinstance(val, list):
                errors.append(TaskPackageError(
                    error_type="type_error",
                    file_path=file_path,
                    field_name=list_field,
                    reason=f"{list_field} 必须是数组",
                ))

        write_paths = raw.get("allowed_write_paths")
        if isinstance(write_paths, list) and len(write_paths) == 0:
            errors.append(TaskPackageError(
                error_type="empty_field",
                file_path=file_path,
                field_name="allowed_write_paths",
                reason="allowed_write_paths 不能为空",
            ))

        acceptance = raw.get("acceptance_refs")
        if isinstance(acceptance, list) and len(acceptance) == 0:
            errors.append(TaskPackageError(
                error_type="empty_field",
                file_path=file_path,
                field_name="acceptance_refs",
                reason="acceptance_refs 至少需要一个引用",
            ))

        return errors
