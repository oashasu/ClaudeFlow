"""Snapshot快照层核心模块

功能：
1. baseline/incremental JSON模板定义
2. Schema验证（jsonschema）
3. 存储管理（save/load/get_latest）
4. Git commit hash绑定
5. 快照链追溯

设计原则：
- baseline不可修改，incremental仅追加
- 统一UTF-8序列化，JSON Schema强校验
- 绑定Git Commit哈希
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import jsonschema
from jsonschema import validate, ValidationError


# ============ Schema定义 ============

BASELINE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Baseline Snapshot",
    "type": "object",
    "required": [
        "snapshot_id",
        "snapshot_type",
        "git_commit_hash",
        "timestamp",
        "milestone",
        "core_goals",
    ],
    "properties": {
        "snapshot_id": {"type": "string", "minLength": 1},
        "snapshot_type": {"type": "string", "enum": ["baseline"]},
        "git_commit_hash": {"type": "string", "minLength": 7},
        "timestamp": {"type": "string", "format": "date-time"},
        "milestone": {"type": "string", "minLength": 1},
        "core_goals": {
            "type": "array",
            "items": {"type": "string"},
        },
        "global_constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string"},
                    "rule": {"type": "string"},
                    "threshold": {"type": "number"},
                },
            },
        },
        "architecture_decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "decision": {"type": "string"},
                    "rationale": {"type": "string"},
                },
            },
        },
        "acceptance_criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criteria_id": {"type": "string"},
                    "criteria": {"type": "string"},
                    "type": {"type": "string", "enum": ["boolean", "numeric"]},
                },
            },
        },
        "dependencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dep_id": {"type": "string"},
                    "module": {"type": "string"},
                    "version": {"type": "string"},
                },
            },
        },
        "next_phase_boundary": {
            "type": "object",
            "properties": {
                "phase": {"type": "string"},
                "input": {"type": "array", "items": {"type": "string"}},
                "output": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "additionalProperties": False,
}

INCREMENTAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Incremental Snapshot",
    "type": "object",
    "required": [
        "snapshot_id",
        "snapshot_type",
        "parent_snapshot_id",
        "git_commit_hash",
        "timestamp",
    ],
    "properties": {
        "snapshot_id": {"type": "string", "minLength": 1},
        "snapshot_type": {"type": "string", "enum": ["incremental"]},
        "parent_snapshot_id": {"type": "string", "minLength": 1},
        "git_commit_hash": {"type": "string", "minLength": 7},
        "timestamp": {"type": "string", "format": "date-time"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["change_type", "target_id"],
                "properties": {
                    "change_type": {"type": "string", "enum": ["add", "update", "delete"]},
                    "target_id": {"type": "string"},
                    "old_value": {"type": "string"},
                    "new_value": {"type": "string"},
                    "rationale": {"type": "string"},
                },
            },
        },
        "acceptance_result": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criteria_id": {"type": "string"},
                    "passed": {"type": "boolean"},
                },
            },
        },
    },
    "additionalProperties": False,
}


class BaselineSchema:
    """Baseline Schema验证器"""

    @staticmethod
    def validate(data: Dict[str, Any]) -> List[str]:
        """验证baseline数据，返回错误列表"""
        try:
            validate(instance=data, schema=BASELINE_SCHEMA)
            return []
        except ValidationError as e:
            return [str(e.message)]
        except Exception as e:
            return [str(e)]


class IncrementalSchema:
    """Incremental Schema验证器"""

    @staticmethod
    def validate(data: Dict[str, Any]) -> List[str]:
        """验证incremental数据，返回错误列表"""
        try:
            validate(instance=data, schema=INCREMENTAL_SCHEMA)
            return []
        except ValidationError as e:
            return [str(e.message)]
        except Exception as e:
            return [str(e)]


# ============ Git绑定 ============


def get_git_commit_hash(git_repo_path: Optional[str] = None) -> Optional[str]:
    """获取当前Git commit hash

    Args:
        git_repo_path: Git仓库路径，默认当前目录

    Returns:
        Git commit hash（短格式7位），或None（无git仓库）
    """
    try:
        cmd = ["git", "rev-parse", "--short", "HEAD"]
        if git_repo_path:
            result = subprocess.run(
                cmd,
                cwd=git_repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return None


# ============ 快照创建工厂 ============


def _generate_snapshot_id() -> str:
    """生成快照ID（snap_xxxxx格式）"""
    import random
    import string
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"snap_{suffix}"


def _get_timestamp() -> str:
    """获取当前UTC时间戳"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_baseline_snapshot(
    task_id: str,
    milestone: str,
    core_goals: List[str],
    git_repo_path: Optional[str] = None,
    global_constraints: Optional[List[Dict]] = None,
    architecture_decisions: Optional[List[Dict]] = None,
    acceptance_criteria: Optional[List[Dict]] = None,
    dependencies: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """创建baseline快照

    Args:
        task_id: 任务ID
        milestone: 里程碑名称
        core_goals: 核心目标列表
        git_repo_path: Git仓库路径（自动绑定commit hash）
        global_constraints: 全局约束
        architecture_decisions: 架构决策
        acceptance_criteria: 验收标准
        dependencies: 依赖项

    Returns:
        baseline快照字典
    """
    git_hash = get_git_commit_hash(git_repo_path) or "no_git"

    return {
        "snapshot_id": _generate_snapshot_id(),
        "snapshot_type": "baseline",
        "git_commit_hash": git_hash,
        "timestamp": _get_timestamp(),
        "milestone": milestone,
        "core_goals": core_goals,
        "global_constraints": global_constraints or [],
        "architecture_decisions": architecture_decisions or [],
        "acceptance_criteria": acceptance_criteria or [],
        "dependencies": dependencies or [],
    }


