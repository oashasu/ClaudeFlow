"""CLI接口模块 - 命令行命令

V1核心功能：task create/list/show、status --all/--task
"""

import argparse
from dataclasses import dataclass
from typing import Optional, List, Any

from claudeflow.task_manager import TaskManager, TaskNotFoundError
from claudeflow.scheduler import Scheduler
from claudeflow.state_machine import TaskStatus


@dataclass
class CliResult:
    """CLI命令执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    task_id: Optional[str] = None


class CliApp:
    """CLI应用"""

    def __init__(self, tasks_dir: str):
        """
        初始化CLI应用

        Args:
            tasks_dir: 任务存储目录
        """
        self.tasks_dir = tasks_dir
        self.task_manager = TaskManager(tasks_dir=tasks_dir)
        self.scheduler = Scheduler(task_manager=self.task_manager)

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
        parser = argparse.ArgumentParser(prog="claudflow")
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

        return parser

    def _handle_command(self, parsed: argparse.Namespace) -> CliResult:
        """处理解析后的命令"""
        if parsed.command == "task":
            return self._handle_task_command(parsed)
        elif parsed.command == "status":
            return self._handle_status_command(parsed)
        else:
            return CliResult(success=False, error="未知命令")

    def _handle_task_command(self, parsed: argparse.Namespace) -> CliResult:
        """处理task命令"""
        if parsed.task_command == "create":
            return self._handle_task_create(parsed)
        elif parsed.task_command == "list":
            return self._handle_task_list(parsed)
        elif parsed.task_command == "show":
            return self._handle_task_show(parsed)
        else:
            return CliResult(success=False, error="未知task命令")

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


def main():
    """CLI入口函数"""
    import sys
    import os

    # 默认tasks目录
    tasks_dir = os.environ.get("CLAUDFLOW_TASKS_DIR", "./tasks")

    cli = CliApp(tasks_dir=tasks_dir)
    result = cli.run(sys.argv[1:])

    if result.success:
        print(result.output)
    else:
        print(f"错误: {result.error}", file=sys.stderr)
        sys.exit(1)