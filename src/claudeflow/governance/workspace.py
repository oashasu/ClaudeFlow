"""T001: GovernanceWorkspace — .super-dev/ 目录初始化。

职责:
- 初始化 .super-dev/ 目录结构
- 返回关键路径
- 幂等：重复执行不破坏已有内容
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WORKFLOW_MD = """\
# Workflow State

This file tracks the current Super Dev workflow state.
Governor hosts write governance decisions here; ClaudeFlow reads them.
"""

DEFAULT_PIPELINE_STATE = {
    "workflow_version": "1",
    "current_phase": "drafting",
    "current_stage": "",
    "current_gate": "",
    "gate_status": "open",
    "governor": {"host": ""},
    "advance_allowed": False,
    "reopen_required": False,
    "tasks": [],
    "timestamps": {"updated_at": ""},
}

DEFAULT_ROLES_YAML = """\
# Roles configuration for governance
roles: []
"""


@dataclass(frozen=True)
class WorkspacePaths:
    """治理工作区关键路径。"""

    root: Path
    workflow_md: Path
    pipeline_state: Path
    roles_yaml: Path
    phases_dir: Path


class GovernanceWorkspace:
    """治理工作区初始化器。"""

    DIR_NAME = ".super-dev"

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve()
        self._paths = WorkspacePaths(
            root=self.project_root / self.DIR_NAME,
            workflow_md=self.project_root / self.DIR_NAME / "WORKFLOW.md",
            pipeline_state=self.project_root / self.DIR_NAME / "pipeline-state.json",
            roles_yaml=self.project_root / self.DIR_NAME / "roles.yaml",
            phases_dir=self.project_root / self.DIR_NAME / "phases",
        )

    @property
    def paths(self) -> WorkspacePaths:
        return self._paths

    def initialize(self) -> WorkspacePaths:
        """初始化治理工作区，幂等执行。

        - 缺失目录自动补齐
        - 已存在文件不覆盖
        - 重复执行不报错
        """
        self._paths.root.mkdir(parents=True, exist_ok=True)
        self._paths.phases_dir.mkdir(parents=True, exist_ok=True)

        if not self._paths.workflow_md.exists():
            self._paths.workflow_md.write_text(DEFAULT_WORKFLOW_MD, encoding="utf-8")

        if not self._paths.pipeline_state.exists():
            self._write_json(self._paths.pipeline_state, DEFAULT_PIPELINE_STATE)

        if not self._paths.roles_yaml.exists():
            self._paths.roles_yaml.write_text(DEFAULT_ROLES_YAML, encoding="utf-8")

        return self._paths

    def is_initialized(self) -> bool:
        return self._paths.root.is_dir()

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
