"""T302: Action Audit 测试

验证审计记录存储、查询与 API 端点。
"""

import pytest
import tempfile
import os
from pathlib import Path

from claudeflow.runtime.action_audit import (
    ActionAuditRecord,
    ActionAuditStore,
    create_audit_record,
)


class TestActionAuditRecord:
    """测试审计记录模型"""

    def test_create_intervene_record(self):
        record = create_audit_record(
            action_type="intervene",
            target_task_id="task-001",
            target_session_id="sess-001",
            success=True,
            message="干预成功",
            prompt="请继续实现",
        )
        assert record.action_type == "intervene"
        assert record.target_task_id == "task-001"
        assert record.target_session_id == "sess-001"
        assert record.success is True
        assert record.prompt == "请继续实现"
        assert record.action_id.startswith("audit-")

    def test_create_complete_record(self):
        record = create_audit_record(
            action_type="complete",
            target_task_id="task-002",
            success=True,
            message="任务完成",
            summary="实现完成",
            changed_files=["src/main.py"],
            test_status="passed",
            test_count=10,
        )
        assert record.action_type == "complete"
        assert record.summary == "实现完成"
        assert record.changed_files == ["src/main.py"]
        assert record.test_count == 10

    def test_create_fail_record(self):
        record = create_audit_record(
            action_type="fail",
            target_task_id="task-003",
            success=False,
            message="任务失败",
            reason="依赖阻塞",
        )
        assert record.action_type == "fail"
        assert record.success is False
        assert record.reason == "依赖阻塞"


class TestActionAuditStore:
    """测试审计记录存储"""

    def test_write_and_list_records(self, tmp_path: Path):
        store = ActionAuditStore(governance_root=str(tmp_path))

        # 写入三条记录
        r1 = create_audit_record("intervene", "task-001", success=True, message="干预成功")
        r2 = create_audit_record("complete", "task-002", success=True, message="完成成功")
        r3 = create_audit_record("fail", "task-003", success=False, message="失败")

        store.write_record(r1)
        store.write_record(r2)
        store.write_record(r3)

        # 查询列表
        records = store.list_records()
        assert len(records) == 3
        # 按时间倒序
        assert records[0].action_id == r3.action_id

    def test_list_records_by_action_type(self, tmp_path: Path):
        store = ActionAuditStore(governance_root=str(tmp_path))

        r1 = create_audit_record("intervene", "task-001", success=True, message="干预")
        r2 = create_audit_record("complete", "task-002", success=True, message="完成")
        r3 = create_audit_record("intervene", "task-003", success=True, message="干预2")

        store.write_record(r1)
        store.write_record(r2)
        store.write_record(r3)

        # 按类型过滤
        intervene_records = store.list_records(action_type="intervene")
        assert len(intervene_records) == 2

        complete_records = store.list_records(action_type="complete")
        assert len(complete_records) == 1

    def test_list_records_by_task_id(self, tmp_path: Path):
        store = ActionAuditStore(governance_root=str(tmp_path))

        r1 = create_audit_record("intervene", "task-001", success=True, message="干预")
        r2 = create_audit_record("complete", "task-001", success=True, message="完成")
        r3 = create_audit_record("fail", "task-002", success=False, message="失败")

        store.write_record(r1)
        store.write_record(r2)
        store.write_record(r3)

        # 按任务 ID 过滤
        task1_records = store.list_records(target_task_id="task-001")
        assert len(task1_records) == 2

        task2_records = store.list_records(target_task_id="task-002")
        assert len(task2_records) == 1

    def test_get_record_by_id(self, tmp_path: Path):
        store = ActionAuditStore(governance_root=str(tmp_path))

        r1 = create_audit_record("intervene", "task-001", success=True, message="干预")
        store.write_record(r1)

        # 查询单条
        found = store.get_record(r1.action_id)
        assert found is not None
        assert found.action_id == r1.action_id
        assert found.target_task_id == "task-001"

        # 查询不存在的
        not_found = store.get_record("audit-nonexistent")
        assert not_found is None

    def test_clear_records(self, tmp_path: Path):
        store = ActionAuditStore(governance_root=str(tmp_path))

        r1 = create_audit_record("intervene", "task-001", success=True, message="干预")
        store.write_record(r1)

        assert len(store.list_records()) == 1

        store.clear_records()
        assert len(store.list_records()) == 0

    def test_limit_records(self, tmp_path: Path):
        store = ActionAuditStore(governance_root=str(tmp_path))

        # 写入 20 条记录
        for i in range(20):
            store.write_record(create_audit_record("intervene", f"task-{i}", success=True, message=f"干预{i}"))

        # 限制数量
        records = store.list_records(limit=5)
        assert len(records) == 5
        # 应该是最新的 5 条
        assert records[0].target_task_id == "task-19"


class TestActionAuditStoreWithoutGovernance:
    """测试无 governance_root 的存储"""

    def test_default_audit_dir(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["CLAUDEFLOW_AUDIT_DIR"] = tmp_dir
            store = ActionAuditStore()

            r1 = create_audit_record("intervene", "task-001", success=True, message="干预")
            store.write_record(r1)

            records = store.list_records()
            assert len(records) == 1

            del os.environ["CLAUDEFLOW_AUDIT_DIR"]