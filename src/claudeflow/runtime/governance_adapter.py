"""GovernanceRuntimeAdapter — 治理任务包到 runtime 的适配链。

T104 实现:
- 读取 TaskPackage YAML
- 生成 RuntimeTaskSpec
- 映射 executor_type / write_paths / acceptance_refs / constraints
- 打通 governance → runtime 主链
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from claudeflow.governance.task_loader import TaskPackage, TaskPackageLoader, TaskPackageError
from claudeflow.runtime.driver_base import RuntimeTaskSpec


class GovernanceRuntimeAdapterError:
    """适配错误。"""

    def __init__(
        self,
        error_type: str,
        file_path: str,
        reason: str,
    ) -> None:
        self.error_type = error_type
        self.file_path = file_path
        self.reason = reason

    def to_dict(self) -> Dict[str, str]:
        return {
            "error_type": self.error_type,
            "file_path": self.file_path,
            "reason": self.reason,
        }


class GovernanceRuntimeAdapter:
    """治理任务包到 Runtime 的适配器。

    负责将 .super-dev/phases/phase-1/tasks/*.yaml 转换为
    RuntimeTaskSpec，让 runtime 可以直接派发执行。

    映射规则（按 spec.md 定义）:
    - id -> task_id
    - phase_id -> phase_id
    - executor_type -> executor_type
    - inputs -> read_paths/document_refs
    - allowed_write_paths -> write_paths
    - constraints -> constraints
    - acceptance_refs -> acceptance_refs
    """

    def __init__(self, task_loader: Optional[TaskPackageLoader] = None) -> None:
        self._loader = task_loader or TaskPackageLoader()

    def load_task_package(
        self,
        yaml_path: str | Path,
    ) -> tuple[Optional[RuntimeTaskSpec], List[GovernanceRuntimeAdapterError]]:
        """从单个任务包 YAML 文件生成 RuntimeTaskSpec。

        Args:
            yaml_path: 任务包 YAML 文件路径

        Returns:
            (RuntimeTaskSpec 或 None, 错误列表)
        """
        pkg, errors = self._loader.load_file(yaml_path)

        if errors:
            adapter_errors = [
                GovernanceRuntimeAdapterError(
                    error_type=e.error_type,
                    file_path=e.file_path,
                    reason=e.reason,
                )
                for e in errors
            ]
            return None, adapter_errors

        if pkg is None:
            return None, [
                GovernanceRuntimeAdapterError(
                    error_type="parse_failed",
                    file_path=str(yaml_path),
                    reason="任务包解析返回空结果",
                )
            ]

        return self._convert_package_to_spec(pkg), []

    def load_phase_tasks(
        self,
        governance_root: str | Path,
        phase_id: str,
    ) -> tuple[List[RuntimeTaskSpec], List[GovernanceRuntimeAdapterError]]:
        """加载指定阶段的所有任务包并转换为 RuntimeTaskSpec。

        Args:
            governance_root: .super-dev 根目录
            phase_id: 阶段 ID（如 "phase-1"）

        Returns:
            (RuntimeTaskSpec 列表, 错误列表)
        """
        tasks_dir = Path(governance_root) / "phases" / phase_id / "tasks"

        if not tasks_dir.is_dir():
            return [], [
                GovernanceRuntimeAdapterError(
                    error_type="tasks_dir_not_found",
                    file_path=str(tasks_dir),
                    reason=f"阶段 {phase_id} 的任务目录不存在",
                )
            ]

        packages, errors = self._loader.load_directory(tasks_dir)

        adapter_errors = [
            GovernanceRuntimeAdapterError(
                error_type=e.error_type,
                file_path=e.file_path,
                reason=e.reason,
            )
            for e in errors
        ]

        specs: List[RuntimeTaskSpec] = []
        for pkg in packages:
            spec = self._convert_package_to_spec(pkg)
            specs.append(spec)

        return specs, adapter_errors

    def _convert_package_to_spec(self, pkg: TaskPackage) -> RuntimeTaskSpec:
        """将 TaskPackage 转换为 RuntimeTaskSpec。

        映射规则:
        - id -> task_id
        - phase_id -> phase_id
        - executor_type -> executor_type
        - inputs -> read_paths + document_refs（分离）
        - allowed_write_paths -> write_paths
        - constraints -> constraints
        - acceptance_refs -> acceptance_refs
        - title -> prompt（可被 override）
        - priority -> priority（从 raw 提取）
        """
        read_paths: List[str] = []
        document_refs: List[str] = []

        for input_ref in pkg.inputs:
            input_str = str(input_ref)
            if input_str.endswith(".md") or input_str.endswith(".yaml"):
                document_refs.append(input_str)
            else:
                read_paths.append(input_str)

        prompt = pkg.raw.get("prompt", pkg.title)
        priority = pkg.raw.get("priority", "medium")

        return RuntimeTaskSpec(
            task_id=pkg.id,
            phase_id=pkg.phase_id,
            executor_type=pkg.executor_type,
            prompt=prompt,
            read_paths=read_paths,
            write_paths=list(pkg.allowed_write_paths),
            constraints=list(pkg.constraints),
            acceptance_refs=list(pkg.acceptance_refs),
            document_refs=document_refs,
            priority=priority,
        )

    def validate_executor_type(
        self,
        spec: RuntimeTaskSpec,
        supported_types: List[str],
    ) -> tuple[bool, str]:
        """校验 RuntimeTaskSpec 的 executor_type 是否在支持列表中。

        Args:
            spec: 运行时任务规格
            supported_types: 支持的 executor_type 列表

        Returns:
            (是否有效, reason_code)
        """
        if spec.executor_type not in supported_types:
            return False, "unsupported_executor_type"

        if spec.executor_type == "future":
            return False, "future_executor_not_dispatchable"

        return True, ""

    def build_dispatch_input(
        self,
        spec: RuntimeTaskSpec,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建派发输入对象（用于 runtime dispatch）。

        Args:
            spec: 运行时任务规格
            cwd: 工作目录

        Returns:
            结构化派发输入
        """
        return {
            "task_id": spec.task_id,
            "phase_id": spec.phase_id,
            "executor_type": spec.executor_type,
            "prompt": spec.prompt,
            "read_paths": list(spec.read_paths),
            "write_paths": list(spec.write_paths),
            "constraints": list(spec.constraints),
            "acceptance_refs": list(spec.acceptance_refs),
            "document_refs": list(spec.document_refs),
            "priority": spec.priority,
            "cwd": cwd,
        }