def create_incremental_snapshot(
    parent_snapshot_id: str,
    changes: List[Dict[str, Any]],
    acceptance_result: Optional[List[Dict]] = None,
    git_repo_path: Optional[str] = None,
) -> Dict[str, Any]:
    """创建incremental快照

    Args:
        parent_snapshot_id: 父快照ID
        changes: 变更列表
        acceptance_result: 验收结果
        git_repo_path: Git仓库路径

    Returns:
        incremental快照字典
    """
    git_hash = get_git_commit_hash(git_repo_path) or "no_git"

    return {
        "snapshot_id": _generate_snapshot_id(),
        "snapshot_type": "incremental",
        "parent_snapshot_id": parent_snapshot_id,
        "git_commit_hash": git_hash,
        "timestamp": _get_timestamp(),
        "changes": changes,
        "acceptance_result": acceptance_result or [],
    }


# ============ 存储管理 ============


@dataclass
class SnapshotManager:
    """快照存储管理器

    功能：
    - save_snapshot: 写入JSON文件
    - load_snapshot: 读取JSON文件
    - get_latest_snapshot: 获取最新快照
    - get_snapshot_chain: 获取快照链（追溯）

    存储路径：base_dir/checkpoints/{task_id}/
    """

    base_dir: str = field(default_factory=lambda: os.getcwd())

    def _get_task_dir(self, task_id: str) -> Path:
        """获取任务目录"""
        return Path(self.base_dir) / "checkpoints" / task_id

    def save_snapshot(
        self,
        task_id: str,
        snapshot_dict: Dict[str, Any],
    ) -> str:
        """保存快照

        Args:
            task_id: 任务ID
            snapshot_dict: 快照字典

        Returns:
            snapshot_id
        """
        task_dir = self._get_task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        snapshot_id = snapshot_dict["snapshot_id"]
        filename = f"{snapshot_id}.json"
        filepath = task_dir / filename

        # UTF-8序列化
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)

        return snapshot_id

    def load_snapshot(
        self,
        task_id: str,
        snapshot_id: str,
    ) -> Optional[Dict[str, Any]]:
        """加载快照

        Args:
            task_id: 任务ID
            snapshot_id: 快照ID

        Returns:
            快照字典，或None（不存在）
        """
        task_dir = self._get_task_dir(task_id)
        filepath = task_dir / f"{snapshot_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_latest_snapshot(
        self,
        task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取最新快照

        按timestamp排序，返回最新的快照。

        Args:
            task_id: 任务ID

        Returns:
            最新快照字典，或None（无快照）
        """
        task_dir = self._get_task_dir(task_id)

        if not task_dir.exists():
            return None

        # 收集所有快照
        snapshots = []
        for filepath in task_dir.glob("*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                snapshots.append(json.load(f))

        if not snapshots:
            return None

        # 按timestamp排序（最新优先）
        snapshots.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
        return snapshots[0]

    def get_snapshot_chain(
        self,
        task_id: str,
        snapshot_id: str,
    ) -> List[Dict[str, Any]]:
        """获取快照链（追溯）

        从指定snapshot_id追溯所有父快照，直到baseline。

        Args:
            task_id: 任务ID
            snapshot_id: 起始快照ID

        Returns:
            快照链列表（从baseline到目标）
        """
        chain = []
        current_id = snapshot_id

        while current_id:
            snapshot = self.load_snapshot(task_id, current_id)
            if not snapshot:
                break

            chain.append(snapshot)

            # 如果是baseline，追溯结束
            if snapshot.get("snapshot_type") == "baseline":
                break

            # 继续追溯父快照
            current_id = snapshot.get("parent_snapshot_id")

        # 反转顺序：baseline在最前
        chain.reverse()
        return chain

    def list_snapshots(self, task_id: str) -> List[str]:
        """列出所有快照ID

        Args:
            task_id: 任务ID

        Returns:
            快照ID列表
        """
        task_dir = self._get_task_dir(task_id)

        if not task_dir.exists():
            return []

        return [f.stem for f in task_dir.glob("*.json")]

    def delete_snapshot(
        self,
        task_id: str,
        snapshot_id: str,
    ) -> bool:
        """删除快照

        Args:
            task_id: 任务ID
            snapshot_id: 快照ID

        Returns:
            是否删除成功
        """
        task_dir = self._get_task_dir(task_id)
        filepath = task_dir / f"{snapshot_id}.json"

        if not filepath.exists():
            return False

        filepath.unlink()
        return True