"""Snapshot快照层单元测试

TDD开发流程：
1. JSON模板定义（baseline/incremental）
2. Schema验证
3. 存储管理
4. Git绑定
"""

import pytest
import tempfile
import os
import json
from datetime import datetime


class TestBaselineSchema:
    """Baseline JSON模板Schema验证"""

    def test_baseline_required_fields(self):
        """测试：baseline必填字段验证"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager, BaselineSchema

        # 最小有效baseline
        baseline = {
            "snapshot_id": "snap_001",
            "snapshot_type": "baseline",
            "git_commit_hash": "a1b2c3d",
            "timestamp": "2026-04-21T10:30:00Z",
            "milestone": "需求定稿",
            "core_goals": ["目标1", "目标2"],
            "global_constraints": [],
            "architecture_decisions": [],
            "acceptance_criteria": [],
            "dependencies": [],
        }

        # 验证通过
        errors = BaselineSchema.validate(baseline)
        assert errors == []

    def test_baseline_missing_snapshot_id(self):
        """测试：缺少snapshot_id验证失败"""
        from claudeflow.legacy.governance.snapshot import BaselineSchema

        baseline = {
            "snapshot_type": "baseline",
            "git_commit_hash": "a1b2c3d",
            "timestamp": "2026-04-21T10:30:00Z",
        }

        errors = BaselineSchema.validate(baseline)
        assert len(errors) > 0
        assert "snapshot_id" in str(errors)

    def test_baseline_invalid_snapshot_type(self):
        """测试：snapshot_type必须是baseline"""
        from claudeflow.legacy.governance.snapshot import BaselineSchema

        baseline = {
            "snapshot_id": "snap_001",
            "snapshot_type": "invalid_type",
            "git_commit_hash": "a1b2c3d",
            "timestamp": "2026-04-21T10:30:00Z",
        }

        errors = BaselineSchema.validate(baseline)
        assert len(errors) > 0


class TestIncrementalSchema:
    """Incremental JSON模板Schema验证"""

    def test_incremental_required_fields(self):
        """测试：incremental必填字段验证"""
        from claudeflow.legacy.governance.snapshot import IncrementalSchema

        incremental = {
            "snapshot_id": "snap_002",
            "snapshot_type": "incremental",
            "parent_snapshot_id": "snap_001",
            "git_commit_hash": "e4f5g6h",
            "timestamp": "2026-04-21T12:00:00Z",
            "changes": [],
            "acceptance_result": [],
        }

        errors = IncrementalSchema.validate(incremental)
        assert errors == []

    def test_incremental_missing_parent_id(self):
        """测试：incremental缺少parent_snapshot_id"""
        from claudeflow.legacy.governance.snapshot import IncrementalSchema

        incremental = {
            "snapshot_id": "snap_002",
            "snapshot_type": "incremental",
            "git_commit_hash": "e4f5g6h",
            "timestamp": "2026-04-21T12:00:00Z",
        }

        errors = IncrementalSchema.validate(incremental)
        assert len(errors) > 0
        assert "parent_snapshot_id" in str(errors)

    def test_incremental_change_types(self):
        """测试：changes变更类型枚举"""
        from claudeflow.legacy.governance.snapshot import IncrementalSchema

        incremental = {
            "snapshot_id": "snap_002",
            "snapshot_type": "incremental",
            "parent_snapshot_id": "snap_001",
            "git_commit_hash": "e4f5g6h",
            "timestamp": "2026-04-21T12:00:00Z",
            "changes": [
                {
                    "change_type": "add",
                    "target_id": "D001",
                    "new_value": "新决策",
                },
                {
                    "change_type": "update",
                    "target_id": "D002",
                    "old_value": "旧值",
                    "new_value": "新值",
                },
                {
                    "change_type": "delete",
                    "target_id": "D003",
                },
            ],
            "acceptance_result": [],
        }

        errors = IncrementalSchema.validate(incremental)
        assert errors == []


class TestSnapshotStorage:
    """快照存储管理测试"""

    def test_save_snapshot_creates_file(self):
        """测试：保存快照创建JSON文件"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoints", "task_001")
            manager = SnapshotManager(base_dir=tmpdir)

            snapshot_id = manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_001",
                    "snapshot_type": "baseline",
                    "git_commit_hash": "a1b2c3d",
                    "timestamp": "2026-04-21T10:30:00Z",
                    "milestone": "需求定稿",
                    "core_goals": ["目标1"],
                    "global_constraints": [],
                    "architecture_decisions": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                }
            )

            assert snapshot_id == "snap_001"
            # 验证文件存在
            files = os.listdir(checkpoint_dir)
            assert len(files) > 0
            assert files[0].endswith(".json")

    def test_load_snapshot_success(self):
        """测试：加载快照成功"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 先保存
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_001",
                    "snapshot_type": "baseline",
                    "git_commit_hash": "a1b2c3d",
                    "timestamp": "2026-04-21T10:30:00Z",
                    "milestone": "需求定稿",
                    "core_goals": [],
                    "global_constraints": [],
                    "architecture_decisions": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                }
            )

            # 再加载
            loaded = manager.load_snapshot(task_id="task_001", snapshot_id="snap_001")

            assert loaded["snapshot_id"] == "snap_001"
            assert loaded["snapshot_type"] == "baseline"
            assert loaded["git_commit_hash"] == "a1b2c3d"

    def test_load_snapshot_not_found(self):
        """测试：加载不存在的快照返回None"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            loaded = manager.load_snapshot(task_id="task_001", snapshot_id="not_exist")

            assert loaded is None

    def test_get_latest_snapshot(self):
        """测试：获取最新快照"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 保存多个快照
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_001",
                    "snapshot_type": "baseline",
                    "git_commit_hash": "a1b2c3d",
                    "timestamp": "2026-04-21T10:00:00Z",
                    "milestone": "需求定稿",
                    "core_goals": [],
                    "global_constraints": [],
                    "architecture_decisions": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                }
            )
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_002",
                    "snapshot_type": "incremental",
                    "parent_snapshot_id": "snap_001",
                    "git_commit_hash": "e4f5g6h",
                    "timestamp": "2026-04-21T12:00:00Z",
                    "changes": [],
                    "acceptance_result": [],
                }
            )

            # 获取最新
            latest = manager.get_latest_snapshot(task_id="task_001")

            assert latest["snapshot_id"] == "snap_002"

    def test_get_latest_snapshot_empty(self):
        """测试：空任务返回None"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            latest = manager.get_latest_snapshot(task_id="task_empty")

            assert latest is None


