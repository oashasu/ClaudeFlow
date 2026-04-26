"""CLI接口模块单元测试

CLI命令：task create/list/show、status --all/--task
"""

import json
import pytest
import tempfile
from io import StringIO
import sys


class TestCliTaskCreate:
    """CLI任务创建命令测试"""

    def test_cli_task_create_success(self):
        """测试：CLI创建任务成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 模拟命令行参数
            result = cli.run(["task", "create", "--name", "测试任务", "--domain", "AT_支付域"])

            assert result.success == True
            assert "task_" in result.output

    def test_cli_task_create_with_priority(self):
        """测试：CLI创建任务指定优先级"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            result = cli.run([
                "task", "create",
                "--name", "高优先级任务",
                "--domain", "AT_支付域",
                "--priority", "高"
            ])

            assert result.success == True

    def test_cli_task_create_missing_name(self):
        """测试：CLI创建任务缺少名称"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            result = cli.run(["task", "create", "--domain", "AT_支付域"])

            assert result.success == False
            assert "name" in result.error.lower()


class TestCliTaskList:
    """CLI任务列表命令测试"""

    def test_cli_task_list_empty(self):
        """测试：CLI空任务列表"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            result = cli.run(["task", "list"])

            assert result.success == True
            assert "无任务" in result.output or result.output == ""

    def test_cli_task_list_with_tasks(self):
        """测试：CLI显示任务列表"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 先创建任务
            cli.run(["task", "create", "--name", "任务1", "--domain", "AT_支付域"])
            cli.run(["task", "create", "--name", "任务2", "--domain", "DA_订单域"])

            # 列出任务
            result = cli.run(["task", "list"])

            assert result.success == True
            assert "任务1" in result.output
            assert "任务2" in result.output

    def test_cli_task_list_with_status_filter(self):
        """测试：CLI按状态过滤任务列表"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            cli.run(["task", "create", "--name", "任务", "--domain", "AT_支付域"])

            result = cli.run(["task", "list", "--status", "pending"])

            assert result.success == True


class TestCliTaskShow:
    """CLI任务详情命令测试"""

    def test_cli_task_show_success(self):
        """测试：CLI显示任务详情"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            create_result = cli.run(["task", "create", "--name", "详情测试", "--domain", "AT_支付域"])
            task_id = create_result.task_id

            # 显示详情
            result = cli.run(["task", "show", "--id", task_id])

            assert result.success == True
            assert "详情测试" in result.output
            assert "AT_支付域" in result.output

    def test_cli_task_show_not_found(self):
        """测试：CLI显示不存在任务"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            result = cli.run(["task", "show", "--id", "nonexistent"])

            assert result.success == False
            assert "不存在" in result.error


class TestCliStatus:
    """CLI状态命令测试"""

    def test_cli_status_all(self):
        """测试：CLI全局状态"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            result = cli.run(["status", "--all"])

            assert result.success == True
            assert "任务" in result.output

    def test_cli_status_task(self):
        """测试：CLI指定任务状态"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            create_result = cli.run(["task", "create", "--name", "状态测试", "--domain", "AT_支付域"])
            task_id = create_result.task_id

            result = cli.run(["status", "--task", task_id])

            assert result.success == True


