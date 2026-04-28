"""T203: Rework Task Generator — 从 review artifact 生成返工任务包。

职责:
- 读取原任务包和 review artifact
- 生成返工任务包
- 继承原任务关键约束
- 记录 rework_round

验收标准 A23:
- review 判定 rework_required 后生成返工任务包
- 返工任务包继承原任务关键约束

关键约束:
- 返工任务必须继承原 allowed_write_paths 与 acceptance_refs
- 不得发明新 schema 替代 task package

返工任务包路径:
.super-dev/phases/<phase-id>/tasks/<original-id>-R<n>.yaml

返工任务必须继承:
- phase_id
- executor_type
- allowed_write_paths
- acceptance_refs
- gate_on_complete

返工任务必须新增:
- rework_context.original_task_id
- rework_context.findings_ref
- rework_context.rework_round
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claudeflow.governance.task_loader import (
    TaskPackage,
    TaskPackageLoader,
    TaskPackageError,
)
from claudeflow.governance.review_artifact import (
    ReviewArtifact,
    ReviewArtifactWriter,
)


@dataclass
class ReworkContext:
    """返工任务上下文。"""

    original_task_id: str
    findings_ref: str  # review artifact 文件路径
    rework_round: int
    blocker_count: int
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_task_id": self.original_task_id,
            "findings_ref": self.findings_ref,
            "rework_round": self.rework_round,
            "blocker_count": self.blocker_count,
            "summary": self.summary,
        }


@dataclass
class ReworkTaskPackage:
    """返工任务包结构。"""

    # 继承字段
    id: str  # <original-id>-R<n>
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

    # 新增字段
    rework_context: ReworkContext

    # 元数据
    generated_at: str
    priority: str = "high"

    raw: Dict[str, Any] = field(default_factory=dict)

    def to_yaml_dict(self) -> Dict[str, Any]:
        """生成 YAML 写入格式。"""
        return {
            "id": self.id,
            "phase_id": self.phase_id,
            "title": self.title,
            "executor_type": self.executor_type,
            "reviewer_type": self.reviewer_type,
            "priority": self.priority,
            "inputs": self.inputs,
            "constraints": self.constraints,
            "allowed_write_paths": self.allowed_write_paths,
            "acceptance_refs": self.acceptance_refs,
            "outputs": ["changed_files", "test_evidence", "summary"],
            "done_definition": self.done_definition,
            "rework_policy": {
                "max_rounds": 2,
                "inherit_previous_findings": True,
            },
            "rework_context": self.rework_context.to_dict(),
            "gate_on_complete": self.gate_on_complete,
        }


class ReworkTaskGenerator:
    """返工任务生成器。"""

    def __init__(self, governance_root: str | Path) -> None:
        self.governance_root = Path(governance_root)
        self.task_loader = TaskPackageLoader()
        self.review_writer = ReviewArtifactWriter(governance_root)

    def _get_tasks_dir(self, phase_id: str) -> Path:
        """获取任务包目录。"""
        return self.governance_root / "phases" / phase_id / "tasks"

    def _get_rework_task_path(self, phase_id: str, original_task_id: str, round: int) -> Path:
        """获取返工任务包路径。"""
        rework_id = f"{original_task_id}-R{round}"
        return self._get_tasks_dir(phase_id) / f"{rework_id}.yaml"

    def _load_original_task(self, phase_id: str, task_id: str) -> Optional[TaskPackage]:
        """加载原始任务包。"""
        task_path = self._get_tasks_dir(phase_id) / f"{task_id}.yaml"
        if not task_path.exists():
            return None

        pkg, errors = self.task_loader.load_file(task_path)
        if errors:
            return None
        return pkg

    def _get_existing_rework_rounds(self, phase_id: str, original_task_id: str) -> int:
        """获取已存在的返工轮次数量。"""
        tasks_dir = self._get_tasks_dir(phase_id)
        rounds = 0
        for f in tasks_dir.glob(f"{original_task_id}-R*.yaml"):
            try:
                # 从文件名提取轮次号
                name = f.stem
                round_part = name.split("-R")[-1]
                round_num = int(round_part)
                rounds = max(rounds, round_num)
            except (ValueError, IndexError):
                pass
        return rounds

    def generate(
        self,
        review_artifact: ReviewArtifact,
        original_task_id: str,
        phase_id: str,
    ) -> Optional[ReworkTaskPackage]:
        """从 review artifact 生成返工任务包。

        Args:
            review_artifact: 审查产物
            original_task_id: 原任务 ID
            phase_id: 阶段 ID

        Returns:
            ReworkTaskPackage 或 None（如果无法生成）
        """
        # 验证 decision 为 rework_required
        if review_artifact.decision != "rework_required":
            return None

        # 加载原任务包
        original_pkg = self._load_original_task(phase_id, original_task_id)
        if original_pkg is None:
            # 尝试加载已有的返工任务（后续返工）
            existing_rounds = self._get_existing_rework_rounds(phase_id, original_task_id)
            if existing_rounds > 0:
                # 加载上一轮返工任务作为模板
                prev_rework_path = self._get_rework_task_path(phase_id, original_task_id, existing_rounds)
                pkg, _ = self.task_loader.load_file(prev_rework_path)
                if pkg:
                    original_pkg = pkg

        if original_pkg is None:
            return None

        # 确定返工轮次
        existing_rounds = self._get_existing_rework_rounds(phase_id, original_task_id)
        next_round = existing_rounds + 1

        # 检查是否超过最大返工轮次
        if next_round > 2:  # 默认 max_rounds = 2
            return None

        # 生成返工任务 ID
        rework_id = f"{original_task_id}-R{next_round}"

        # 生成返工任务标题
        blocker_count = len(review_artifact.blocker_findings)
        title = f"[Rework R{next_round}] Fix {blocker_count} blockers from review"

        # 构建 findings_ref
        findings_ref = f"../reviews/{original_task_id}-review.md"

        # 构建 inputs（添加 review artifact 作为输入）
        inputs = list(original_pkg.inputs)
        if findings_ref not in inputs:
            inputs.append(findings_ref)

        # 构建 constraints（添加 blocker 信息）
        constraints = list(original_pkg.constraints)
        for finding in review_artifact.blocker_findings:
            constraint = f"Fix blocker: {finding.description}"
            if finding.location:
                constraint += f" ({finding.location})"
            constraints.append(constraint)

        # 创建返工任务包
        rework_context = ReworkContext(
            original_task_id=original_task_id,
            findings_ref=findings_ref,
            rework_round=next_round,
            blocker_count=blocker_count,
            summary=review_artifact.summary,
        )

        rework_pkg = ReworkTaskPackage(
            id=rework_id,
            phase_id=phase_id,
            title=title,
            executor_type=original_pkg.executor_type,
            reviewer_type=original_pkg.reviewer_type,
            inputs=inputs,
            constraints=constraints,
            allowed_write_paths=list(original_pkg.allowed_write_paths),
            acceptance_refs=list(original_pkg.acceptance_refs),
            done_definition=list(original_pkg.done_definition),
            gate_on_complete=original_pkg.gate_on_complete,
            rework_context=rework_context,
            generated_at=datetime.now(timezone.utc).isoformat(),
            priority="high",
        )

        return rework_pkg

    def write(self, rework_pkg: ReworkTaskPackage) -> Path:
        """原子写入返工任务包到 YAML 文件。

        Args:
            rework_pkg: 返工任务包

        Returns:
            写入的文件路径
        """
        target_path = self._get_rework_task_path(
            rework_pkg.phase_id,
            rework_pkg.rework_context.original_task_id,
            rework_pkg.rework_context.rework_round,
        )

        # 确保目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成 YAML 内容
        content = yaml.dump(rework_pkg.to_yaml_dict(), allow_unicode=True, sort_keys=False)

        # 原子写入
        fd, tmp_path = tempfile.mkstemp(
            dir=str(target_path.parent),
            prefix=f".{rework_pkg.id}-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(target_path))
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

        return target_path

    def generate_and_write(
        self,
        review_artifact: ReviewArtifact,
        original_task_id: str,
        phase_id: str,
    ) -> tuple[Optional[ReworkTaskPackage], Optional[Path]]:
        """生成并写入返工任务包。

        Returns:
            (rework_pkg, path) 或 (None, None)
        """
        rework_pkg = self.generate(review_artifact, original_task_id, phase_id)
        if rework_pkg is None:
            return None, None

        path = self.write(rework_pkg)
        return rework_pkg, path

    def get_rework_tasks(self, phase_id: str, original_task_id: str) -> List[ReworkTaskPackage]:
        """获取某任务的所有返工任务。"""
        tasks_dir = self._get_tasks_dir(phase_id)
        rework_tasks = []

        for f in tasks_dir.glob(f"{original_task_id}-R*.yaml"):
            pkg, errors = self.task_loader.load_file(f)
            if pkg and not errors:
                # 从 raw 构建 rework_context
                raw_context = pkg.raw.get("rework_context", {})
                rework_context = ReworkContext(
                    original_task_id=raw_context.get("original_task_id", original_task_id),
                    findings_ref=raw_context.get("findings_ref", ""),
                    rework_round=raw_context.get("rework_round", 1),
                    blocker_count=raw_context.get("blocker_count", 0),
                    summary=raw_context.get("summary"),
                )
                rework_pkg = ReworkTaskPackage(
                    id=pkg.id,
                    phase_id=pkg.phase_id,
                    title=pkg.title,
                    executor_type=pkg.executor_type,
                    reviewer_type=pkg.reviewer_type,
                    inputs=pkg.inputs,
                    constraints=pkg.constraints,
                    allowed_write_paths=pkg.allowed_write_paths,
                    acceptance_refs=pkg.acceptance_refs,
                    done_definition=pkg.done_definition,
                    gate_on_complete=pkg.gate_on_complete,
                    rework_context=rework_context,
                    generated_at=pkg.raw.get("generated_at", ""),
                    priority=pkg.raw.get("priority", "high"),
                    raw=pkg.raw,
                )
                rework_tasks.append(rework_pkg)

        # 按轮次排序
        rework_tasks.sort(key=lambda t: t.rework_context.rework_round)
        return rework_tasks

    def has_rework_tasks(self, phase_id: str, task_id: str) -> bool:
        """检查某任务是否有返工任务。"""
        tasks_dir = self._get_tasks_dir(phase_id)
        return bool(list(tasks_dir.glob(f"{task_id}-R*.yaml")))