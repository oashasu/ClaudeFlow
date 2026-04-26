"""ClaudeFlow CLI 入口。"""

import argparse
import json
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from claudeflow.runtime import RuntimeManager, TaskGraphValidationError, WorkerTaskSpec
from claudeflow.workflow import Scheduler, TaskManager, TaskNotFoundError, TaskStatus


@dataclass
class CliResult:
    """CLI命令执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    task_id: Optional[str] = None


class CliApp:
    """CLI应用"""

    def __init__(self, tasks_dir: str, repo_path: Optional[str] = None):
        """
        初始化CLI应用

        Args:
            tasks_dir: 任务存储目录
            repo_path: 仓库根目录
        """
        self.tasks_dir = tasks_dir
        self.repo_path = repo_path or os.getcwd()
        self.task_manager = TaskManager(tasks_dir=tasks_dir)
        self.scheduler = Scheduler(task_manager=self.task_manager)
        self.runtime_manager = RuntimeManager(repo_path=self.repo_path)

    def run(self, args: List[str]) -> CliResult:
        """
        执行CLI命令

        Args:
            args: 命令行参数列表

        Returns:
            执行结果
        """
        parser = self._create_parser()

        try:
            parsed = parser.parse_args(args)
            return self._handle_command(parsed)
        except SystemExit:
            # argparse解析失败
            return CliResult(success=False, error="参数解析失败")

    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令解析器"""
        parser = argparse.ArgumentParser(prog="claudeflow")
        subparsers = parser.add_subparsers(dest="command")

        # task命令
        task_parser = subparsers.add_parser("task")
        task_subparsers = task_parser.add_subparsers(dest="task_command")

        # task create
        create_parser = task_subparsers.add_parser("create")
        create_parser.add_argument("--name", required=False)
        create_parser.add_argument("--domain", required=False)
        create_parser.add_argument("--priority", default="中")
        create_parser.add_argument("--description", default=None)

        # task list
        list_parser = task_subparsers.add_parser("list")
        list_parser.add_argument("--status", default=None)
        list_parser.add_argument("--limit", type=int, default=None)

        # task show
        show_parser = task_subparsers.add_parser("show")
        show_parser.add_argument("--id", required=True)

        # status命令
        status_parser = subparsers.add_parser("status")
        status_parser.add_argument("--all", action="store_true")
        status_parser.add_argument("--task", default=None)

        # runtime命令
        runtime_parser = subparsers.add_parser("runtime")
        runtime_subparsers = runtime_parser.add_subparsers(dest="runtime_command")

        # runtime init
        runtime_subparsers.add_parser("init")

        # runtime status
        runtime_subparsers.add_parser("status")

        # runtime plan
        plan_runtime_parser = runtime_subparsers.add_parser("plan")
        plan_runtime_parser.add_argument("--task-graph-file", default=None)
        plan_runtime_parser.add_argument("--json", action="store_true")

        # runtime show
        show_runtime_parser = runtime_subparsers.add_parser("show")
        show_runtime_parser.add_argument("--task-id", required=True)

        # runtime explain
        explain_runtime_parser = runtime_subparsers.add_parser("explain")
        explain_runtime_parser.add_argument("--task-id", required=True)
        explain_runtime_parser.add_argument("--task-graph-file", default=None)
        explain_runtime_parser.add_argument("--json", action="store_true")

        # runtime start
        start_parser = runtime_subparsers.add_parser("start")
        start_parser.add_argument("--task-id", required=True)
        start_parser.add_argument("--prompt", required=False)
        start_parser.add_argument("--owner-role", default="worker-agent")
        start_parser.add_argument("--task-type", default="ImplementTask")
        start_parser.add_argument("--base-branch", default="HEAD")
        start_parser.add_argument("--task-graph-file", default=None)
        start_parser.add_argument("--write-path", action="append", default=[])
        start_parser.add_argument("--read-path", action="append", default=[])
        start_parser.add_argument("--protocol-ref", action="append", default=[])
        start_parser.add_argument("--design-ref", action="append", default=[])

        # runtime complete
        complete_parser = runtime_subparsers.add_parser("complete")
        complete_parser.add_argument("--task-id", required=True)
        complete_parser.add_argument("--summary", default="")
        complete_parser.add_argument("--changed-file", action="append", default=[])
        complete_parser.add_argument("--test-status", default=None)
        complete_parser.add_argument("--test-count", type=int, default=None)

        # runtime fail
        fail_parser = runtime_subparsers.add_parser("fail")
        fail_parser.add_argument("--task-id", required=True)
        fail_parser.add_argument("--reason", required=True)

        # runtime dispatch
        dispatch_parser = runtime_subparsers.add_parser("dispatch")
        dispatch_parser.add_argument("--task-graph-file", required=False)
        dispatch_parser.add_argument("--base-branch", default="HEAD")
        dispatch_parser.add_argument("--limit", type=int, default=None)
        dispatch_parser.add_argument("--max-concurrent", type=int, default=None)
        dispatch_parser.add_argument("--executor-type", default="claude")
        dispatch_parser.add_argument("--json", action="store_true")
        # T106: 治理入口参数
        dispatch_parser.add_argument("--governance-root", default=None)
        dispatch_parser.add_argument("--phase-id", default=None)

        return parser

    def _handle_command(self, parsed: argparse.Namespace) -> CliResult:
        """处理解析后的命令"""
        handlers: Dict[str, Callable[[argparse.Namespace], CliResult]] = {
            "task": self._handle_task_command,
            "status": self._handle_status_command,
            "runtime": self._handle_runtime_command,
        }
        handler = handlers.get(parsed.command)
        if handler is None:
            return CliResult(success=False, error="未知命令")
        return handler(parsed)

    def _handle_task_command(self, parsed: argparse.Namespace) -> CliResult:
        """处理task命令"""
        handlers: Dict[str, Callable[[argparse.Namespace], CliResult]] = {
            "create": self._handle_task_create,
            "list": self._handle_task_list,
            "show": self._handle_task_show,
        }
        handler = handlers.get(parsed.task_command)
        if handler is None:
            return CliResult(success=False, error="未知task命令")
        return handler(parsed)

    def _handle_task_create(self, parsed: argparse.Namespace) -> CliResult:
        """处理task create命令"""
        if not parsed.name:
            return CliResult(success=False, error="缺少必需参数: --name")

        if not parsed.domain:
            return CliResult(success=False, error="缺少必需参数: --domain")

        try:
            task = self.task_manager.create_task(
                name=parsed.name,
                domain=parsed.domain,
                priority=parsed.priority,
                description=parsed.description
            )

            output = f"任务创建成功:\n  任务ID: {task.id}\n  名称: {task.name}\n  领域: {task.domain}"
            return CliResult(success=True, output=output, task_id=task.id)

        except Exception as e:
            return CliResult(success=False, error=str(e))

    def _handle_task_list(self, parsed: argparse.Namespace) -> CliResult:
        """处理task list命令"""
        status = None
        if parsed.status:
            try:
                status = TaskStatus(parsed.status)
            except ValueError:
                pass

        tasks = self.task_manager.list_tasks(status=status, limit=parsed.limit)

        if not tasks:
            return CliResult(success=True, output="无任务")

        lines = ["任务列表:"]
        for task in tasks:
            lines.append(f"  {task.id} | {task.name} | {task.domain} | {task.status}")

        return CliResult(success=True, output="\n".join(lines))

    def _handle_task_show(self, parsed: argparse.Namespace) -> CliResult:
        """处理task show命令"""
        try:
            task = self.task_manager.get_task(parsed.id)

            lines = [
                f"任务详情: {task.id}",
                f"  名称: {task.name}",
                f"  领域: {task.domain}",
                f"  状态: {task.status}",
                f"  优先级: {task.priority}",
                f"  创建时间: {task.created_at}",
            ]

            if task.assigned_employee:
                lines.append(f"  分配员工: {task.assigned_employee}")

            if task.description:
                lines.append(f"  描述: {task.description}")

            return CliResult(success=True, output="\n".join(lines))

        except TaskNotFoundError:
            return CliResult(success=False, error=f"任务不存在: {parsed.id}")

    def _handle_status_command(self, parsed: argparse.Namespace) -> CliResult:
        """处理status命令"""
        if parsed.all:
            return self._handle_status_all()
        elif parsed.task:
            return self._handle_status_task(parsed.task)
        else:
            return CliResult(success=False, error="需要指定 --all 或 --task")

    def _handle_status_all(self) -> CliResult:
        """处理status --all命令"""
        all_tasks = self.task_manager.list_tasks()

        pending_count = len([t for t in all_tasks if t.status == "pending"])
        running_count = len([t for t in all_tasks if t.status == "running"])
        completed_count = len([t for t in all_tasks if t.status == "completed"])

        lines = [
            "ClaudeFlow 系统状态:",
            f"  任务总数: {len(all_tasks)}",
            f"  待执行: {pending_count}",
            f"  执行中: {running_count}",
            f"  已完成: {completed_count}",
        ]

        return CliResult(success=True, output="\n".join(lines))

    def _handle_status_task(self, task_id: str) -> CliResult:
        """处理status --task命令"""
        try:
            task = self.task_manager.get_task(task_id)
            ctx = self.scheduler.get_task_context(task_id)

            lines = [
                f"任务状态: {task.id}",
                f"  整体状态: {task.status}",
                f"  当前阶段: {ctx['current_phase']}",
                f"  重试次数: {ctx['retry_count']}",
                f"  进度: {self.scheduler.get_progress(task_id)}%",
            ]

            return CliResult(success=True, output="\n".join(lines))

        except TaskNotFoundError:
            return CliResult(success=False, error=f"任务不存在: {task_id}")

    def _handle_runtime_command(self, parsed: argparse.Namespace) -> CliResult:
        """处理runtime命令"""
        handlers: Dict[str, Callable[[argparse.Namespace], CliResult]] = {
            "init": lambda _: self._handle_runtime_init(),
            "status": lambda _: self._handle_runtime_status(),
            "plan": self._handle_runtime_plan,
            "show": self._handle_runtime_show,
            "explain": self._handle_runtime_explain,
            "start": self._handle_runtime_start,
            "complete": self._handle_runtime_complete,
            "fail": self._handle_runtime_fail,
            "dispatch": self._handle_runtime_dispatch,
        }
        handler = handlers.get(parsed.runtime_command)
        if handler is None:
            return CliResult(success=False, error="未知runtime命令")
        return handler(parsed)

    def _load_runtime_tasks(self, task_graph_file: str) -> List[WorkerTaskSpec]:
        """读取并初始化 runtime task graph。"""
        tasks = self.runtime_manager.load_task_graph(task_graph_file)
        self.runtime_manager.initialize_task_graph(tasks)
        return tasks

    @staticmethod
    def _build_runtime_task(parsed: argparse.Namespace) -> WorkerTaskSpec:
        """从 CLI 参数构造单任务 worker 定义。"""
        return WorkerTaskSpec(
            task_id=parsed.task_id,
            prompt=parsed.prompt,
            owner_role=parsed.owner_role,
            task_type=parsed.task_type,
            read_paths=list(parsed.read_path or []),
            write_paths=list(parsed.write_path or []),
            protocol_refs=list(parsed.protocol_ref or []),
            design_refs=list(parsed.design_ref or []),
        )

    @staticmethod
    def _append_task_lines(lines: List[str], header: str, task_ids: List[str]) -> None:
        """向输出中追加任务列表。"""
        lines.append(header)
        for task_id in task_ids:
            lines.append(f"    - {task_id}")

    @staticmethod
    def _append_labeled_lines(lines: List[str], header: str, items: List[str]) -> None:
        """向输出中追加说明性列表。"""
        lines.append(header)
        for item in items:
            lines.append(f"    - {item}")

    @staticmethod
    def _json_result(payload: Dict[str, object], task_id: Optional[str] = None) -> CliResult:
        """构造 JSON 输出结果。"""
        return CliResult(
            success=True,
            output=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            task_id=task_id,
        )

    def _handle_runtime_init(self) -> CliResult:
        """初始化 runtime 目录。"""
        self.runtime_manager.ensure_layout()
        return CliResult(
            success=True,
            output=f"Runtime 初始化完成: {self.runtime_manager.runtime_dir}"
        )

    def _handle_runtime_status(self) -> CliResult:
        """查看 runtime 总览状态。"""
        status = self.runtime_manager.get_runtime_status()
        sessions = self.runtime_manager.list_session_indexes()

        lines = [
            "ClaudeFlow Runtime 状态:",
            f"  Repo: {status['repo_path']}",
            f"  Active Agents: {status['active_agents']}",
            f"  Queued Tasks: {status['queued_tasks']}",
            f"  Completed Tasks: {status['completed_tasks']}",
            f"  Failed Tasks: {status['failed_tasks']}",
            f"  Intervention Required: {status['intervention_required']}",
            f"  Running Tasks: {', '.join(status['running_tasks']) if status['running_tasks'] else '-'}",
            f"  Session Indexes: {len(sessions)}",
        ]
        return CliResult(success=True, output="\n".join(lines))

    def _handle_runtime_plan(self, parsed: argparse.Namespace) -> CliResult:
        """查看当前调度计划。"""
        if parsed.task_graph_file:
            try:
                self._load_runtime_tasks(parsed.task_graph_file)
            except TaskGraphValidationError as exc:
                return CliResult(success=False, error=str(exc))

        # T106: executor_type 参数
        executor_type = getattr(parsed, "executor_type", "claude")
        plan = self.runtime_manager.get_dispatch_plan(executor_type=executor_type)
        runnable = plan["runnable"]
        blocked = plan["blocked"]
        running = plan["running"]

        if parsed.json:
            payload = {
                "runnable": [
                    {
                        "task_id": task.task_id,
                        "priority": task.priority,
                        "executor_type": task.executor_type,  # T106: 宿主字段
                        "phase_id": task.phase_id,  # T109: RuntimeTaskSpec 字段
                    }
                    for task in runnable
                ],
                "blocked": blocked,
                "running": running,
            }
            return self._json_result(payload)

        lines = [
            "Runtime 调度计划:",
            f"  Runnable: {len(runnable)}",
            f"  Blocked: {len(blocked)}",
            f"  Running: {len(running)}",
        ]
        if runnable:
            self._append_labeled_lines(
                lines,
                "  可运行任务:",
                [f"{task.task_id} [priority={task.priority}, executor={task.executor_type}]" for task in runnable],
            )
        if blocked:
            self._append_labeled_lines(
                lines,
                "  阻塞任务:",
                [
                    f"{item['task_id']} [priority={item['priority']}, code={item['reason_code']}]: {item['reason']}"
                    for item in blocked
                ],
            )
        if running:
            self._append_labeled_lines(
                lines,
                "  运行中任务:",
                [
                    f"{item['task_id']} [priority={item['priority']}, code={item['reason_code']}]: {item['reason']}"
                    for item in running
                ],
            )
        return CliResult(success=True, output="\n".join(lines))

    def _handle_runtime_show(self, parsed: argparse.Namespace) -> CliResult:
        """查看单任务 runtime 会话详情。"""
        try:
            index = self.runtime_manager.get_session_index(parsed.task_id)
        except Exception as exc:
            return CliResult(success=False, error=str(exc))

        lines = [
            f"Runtime 任务详情: {index['task_id']}",
            f"  Session ID: {index['session_id']}",
            f"  状态: {index['status']}",
            f"  Worktree: {index['worktree']}",
            f"  Owner Role: {index['owner_role']}",
            f"  Task Type: {index['task_type']}",
            f"  Write Paths: {', '.join(index['write_paths']) if index['write_paths'] else '-'}",
            f"  Protocol Refs: {', '.join(index['protocol_refs']) if index['protocol_refs'] else '-'}",
            f"  Design Refs: {', '.join(index['design_refs']) if index['design_refs'] else '-'}",
            f"  Summary: {index['summary'] or '-'}",
        ]
        return CliResult(success=True, output="\n".join(lines), task_id=index["task_id"])

    def _handle_runtime_explain(self, parsed: argparse.Namespace) -> CliResult:
        """解释单任务当前为何可运行或被阻塞。"""
        if parsed.task_graph_file:
            try:
                self._load_runtime_tasks(parsed.task_graph_file)
            except TaskGraphValidationError as exc:
                return CliResult(success=False, error=str(exc))

        try:
            explanation = self.runtime_manager.explain_task(parsed.task_id)
        except Exception as exc:
            return CliResult(success=False, error=str(exc))

        if parsed.json:
            return self._json_result(explanation, task_id=explanation["task_id"])

        # T106: 输出宿主字段 executor_type / driver_name
        lines = [
            f"Runtime 任务解释: {explanation['task_id']}",
            f"  State: {explanation['state']}",
            f"  Priority: {explanation['priority']}",
            f"  Reason Code: {explanation['reason_code']}",
            f"  Reason: {explanation['reason']}",
            f"  Dependencies: {', '.join(explanation['dependencies']) if explanation['dependencies'] else '-'}",
            f"  Executor Type: {explanation.get('executor_type', '-')}",
            f"  Driver Name: {explanation.get('driver_name', '-')}",
        ]
        return CliResult(success=True, output="\n".join(lines), task_id=explanation["task_id"])

    def _handle_runtime_start(self, parsed: argparse.Namespace) -> CliResult:
        """启动 runtime worker。"""
        if parsed.task_graph_file:
            try:
                tasks = self._load_runtime_tasks(parsed.task_graph_file)
            except TaskGraphValidationError as exc:
                return CliResult(success=False, error=str(exc))
            task = next((item for item in tasks if item.task_id == parsed.task_id), None)
            if task is None:
                return CliResult(
                    success=False,
                    error=f"task graph 中不存在任务: {parsed.task_id}",
                )
        else:
            if not parsed.prompt:
                return CliResult(success=False, error="缺少必需参数: --prompt")
            task = self._build_runtime_task(parsed)
            self.runtime_manager.initialize_task_graph([task])

        index = self.runtime_manager.start_worker(task, base_branch=parsed.base_branch)

        lines = [
            "Runtime Worker 已启动:",
            f"  任务ID: {index.task_id}",
            f"  Session ID: {index.session_id}",
            f"  Worktree: {index.worktree}",
            f"  状态: {index.status}",
        ]
        if parsed.task_graph_file:
            lines.append(f"  Task Graph: {parsed.task_graph_file}")
        return CliResult(success=True, output="\n".join(lines), task_id=index.task_id)

    def _handle_runtime_complete(self, parsed: argparse.Namespace) -> CliResult:
        """完成 runtime worker。"""
        tests = {}
        if parsed.test_status is not None:
            tests["status"] = parsed.test_status
        if parsed.test_count is not None:
            tests["count"] = parsed.test_count

        index = self.runtime_manager.complete_worker(
            parsed.task_id,
            summary=parsed.summary,
            changed_files=list(parsed.changed_file or []),
            tests=tests,
        )
        next_tasks = self.runtime_manager.get_runnable_tasks()

        lines = [
            "Runtime Worker 已完成:",
            f"  任务ID: {index['task_id']}",
            f"  状态: {index['status']}",
        ]
        if parsed.summary:
            lines.append(f"  摘要: {parsed.summary}")
        if next_tasks:
            self._append_task_lines(
                lines,
                "  新可运行任务:",
                [task.task_id for task in next_tasks],
            )
        else:
            lines.append("  新可运行任务: -")
        return CliResult(success=True, output="\n".join(lines), task_id=parsed.task_id)

    def _handle_runtime_fail(self, parsed: argparse.Namespace) -> CliResult:
        """标记 runtime worker 失败。"""
        index = self.runtime_manager.fail_worker(parsed.task_id, parsed.reason)

        lines = [
            "Runtime Worker 已失败:",
            f"  任务ID: {index['task_id']}",
            f"  状态: {index['status']}",
            f"  原因: {parsed.reason}",
        ]
        return CliResult(success=True, output="\n".join(lines), task_id=parsed.task_id)

    def _handle_runtime_dispatch(self, parsed: argparse.Namespace) -> CliResult:
        """自动启动当前可运行节点。

        T106: 支持两种入口:
        1. 传统 task-graph-file 入口
        2. 治理入口 governance-root + phase-id
        """
        # T106: 检查治理入口参数
        if parsed.governance_root and parsed.phase_id:
            # 治理入口派发
            try:
                result = self.runtime_manager.dispatch_from_governance(
                    governance_root=parsed.governance_root,
                    phase_id=parsed.phase_id,
                    base_branch=parsed.base_branch,
                    limit=parsed.limit,
                )
            except Exception as exc:
                return CliResult(success=False, error=str(exc))
        elif parsed.task_graph_file:
            # 传统 task-graph 入口
            try:
                tasks = self._load_runtime_tasks(parsed.task_graph_file)
            except TaskGraphValidationError as exc:
                return CliResult(success=False, error=str(exc))
            executor_type = getattr(parsed, "executor_type", "claude")
            result = self.runtime_manager.dispatch_runnable_tasks(
                base_branch=parsed.base_branch,
                limit=parsed.limit,
                max_concurrent=parsed.max_concurrent,
                executor_type=executor_type,
            )
        else:
            return CliResult(
                success=False,
                error="必须指定 --task-graph-file 或 --governance-root/--phase-id",
            )

        if parsed.json:
            payload = {
                "runnable_count": result["runnable_count"],
                "blocked_count": result["blocked_count"],
                "active_agents": result["active_agents"],
                "available_slots": result["available_slots"],
                "max_concurrent": result["max_concurrent"],
                "started": result["started"],
                "skipped": result["skipped"],
                "blocked": result["blocked"],
            }
            return self._json_result(payload)

        started = result["started"]
        skipped = result["skipped"]
        blocked = result["blocked"]
        lines = [
            "Runtime Dispatch 完成:",
            f"  Runnable Tasks: {result['runnable_count']}",
            f"  Blocked Tasks: {result['blocked_count']}",
            f"  Active Agents: {result['active_agents']}",
            f"  Available Slots: {result['available_slots']}",
            f"  Max Concurrent: {result['max_concurrent'] if result['max_concurrent'] is not None else '-'}",
            f"  Started: {len(started)}",
            f"  Skipped: {len(skipped)}",
        ]
        if started:
            lines.append("  已启动任务:")
            for item in started:
                # T106: 输出 executor_type 和 driver_name
                executor = item.get("executor_type", "-")
                driver = item.get("driver_name", "-")
                lines.append(
                    f"    - {item['task_id']} ({item['session_id']}, priority={item.get('priority', 'medium')}, executor={executor}, driver={driver})"
                )
        if skipped:
            lines.append("  已跳过任务:")
            for item in skipped:
                lines.append(
                    f"    - {item['task_id']} [{item.get('reason_code', 'runtime_skip')}]: {item['reason']}"
                )
        if blocked:
            self._append_labeled_lines(
                lines,
                "  当前不可运行任务:",
                [
                    f"{item['task_id']} [priority={item.get('priority', 'medium')}, code={item.get('reason_code', 'blocked')}]: {item['reason']}"
                    for item in blocked
                ],
            )

        return CliResult(success=True, output="\n".join(lines))


def main():
    """CLI入口函数"""
    import sys
    import os

    # 默认tasks目录
    tasks_dir = os.environ.get("CLAUDFLOW_TASKS_DIR", "./tasks")
    repo_path = os.environ.get("CLAUDFLOW_REPO_DIR", os.getcwd())

    cli = CliApp(tasks_dir=tasks_dir, repo_path=repo_path)
    result = cli.run(sys.argv[1:])

    if result.success:
        print(result.output)
    else:
        print(f"错误: {result.error}", file=sys.stderr)
        sys.exit(1)