class TestCliRuntime:
    """CLI runtime 命令测试"""

    def test_cli_runtime_init_success(self):
        """测试：runtime init 成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            result = cli.run(["runtime", "init"])

            assert result.success == True
            assert "Runtime 初始化完成" in result.output

    def test_cli_runtime_start_success(self):
        """测试：runtime start 成功"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import SessionIndex

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "start_worker",
                    lambda task, base_branch="HEAD": SessionIndex(
                        task_id=task.task_id,
                        session_id="sess-123",
                        worktree=f"{tmpdir}/.worktrees/{task.task_id}",
                        status="running",
                        owner_role=task.owner_role,
                        task_type=task.task_type,
                        prompt=task.prompt,
                        priority=task.priority,
                        write_paths=task.write_paths,
                        protocol_refs=task.protocol_refs,
                        design_refs=task.design_refs,
                    ),
                )

                result = cli.run([
                    "runtime", "start",
                    "--task-id", "impl_auth_controller",
                    "--prompt", "实现 AuthController",
                    "--write-path", "src/controllers/AuthController.java",
                    "--protocol-ref", "auth_api@v2",
                ])

            assert result.success == True
            assert "sess-123" in result.output
            assert "impl_auth_controller" in result.output

    def test_cli_runtime_start_from_task_graph_file_success(self):
        """测试：runtime start 支持从 task graph 文件读取任务"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import SessionIndex, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)
            graph_file = f"{tmpdir}/task-graph.json"

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "load_task_graph",
                    lambda path: [
                        WorkerTaskSpec(
                            task_id="impl_auth_controller",
                            prompt="实现 AuthController",
                            owner_role="backend-agent",
                            task_type="ImplementTask",
                            write_paths=["src/controllers/AuthController.java"],
                            protocol_refs=["auth_api@v2"],
                        )
                    ],
                )
                captured = {}

                def _init(tasks):
                    captured["initialized"] = [task.task_id for task in tasks]

                mp.setattr(cli.runtime_manager, "initialize_task_graph", _init)
                mp.setattr(
                    cli.runtime_manager,
                    "start_worker",
                    lambda task, base_branch="HEAD": SessionIndex(
                        task_id=task.task_id,
                        session_id="sess-456",
                        worktree=f"{tmpdir}/.worktrees/{task.task_id}",
                        status="running",
                        owner_role=task.owner_role,
                        task_type=task.task_type,
                        prompt=task.prompt,
                        priority=task.priority,
                        write_paths=task.write_paths,
                        protocol_refs=task.protocol_refs,
                        design_refs=task.design_refs,
                    ),
                )

                result = cli.run([
                    "runtime", "start",
                    "--task-id", "impl_auth_controller",
                    "--task-graph-file", graph_file,
                ])

            assert result.success == True
            assert "sess-456" in result.output
            assert graph_file in result.output
            assert captured["initialized"] == ["impl_auth_controller"]

    def test_cli_runtime_start_from_task_graph_missing_task(self):
        """测试：task graph 中缺少指定任务时返回错误"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "load_task_graph",
                    lambda path: [WorkerTaskSpec(task_id="other_task", prompt="其他任务")],
                )
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)

                result = cli.run([
                    "runtime", "start",
                    "--task-id", "missing_task",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                ])

            assert result.success == False
            assert "task graph 中不存在任务" in result.error

    def test_cli_runtime_start_invalid_task_graph_returns_error(self):
        """测试：非法 task graph 返回错误"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import TaskGraphValidationError

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "load_task_graph",
                    lambda path: (_ for _ in ()).throw(TaskGraphValidationError("task graph 必须包含非空 tasks 数组")),
                )

                result = cli.run([
                    "runtime", "start",
                    "--task-id", "impl_auth_controller",
                    "--task-graph-file", f"{tmpdir}/invalid-task-graph.json",
                ])

            assert result.success == False
            assert "task graph 必须包含非空 tasks 数组" in result.error

    def test_cli_runtime_status_success(self):
        """测试：runtime status 成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "get_runtime_status",
                    lambda: {
                        "repo_path": tmpdir,
                        "active_agents": 1,
                        "queued_tasks": 2,
                        "completed_tasks": 3,
                        "failed_tasks": 0,
                        "intervention_required": False,
                        "running_tasks": ["impl_auth_controller"],
                    },
                )
                mp.setattr(
                    cli.runtime_manager,
                    "list_session_indexes",
                    lambda: [{"task_id": "impl_auth_controller"}],
                )

                result = cli.run(["runtime", "status"])

            assert result.success == True
            assert "Active Agents: 1" in result.output
            assert "Intervention Required: False" in result.output
            assert "impl_auth_controller" in result.output

    def test_cli_runtime_plan_success(self):
        """测试：runtime plan 成功"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import RuntimeReasonCode
        from claudeflow.runtime.driver_base import RuntimeTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "load_task_graph", lambda path: [])
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "get_dispatch_plan",
                    lambda executor_type="claude": {
                        "runnable": [RuntimeTaskSpec(task_id="task_a", phase_id="phase-1", prompt="实现A", priority="high", executor_type="claude")],
                        "blocked": [
                            {
                                "task_id": "task_b",
                                "priority": "medium",
                                "reason_code": RuntimeReasonCode.WAITING_DEPENDENCY,
                                "reason": "等待依赖完成: task_a(running)",
                            }
                        ],
                        "running": [
                            {
                                "task_id": "task_c",
                                "priority": "low",
                                "reason_code": RuntimeReasonCode.SESSION_RUNNING,
                                "reason": "任务已有运行中的会话",
                            }
                        ],
                    },
                )

                result = cli.run([
                    "runtime", "plan",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                ])

            assert result.success == True
            assert "Runnable: 1" in result.output
            assert f"code={RuntimeReasonCode.WAITING_DEPENDENCY}" in result.output
            assert f"code={RuntimeReasonCode.SESSION_RUNNING}" in result.output

    def test_cli_runtime_plan_json_success(self):
        """测试：runtime plan 支持 JSON 输出"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "load_task_graph", lambda path: [])
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "get_dispatch_plan",
                    lambda executor_type="claude": {
                        "runnable": [],
                        "blocked": [{"task_id": "task_b", "priority": "medium", "reason_code": "waiting_dependency", "reason": "等待依赖完成"}],
                        "running": [],
                    },
                )

                result = cli.run([
                    "runtime", "plan",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                    "--json",
                ])

            payload = json.loads(result.output)
            assert result.success == True
            assert payload["blocked"][0]["reason_code"] == "waiting_dependency"

    def test_cli_runtime_show_success(self):
        """测试：runtime show 成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "get_session_index",
                    lambda task_id: {
                        "task_id": task_id,
                        "session_id": "sess-123",
                        "status": "running",
                        "worktree": f"{tmpdir}/.worktrees/{task_id}",
                        "owner_role": "backend-agent",
                        "task_type": "ImplementTask",
                        "write_paths": ["src/controllers/AuthController.java"],
                        "protocol_refs": ["auth_api@v2"],
                        "design_refs": ["architecture@v2"],
                        "summary": "进行中",
                    },
                )

                result = cli.run(["runtime", "show", "--task-id", "impl_auth_controller"])

            assert result.success == True
            assert "sess-123" in result.output
            assert "backend-agent" in result.output
            assert "进行中" in result.output

    def test_cli_runtime_show_not_found(self):
        """测试：runtime show 不存在任务"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "get_session_index",
                    lambda task_id: (_ for _ in ()).throw(Exception(f"未找到任务会话索引: {task_id}")),
                )

                result = cli.run(["runtime", "show", "--task-id", "missing_task"])

            assert result.success == False
            assert "未找到任务会话索引" in result.error

    def test_cli_runtime_explain_success(self):
        """测试：runtime explain 成功"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import RuntimeReasonCode

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "load_task_graph", lambda path: [])
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "explain_task",
                    lambda task_id: {
                        "task_id": task_id,
                        "state": "blocked",
                        "priority": "high",
                        "reason_code": RuntimeReasonCode.WAITING_DEPENDENCY,
                        "reason": "等待依赖完成: task_a(running)",
                        "dependencies": ["task_a"],
                        "executor_type": "",
                        "driver_name": "",
                    },
                )

                result = cli.run([
                    "runtime", "explain",
                    "--task-id", "task_b",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                ])

            assert result.success == True
            assert "blocked" in result.output
            assert RuntimeReasonCode.WAITING_DEPENDENCY in result.output
            assert "等待依赖完成" in result.output

    def test_cli_runtime_explain_json_success(self):
        """测试：runtime explain 支持 JSON 输出"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "load_task_graph", lambda path: [])
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "explain_task",
                    lambda task_id: {
                        "task_id": task_id,
                        "state": "blocked",
                        "priority": "high",
                        "reason_code": "waiting_dependency",
                        "reason": "等待依赖完成",
                        "dependencies": ["task_a"],
                        "executor_type": "",
                        "driver_name": "",
                    },
                )

                result = cli.run([
                    "runtime", "explain",
                    "--task-id", "task_b",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                    "--json",
                ])

            payload = json.loads(result.output)
            assert result.success == True
            assert payload["reason_code"] == "waiting_dependency"

    def test_cli_runtime_complete_success(self):
        """测试：runtime complete 成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "complete_worker",
                    lambda task_id, summary="", changed_files=None, tests=None: {
                        "task_id": task_id,
                        "status": "completed",
                    },
                )
                mp.setattr(
                    cli.runtime_manager,
                    "get_runnable_tasks",
                    lambda: [],
                )

                result = cli.run([
                    "runtime", "complete",
                    "--task-id", "impl_auth_controller",
                    "--summary", "已实现",
                    "--changed-file", "src/controllers/AuthController.java",
                    "--test-status", "passed",
                    "--test-count", "3",
                ])

            assert result.success == True
            assert "completed" in result.output
            assert "已实现" in result.output
            assert "新可运行任务: -" in result.output

    def test_cli_runtime_complete_reports_new_runnable_tasks(self):
        """测试：runtime complete 后返回新 runnable 节点"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "complete_worker",
                    lambda task_id, summary="", changed_files=None, tests=None: {
                        "task_id": task_id,
                        "status": "completed",
                    },
                )
                mp.setattr(
                    cli.runtime_manager,
                    "get_runnable_tasks",
                    lambda: [WorkerTaskSpec(task_id="task_b", prompt="实现B")],
                )

                result = cli.run([
                    "runtime", "complete",
                    "--task-id", "task_a",
                ])

            assert result.success == True
            assert "task_b" in result.output

    def test_cli_runtime_fail_success(self):
        """测试：runtime fail 成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "fail_worker",
                    lambda task_id, reason: {
                        "task_id": task_id,
                        "status": "failed",
                        "summary": reason,
                    },
                )

                result = cli.run([
                    "runtime", "fail",
                    "--task-id", "impl_auth_controller",
                    "--reason", "测试失败，需要人工介入",
                ])

            assert result.success == True
            assert "failed" in result.output
            assert "测试失败，需要人工介入" in result.output

    def test_cli_runtime_dispatch_success(self):
        """测试：runtime dispatch 成功"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import RuntimeReasonCode

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "load_task_graph", lambda path: [])
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "dispatch_runnable_tasks",
                    lambda base_branch="HEAD", limit=None, max_concurrent=None, executor_type="claude": {
                        "runnable_count": 2,
                        "blocked_count": 1,
                        "active_agents": 1,
                        "available_slots": 1,
                        "max_concurrent": max_concurrent,
                        "started": [
                            {"task_id": "task_a", "session_id": "sess-a", "priority": "high", "executor_type": "claude", "driver_name": "claude-driver"},
                            {"task_id": "task_b", "session_id": "sess-b", "priority": "medium", "executor_type": "claude", "driver_name": "claude-driver"},
                        ],
                        "skipped": [],
                        "blocked": [
                            {
                                "task_id": "task_c",
                                "priority": "low",
                                "reason_code": RuntimeReasonCode.WAITING_DEPENDENCY,
                                "reason": "等待依赖完成: task_b(running)",
                            },
                        ],
                    },
                )

                result = cli.run([
                    "runtime", "dispatch",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                    "--max-concurrent", "2",
                ])

            assert result.success == True
            assert "Started: 2" in result.output
            assert "Blocked Tasks: 1" in result.output
            assert "Max Concurrent: 2" in result.output
            assert "Available Slots: 1" in result.output
            assert "task_a" in result.output
            assert "sess-b" in result.output
            assert f"code={RuntimeReasonCode.WAITING_DEPENDENCY}" in result.output
            assert "等待依赖完成" in result.output

    def test_cli_runtime_dispatch_json_success(self):
        """测试：runtime dispatch 支持 JSON 输出"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(cli.runtime_manager, "load_task_graph", lambda path: [])
                mp.setattr(cli.runtime_manager, "initialize_task_graph", lambda tasks: None)
                mp.setattr(
                    cli.runtime_manager,
                    "dispatch_runnable_tasks",
                    lambda base_branch="HEAD", limit=None, max_concurrent=None, executor_type="claude": {
                        "runnable_count": 1,
                        "blocked_count": 1,
                        "active_agents": 0,
                        "available_slots": 1,
                        "max_concurrent": max_concurrent,
                        "started": [{"task_id": "task_a", "session_id": "sess-a", "priority": "high", "executor_type": "claude", "driver_name": "claude-driver"}],
                        "skipped": [],
                        "blocked": [{"task_id": "task_b", "priority": "medium", "reason_code": "waiting_dependency", "reason": "等待依赖完成"}],
                    },
                )

                result = cli.run([
                    "runtime", "dispatch",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                    "--json",
                ])

            payload = json.loads(result.output)
            assert result.success == True
            assert payload["started"][0]["task_id"] == "task_a"
            assert payload["blocked"][0]["reason_code"] == "waiting_dependency"

    def test_cli_runtime_dispatch_invalid_task_graph(self):
        """测试：runtime dispatch 非法 task graph"""
        from claudeflow.cli import CliApp
        from claudeflow.runtime.manager import TaskGraphValidationError

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "load_task_graph",
                    lambda path: (_ for _ in ()).throw(TaskGraphValidationError("task_id 重复: task_a")),
                )

                result = cli.run([
                    "runtime", "dispatch",
                    "--task-graph-file", f"{tmpdir}/task-graph.json",
                ])

            assert result.success == False
            assert "task_id 重复" in result.error

    def test_cli_runtime_dispatch_governance_entry_success(self):
        """T106: 测试 runtime dispatch 治理入口成功"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    cli.runtime_manager,
                    "dispatch_from_governance",
                    lambda governance_root, phase_id, base_branch="HEAD", limit=None: {
                        "started": [{"task_id": "T101", "session_id": "sess-101", "executor_type": "claude", "driver_name": "claude-driver", "priority": "high"}],
                        "skipped": [],
                        "blocked": [],
                        "runnable_count": 1,
                        "blocked_count": 0,
                        "active_agents": 1,
                        "available_slots": 3,
                        "max_concurrent": None,
                    },
                )

                result = cli.run([
                    "runtime", "dispatch",
                    "--governance-root", "/path/to/.super-dev",
                    "--phase-id", "phase-1",
                ])

            assert result.success == True
            assert "Started: 1" in result.output
            assert "T101" in result.output
            assert "claude-driver" in result.output

    def test_cli_runtime_dispatch_requires_entry_params(self):
        """T106: 测试 runtime dispatch 必须指定入口参数"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir, repo_path=tmpdir)

            result = cli.run([
                "runtime", "dispatch",
            ])

            assert result.success == False
            assert "必须指定" in result.error


class TestCliResult:
    """CLI结果对象测试"""

    def test_cli_result_has_required_fields(self):
        """测试：CLI结果包含必需字段"""
        from claudeflow.cli import CliResult

        result = CliResult(success=True, output="测试输出")

        assert hasattr(result, "success")
        assert hasattr(result, "output")

    def test_cli_result_error_field(self):
        """测试：CLI结果错误字段"""
        from claudeflow.cli import CliResult

        result = CliResult(success=False, error="测试错误")

        assert result.error == "测试错误"


class TestCliApp:
    """CLI应用测试"""

    def test_cli_app_initialization(self):
        """测试：CLI应用初始化"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            assert cli.tasks_dir == tmpdir

    def test_cli_app_has_task_manager(self):
        """测试：CLI应用包含任务管理器"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            assert hasattr(cli, "task_manager")

    def test_cli_app_has_scheduler(self):
        """测试：CLI应用包含调度器"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            assert hasattr(cli, "scheduler")
