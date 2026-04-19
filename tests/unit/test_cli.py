"""CLI接口模块单元测试

CLI命令：task create/list/show、status --all/--task
"""

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