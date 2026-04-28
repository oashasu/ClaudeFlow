"""T303: Runtime Schema 验证测试

验证 examples/*.schema.json 与 API 输出一致。
"""

import json
import pytest
from pathlib import Path

try:
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SCHEMA_DIR = Path(__file__).parent.parent.parent / "examples"


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema 未安装")
class TestRuntimePlanSchema:
    """验证 runtime-plan.schema.json"""

    def test_schema_exists(self):
        schema_path = SCHEMA_DIR / "runtime-plan.schema.json"
        assert schema_path.exists()

    def test_sample_matches_schema(self):
        schema_path = SCHEMA_DIR / "runtime-plan.schema.json"
        sample_path = SCHEMA_DIR / "runtime-plan.sample.json"

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        validate(instance=sample, schema=schema)

    def test_valid_plan_matches_schema(self):
        """A34: API 输出格式验证"""
        schema_path = SCHEMA_DIR / "runtime-plan.schema.json"
        schema = json.loads(schema_path.read_text())

        valid_plan = {
            "runnable": [
                {"task_id": "t1", "priority": "high", "owner_role": "agent", "task_type": "ImplementTask"}
            ],
            "blocked": [
                {"task_id": "t2", "priority": "medium", "reason_code": "waiting", "reason": "blocked"}
            ],
            "running": []
        }

        validate(instance=valid_plan, schema=schema)

    def test_missing_runnable_fails(self):
        """A34: 缺少 runnable 必须失败"""
        schema_path = SCHEMA_DIR / "runtime-plan.schema.json"
        schema = json.loads(schema_path.read_text())

        invalid_plan = {"blocked": [], "running": []}

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_plan, schema=schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema 未安装")
class TestRuntimeStatusSchema:
    """验证 runtime-status.schema.json"""

    def test_schema_exists(self):
        schema_path = SCHEMA_DIR / "runtime-status.schema.json"
        assert schema_path.exists()

    def test_sample_matches_schema(self):
        schema_path = SCHEMA_DIR / "runtime-status.schema.json"
        sample_path = SCHEMA_DIR / "runtime-status.sample.json"

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        validate(instance=sample, schema=schema)

    def test_valid_status_matches_schema(self):
        """A34: API 输出格式验证"""
        schema_path = SCHEMA_DIR / "runtime-status.schema.json"
        schema = json.loads(schema_path.read_text())

        valid_status = {
            "repo_path": "/tmp/repo",
            "active_agents": 2,
            "queued_tasks": 5,
            "completed_tasks": 10,
            "failed_tasks": 1,
            "intervention_required": True,
            "running_tasks": ["t1"]
        }

        validate(instance=valid_status, schema=schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema 未安装")
class TestRuntimeSessionsSchema:
    """验证 runtime-sessions.schema.json"""

    def test_schema_exists(self):
        schema_path = SCHEMA_DIR / "runtime-sessions.schema.json"
        assert schema_path.exists()

    def test_sample_matches_schema(self):
        schema_path = SCHEMA_DIR / "runtime-sessions.schema.json"
        sample_path = SCHEMA_DIR / "runtime-sessions.sample.json"

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        validate(instance=sample, schema=schema)

    def test_valid_session_matches_schema(self):
        """A34: API 输出格式验证"""
        schema_path = SCHEMA_DIR / "runtime-sessions.schema.json"
        schema = json.loads(schema_path.read_text())

        valid_sessions = [
            {"task_id": "t1", "session_id": "s1", "status": "running", "priority": "high"}
        ]

        validate(instance=valid_sessions, schema=schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema 未安装")
class TestRuntimeEventsSchema:
    """验证 runtime-events.schema.json"""

    def test_schema_exists(self):
        schema_path = SCHEMA_DIR / "runtime-events.schema.json"
        assert schema_path.exists()

    def test_sample_matches_schema(self):
        schema_path = SCHEMA_DIR / "runtime-events.schema.json"
        sample_path = SCHEMA_DIR / "runtime-events.sample.json"

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        validate(instance=sample, schema=schema)

    def test_valid_events_matches_schema(self):
        """A34: API 输出格式验证"""
        schema_path = SCHEMA_DIR / "runtime-events.schema.json"
        schema = json.loads(schema_path.read_text())

        valid_events = {
            "session_id": "s1",
            "events_count": 1,
            "parsed_events": [{"type": "thinking", "text": "x"}],
            "raw_events": []
        }

        validate(instance=valid_events, schema=schema)

    def test_invalid_event_type_fails(self):
        """A34: 无效 event type 必须失败"""
        schema_path = SCHEMA_DIR / "runtime-events.schema.json"
        schema = json.loads(schema_path.read_text())

        invalid_events = {
            "session_id": "s1",
            "events_count": 1,
            "parsed_events": [{"type": "invalid_type"}],
            "raw_events": []
        }

        with pytest.raises(JsonSchemaValidationError):
            validate(instance=invalid_events, schema=schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema 未安装")
class TestRuntimeDispatchSchema:
    """验证 runtime-dispatch.schema.json"""

    def test_schema_exists(self):
        schema_path = SCHEMA_DIR / "runtime-dispatch.schema.json"
        assert schema_path.exists()

    def test_sample_matches_schema(self):
        schema_path = SCHEMA_DIR / "runtime-dispatch.schema.json"
        sample_path = SCHEMA_DIR / "runtime-dispatch.sample.json"

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        validate(instance=sample, schema=schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema 未安装")
class TestRuntimeExplainSchema:
    """验证 runtime-explain.schema.json"""

    def test_schema_exists(self):
        schema_path = SCHEMA_DIR / "runtime-explain.schema.json"
        assert schema_path.exists()

    def test_sample_matches_schema(self):
        schema_path = SCHEMA_DIR / "runtime-explain.schema.json"
        sample_path = SCHEMA_DIR / "runtime-explain.sample.json"

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        validate(instance=sample, schema=schema)


class TestSchemaFilesExist:
    """A34: 所有必需 schema 文件存在"""

    def test_all_schema_files_exist(self):
        required_schemas = [
            "runtime-plan.schema.json",
            "runtime-dispatch.schema.json",
            "runtime-explain.schema.json",
            "runtime-status.schema.json",
            "runtime-sessions.schema.json",
            "runtime-events.schema.json",
        ]

        for name in required_schemas:
            path = SCHEMA_DIR / name
            assert path.exists(), f"{name} 不存在"

    def test_all_sample_files_exist(self):
        required_samples = [
            "runtime-plan.sample.json",
            "runtime-dispatch.sample.json",
            "runtime-explain.sample.json",
            "runtime-status.sample.json",
            "runtime-sessions.sample.json",
            "runtime-events.sample.json",
        ]

        for name in required_samples:
            path = SCHEMA_DIR / name
            assert path.exists(), f"{name} 不存在"