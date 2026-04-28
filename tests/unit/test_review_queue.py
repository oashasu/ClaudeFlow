"""T202: Review Queue — Worker 结果回收到 review-ready 状态测试。

验收标准 A22:
- Worker 结果回收后进入 submitted 或 under_review
- pipeline-state.json 可见状态变化

关键约束:
- 必须回写 pipeline-state.json
- 不得绕开现有 RuntimeManager 结果回收路径
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from claudeflow.governance.review_queue import (
    ReviewQueue,
    ReviewQueueEntry,
    ReviewQueueIndex,
)
from claudeflow.governance.pipeline_state import PipelineStateStore


@pytest.fixture
def tmp_governance_root(tmp_path):
    """创建临时治理根目录。"""
    root = tmp_path / ".super-dev"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def review_queue(tmp_governance_root):
    """创建 ReviewQueue。"""
    return ReviewQueue(tmp_governance_root)


@pytest.fixture
def pipeline_state_file(tmp_governance_root):
    """创建有效的 pipeline-state.json。"""
    state_path = tmp_governance_root / "pipeline-state.json"
    state_data = {
        "workflow_version": "v1",
        "project": "test-project",
        "current_phase": "phase-1",
        "current_stage": "in_execution",
        "current_gate": "",
        "gate_status": "open",
        "governor": {"host": "codex", "mode": "governor"},
        "advance_allowed": False,
        "reopen_required": False,
        "phases": {
            "phase-1": {
                "status": "in_execution",
                "docs_ready": True,
                "tasks_ready": True,
                "quality_gate_passed": False,
                "completed_tasks": [],
                "pending_tasks": ["T101"],
            }
        },
        "tasks": {
            "T101": {
                "phase_id": "phase-1",
                "executor_type": "claude",
                "status": "implementing",
                "review_status": "pending",
            }
        },
        "timestamps": {"updated_at": "2026-01-01T00:00:00Z"},
        "commits": {},
    }
    state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    return state_path


class TestReviewQueueEntry:
    """ReviewQueueEntry 数据结构测试。"""

    def test_entry_creation(self):
        entry = ReviewQueueEntry(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            status="submitted",
            submitted_at="2026-01-01T12:00:00Z",
        )
        assert entry.task_id == "T101"
        assert entry.status == "submitted"

    def test_entry_with_result_data(self):
        entry = ReviewQueueEntry(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            status="submitted",
            submitted_at="2026-01-01T12:00:00Z",
            summary="Implementation complete",
            changed_files=["src/main.py", "tests/test_main.py"],
            tests={"passed": 10, "failed": 0},
            known_issues=["Minor style issue"],
            test_evidence=["pytest output"],
            driver_name="claude-driver",
            worktree="/path/to/worktree",
        )
        assert entry.summary == "Implementation complete"
        assert len(entry.changed_files) == 2

    def test_entry_to_dict(self):
        entry = ReviewQueueEntry(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            status="submitted",
            submitted_at="2026-01-01T12:00:00Z",
            summary="Done",
        )
        d = entry.to_dict()
        assert d["task_id"] == "T101"
        assert d["summary"] == "Done"


class TestReviewQueueIndex:
    """ReviewQueueIndex 测试。"""

    def test_empty_index(self):
        index = ReviewQueueIndex()
        assert len(index.entries) == 0

    def test_index_with_entries(self):
        entry1 = ReviewQueueEntry(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            status="submitted",
            submitted_at="2026-01-01T12:00:00Z",
        )
        entry2 = ReviewQueueEntry(
            task_id="T102",
            phase_id="phase-1",
            executor_type="claude",
            status="submitted",
            submitted_at="2026-01-01T12:00:00Z",
        )
        index = ReviewQueueIndex(entries=[entry1, entry2])
        assert len(index.entries) == 2

    def test_index_to_dict(self):
        entry = ReviewQueueEntry(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            status="submitted",
            submitted_at="2026-01-01T12:00:00Z",
        )
        index = ReviewQueueIndex(entries=[entry], updated_at="2026-01-01T12:00:00Z")
        d = index.to_dict()
        assert "entries" in d
        assert len(d["entries"]) == 1


class TestReviewQueue:
    """ReviewQueue 主功能测试。"""

    def test_submit_result_creates_entry(self, review_queue, pipeline_state_file):
        entry = review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            summary="Task completed successfully",
            changed_files=["src/main.py"],
        )
        assert entry.task_id == "T101"
        assert entry.status == "submitted"
        assert entry.summary == "Task completed successfully"

    def test_submit_result_updates_pipeline_state(self, review_queue, pipeline_state_file):
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            summary="Done",
        )

        # 验证 pipeline-state.json 已更新
        store = PipelineStateStore(pipeline_state_file)
        state, errors = store.load()
        assert not errors
        assert state.raw["tasks"]["T101"]["status"] == "submitted"
        assert state.raw["tasks"]["T101"]["review_status"] == "pending"

    def test_submit_result_creates_queue_file(self, review_queue, tmp_governance_root):
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
        )

        queue_path = tmp_governance_root / "review-queue.json"
        assert queue_path.exists()

        # 验证内容
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
        assert len(raw["entries"]) == 1
        assert raw["entries"][0]["task_id"] == "T101"

    def test_submit_from_runtime_result(self, review_queue, pipeline_state_file):
        runtime_result = {
            "task_id": "T101",
            "success": True,
            "executor_type": "claude",
            "driver_name": "claude-driver",
            "summary": "All tests passed",
            "changed_files": ["src/api.py", "tests/test_api.py"],
            "tests": {"passed": 20, "failed": 0},
            "known_issues": [],
            "test_evidence": ["pytest-report.txt"],
        }

        entry = review_queue.submit_from_runtime_result(
            runtime_result=runtime_result,
            phase_id="phase-1",
            worktree="/worktrees/T101",
        )

        assert entry.task_id == "T101"
        assert entry.summary == "All tests passed"
        assert len(entry.changed_files) == 2
        assert entry.driver_name == "claude-driver"
        assert entry.worktree == "/worktrees/T101"

    def test_get_pending_reviews(self, review_queue, pipeline_state_file):
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
        )
        review_queue.submit_result(
            task_id="T102",
            phase_id="phase-1",
            executor_type="claude",
        )

        pending = review_queue.get_pending_reviews()
        assert len(pending) == 2
        task_ids = [e.task_id for e in pending]
        assert "T101" in task_ids
        assert "T102" in task_ids

    def test_get_entry(self, review_queue, pipeline_state_file):
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            summary="Task 101 done",
        )

        entry = review_queue.get_entry("T101")
        assert entry is not None
        assert entry.summary == "Task 101 done"

    def test_get_entry_not_found(self, review_queue):
        entry = review_queue.get_entry("NONEXISTENT")
        assert entry is None

    def test_mark_under_review(self, review_queue, pipeline_state_file):
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
        )

        entry = review_queue.mark_under_review("T101")
        assert entry is not None
        assert entry.status == "under_review"

        # 验证 pipeline-state 也更新了
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["tasks"]["T101"]["review_status"] == "in_review"

    def test_remove_from_queue(self, review_queue, pipeline_state_file):
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
        )

        result = review_queue.remove_from_queue("T101")
        assert result

        pending = review_queue.get_pending_reviews()
        assert len(pending) == 0

    def test_remove_nonexistent(self, review_queue):
        result = review_queue.remove_from_queue("NONEXISTENT")
        assert not result


class TestA22Acceptance:
    """A22 验收测试：结果进入待审查状态。"""

    def test_A22_result_enters_submitted_status(self, review_queue, pipeline_state_file):
        """A22 验收：Worker 结果回收后进入 submitted 状态。"""
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            summary="Implementation complete",
        )

        # 验证 pipeline-state.json 中任务状态
        store = PipelineStateStore(pipeline_state_file)
        state, errors = store.load()
        assert not errors
        assert state.raw["tasks"]["T101"]["status"] == "submitted"

    def test_A22_pipeline_state_visible(self, review_queue, pipeline_state_file):
        """A22 验收：pipeline-state.json 可见状态变化。"""
        # 提交结果
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            changed_files=["src/main.py"],
            tests={"passed": 10},
        )

        # 直接读取文件验证
        raw_state = json.loads(pipeline_state_file.read_text(encoding="utf-8"))

        # 状态可见
        assert raw_state["tasks"]["T101"]["status"] == "submitted"
        assert raw_state["tasks"]["T101"]["review_status"] == "pending"

        # 结果数据可见
        assert "changed_files" in raw_state["tasks"]["T101"]
        assert "tests" in raw_state["tasks"]["T101"]

    def test_A22_under_review_transition(self, review_queue, pipeline_state_file):
        """A22 验收：状态可从 submitted 转换到 under_review。"""
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
        )

        review_queue.mark_under_review("T101")

        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["tasks"]["T101"]["review_status"] == "in_review"

    def test_A22_multiple_phase_tasks(self, review_queue, tmp_governance_root):
        """A22 验收：多 phase 多任务可独立管理。"""
        # 创建 phase-1 和 phase-2 的 pipeline state
        state_path = tmp_governance_root / "pipeline-state.json"
        state_data = {
            "workflow_version": "v1",
            "project": "test",
            "current_phase": "phase-1",
            "current_stage": "implementation_review",
            "current_gate": "implementation_review",
            "gate_status": "open",
            "governor": {"host": "codex", "mode": "governor"},
            "advance_allowed": False,
            "reopen_required": False,
            "phases": {
                "phase-1": {"status": "implementation_review", "pending_tasks": ["T101"]},
                "phase-2": {"status": "implementation_review", "pending_tasks": ["T201"]},
            },
            "tasks": {
                "T101": {"phase_id": "phase-1", "executor_type": "claude", "status": "implementing"},
                "T201": {"phase_id": "phase-2", "executor_type": "claude", "status": "implementing"},
            },
            "timestamps": {"updated_at": ""},
        }
        state_path.write_text(json.dumps(state_data), encoding="utf-8")

        # 提交两个任务
        review_queue.submit_result(task_id="T101", phase_id="phase-1", executor_type="claude")
        review_queue.submit_result(task_id="T201", phase_id="phase-2", executor_type="claude")

        # 验证两个任务都在队列中
        pending = review_queue.get_pending_reviews()
        assert len(pending) == 2


class TestReviewQueuePersistence:
    """Review Queue 持久化测试。"""

    def test_queue_survives_reload(self, tmp_governance_root, pipeline_state_file):
        """队列数据在重新加载后保持。"""
        queue1 = ReviewQueue(tmp_governance_root)
        queue1.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
            summary="First task",
        )

        # 创建新实例加载同一队列
        queue2 = ReviewQueue(tmp_governance_root)
        entry = queue2.get_entry("T101")
        assert entry is not None
        assert entry.summary == "First task"

    def test_queue_file_format_valid(self, review_queue, tmp_governance_root):
        """队列文件格式正确可解析。"""
        review_queue.submit_result(
            task_id="T101",
            phase_id="phase-1",
            executor_type="claude",
        )

        queue_path = tmp_governance_root / "review-queue.json"
        raw = json.loads(queue_path.read_text(encoding="utf-8"))

        # 验证结构
        assert "entries" in raw
        assert "updated_at" in raw
        assert isinstance(raw["entries"], list)