class TestGitBinding:
    """Git commit hash绑定测试"""

    def test_get_current_git_hash(self):
        """测试：获取当前Git commit hash"""
        from claudeflow.legacy.governance.snapshot import get_git_commit_hash

        # 在claudeflow项目目录中测试（有git）
        git_hash = get_git_commit_hash("/Users/claw/sandbox/personal/claudeflow")

        # Git hash应该是7位以上的十六进制字符串
        assert git_hash is not None
        assert len(git_hash) >= 7
        assert all(c in "0123456789abcdef" for c in git_hash.lower())

    def test_get_git_hash_no_git_repo(self):
        """测试：无git仓库返回None"""
        from claudeflow.legacy.governance.snapshot import get_git_commit_hash

        with tempfile.TemporaryDirectory() as tmpdir:
            git_hash = get_git_commit_hash(tmpdir)

            assert git_hash is None

    def test_snapshot_auto_git_binding(self):
        """测试：保存快照自动绑定git hash"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager, create_baseline_snapshot

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 创建baseline（自动绑定git）
            snapshot = create_baseline_snapshot(
                task_id="task_001",
                milestone="需求定稿",
                core_goals=["目标1"],
                git_repo_path="/Users/claw/sandbox/personal/claudeflow",
            )

            # 验证git hash已绑定
            assert snapshot["git_commit_hash"] is not None
            assert len(snapshot["git_commit_hash"]) >= 7


class TestSnapshotChain:
    """快照链测试（baseline → incremental）"""

    def test_create_incremental_from_baseline(self):
        """测试：从baseline创建incremental"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager, create_incremental_snapshot

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 保存baseline
            baseline = {
                "snapshot_id": "snap_001",
                "snapshot_type": "baseline",
                "git_commit_hash": "a1b2c3d",
                "timestamp": "2026-04-21T10:00:00Z",
                "milestone": "需求定稿",
                "core_goals": ["目标1"],
                "global_constraints": [],
                "architecture_decisions": [],
                "acceptance_criteria": [],
                "dependencies": [],
            }
            manager.save_snapshot(task_id="task_001", snapshot_dict=baseline)

            # 创建incremental
            incremental = create_incremental_snapshot(
                parent_snapshot_id="snap_001",
                changes=[
                    {
                        "change_type": "update",
                        "target_id": "D001",
                        "old_value": "分层架构",
                        "new_value": "微服务架构",
                        "rationale": "性能提升",
                    }
                ],
                acceptance_result=[{"criteria_id": "AC001", "passed": True}],
                git_repo_path="/Users/claw/sandbox/personal/claudeflow",
            )

            # 验证incremental
            assert incremental["snapshot_type"] == "incremental"
            assert incremental["parent_snapshot_id"] == "snap_001"
            assert len(incremental["changes"]) == 1

    def test_snapshot_chain_traceability(self):
        """测试：快照链可追溯"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 创建快照链：baseline → inc1 → inc2
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_001",
                    "snapshot_type": "baseline",
                    "git_commit_hash": "a1b2c3d",
                    "timestamp": "2026-04-21T10:00:00Z",
                    "milestone": "需求定稿",
                    "core_goals": [],
                    "global_constraints": [],
                    "architecture_decisions": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                }
            )
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_002",
                    "snapshot_type": "incremental",
                    "parent_snapshot_id": "snap_001",
                    "git_commit_hash": "e4f5g6h",
                    "timestamp": "2026-04-21T11:00:00Z",
                    "changes": [],
                    "acceptance_result": [],
                }
            )
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_003",
                    "snapshot_type": "incremental",
                    "parent_snapshot_id": "snap_002",
                    "git_commit_hash": "i7j8k9l",
                    "timestamp": "2026-04-21T12:00:00Z",
                    "changes": [],
                    "acceptance_result": [],
                }
            )

            # 追溯链：snap_003 → snap_002 → snap_001
            chain = manager.get_snapshot_chain(task_id="task_001", snapshot_id="snap_003")

            assert len(chain) == 3
            assert chain[0]["snapshot_id"] == "snap_001"
            assert chain[1]["snapshot_id"] == "snap_002"
            assert chain[2]["snapshot_id"] == "snap_003"


class TestSnapshotManagerExtra:
    """SnapshotManager额外功能测试"""

    def test_list_snapshots(self):
        """测试：列出所有快照ID"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 保存多个快照
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_001",
                    "snapshot_type": "baseline",
                    "git_commit_hash": "a1b2c3d",
                    "timestamp": "2026-04-21T10:00:00Z",
                    "milestone": "需求定稿",
                    "core_goals": [],
                    "global_constraints": [],
                    "architecture_decisions": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                }
            )
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_002",
                    "snapshot_type": "incremental",
                    "parent_snapshot_id": "snap_001",
                    "git_commit_hash": "e4f5g6h",
                    "timestamp": "2026-04-21T11:00:00Z",
                    "changes": [],
                    "acceptance_result": [],
                }
            )

            # 列出快照
            snapshot_ids = manager.list_snapshots(task_id="task_001")

            assert len(snapshot_ids) == 2
            assert "snap_001" in snapshot_ids
            assert "snap_002" in snapshot_ids

    def test_list_snapshots_empty(self):
        """测试：空任务返回空列表"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            snapshot_ids = manager.list_snapshots(task_id="task_empty")

            assert snapshot_ids == []

    def test_delete_snapshot(self):
        """测试：删除快照"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            # 保存快照
            manager.save_snapshot(
                task_id="task_001",
                snapshot_dict={
                    "snapshot_id": "snap_001",
                    "snapshot_type": "baseline",
                    "git_commit_hash": "a1b2c3d",
                    "timestamp": "2026-04-21T10:00:00Z",
                    "milestone": "需求定稿",
                    "core_goals": [],
                    "global_constraints": [],
                    "architecture_decisions": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                }
            )

            # 删除快照
            result = manager.delete_snapshot(task_id="task_001", snapshot_id="snap_001")

            assert result is True
            # 验证文件不存在
            assert manager.load_snapshot(task_id="task_001", snapshot_id="snap_001") is None

    def test_delete_snapshot_not_found(self):
        """测试：删除不存在的快照返回False"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)

            result = manager.delete_snapshot(task_id="task_001", snapshot_id="not_exist")

            assert result is False